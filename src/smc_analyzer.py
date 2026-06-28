# src/smc_analyzer.py
import logging
import hashlib
from datetime import datetime

import pandas as pd

from src.config import (
    CONFLUENCE_THRESHOLD, HTF_BIAS_MIN_CANDLES, CONFLUENCE_WEIGHTS,
    CONFLUENCE_DECAY_START, CONFLUENCE_DECAY_RATE, FVG_MIN_ATR_MULTIPLE,
    FVG_MAX_AGE_CANDLES, FVG_MIN_DISPLACEMENT_BODY_RATIO, FVG_CLUSTER_MAX_GAP,
    FVG_PARTIAL_FILL_BONUS_RANGE, MIN_FVG_GAP_SIZE, MIN_FVG_GAP_SIZE_DEFAULT,
    ENTRY_SCORE_EXCELLENT, ENTRY_SCORE_GOOD, ENTRY_SCORE_MARGINAL, KILLZONE_RANGES
)

logger = logging.getLogger(__name__)

class SMCAnalyzer:
    """
    Smart Money Concepts (SMC) Analyzer.
    Upgraded with Institutional Confluence Architecture (HTF Bias, Liquidity Sweeps, OTE Zones, OBs).
    """

    @staticmethod
    def analyze_fvgs(candles):
        fvgs = []
        if len(candles) < 3: return fvgs

        for i in range(len(candles) - 2):
            c1, c2, c3 = candles[i], candles[i+1], candles[i+2]
            
            # 🟢 Bullish FVG
            if c3['low'] > c1['high'] and c2['close'] > c2['open']:
                fvgs.append({
                    'type': 'BULLISH_FVG', 'time': c2['time'], 'creation_index': i+2,
                    'top': c3['low'], 'bottom': c1['high'], 'gap_size': round(c3['low'] - c1['high'], 2)
                })
            # 🔴 Bearish FVG
            elif c3['high'] < c1['low'] and c2['close'] < c2['open']:
                fvgs.append({
                    'type': 'BEARISH_FVG', 'time': c2['time'], 'creation_index': i+2,
                    'top': c1['low'], 'bottom': c3['high'], 'gap_size': round(c1['low'] - c3['high'], 2)
                })
        return fvgs

    @staticmethod
    def _find_swing_points(candles, left=2, right=2):
        swings = []
        for i in range(left, len(candles) - right):
            window = candles[i-left : i+right+1]
            highs = [c['high'] for c in window]
            lows = [c['low'] for c in window]
            
            if candles[i]['high'] == max(highs):
                swings.append({'type': 'HIGH', 'index': i, 'price': candles[i]['high']})
            if candles[i]['low'] == min(lows):
                swings.append({'type': 'LOW', 'index': i, 'price': candles[i]['low']})
        return swings

    @staticmethod
    def determine_htf_bias(candles_up_to_now, htf_minutes=15):
        if not candles_up_to_now or len(candles_up_to_now) < HTF_BIAS_MIN_CANDLES: return "RANGING"
        try:
            df = pd.DataFrame(candles_up_to_now)
            df['datetime'] = pd.to_datetime(df['time'])
            df.set_index('datetime', inplace=True)
            htf_df = df.resample(f'{htf_minutes}min').agg({
                'time': 'first', 'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
            }).dropna()
            
            htf_candles = htf_df.to_dict('records')
            swings = SMCAnalyzer._find_swing_points(htf_candles, left=1, right=1)
            
            if len(swings) < 4: return "RANGING"
            
            recent_highs = [s['price'] for s in swings if s['type'] == 'HIGH'][-2:]
            recent_lows = [s['price'] for s in swings if s['type'] == 'LOW'][-2:]
            
            if len(recent_highs) == 2 and len(recent_lows) == 2:
                if recent_highs[1] > recent_highs[0] and recent_lows[1] > recent_lows[0]:
                    return "BULLISH"
                elif recent_highs[1] < recent_highs[0] and recent_lows[1] < recent_lows[0]:
                    return "BEARISH"
            return "RANGING"
        except Exception as e:
            logger.warning("HTF Bias calculation failed: %s. Defaulting to RANGING.", e)
            return "RANGING"

    @staticmethod
    def detect_liquidity_sweep(candles, creation_index, fvg_type, lookback=20):
        start_idx = max(0, creation_index - lookback)
        window = candles[start_idx:creation_index]
        if len(window) < 5: return False
        
        swings = SMCAnalyzer._find_swing_points(window, left=2, right=2)
        if not swings: return False
        
        c2 = candles[creation_index - 1] 
        
        if fvg_type == 'BULLISH_FVG':
            recent_lows = [s['price'] for s in swings if s['type'] == 'LOW']
            if recent_lows:
                prior_low = recent_lows[-1]
                if c2['low'] < prior_low and c2['close'] > prior_low:
                    return True
        elif fvg_type == 'BEARISH_FVG':
            recent_highs = [s['price'] for s in swings if s['type'] == 'HIGH']
            if recent_highs:
                prior_high = recent_highs[-1]
                if c2['high'] > prior_high and c2['close'] < prior_high:
                    return True
        return False

    @staticmethod
    def classify_price_zone(price_level, recent_high, recent_low):
        rng = recent_high - recent_low
        if rng == 0: return "NEUTRAL"
        pos = (price_level - recent_low) / rng
        if pos <= 0.382: return "DEEP_DISCOUNT"
        if pos <= 0.500: return "DISCOUNT"
        if pos <= 0.618: return "PREMIUM"
        return "DEEP_PREMIUM"

    @staticmethod
    def analyze_order_blocks(candles, displacement_factor=1.5, lookback_atr=14):
        obs = []
        if len(candles) < lookback_atr + 2: return obs

        for i in range(lookback_atr, len(candles) - 1):
            avg_range = sum((c['high'] - c['low']) for c in candles[i-lookback_atr:i]) / lookback_atr
            c_target = candles[i]
            c_disp = candles[i+1]
            disp_range = c_disp['high'] - c_disp['low']

            if disp_range > (displacement_factor * avg_range):
                if c_target['close'] < c_target['open'] and c_disp['close'] > c_disp['open'] and c_disp['close'] > c_target['high']:
                    obs.append({'type': 'BULLISH_OB', 'top': c_target['high'], 'bottom': c_target['low']})
                elif c_target['close'] > c_target['open'] and c_disp['close'] < c_disp['open'] and c_disp['close'] < c_target['low']:
                    obs.append({'type': 'BEARISH_OB', 'top': c_target['high'], 'bottom': c_target['low']})
        return obs

    @staticmethod
    def enrich_with_confluence(candles, fvgs):
        enriched_fvgs = []
        for fvg in fvgs:
            idx = fvg['creation_index']
            candles_up_to_fvg = candles[:idx+1]
            
            bias = SMCAnalyzer.determine_htf_bias(candles_up_to_fvg)
            htf_aligned = (fvg['type'] == 'BULLISH_FVG' and bias == 'BULLISH') or (fvg['type'] == 'BEARISH_FVG' and bias == 'BEARISH')
            swept = SMCAnalyzer.detect_liquidity_sweep(candles, idx, fvg['type'])
            
            zone_aligned = False
            zone_label = "NEUTRAL"
            available_lookback = min(100, idx)
            if available_lookback >= 10:
                lookback_window = candles[idx - available_lookback:idx]
                r_high = max(c['high'] for c in lookback_window)
                r_low = min(c['low'] for c in lookback_window)
                zone_label = SMCAnalyzer.classify_price_zone(fvg['bottom'], r_high, r_low)
                if fvg['type'] == 'BULLISH_FVG' and zone_label in ['DISCOUNT', 'DEEP_DISCOUNT']:
                    zone_aligned = True
                if fvg['type'] == 'BEARISH_FVG' and zone_label in ['PREMIUM', 'DEEP_PREMIUM']:
                    zone_aligned = True
                    
            obs = SMCAnalyzer.analyze_order_blocks(candles_up_to_fvg)
            ob_overlap = False
            for ob in obs:
                if max(fvg['bottom'], ob['bottom']) < min(fvg['top'], ob['top']):
                    ob_overlap = True
                    break

            confluence_count = sum([htf_aligned, swept, zone_aligned, ob_overlap])

            fvg['confluence'] = {
                'htf_bias': bias, 'htf_aligned': htf_aligned,
                'liquidity_sweep': swept, 'zone': zone_label,
                'zone_aligned': zone_aligned, 'ob_confluence': ob_overlap
            }
            fvg['confluence_count'] = confluence_count
            fvg['passes_confluence'] = confluence_count >= CONFLUENCE_THRESHOLD
            
            enriched_fvgs.append(fvg)
            
        return enriched_fvgs

    @staticmethod
    def generate_fvg_id(fvg):
        raw = f"{fvg['type']}_{fvg['time']}_{fvg['top']}_{fvg['bottom']}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @staticmethod
    def is_fvg_still_valid(fvg, candles):
        creation_idx = fvg.get('creation_index', 0)
        for candle in candles[creation_idx + 1:]:
            if fvg['type'] == 'BULLISH_FVG':
                if candle['close'] < fvg['bottom']: return False
            elif fvg['type'] == 'BEARISH_FVG':
                if candle['close'] > fvg['top']: return False
        return True

    @staticmethod
    def get_fvg_fill_percentage(fvg, candles):
        creation_idx = fvg.get('creation_index', 0)
        gap_size = fvg['top'] - fvg['bottom']
        if gap_size <= 0: return 100.0

        max_penetration = 0.0
        for candle in candles[creation_idx + 1:]:
            if fvg['type'] == 'BULLISH_FVG':
                if candle['low'] < fvg['top']:
                    penetration = fvg['top'] - max(candle['low'], fvg['bottom'])
                    max_penetration = max(max_penetration, penetration)
            elif fvg['type'] == 'BEARISH_FVG':
                if candle['high'] > fvg['bottom']:
                    penetration = min(candle['high'], fvg['top']) - fvg['bottom']
                    max_penetration = max(max_penetration, penetration)

        fill_pct = (max_penetration / gap_size) * 100.0
        return round(min(fill_pct, 100.0), 1)

    @staticmethod
    def calculate_displacement_strength(candles, fvg, lookback_atr=14):
        result = {'atr_multiple': 0.0, 'body_ratio': 0.0, 'is_strong': False}

        creation_idx = fvg.get('creation_index', 0)
        disp_idx = creation_idx - 1

        if disp_idx < lookback_atr or disp_idx >= len(candles): return result

        disp_candle = candles[disp_idx]
        atr_window = candles[disp_idx - lookback_atr:disp_idx]
        if not atr_window: return result

        avg_range = sum(c['high'] - c['low'] for c in atr_window) / len(atr_window)
        if avg_range == 0: return result

        disp_range = disp_candle['high'] - disp_candle['low']
        body_size = abs(disp_candle['close'] - disp_candle['open'])

        atr_multiple = round(disp_range / avg_range, 2)
        body_ratio = body_size / disp_range if disp_range > 0 else 0.0

        # This resolves the cut-off syntax issue
        is_strong = (atr_multiple >= FVG_MIN_ATR_MULTIPLE) and (body_ratio >= FVG_MIN_DISPLACEMENT_BODY_RATIO)

        result['atr_multiple'] = atr_multiple
        result['body_ratio'] = round(body_ratio, 2)
        result['is_strong'] = is_strong

        return result