# src/config.py

import os
import datetime
from dotenv import load_dotenv
import pytz

# Load environment variables from .env file
load_dotenv()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
print(f"DEBUG: UPSTOX_ACCESS_TOKEN loaded? {'yes' if UPSTOX_ACCESS_TOKEN else 'NO - Set it in .env!'}")

UPSTOX_BASE_URL = os.getenv("UPSTOX_BASE_URL", "https://api.upstox.com/v2")

# --- Trading Parameters ---
BRENT_CRUDE_THRESHOLD = 90.0
USD_INR_SHARP_DEPRECIATION_THRESHOLD = 0.005
USD_INR_SHARP_APPRECIATION_THRESHOLD = 0.005
VIX_THRESHOLD = 16.5
NIFTY_SYMBOL = "NSE_INDEX|Nifty 50"
BANKNIFTY_SYMBOL = "NSE_INDEX|Nifty Bank"
INDIA_VIX_SYMBOL = "NSE_INDEX|India VIX"
WEEKLY_EXPIRY_TRADING_DAY = 3  # Wednesday
EMA_PERIOD = 50

# --- Time Settings ---
IST_TIMEZONE = pytz.timezone("Asia/Kolkata")
MARKET_OPEN_TIME = datetime.time(9, 15, 0)
MARKET_CLOSE_TIME = datetime.time(15, 30, 0)
PRE_MARKET_ANALYSIS_TIME = datetime.time(8, 0, 0)
VOLATILITY_FILTER_WINDOW_END = datetime.time(9, 30, 0)

# --- File Paths ---
LOG_FILE = os.path.join("logs", "trading_bot.log")
