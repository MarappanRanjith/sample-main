import datetime
import pandas as pd
import yfinance as yf
import requests
from src.utils import logger
from src.upstox_handler import UpstoxHandler, get_auth_headers
from src.smc_analyzer import SMCAnalyzer
from src.config import UPSTOX_BASE_URL, NIFTY_SYMBOL, BANKNIFTY_SYMBOL, EMA_PERIOD

UNDERLYING_OPTION_SYMBOLS = {
    "NSE_INDEX|Nifty 50": "NSE_FO|NIFTY",
    "NSE_INDEX|Nifty Bank": "NSE_FO|BANKNIFTY"
}

class DataFetcher:
    def __init__(self):
        self.upstox_handler = UpstoxHandler()
        logger.info("DataFetcher initialized.")

    # ... [Keep fetch_brent_crude_price, fetch_usd_inr_rate, _get_underlying_option_symbol, get_latest_candle_ohlc, get_recent_candles, get_ema_data, fetch_options_chain, _flatten_option_contracts, find_max_oi_strikes, get_vwap as they are] ...

    def get_current_futures_symbol(self, underlying="BANKNIFTY"):
        """
        Fetches the active BANKNIFTY Futures instrument_key using the Upstox v2 Search API.
        """
        logger.info(f"Fetching active Futures instrument_key for {underlying} from Upstox Search API...")

        endpoint = f"{UPSTOX_BASE_URL.replace('/v2', '')}/v2/instruments/search"
        params = {
            "query": underlying,
            "segments": "FO",
            "instrument_types": "FUT",
            "expiry": "current_month",
            "page_number": 1,
            "records": 5
        }

        try:
            response = requests.get(endpoint, headers=get_auth_headers(), params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            instruments = data.get('data', [])
            if not instruments:
                logger.error(f"No futures contracts found for {underlying} using Search API.")
                return None

            # The search API returns results. We take the first one (near-month)
            instrument = instruments[0]
            instrument_key = instrument.get('instrument_key')
            # FIX: API field is 'trading_symbol' (with underscore), not 'tradingsymbol'.
            # The old key meant this line always logged None for the symbol name
            # even though instrument_key itself was unaffected.
            trading_symbol = instrument.get('trading_symbol')

            logger.info(f"✓ Found {underlying} Future: {trading_symbol} -> Key: {instrument_key}")
            return instrument_key

        except Exception as e:
            logger.error(f"Failed to fetch instrument via Search API: {e}")
            return None

    def get_entry_quality_score(self, gap_size, vol_multiplier):
        """
        Thin wrapper around SMCAnalyzer.score_entry_quality so callers that
        expect this method on DataFetcher (rather than reaching into
        smc_analyzer directly) keep working. The actual scoring logic lives
        in SMCAnalyzer — single source of truth, so backtester and live bot
        can never drift apart on what counts as a "Sniper" entry.

        Returns: (score: float 0-100, label: "LOW" | "MEDIUM" | "HIGH" | "SNIPER")
        """
        return SMCAnalyzer.score_entry_quality(gap_size, vol_multiplier)
    
    def get_recent_candles(self, symbol, interval="1minute", count=150):
        """Fetches recent candles and formats them with VWAP and Vol SMA for SMC Analyzer."""
        from src.utils import logger
        import pandas as pd
        
        logger.info(f"Fetching {count} recent {interval} candles for {symbol}...")
        intraday_data = self.upstox_handler.get_intraday_data(symbol, interval)
        
        if not intraday_data:
            logger.warning(f"Could not fetch intraday data for {symbol}.")
            return []
            
        try:
            data = intraday_data.get('data', {}).get('candles', [])
            if not data:
                return []
                
            # Upstox returns newest first. Slice the count and reverse to oldest-first.
            recent_subset = data[:count]
            recent_subset.reverse()
            
            df = pd.DataFrame(recent_subset, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
            
            # Calculate VWAP
            df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
            df['tp_vol'] = df['typical_price'] * df['volume']
            df['cum_tp_vol'] = df['tp_vol'].cumsum()
            df['cum_vol'] = df['volume'].cumsum()
            df['vwap'] = df['cum_tp_vol'] / df['cum_vol']
            
            # Calculate Volume SMA
            df['vol_sma_20'] = df['volume'].rolling(window=20).mean().fillna(1)
            
            formatted_candles = []
            for _, row in df.iterrows():
                formatted_candles.append({
                    'time': row['timestamp'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume'],
                    'vwap': row['vwap'],
                    'vol_sma_20': row['vol_sma_20']
                })
            
            logger.info(f"✓ Fetched and formatted {len(formatted_candles)} live candles with VWAP/Vol.")
            return formatted_candles
            
        except Exception as e:
            logger.error(f"Error formatting recent candles: {e}")
            return []