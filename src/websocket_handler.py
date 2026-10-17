# src/websocket_handler.py
import threading
import time
import logging
from src.config import INDIA_VIX_SYMBOL, NIFTY_SYMBOL, BANKNIFTY_SYMBOL
from src.utils import logger
from src.upstox_handler import get_auth_headers
import requests

class WebSocketHandler:
    def __init__(self, access_token=None):
        self.access_token = access_token
        self.ltp_data = {}
        self.subscribed_symbols = [INDIA_VIX_SYMBOL, NIFTY_SYMBOL, BANKNIFTY_SYMBOL]
        self.running = False
        self.thread = None
        logger.info("WebSocketHandler initialized (using REST API as fallback).")

    def _fetch_ltp_rest(self, symbol):
        """Fetch LTP using Upstox REST API instead of WebSocket."""
        try:
            endpoint = f"https://api.upstox.com/v2/market-quote/ltp"
            params = {"instrument_key": symbol}
            response = requests.get(endpoint, headers=get_auth_headers(), params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') == 'success':
                # Response format: {'status': 'success', 'data': {'NSE_INDEX:India VIX': {'last_price': 15.5}}}
                key = symbol.replace('|', ':')
                ltp = data['data'].get(key, {}).get('last_price')
                if ltp:
                    self.ltp_data[symbol] = float(ltp)
                    return float(ltp)
        except Exception as e:
            logger.debug(f"Failed to fetch LTP for {symbol}: {e}")
        return None

    def _poll_ltp_loop(self):
        """Background thread: periodically fetch LTP for subscribed symbols."""
        logger.info("LTP polling thread started.")
        poll_count = 0
        
        while self.running:
            try:
                for symbol in self.subscribed_symbols:
                    ltp = self._fetch_ltp_rest(symbol)
                    if ltp:
                        logger.debug(f"LTP {symbol}: {ltp}")
                
                poll_count += 1
                if poll_count % 6 == 0:  # Log every 6 polls (every 30 seconds if 5s sleep)
                    logger.info(f"LTP Data Snapshot: {self.ltp_data}")
                
                time.sleep(5)  # Fetch LTP every 5 seconds
            except Exception as e:
                logger.error(f"Error in LTP polling loop: {e}")
                time.sleep(5)

        logger.info("LTP polling thread stopped.")

    def connect(self):
        """Start the LTP polling thread."""
        if self.running:
            logger.info("WebSocket polling is already running.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._poll_ltp_loop, daemon=True)
        self.thread.start()
        logger.info("WebSocket LTP polling started.")

    def get_ltp(self, symbol):
        """Returns the last traded price for a given symbol."""
        ltp = self.ltp_data.get(symbol)
        if ltp:
            logger.debug(f"Retrieved LTP for {symbol}: {ltp}")
        return ltp

    def stop(self):
        """Stop the LTP polling thread."""
        logger.info("Stopping WebSocket handler...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("WebSocket handler stopped.")
