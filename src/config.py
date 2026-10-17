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

# =========================================================================
# SMC ANALYZER CONFIGURATION
# =========================================================================

# =============================================================================
# 🔧 FIX #4 — Increased Candle Fetch Count
# Previously 150. Increased to 250 so that FVGs at index 100+ have proper
# lookback data for PD Zone classification and HTF Bias determination.
# =============================================================================
CANDLE_FETCH_COUNT = 250

# =============================================================================
# 🔧 FIX #5 — Minimum candles required for HTF Bias calculation
# Previously 30 (produced only ~2 HTF candles, too few for swing detection).
# Now 75 (produces ~5 HTF candles, enough for 4 swing points).
# =============================================================================
HTF_BIAS_MIN_CANDLES = 75

# =============================================================================
# 🔧 FIX #7 — Minimum FVG Gap Size Filter (Eliminates Noise Signals)
# Gaps smaller than these are bid-ask spread noise, not tradeable FVGs.
# Values in absolute points for each index.
# =============================================================================
MIN_FVG_GAP_SIZE = {
    "NIFTY": 3.0,
    "BANKNIFTY": 8.0,
    "NIFTYIT": 5.0,
}
MIN_FVG_GAP_SIZE_DEFAULT = 5.0  # Fallback for any unlisted index

# =============================================================================
# 🔧 FIX #8 — Killzone Windows (High-Probability Trading Sessions)
# FVGs during lunch session (11:00–13:00) are typically low-quality.
# Only alert during these optimal scalping windows.
# =============================================================================
KILLZONES = [
    (datetime.time(9, 20), datetime.time(10, 45)),   # Morning session
    (datetime.time(14, 0), datetime.time(15, 15)),    # Afternoon session
]
KILLZONE_ENABLED = True  # Set to False to scan all market hours

# src/config.py — Required constants for SMCAnalyzer

# --- FVG Detection ---
FVG_MIN_ATR_MULTIPLE = 0.3              # ENH #7: Dynamic ATR gap filter multiplier
FVG_MAX_AGE_CANDLES = 200               # ENH #1: Max candle age before FVG expires
FVG_MIN_DISPLACEMENT_BODY_RATIO = 0.6   # ENH #10: Min body/range ratio for displacement
FVG_CLUSTER_MAX_GAP = 5.0              # ENH #8: Max price gap to cluster FVGs
MIN_FVG_GAP_SIZE = {}                   # Per-symbol static min gap (e.g., {"RELIANCE": 0.5})
FVG_PARTIAL_FILL_BONUS_RANGE = (0.3, 0.7)  # ENH #4: Optimal partial fill range

# --- Confluence & Scoring ---
CONFLUENCE_THRESHOLD = 4.0              # Minimum weighted confluence to pass
CONFLUENCE_WEIGHTS = {                  # ENH #12: Weighted confluence scoring
    'htf_bias': 2.0,
    'liquidity_sweep': 1.5,
    'ob_alignment': 1.5,
    'pd_zone': 1.0,
    'killzone': 1.0,
}
CONFLUENCE_DECAY_START = 30             # ENH #11: Candles before decay begins
CONFLUENCE_DECAY_RATE = 0.05            # ENH #11: Decay per candle after start

# --- Entry Scoring ---
ENTRY_SCORE_EXCELLENT = 8.0
ENTRY_SCORE_GOOD = 6.0
ENTRY_SCORE_MARGINAL = 4.0

# --- HTF Bias ---
HTF_BIAS_MIN_CANDLES = 75              # FIX #2: Minimum 1-min candles for HTF resample

# --- Session / Killzones (Indian Market) ---
KILLZONE_RANGES = {
    'opening': ('09:15', '10:15'),
    'mid_session': ('11:30', '13:00'),
    'closing': ('14:30', '15:30'),
}