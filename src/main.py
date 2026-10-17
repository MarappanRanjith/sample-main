# src/main.py
import sys
import os
import datetime
import time
import threading
import logging
from pathlib import Path

# Ensure project root is on sys.path when running `python src/main.py` so
# `from src...` imports work as expected. This keeps both `python src/main.py`
# and `python -m src.main` usable.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import IST_TIMEZONE, MARKET_OPEN_TIME, MARKET_CLOSE_TIME, PRE_MARKET_ANALYSIS_TIME, VOLATILITY_FILTER_WINDOW_END, UPSTOX_ACCESS_TOKEN
from src.utils import logger
from src.upstox_handler import UpstoxHandler
from src.data_fetcher import DataFetcher
from src.trading_logic import TradingLogic
from src.websocket_handler import WebSocketHandler

class TradingBot:
    def __init__(self):
        self.logger = logger # Use the globally configured logger
        self.logger.info("Initializing Trading Bot...")

        # Initialize core components
        # IMPORTANT: Handle Upstox authentication properly (get/refresh token)
        # For simplicity, assume UPSTOX_ACCESS_TOKEN is valid in config
        self.upstox_handler = UpstoxHandler()
        self.data_fetcher = DataFetcher()
        # Initialize WebSocket handler AFTER getting a valid access token from config
        self.ws_handler = WebSocketHandler(access_token=UPSTOX_ACCESS_TOKEN)
        self.trading_logic = TradingLogic(self.ws_handler, self.upstox_handler, self.data_fetcher)

        self.running = False
        self.market_open = False
        self.analysis_done = False
        self.logger.info("Trading Bot initialized.")

    def start_websocket(self):
        # Start WebSocket in a separate thread
        self.ws_handler.connect()
        # Give it some time to connect and subscribe
        time.sleep(5) # Adjust as needed

    def stop_websocket(self):
        self.ws_handler.stop()

    def check_market_hours(self):
        """Checks if the market is currently open based on IST."""
        now = datetime.datetime.now(IST_TIMEZONE)
        current_time = now.time()

        if MARKET_OPEN_TIME <= current_time < MARKET_CLOSE_TIME:
            if not self.market_open:
                self.logger.info("Market is now OPEN.")
                self.market_open = True
        elif current_time >= MARKET_CLOSE_TIME:
            if self.market_open:
                self.logger.info("Market has closed.")
                self.market_open = False
                self.running = False # Stop the bot after market close
        else: # Before market open
            if self.market_open: # Just closed
                self.market_open = False
            # logger.debug("Market is closed.") # Can be noisy, use debug level

    def perform_pre_market_analysis(self):
        """Runs analysis tasks before the market opens."""
        now = datetime.datetime.now(IST_TIMEZONE)
        if now.time() >= PRE_MARKET_ANALYSIS_TIME and not self.analysis_done:
            self.trading_logic.run_pre_market_analysis()
            self.analysis_done = True
            self.logger.info("Pre-market analysis completed.")

    def run_live_trading_loop(self):
        """Main loop for live trading operations."""
        self.logger.info("Starting live trading loop (TEST MODE)...")
        self.start_websocket() # Start fetching live data

        # TEST MODE: Run continuously while the bot is flagged as running.
        # Avoid market_open gating so the loop does not immediately exit on weekends.
        while self.running:
            # In test mode, skip market hours checks that would stop the loop.
            # self.check_market_hours()

            # Perform checks that need to run during live test mode
            self.trading_logic.run_live_trading_checks() # Evaluates VIX filter and determines mode

            # Execute trades based on the determined mode
            self.trading_logic.execute_trade_signal()

            # Add logic here for risk management (trailing stops, monitoring open positions)
            # e.g., self.risk_manager.manage_positions()

            # Sleep for a defined interval (e.g., every 10 seconds)
            # Adjust sleep time based on how frequently you need to check conditions
            time.sleep(10)

        self.stop_websocket()
        self.logger.info("Trading Bot stopped.")

    def run(self):
        """Starts the main trading bot process."""
        self.running = True
        self.logger.info("Trading Bot starting...")

        # Main loop logic: Check time and trigger actions
        while self.running:
            now = datetime.datetime.now(IST_TIMEZONE)
            current_time = now.time()

            # Perform pre-market analysis once
            if current_time >= PRE_MARKET_ANALYSIS_TIME and not self.analysis_done:
                 self.perform_pre_market_analysis()

            # TEST MODE: Bypass market hours check for weekend testing
            # if current_time >= MARKET_OPEN_TIME and current_time < MARKET_CLOSE_TIME:
            if not self.market_open: # Start only once in test mode
                self.market_open = True
                self.logger.info("Starting live trading loop (TEST MODE)...")
                self.run_live_trading_loop() # This loop runs until explicitly stopped
                break # Exit this outer loop once live trading finishes

            # Add logic for end-of-day cleanup or overnight tasks if needed

            # Wait before checking the time again (e.g., every minute)
            time.sleep(60)

        self.logger.info("Trading Bot finished execution.")


if __name__ == "__main__":
    bot = TradingBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.logger.info("Bot stopped manually by user (Ctrl+C).")
        bot.running = False # Ensure flags are reset
        bot.stop_websocket() # Ensure websocket is closed
    except Exception as e:
        bot.logger.exception(f"An unhandled error occurred: {e}")
        bot.running = False
        bot.stop_websocket()
