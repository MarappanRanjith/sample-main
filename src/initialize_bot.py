import os

# Define the folder structure
folders = ['src', 'logs', 'data']
for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Define all the files and their content based on your 10-module requirement
files = {
    ".env": """UPSTOX_CLIENT_ID=YOUR_ID
UPSTOX_CLIENT_SECRET=YOUR_SECRET
UPSTOX_REDIRECT_URI=http://localhost:8080/callback
UPSTOX_AUTH_CODE=
VIX_FREEZE_THRESHOLD=16.5
BRENT_CAUTION_LEVEL=90.0
USDINR_CAUTION_LEVEL=84.5
""",

    "src/config.py": """import os
from dotenv import load_dotenv
from enum import Enum

load_dotenv()

CONFIG = {
    "client_id": os.getenv("UPSTOX_CLIENT_ID"),
    "client_secret": os.getenv("UPSTOX_CLIENT_SECRET"),
    "redirect_uri": os.getenv("UPSTOX_REDIRECT_URI"),
    "access_token": None,
    "NIFTY_INDEX": "NSE_INDEX|Nifty 50",
    "BANKNIFTY_INDEX": "NSE_INDEX|Nifty Bank",
    "INDIA_VIX": "NSE_INDEX|India VIX",
    "VIX_FREEZE_THRESHOLD": float(os.getenv("VIX_FREEZE_THRESHOLD", 16.5)),
    "BRENT_CAUTION_LEVEL": float(os.getenv("BRENT_CAUTION_LEVEL", 90.0)),
    "USDINR_CAUTION_LEVEL": float(os.getenv("USDINR_CAUTION_LEVEL", 84.5)),
    "EMA_PERIOD": 50
}

class SystemBias(Enum):
    RISK_ON = "RISK_ON"
    CAUTIOUS = "CAUTIOUS"
    NEUTRAL = "NEUTRAL"

class TradingRegime(Enum):
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    FROZEN = "FROZEN"
    STANDBY = "STANDBY"

MARKET_STATE = {
    "bias": SystemBias.NEUTRAL,
    "regime": TradingRegime.STANDBY,
    "safe_to_trade": True,
    "vix_current": 0.0,
    "max_call_oi_strike": None,
    "max_put_oi_strike": None,
    "ema_50": 0.0,
    "trailing_stop": 0.0,
    "brent_price": 0.0,
    "usdinr_rate": 0.0
}
""",

    "src/upstox_auth.py": """import requests
from src.config import CONFIG

def generate_access_token(auth_code):
    url = "https://api.upstox.com/v2/login/authorization/token"
    data = {
        'code': auth_code,
        'client_id': CONFIG['client_id'],
        'client_secret': CONFIG['client_secret'],
        'redirect_uri': CONFIG['redirect_uri'],
        'grant_type': 'authorization_code'
    }
    headers = {'accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
    
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        CONFIG['access_token'] = response.json()['access_token']
        print("Success: Access Token Generated")
        return CONFIG['access_token']
    else:
        raise Exception(f"Auth Failed: {response.text}")

def get_auth_headers():
    return {
        'Authorization': f'Bearer {CONFIG["access_token"]}',
        'accept': 'application/json'
    }
""",

    "src/macro_filters.py": """import yfinance as yf
from src.config import MARKET_STATE, SystemBias, CONFIG

def fetch_brent_crude():
    data = yf.Ticker("BZ=F").fast_info['last_price']
    MARKET_STATE['brent_price'] = round(data, 2)
    return MARKET_STATE['brent_price']

def fetch_usdinr():
    data = yf.Ticker("INR=X").fast_info['last_price']
    MARKET_STATE['usdinr_rate'] = round(data, 2)
    return MARKET_STATE['usdinr_rate']

def evaluate_macro_bias():
    brent = fetch_brent_crude()
    usdinr = fetch_usdinr()
    if brent > CONFIG['BRENT_CAUTION_LEVEL'] or usdinr > CONFIG['USDINR_CAUTION_LEVEL']:
        MARKET_STATE['bias'] = SystemBias.CAUTIOUS
    else:
        MARKET_STATE['bias'] = SystemBias.RISK_ON
    return MARKET_STATE['bias']
""",

    "src/oi_analysis.py": """import requests
import pandas as pd
from src.upstox_auth import get_auth_headers
from src.config import MARKET_STATE

def fetch_option_chain(instrument_key, expiry_date):
    url = f"https://api.upstox.com/v2/option/chain?instrument_key={instrument_key}&expiry_date={expiry_date}"
    response = requests.get(url, headers=get_auth_headers())
    data = response.json()['data']
    
    df = pd.DataFrame([{
        'strike': x['strike_price'],
        'call_oi': x['call_options']['market_data']['oi'],
        'put_oi': x['put_options']['market_data']['oi'],
        'call_ltp': x['call_options']['market_data']['ltp'],
        'put_ltp': x['put_options']['market_data']['ltp']
    } for x in data])
    return df

def find_oi_walls(df):
    MARKET_STATE['max_call_oi_strike'] = df.loc[df['call_oi'].idxmax()]['strike']
    MARKET_STATE['max_put_oi_strike'] = df.loc[df['put_oi'].idxmax()]['strike']
    print(f"RESISTANCE (Call Wall): {MARKET_STATE['max_call_oi_strike']}")
    print(f"SUPPORT (Put Wall): {MARKET_STATE['max_put_oi_strike']}")
""",

    "src/volatility_filter.py": """import requests
import time
from src.upstox_auth import get_auth_headers
from src.config import MARKET_STATE, CONFIG, TradingRegime

def volatility_filter():
    print("Starting 15-min India VIX window...")
    vix_readings = []
    for _ in range(15):
        url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={CONFIG['INDIA_VIX']}"
        response = requests.get(url, headers=get_auth_headers())
        vix = response.json()['data']['NSE_INDEX:India VIX']['last_price']
        
        if vix > CONFIG['VIX_FREEZE_THRESHOLD']:
            MARKET_STATE['safe_to_trade'] = False
            MARKET_STATE['regime'] = TradingRegime.FROZEN
            print(f"WARNING: VIX SPIKE {vix}. TRADING FROZEN.")
            return False
        
        vix_readings.append(vix)
        print(f"VIX Polling: {vix}")
        time.sleep(60)
    
    MARKET_STATE['safe_to_trade'] = True
    print(f"VIX Stable. Avg: {sum(vix_readings)/15}")
    return True
""",

    "src/ema_calculator.py": """import requests
import pandas as pd
from datetime import datetime, timedelta
from src.upstox_auth import get_auth_headers
from src.config import MARKET_STATE, CONFIG

def fetch_historical_candles(instrument_key):
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
    key = instrument_key.replace("|", "%7C")
    
    url = f"https://api.upstox.com/v2/historical-candle/{key}/day/{to_date}/{from_date}"
    response = requests.get(url, headers=get_auth_headers())
    candles = response.json()['data']['candles']
    
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
    df['close'] = df['close'].astype(float)
    return df.iloc[::-1] # Sort ascending

def calculate_ema_50(df):
    ema = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
    MARKET_STATE['ema_50'] = round(ema, 2)
    return MARKET_STATE['ema_50']
""",

    "src/regime_engine.py": """from src.config import MARKET_STATE, TradingRegime, CONFIG

def determine_trading_regime(current_price):
    if not MARKET_STATE['safe_to_trade']: return TradingRegime.FROZEN
    
    call_wall = MARKET_STATE['max_call_oi_strike']
    put_wall = MARKET_STATE['max_put_oi_strike']
    if not call_wall or not put_wall: return TradingRegime.STANDBY
    
    midpoint = (call_wall + put_wall) / 2
    band = (call_wall - put_wall) * 0.20
    vix_cooling = MARKET_STATE['vix_current'] < (CONFIG['VIX_FREEZE_THRESHOLD'] - 1.5)
    
    if current_price > call_wall and vix_cooling:
        res = TradingRegime.MOMENTUM
    elif abs(current_price - midpoint) < band:
        res = TradingRegime.MEAN_REVERSION
    else:
        res = TradingRegime.STANDBY
        
    MARKET_STATE['regime'] = res
    print(f"Assigned Regime: {res.name} at Price {current_price}")
    return res
""",

    "src/risk_manager.py": """from src.config import MARKET_STATE

def update_trailing_stop(current_price):
    ema_50 = MARKET_STATE['ema_50']
    proposed_stop = round(ema_50 * 0.997, 2) # 0.3% buffer
    
    if proposed_stop > MARKET_STATE['trailing_stop']:
        MARKET_STATE['trailing_stop'] = proposed_stop
        
    if current_price < MARKET_STATE['trailing_stop']:
        print("!!! STOP HIT !!! EXITING...")
        return True
    return False
""",

    "src/price_feed.py": """import requests
from src.upstox_handler import get_auth_headers

def fetch_ltp(instrument_key):
    url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={instrument_key}"
    response = requests.get(url, headers=get_auth_headers())
    key = instrument_key.replace("|", ":")
    return response.json()['data'][key]['last_price']
""",

    "src/main.py": """from src.upstox_auth import generate_access_token
from src.macro_filters import evaluate_macro_bias
from src.oi_analysis import fetch_option_chain, find_oi_walls
from src.ema_calculator import fetch_historical_candles, calculate_ema_50
from src.volatility_filter import volatility_filter
from src.price_feed import fetch_ltp
from src.regime_engine import determine_trading_regime
from src.risk_manager import update_trailing_stop
from src.config import CONFIG, MARKET_STATE

def run_premarket_intelligence(auth_code, expiry_date):
    print("--- 8:00 AM Intel Phase ---")
    generate_access_token(auth_code)
    evaluate_macro_bias()
    df_oi = fetch_option_chain(CONFIG['NIFTY_INDEX'], expiry_date)
    find_oi_walls(df_oi)
    df_hist = fetch_historical_candles(CONFIG['NIFTY_INDEX'])
    calculate_ema_50(df_hist)
    print(f"Summary: Bias={MARKET_STATE['bias'].name}, EMA50={MARKET_STATE['ema_50']}")

def run_market_open_phase():
    print("--- 9:15 AM Execution Phase ---")
    if volatility_filter():
        price = fetch_ltp(CONFIG['NIFTY_INDEX'])
        regime = determine_trading_regime(price)
        update_trailing_stop(price)
        print(f"Live: LTP={price}, Regime={regime.name}, Stop={MARKET_STATE['trailing_stop']}")
""",

    "src/scheduler.py": """from apscheduler.schedulers.blocking import BlockingScheduler
from src.main import run_premarket_intelligence, run_market_open_phase
import os

# CONFIG
AUTH_CODE = "PASTE_YOUR_CODE_HERE"
EXPIRY = "2024-05-30" # Update this weekly

scheduler = BlockingScheduler(timezone="Asia/Kolkata")

scheduler.add_job(lambda: run_premarket_intelligence(AUTH_CODE, EXPIRY), 'cron', hour=8, minute=0)
scheduler.add_job(run_market_open_phase, 'cron', hour=9, minute=15)

print("Scheduler active. Waiting for 8:00 AM...")
scheduler.start()
"""
}

# Create the files
for path, content in files.items():
    with open(path, 'w') as f:
        f.write(content.strip())
    print(f"Created: {path}")

print("\\nInitialization Complete! Follow the README to start trading.")