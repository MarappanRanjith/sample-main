# =============================================================================
# src/config.py — Consolidated Configuration for SMC Trading Bot
# =============================================================================

import os
import datetime
from dotenv import load_dotenv
import pytz

# Load environment variables from .env file
load_dotenv()


# =============================================================================
# 🔑 API / BROKER CREDENTIALS
# =============================================================================
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
print(f"DEBUG: UPSTOX_ACCESS_TOKEN loaded? {'yes' if UPSTOX_ACCESS_TOKEN else 'NO - Set it in .env!'}")

UPSTOX_BASE_URL = os.getenv("UPSTOX_BASE_URL", "https://api.upstox.com/v2")


# =============================================================================
# 📈 INSTRUMENT SYMBOLS
# =============================================================================
NIFTY_SYMBOL = "NSE_INDEX|Nifty 50"
BANKNIFTY_SYMBOL = "NSE_INDEX|Nifty Bank"
INDIA_VIX_SYMBOL = "NSE_INDEX|India VIX"


# =============================================================================
# 🌍 MACRO / VOLATILITY FILTERS
# =============================================================================
BRENT_CRUDE_THRESHOLD = 90.0
USD_INR_SHARP_DEPRECIATION_THRESHOLD = 0.005
USD_INR_SHARP_APPRECIATION_THRESHOLD = 0.005
VIX_THRESHOLD = 16.5


# =============================================================================
# 📊 GENERAL TRADING PARAMETERS
# =============================================================================
WEEKLY_EXPIRY_TRADING_DAY = 3       # Wednesday (0=Mon, 6=Sun)
EMA_PERIOD = 50


# =============================================================================
# 🕐 TIME SETTINGS (Indian Standard Time)
# =============================================================================
IST_TIMEZONE = pytz.timezone("Asia/Kolkata")
MARKET_OPEN_TIME = datetime.time(9, 15, 0)
MARKET_CLOSE_TIME = datetime.time(15, 30, 0)
PRE_MARKET_ANALYSIS_TIME = datetime.time(8, 0, 0)
VOLATILITY_FILTER_WINDOW_END = datetime.time(9, 30, 0)


# =============================================================================
# 📁 FILE PATHS
# =============================================================================
LOG_FILE = os.path.join("logs", "trading_bot.log")


# =============================================================================
# =============================================================================
#                    SMC ANALYZER CONFIGURATION
# =============================================================================
# =============================================================================


# =============================================================================
# 📦 DATA FETCH
# FIX #4 — Increased from 150 to 250 so FVGs at index 100+ have proper
# lookback data for PD Zone classification and HTF Bias determination.
# =============================================================================
CANDLE_FETCH_COUNT = 250


# =============================================================================
# 📐 HTF (Higher Time Frame) BIAS
# FIX #5 — Increased from 30 to 75 (produces ~5 HTF candles from 1-min data,
# enough for 4 swing points needed for bias detection).
# =============================================================================
HTF_BIAS_MIN_CANDLES = 75


# =============================================================================
# 🔍 FVG DETECTION
# =============================================================================

# ENH #7: Dynamic ATR-based gap filter
# FVG gap must be >= ATR * this multiplier to qualify
FVG_MIN_ATR_MULTIPLE = 0.3

# ENH #1: Maximum candle age before an FVG expires and is discarded
FVG_MAX_AGE_CANDLES = 200

# ENH #10: Minimum body-to-range ratio on the displacement candle
# Ensures the candle that created the FVG has strong momentum (not a doji)
FVG_MIN_DISPLACEMENT_BODY_RATIO = 0.6

# ENH #8: Maximum price distance (in points) to cluster nearby FVGs
# FVGs within this range are grouped into a single zone
FVG_CLUSTER_MAX_GAP = 5.0

# ENH #4: Optimal partial fill range for bonus scoring
# FVGs filled between 30%-70% get a quality bonus (sweet spot)
FVG_PARTIAL_FILL_BONUS_RANGE = (0.3, 0.7)

# FIX #7: Per-symbol minimum FVG gap size (absolute points)
# Gaps smaller than these are bid-ask spread noise, not tradeable FVGs
MIN_FVG_GAP_SIZE = {
    "NIFTY": 3.0,
    "BANKNIFTY": 8.0,
    "NIFTYIT": 5.0,
}
MIN_FVG_GAP_SIZE_DEFAULT = 5.0     # Fallback for any unlisted symbol


# =============================================================================
# ⚡ KILLZONE WINDOWS (High-Probability Trading Sessions)
# =============================================================================

# Used by live_bot.py — list of time tuples for quick in/out checks
KILLZONES = [
    (datetime.time(9, 20), datetime.time(10, 45)),    # Morning session
    (datetime.time(14, 0), datetime.time(15, 15)),     # Afternoon session
]
KILLZONE_ENABLED = True     # Set to False to scan all market hours

# Used by smc_analyzer.py — dict format with named sessions for scoring
KILLZONE_RANGES = {
    'opening': ('09:15', '10:15'),
    'mid_session': ('11:30', '13:00'),
    'closing': ('14:30', '15:30'),
}


# =============================================================================
# 🎯 CONFLUENCE & SCORING
# =============================================================================

# Minimum weighted confluence score required for a signal to pass
CONFLUENCE_THRESHOLD = 4.0

# ENH #12: Weighted confluence scoring — each factor's contribution
CONFLUENCE_WEIGHTS = {
    'htf_bias': 2.0,            # Higher timeframe trend alignment
    'liquidity_sweep': 1.5,     # Recent liquidity grab detected
    'ob_alignment': 1.5,        # Order block alignment with FVG
    'pd_zone': 1.0,             # Premium/Discount zone position
    'killzone': 1.0,            # Within high-probability session
}

# ENH #11: Confluence time decay
# After CONFLUENCE_DECAY_START candles, score decays by DECAY_RATE per candle
CONFLUENCE_DECAY_START = 30     # Candles before decay begins
CONFLUENCE_DECAY_RATE = 0.05    # Score reduction per candle after decay starts


# =============================================================================
# 🏆 ENTRY QUALITY SCORING THRESHOLDS
# =============================================================================

# Score >= EXCELLENT  → High conviction, full position size
# Score >= GOOD       → Moderate conviction, standard position
# Score >= MARGINAL   → Low conviction, reduced size or skip
# Score <  MARGINAL   → No trade
ENTRY_SCORE_EXCELLENT = 8.0
ENTRY_SCORE_GOOD = 6.0
ENTRY_SCORE_MARGINAL = 4.0