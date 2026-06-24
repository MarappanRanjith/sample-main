# =============================================================================
# src/data_feed.py — Upstox Live Market Data Feed
# =============================================================================

import requests
import pandas as pd
import logging
from datetime import datetime, timedelta

from src.config import (
    UPSTOX_ACCESS_TOKEN,
    UPSTOX_BASE_URL,
    CANDLE_FETCH_COUNT,
    IST_TIMEZONE,
    NIFTY_SYMBOL,
    BANKNIFTY_SYMBOL,
)

logger = logging.getLogger(__name__)


class UpstoxDataFeed:
    """Fetches historical and intraday candle data from Upstox API v2."""

    def __init__(self):
        if not UPSTOX_ACCESS_TOKEN:
            raise ValueError(
                "UPSTOX_ACCESS_TOKEN is not set! "
                "Add it to your .env file."
            )

        self.base_url = UPSTOX_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Symbol mapping for convenience
        self.symbols = {
            "NIFTY": NIFTY_SYMBOL,
            "BANKNIFTY": BANKNIFTY_SYMBOL,
        }

        logger.info("UpstoxDataFeed initialized successfully.")

    # -----------------------------------------------------------------
    # Core: Fetch Historical Candles
    # -----------------------------------------------------------------
    def fetch_historical_candles(
        self,
        instrument_key: str,
        interval: str = "1minute",
        days_back: int = 5,
    ) -> pd.DataFrame:
        """
        Fetch historical candle data from Upstox.

        Args:
            instrument_key: Upstox instrument key (e.g., "NSE_INDEX|Nifty 50")
            interval: Candle interval — '1minute', '5minute', '15minute',
                      '30minute', '1hour', '1day'
            days_back: Number of calendar days to look back

        Returns:
            pd.DataFrame with columns:
            [timestamp, open, high, low, close, volume, oi]
        """
        today = datetime.now(IST_TIMEZONE)
        from_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")

        url = (
            f"{self.base_url}/historical-candle/{instrument_key}"
            f"/{interval}/{to_date}/{from_date}"
        )

        try:
            logger.info(
                f"Fetching candles: {instrument_key} | "
                f"{interval} | {from_date} → {to_date}"
            )
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "success":
                logger.error(f"API error: {data.get('message', 'Unknown')}")
                return pd.DataFrame()

            candles = data.get("data", {}).get("candles", [])

            if not candles:
                logger.warning(f"No candle data returned for {instrument_key}")
                return pd.DataFrame()

            df = pd.DataFrame(
                candles,
                columns=["timestamp", "open", "high", "low", "close", "volume", "oi"],
            )

            # Parse and localize timestamps
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            if df["timestamp"].dt.tz is None:
                df["timestamp"] = df["timestamp"].dt.tz_localize(IST_TIMEZONE)
            else:
                df["timestamp"] = df["timestamp"].dt.tz_convert(IST_TIMEZONE)

            # Sort oldest → newest (Upstox returns newest first)
            df.sort_values("timestamp", inplace=True)
            df.reset_index(drop=True, inplace=True)

            # Trim to CANDLE_FETCH_COUNT
            if len(df) > CANDLE_FETCH_COUNT:
                df = df.tail(CANDLE_FETCH_COUNT).reset_index(drop=True)

            logger.info(f"✅ Fetched {len(df)} candles for {instrument_key}")
            return df

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error(
                    "🚨 401 Unauthorized — Access token expired! "
                    "Regenerate from Upstox dashboard."
                )
            else:
                logger.error(f"HTTP error: {e}")
            return pd.DataFrame()

        except requests.exceptions.Timeout:
            logger.error("⏱️ Request timed out. Check network or retry.")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Unexpected error fetching candles: {e}")
            return pd.DataFrame()

    # -----------------------------------------------------------------
    # Convenience: Fetch Intraday (Today's) Candles
    # -----------------------------------------------------------------
    def fetch_intraday_candles(
        self,
        instrument_key: str,
        interval: str = "1minute",
    ) -> pd.DataFrame:
        """
        Fetch today's intraday candle data.

        Uses the intra-day candle endpoint for real-time data.
        """
        url = (
            f"{self.base_url}/historical-candle/intraday/"
            f"{instrument_key}/{interval}"
        )

        try:
            logger.info(f"Fetching intraday candles: {instrument_key} | {interval}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "success":
                logger.error(f"Intraday API error: {data.get('message')}")
                return pd.DataFrame()

            candles = data.get("data", {}).get("candles", [])

            if not candles:
                logger.warning("No intraday candles returned.")
                return pd.DataFrame()

            df = pd.DataFrame(
                candles,
                columns=["timestamp", "open", "high", "low", "close", "volume", "oi"],
            )

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            if df["timestamp"].dt.tz is None:
                df["timestamp"] = df["timestamp"].dt.tz_localize(IST_TIMEZONE)
            else:
                df["timestamp"] = df["timestamp"].dt.tz_convert(IST_TIMEZONE)

            df.sort_values("timestamp", inplace=True)
            df.reset_index(drop=True, inplace=True)

            logger.info(f"✅ Fetched {len(df)} intraday candles")
            return df

        except Exception as e:
            logger.error(f"Error fetching intraday candles: {e}")
            return pd.DataFrame()

    # -----------------------------------------------------------------
    # Combined: Historical + Intraday (Full Picture)
    # -----------------------------------------------------------------
    def fetch_full_candles(
        self,
        instrument_key: str,
        interval: str = "1minute",
        days_back: int = 5,
    ) -> pd.DataFrame:
        """
        Merges historical + today's intraday candles into one DataFrame.
        Removes duplicates and trims to CANDLE_FETCH_COUNT.
        """
        hist_df = self.fetch_historical_candles(
            instrument_key, interval, days_back
        )
        intra_df = self.fetch_intraday_candles(instrument_key, interval)

        if hist_df.empty and intra_df.empty:
            logger.error("Both historical and intraday data are empty!")
            return pd.DataFrame()

        combined = pd.concat([hist_df, intra_df], ignore_index=True)
        combined.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
        combined.sort_values("timestamp", inplace=True)
        combined.reset_index(drop=True, inplace=True)

        # Trim to configured count
        if len(combined) > CANDLE_FETCH_COUNT:
            combined = combined.tail(CANDLE_FETCH_COUNT).reset_index(drop=True)

        logger.info(f"✅ Combined feed: {len(combined)} candles ready for analysis")
        return combined

    # -----------------------------------------------------------------
    # Helper: Fetch by friendly name
    # -----------------------------------------------------------------
    def fetch_by_name(
        self,
        symbol_name: str,
        interval: str = "1minute",
        days_back: int = 5,
    ) -> pd.DataFrame:
        """
        Fetch candles using a friendly name like 'NIFTY' or 'BANKNIFTY'.
        """
        instrument_key = self.symbols.get(symbol_name.upper())

        if not instrument_key:
            logger.error(
                f"Unknown symbol: {symbol_name}. "
                f"Available: {list(self.symbols.keys())}"
            )
            return pd.DataFrame()

        return self.fetch_full_candles(instrument_key, interval, days_back)