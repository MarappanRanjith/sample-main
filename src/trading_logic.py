# src/trading_logic.py
import logging
from src.config import (
    VIX_THRESHOLD, BRENT_CRUDE_THRESHOLD, USD_INR_SHARP_DEPRECIATION_THRESHOLD,
    USD_INR_SHARP_APPRECIATION_THRESHOLD, NIFTY_SYMBOL, INDIA_VIX_SYMBOL, 
    BANKNIFTY_SYMBOL, IST_TIMEZONE, MARKET_OPEN_TIME, MARKET_CLOSE_TIME,
    VOLATILITY_FILTER_WINDOW_END, WEEKLY_EXPIRY_TRADING_DAY
)
from src.utils import logger
from src.data_fetcher import DataFetcher
from src.upstox_handler import UpstoxHandler
from src.websocket_handler import WebSocketHandler
import datetime
from src.candle_patterns import CandlestickAnalyzer
from src.smc_analyzer import SMCAnalyzer

class TradingLogic:
    def __init__(self, websocket_handler: WebSocketHandler, upstox_handler: UpstoxHandler, data_fetcher: DataFetcher):
        self.ws_handler = websocket_handler
        self.upstox_handler = upstox_handler
        self.data_fetcher = data_fetcher
        self.system_bias = "Neutral"
        self.max_call_oi_strike = None
        self.max_put_oi_strike = None
        self.trading_range_ceiling = None
        self.trading_range_floor = None
        self.freeze_longs = False
        self.current_trading_mode = "Neutral"
        self.ema_50_level = None
        logger.info("TradingLogic initialized.")

    def get_current_weekly_expiry_date(self):
        """Calculate the next weekly expiry date (Wednesdays for Nifty)."""
        today = datetime.datetime.now(IST_TIMEZONE).date()
        days_ahead = WEEKLY_EXPIRY_TRADING_DAY - today.weekday()
        
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        expiry = today + datetime.timedelta(days=days_ahead)
        logger.info(f"Next weekly expiry: {expiry.strftime('%Y-%m-%d')}")
        return expiry.strftime('%Y-%m-%d')

    def evaluate_macro_filters(self):
        """Evaluate macroeconomic indicators to determine system bias."""
        logger.info("Evaluating macro filters...")
        brent_price = self.data_fetcher.fetch_brent_crude_price()
        usd_inr = self.data_fetcher.fetch_usd_inr_rate()

        if brent_price is None or usd_inr is None:
            logger.warning("Could not fetch macro data. Keeping previous bias or Neutral.")
            return

        if brent_price > BRENT_CRUDE_THRESHOLD:
            self.system_bias = "Cautious / Sell on Rise"
            logger.info(f"  Brent Crude ${brent_price} > Threshold ${BRENT_CRUDE_THRESHOLD} -> CAUTIOUS bias")
        elif usd_inr > (84.0 + USD_INR_SHARP_APPRECIATION_THRESHOLD):
            self.system_bias = "Cautious / Sell on Rise"
            logger.info(f"  USD/INR {usd_inr} indicates INR weakness -> CAUTIOUS bias")
        elif brent_price < (BRENT_CRUDE_THRESHOLD - 5) and usd_inr < (84.0 - USD_INR_SHARP_DEPRECIATION_THRESHOLD):
            self.system_bias = "Risk-On / Buy on Dips"
            logger.info(f"  Low Brent (${brent_price}) + INR strength ({usd_inr}) -> RISK-ON bias")
        else:
            self.system_bias = "Neutral"
            logger.info("  Macro conditions neutral")

        logger.info(f"System Bias: {self.system_bias}")

    def evaluate_oi_clusters(self):
        """Fetch and analyze OI clusters to find support/resistance levels."""
        logger.info("Evaluating OI clusters...")
        expiry_date = self.get_current_weekly_expiry_date()

        nifty_oi_response = self.upstox_handler.get_options_chain(NIFTY_SYMBOL, expiry_date)

        if not nifty_oi_response or nifty_oi_response.get('status') != 'success':
            logger.warning(f"Failed to fetch Nifty OI data: {nifty_oi_response}")
            self.max_call_oi_strike = None
            self.max_put_oi_strike = None
            self.trading_range_ceiling = None
            self.trading_range_floor = None
            return

        try:
            options_data = nifty_oi_response.get('data', [])
            max_call_oi = 0
            max_put_oi = 0
            max_call_strike = None
            max_put_strike = None

            for contract in options_data:
                call_oi = contract.get('call_options', {}).get('market_data', {}).get('oi', 0)
                put_oi = contract.get('put_options', {}).get('market_data', {}).get('oi', 0)
                strike = contract.get('strike_price')

                if call_oi > max_call_oi:
                    max_call_oi = call_oi
                    max_call_strike = strike
                if put_oi > max_put_oi:
                    max_put_oi = put_oi
                    max_put_strike = strike

            self.max_call_oi_strike = max_call_strike
            self.max_put_oi_strike = max_put_strike
            self.trading_range_ceiling = max_call_strike
            self.trading_range_floor = max_put_strike

            logger.info(f"Max Call OI Strike: {self.max_call_oi_strike} (OI: {max_call_oi})")
            logger.info(f"Max Put OI Strike: {self.max_put_oi_strike} (OI: {max_put_oi})")
            logger.info(f"Trading Range: Floor={self.trading_range_floor}, Ceiling={self.trading_range_ceiling}")
        except Exception as e:
            logger.error(f"Error parsing OI data: {e}")

    def evaluate_smc_zones(self):
        """Scans for SMC opportunities and prints indications/alerts to the console."""
        candles = self.data_fetcher.get_recent_candles(NIFTY_SYMBOL, interval="1minute", count=60)
        if not candles:
            return
            
        fvgs = SMCAnalyzer.analyze_fvgs(candles)
        obs = SMCAnalyzer.analyze_order_blocks(candles)
        
        # Only log the most recent FVG if it exists
        if fvgs:
            latest_fvg = fvgs[-1]
            logger.info(f"🟢 SMC 1m RADAR [FVG]: {latest_fvg['type']} detected at {latest_fvg['time']}. Zone: {latest_fvg['bottom']} to {latest_fvg['top']}")
            
        # Only log the most recent OB if it exists
        if obs:
            latest_ob = obs[-1]
            logger.info(f"🟣 SMC 1m RADAR [OB]: {latest_ob['type']} detected. Zone: {latest_ob['bottom']} to {latest_ob['top']}")

    def evaluate_volatility_filter(self):
        """Check India VIX during market open window."""
        current_time = datetime.datetime.now(IST_TIMEZONE).time()
        
        if not (MARKET_OPEN_TIME <= current_time <= VOLATILITY_FILTER_WINDOW_END):
            return True

        logger.info("Evaluating Volatility Filter (9:15 - 9:30 AM window)...")
        vix_ltp = self.ws_handler.get_ltp(INDIA_VIX_SYMBOL)

        if vix_ltp is None:
            logger.warning("Could not get live VIX LTP.")
            self.freeze_longs = False
            return True

        if vix_ltp > VIX_THRESHOLD:
            self.freeze_longs = True
            logger.warning(f"VIX SPIKE: {vix_ltp} > {VIX_THRESHOLD} -> LONGS FROZEN")
            return False
        else:
            self.freeze_longs = False
            logger.info(f"VIX OK: {vix_ltp} <= {VIX_THRESHOLD} -> Safe for longs")
            return True

    def calculate_ema_50(self):
        """Calculate 50-day EMA for Nifty."""
        logger.info("Calculating 50-day EMA...")
        self.ema_50_level = self.data_fetcher.get_ema_data(NIFTY_SYMBOL, 50)
        if self.ema_50_level is not None:
            logger.info(f"EMA(50): {self.ema_50_level:.2f}")
        else:
            logger.error("Failed to calculate 50-day EMA")

    def determine_trading_mode(self):
        """Determine market regime (Momentum, Mean-Reversion, Neutral)."""
        current_time = datetime.datetime.now(IST_TIMEZONE).time()
        
        if not (MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME):
            self.current_trading_mode = "Neutral"
            return

        logger.info("Determining trading mode...")
        nifty_ltp = self.ws_handler.get_ltp(NIFTY_SYMBOL)

        if nifty_ltp is None:
            logger.warning("Nifty LTP not available. Mode = Neutral")
            self.current_trading_mode = "Neutral"
            return

        is_safe_for_longs = not self.freeze_longs and self.system_bias != "Cautious / Sell on Rise"

        open_p, high_p, low_p, close_p = self.data_fetcher.get_latest_candle_ohlc(NIFTY_SYMBOL)

        if open_p is None:
            logger.warning("Latest candle OHLC is None. Cannot perform Candlestick Analysis.")
            self.current_trading_mode = "Neutral (Awaiting Data)"
            return # Skip advanced execution for this cycle

        candle_signal = None
        if all([open_p, high_p, low_p, close_p, self.trading_range_floor, self.trading_range_ceiling]):
            candle_signal = CandlestickAnalyzer.analyze_level_interaction(
                open_p, high_p, low_p, close_p, self.trading_range_floor, self.trading_range_ceiling
            )
            logger.info(f"  Candle OHLC: O={open_p}, H={high_p}, L={low_p}, C={close_p} | Signal: {candle_signal}")
        else:
            logger.warning("Could not fetch latest candle OHLC or OI levels are missing.")

        is_above_ceiling = (
            self.trading_range_ceiling is not None and nifty_ltp > self.trading_range_ceiling
        )

        is_near_oi_walls = False
        if self.trading_range_floor and self.trading_range_ceiling:
            range_width = abs(self.trading_range_ceiling - self.trading_range_floor)
            dist_to_closest = min(
                abs(nifty_ltp - self.trading_range_floor),
                abs(nifty_ltp - self.trading_range_ceiling)
            )
            is_near_oi_walls = dist_to_closest < (range_width * 0.2)

        if candle_signal == "BULLISH_BREAKOUT" and is_safe_for_longs:
            self.current_trading_mode = "Breakout BUY"
        elif candle_signal == "BEARISH_BREAKOUT" and not is_safe_for_longs:
            self.current_trading_mode = "Breakout SELL"
        elif is_above_ceiling and is_safe_for_longs:
            self.current_trading_mode = "Momentum BUY"
        elif is_near_oi_walls and not is_above_ceiling:
            self.current_trading_mode = "Mean-Reversion"
        else:
            self.current_trading_mode = "Neutral"

        logger.info(f"Mode: {self.current_trading_mode} | Nifty LTP: {nifty_ltp:.2f} | Safe for Longs: {is_safe_for_longs}")

    def run_pre_market_analysis(self):
        """Run all pre-market analysis (called at 8:00 AM)."""
        logger.info("=" * 60)
        logger.info("PRE-MARKET ANALYSIS (8:00 AM IST)")
        logger.info("=" * 60)
        self.evaluate_macro_filters()
        self.evaluate_oi_clusters()
        self.calculate_ema_50()
        logger.info("=" * 60)
        logger.info("PRE-MARKET ANALYSIS COMPLETE")
        logger.info("=" * 60)

    def run_live_trading_checks(self):
        """Run live checks during trading hours."""
        self.evaluate_oi_clusters()
        self.evaluate_volatility_filter()
        self.evaluate_smc_zones()
        self.determine_trading_mode()

    def execute_trade_signal(self):
        """
        DISABLED FOR DATA VALIDATION PHASE.
        Just logs what would happen. No actual orders placed.
        """
        logger.info(f"[DATA CHECK MODE] Trading Mode: {self.current_trading_mode}")
        logger.info(f"   System Bias: {self.system_bias}")
        logger.info(f"   EMA(50): {self.ema_50_level}")
        logger.info(f"   OI Support: {self.trading_range_floor} | Resistance: {self.trading_range_ceiling}")
