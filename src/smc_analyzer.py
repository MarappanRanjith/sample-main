# src/smc_analyzer.py
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class SMCAnalyzer:
    """
    Smart Money Concepts (SMC) Analyzer.
    Now upgraded with Institutional Confluence Architecture (HTF Bias, Liquidity Sweeps, OTE Zones, OBs).
    """

    @staticmethod
    def analyze_fvgs(candles):
        """Scans a list of candles to find Fair Value Gaps."""
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
        """Finds fractal swing highs and lows."""
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
        """Resamples to HTF and determines bias based on recent swings."""
        if not candles_up_to_now or len(candles_up_to_now) < 30: return "RANGING"
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
        except Exception:
            return "RANGING"

    @staticmethod
    def detect_liquidity_sweep(candles, creation_index, fvg_type, lookback=20):
        """Checks if price swept a prior swing point before creating the FVG."""
        start_idx = max(0, creation_index - lookback)
        window = candles[start_idx:creation_index]
        if len(window) < 5: return False
        
        swings = SMCAnalyzer._find_swing_points(window, left=2, right=2)
        if not swings: return False
        
        c2 = candles[creation_index - 1] # Displacement candle
        
        if fvg_type == 'BULLISH_FVG':
            recent_lows = [s['price'] for s in swings if s['type'] == 'LOW']
            if recent_lows:
                prior_low = recent_lows[-1]
                # Did it sweep below the prior low but close above?
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
        """Classifies price into Premium/Discount levels (OTE)."""
        rng = recent_high - recent_low
        if rng == 0: return "NEUTRAL"
        pos = (price_level - recent_low) / rng
        if pos <= 0.382: return "DEEP_DISCOUNT"
        if pos <= 0.500: return "DISCOUNT"
        if pos <= 0.618: return "PREMIUM"
        return "DEEP_PREMIUM"

    @staticmethod
    def analyze_order_blocks(candles, displacement_factor=1.5, lookback_atr=14):
        """Finds Order Blocks based on strong displacement vs average range."""
        obs = []
        if len(candles) < lookback_atr + 2: return obs

        for i in range(lookback_atr, len(candles) - 1):
            avg_range = sum((c['high'] - c['low']) for c in candles[i-lookback_atr:i]) / lookback_atr
            c_target = candles[i]
            c_disp = candles[i+1]
            disp_range = c_disp['high'] - c_disp['low']

            if disp_range > (displacement_factor * avg_range):
                # Bullish OB (Red candle followed by massive Green)
                if c_target['close'] < c_target['open'] and c_disp['close'] > c_disp['open'] and c_disp['close'] > c_target['high']:
                    obs.append({'type': 'BULLISH_OB', 'top': c_target['high'], 'bottom': c_target['low']})
                # Bearish OB (Green candle followed by massive Red)
                elif c_target['close'] > c_target['open'] and c_disp['close'] < c_disp['open'] and c_disp['close'] < c_target['low']:
                    obs.append({'type': 'BEARISH_OB', 'top': c_target['high'], 'bottom': c_target['low']})
        return obs

    @staticmethod
    def enrich_with_confluence(candles, fvgs):
        """Master orchestrator to apply all 4 confluence checks to FVGs."""
        enriched_fvgs = []
        for fvg in fvgs:
            idx = fvg['creation_index']
            candles_up_to_fvg = candles[:idx+1]
            
            # 1. HTF Bias
            bias = SMCAnalyzer.determine_htf_bias(candles_up_to_fvg)
            htf_aligned = (fvg['type'] == 'BULLISH_FVG' and bias == 'BULLISH') or (fvg['type'] == 'BEARISH_FVG' and bias == 'BEARISH')
            
            # 2. Liquidity Sweep
            swept = SMCAnalyzer.detect_liquidity_sweep(candles, idx, fvg['type'])
            
            # 3. Premium / Discount Zone
            zone_aligned = False
            zone_label = "NEUTRAL"
            if idx >= 100:
                lookback_window = candles[idx-100:idx]
                r_high = max(c['high'] for c in lookback_window)
                r_low = min(c['low'] for c in lookback_window)
                zone_label = SMCAnalyzer.classify_price_zone(fvg['bottom'], r_high, r_low)
                
                if fvg['type'] == 'BULLISH_FVG' and zone_label in ['DISCOUNT', 'DEEP_DISCOUNT']: zone_aligned = True
                if fvg['type'] == 'BEARISH_FVG' and zone_label in ['PREMIUM', 'DEEP_PREMIUM']: zone_aligned = True

            # 4. Order Block Overlap
            obs = SMCAnalyzer.analyze_order_blocks(candles_up_to_fvg)
            ob_overlap = any(
                (ob['type'] == 'BULLISH_OB' and fvg['type'] == 'BULLISH_FVG' and ob['bottom'] <= fvg['top'] and ob['top'] >= fvg['bottom']) or
                (ob['type'] == 'BEARISH_OB' and fvg['type'] == 'BEARISH_FVG' and ob['bottom'] <= fvg['top'] and ob['top'] >= fvg['bottom'])
                for ob in obs
            )

            # Tabulate Score
            confluence_count = sum([htf_aligned, swept, zone_aligned, ob_overlap])
            
            fvg['confluence'] = {
                'htf_bias': bias, 'htf_aligned': htf_aligned,
                'liquidity_sweep': swept, 'zone': zone_label,
                'zone_aligned': zone_aligned, 'ob_confluence': ob_overlap
            }
            fvg['confluence_count'] = confluence_count
            fvg['passes_confluence'] = confluence_count >= 3
            
            enriched_fvgs.append(fvg)
            
        return enriched_fvgs