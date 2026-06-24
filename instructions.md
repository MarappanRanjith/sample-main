# Upstox Trading Bot - Setup & Data Validation Guide

**Last Updated:** 2026-06-15  
**Current Phase:** Data Validation Mode (No Trading Yet)

## Quick Start

```powershell
cd sample_practise
pip install -r requirements.txt
# Update .env with Upstox credentials
python src/main.py
```

---

## 📋 Conversation Summary (Session Notes)

### What We Analyzed
- Reviewed the current `sample_practise` project structure
- Checked Upstox API request structure documentation
- Identified placeholder code that needed real implementation
- Confirmed NO trading should be triggered yet — data validation first

### Changes Made (June 15, 2026)

#### 1. **upstox_handler.py** — Real API Integration
- ✅ Added proper Upstox request headers: `Accept: application/json` + `Authorization: Bearer {token}`
- ✅ Implemented `generate_access_token()` for OAuth flow
- ✅ Real methods: `get_options_chain()`, `get_historical_data()`, `get_live_quote()`, `place_order()`
- ✅ All functions use URL encoding for symbols and error handling
- ❌ Removed all placeholder stubs that returned `None`

#### 2. **data_fetcher.py** — Working Data Sources
- ✅ Replaced placeholder external APIs with **yfinance**:
  - Brent Crude: `yf.Ticker("BZ=F")` 
  - USD/INR: `yf.Ticker("INR=X")`
- ✅ Added `get_ema_data()` with proper Upstox historical candle parsing
- ✅ Added `find_max_oi_strikes()` for OI analysis
- ✅ All methods include detailed logging (✓ symbols for success)

#### 3. **websocket_handler.py** — REST API LTP Polling
- ✅ Replaced fake WebSocket with real REST API calls
- ✅ Polling thread fetches LTP every 5 seconds for:
  - NSE_INDEX|Nifty 50
  - NSE_INDEX|Nifty Bank
  - NSE_INDEX|India VIX
- ✅ Background thread keeps data current
- ✅ Logs snapshot every 30 seconds

#### 4. **trading_logic.py** — Enhanced Analysis + Data Logging
- ✅ Added `get_current_weekly_expiry_date()` — calculates next Wednesday
- ✅ Improved macro bias logic with proper thresholds
- ✅ Better OI cluster detection and parsing
- ✅ **Trade execution DISABLED** — logs `[DATA CHECK MODE]` instead
- ✅ Visual indicators (✓, ▶, 🟢, 🚨) for easy log reading
- ✅ All data checks logged with prices/values

#### 5. **config.py** — Cleanup
- ✅ Added `UPSTOX_BASE_URL` and `UPSTOX_AUTH_URL` constants
- ✅ Removed placeholder external API URLs

#### 6. **main.py** — Bug Fix
- ✅ Fixed WebSocket handler to use `UPSTOX_ACCESS_TOKEN` from config (not invalid handler attribute)

---

## 🚀 How to Run

### Terminal Navigation

**Find your local project:**
```powershell
Get-ChildItem -Path C:\Users\RanjithkumarMarappan -Directory -Recurse -ErrorAction SilentlyContinue | 
  Where-Object { $_.Name -eq 'sample_practise' }
```

**Navigate to the folder:**
```powershell
cd C:\path\to\sample_practise  # Use the path from above
```

### Install Dependencies

```powershell
pip install -r requirements.txt
```

Installs: requests, pandas, numpy, yfinance, apscheduler, python-dotenv, pytz

### Configure `.env`

Edit `sample_practise/.env`:

```env
# Upstox Credentials (from https://upstox.com/developer)
UPSTOX_API_KEY=your_client_id
UPSTOX_API_SECRET=your_client_secret
UPSTOX_ACCESS_TOKEN=your_bearer_token

# Trading Parameters
VIX_FREEZE_THRESHOLD=16.5
BRENT_CAUTION_LEVEL=90.0
EMA_PERIOD=50
```

### Run the Bot

```powershell
python src/main.py
```

---

## 📊 Expected Behavior

### Timeline

| Time (IST) | Action | What You'll See |
|---|---|---|
| Before 8:00 AM | Waiting | (Silent) |
| **8:00 AM** | Pre-Market Analysis | ✓ Brent Crude, USD/INR, OI Walls, EMA(50) logged |
| **9:15 AM** | Market Opens | LTP polling starts (every 5 sec) |
| **9:15-9:30 AM** | Volatility Window | VIX checked, longs frozen if VIX > 16.5 |
| **9:30 AM-3:30 PM** | Live Trading Checks | Trading mode logged (Momentum/Mean-Reversion/Neutral) |
| **After 3:30 PM** | Market Close | Bot exits gracefully |

### Example Log Output

```
2026-01-15 08:00:00,123 - INFO - ============================================================
2026-01-15 08:00:00,124 - INFO - 🟢 PRE-MARKET ANALYSIS (8:00 AM IST)
2026-01-15 08:00:00,125 - INFO - ============================================================
2026-01-15 08:00:05,456 - INFO - ▶ Evaluating macro filters...
2026-01-15 08:00:06,789 - INFO - ✓ Brent Crude price: $88.45
2026-01-15 08:00:07,123 - INFO - ✓ USD/INR rate: 84.32
2026-01-15 08:00:08,456 - INFO - ✓ System Bias: Risk-On / Buy on Dips
2026-01-15 08:00:15,789 - INFO - ✓ Max Call OI Strike: 23100 (OI: 1250000)
2026-01-15 08:00:15,801 - INFO - ✓ Max Put OI Strike: 22900 (OI: 1180000)
2026-01-15 08:00:25,234 - INFO - ✓ 50-day EMA calculated: 22980.45
2026-01-15 09:15:00,500 - INFO - LTP polling thread started.
2026-01-15 09:15:05,678 - DEBUG - LTP NSE_INDEX:Nifty 50: 23050.25
2026-01-15 09:15:06,789 - DEBUG - LTP NSE_INDEX:India VIX: 15.80
2026-01-15 09:15:10,234 - INFO - ✓ VIX OK: 15.80 <= 16.5 → Safe for longs
2026-01-15 09:15:11,456 - INFO - ✓ Mode: Momentum | Nifty LTP: 23050.25 | Safe for Longs: True
2026-01-15 09:15:11,789 - INFO - 🔍 [DATA CHECK MODE] Trading Mode: Momentum
2026-01-15 09:15:11,801 - INFO -    System Bias: Risk-On / Buy on Dips
2026-01-15 09:15:11,812 - INFO -    EMA(50): 22980.45
2026-01-15 09:15:11,823 - INFO -    OI Support: 22900 | Resistance: 23100
```

---

## ✅ Data Validation Checklist

Run the bot and verify:

- [ ] **Pre-market (8:00 AM):**
  - Brent Crude price fetched ✓
  - USD/INR rate fetched ✓
  - System bias determined ✓
  - OI walls identified ✓
  - EMA(50) calculated ✓

- [ ] **Market open (9:15 AM):**
  - Nifty LTP updating every 5 sec ✓
  - India VIX updating every 5 sec ✓
  - VIX check completed ✓
  - Trading mode determined ✓

- [ ] **Live trading (9:15 - 3:30 PM):**
  - Data logged but NO orders placed ✓
  - Mode changes logged ✓
  - All data values appear reasonable ✓

- [ ] **Logging:**
  - `logs/trading_bot.log` created ✓
  - Console output matches file ✓

---

## 📁 Key Files Reference

| File | Purpose | Status |
|---|---|---|
| `src/config.py` | API credentials, thresholds, market times | ✅ Updated |
| `src/upstox_handler.py` | Upstox API wrapper | ✅ Implemented |
| `src/data_fetcher.py` | Brent, USD/INR, historical data | ✅ Implemented |
| `src/websocket_handler.py` | LTP polling via REST | ✅ Implemented |
| `src/trading_logic.py` | Analysis, mode detection, logging | ✅ Implemented (trades disabled) |
| `src/main.py` | Orchestrator, scheduler, market timing | ✅ Fixed |
| `src/utils.py` | Logging setup | ✓ Working |
| `.env` | Credentials (YOU must fill) | ⚠️ Action needed |
| `logs/trading_bot.log` | Runtime logs | 📝 Generated at runtime |

---

## 🔧 Troubleshooting

### Error: ModuleNotFoundError

```powershell
pip install --upgrade -r requirements.txt
```

### Error: UPSTOX_ACCESS_TOKEN not set

- Check `.env` is in `sample_practise/` folder (not `sample_practise/src/`)
- Verify token is not empty
- Get fresh token from [Upstox Developer Console](https://upstox.com/developer)

### Error: API returns 401 Unauthorized

- Access token is expired
- Generate new token via Upstox OAuth flow
- Update `.env` and restart bot

### Bot not running at expected times

- Check system timezone is IST (Asia/Kolkata)
- Or manually adjust times in `src/config.py`:
  ```python
  MARKET_OPEN_TIME = datetime.time(9, 15, 0)      # IST
  PRE_MARKET_ANALYSIS_TIME = datetime.time(8, 0, 0)  # IST
  ```

### LTP not updating

- Verify Upstox access token is valid
- Check network connectivity
- Monitor `logs/trading_bot.log` for API errors

---

## 📝 Next Steps (After Data Validation)

Once all data is flowing correctly:

1. ✅ Verify Brent Crude, USD/INR, OI, EMA, VIX, LTP are accurate
2. ✅ Confirm trading mode decisions align with market
3. ✅ Check logs for any API errors or missing data
4. ⏭️ Then: Implement actual order placement in `execute_trade_signal()`

---

## 1. Project Overview

The system automates trading strategies for Nifty 50 and Bank Nifty based on:
- **Pre-market analysis** (8:00 AM IST): Macro factors, OI clusters, EMA
- **Market open phase** (9:15 AM): Volatility filter check
- **Live trading** (9:15 AM - 3:30 PM): Real-time mode detection and signals

## 2. System Architecture (Modules)

*   `config.py`: Configuration, API keys, thresholds, market times
*   `upstox_handler.py`: Upstox API wrapper (auth, data, orders)
*   `data_fetcher.py`: Macro data (yfinance), historical, EMA
*   `websocket_handler.py`: LTP polling via REST API
*   `trading_logic.py`: Analysis engine, bias, OI, VIX, mode detection
*   `main.py`: Main orchestrator and scheduler
*   `utils.py`: Logging setup
*   `.env`: Credentials (you must configure)

## 3. Project Setup Steps

### Step 3.1: Install Dependencies

```powershell
cd sample_practise
pip install -r requirements.txt
```

### Step 3.2: Configure `.env`

Edit `.env` in `sample_practise/` root:

```env
UPSTOX_API_KEY=your_client_id
UPSTOX_API_SECRET=your_client_secret
UPSTOX_ACCESS_TOKEN=your_bearer_token
UPSTOX_REDIRECT_URI=http://localhost:8080/callback

# Trading Parameters
VIX_FREEZE_THRESHOLD=16.5
BRENT_CAUTION_LEVEL=90.0
USD_INR_HIGH_RATE=84.5
EMA_PERIOD=50
```

### Step 3.3: Run the Bot

```powershell
python src/main.py
```

## 4. Running the System

1. Navigate to `sample_practise` folder
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` with Upstox credentials
4. Run: `python src/main.py`
5. Monitor logs: `Get-Content logs/trading_bot.log -Tail 50`

## 5. Understanding the Output

*   **Console & Log File**: All trading bot events, data fetches, analysis results
*   **Pre-Market (8:00 AM)**: Macro data, OI levels, EMA logged
*   **Market Open (9:15 AM)**: VIX checked, trading mode determined
*   **Trading Session**: LTP updates, mode changes, data validation logged
*   **NO TRADES**: Currently in data validation mode only

## 6. Key Functionality Explanations

*   **Pre-Market Analysis**: Fetches macro, OI, EMA; determines system bias
*   **Volatility Filter**: Checks India VIX; freezes longs if > 16.5
*   **Trading Mode**: Momentum (price > resistance), Mean-Reversion (near OI walls), Neutral
*   **Data Validation**: All data logged but NO orders placed

## 7. Next Steps & Further Development

*   **Data Validation**: Verify all data sources working correctly ✓ (Current Phase)
*   **Trade Execution**: Implement buy/sell orders in `execute_trade_signal()`
*   **Token Refresh**: Add automatic access token refresh before expiry
*   **WebSocket Integration**: Optional upgrade from REST to WebSocket for faster data
*   **Backtesting**: Test strategy on historical data
*   **Paper Trading**: Test on Upstox paper trading account

## 8. Important Considerations

*   **API Rate Limits**: Be mindful of Upstox rate limits; add delays if needed
*   **Security**: Never share `.env` file or commit to public repos
*   **Testing**: Thoroughly test before live trading
*   **Timezone**: Ensure system timezone is IST (Asia/Kolkata)

*   **Action:** Copy the provided code content into each respective `.py` file created in the previous step. Refer to the previous detailed response for the full code for each file (`config.py`, `upstox_handler.py`, etc.).

### Step 3.6: Initial Authorization (`UPSTOX_AUTH_CODE`)

*   **Action:** Obtain the initial authorization code required for Upstox authentication.
*   **Procedure:**
    1.  Run the main script once to trigger the authorization prompt:
        ```bash
        python src/scheduler.py
        ```
        *(Note: You might need to run `python src/main.py` first if `scheduler.py` doesn't trigger the initial auth prompt correctly. The goal is to execute code that calls `get_auth_code_from_user()`)*
    2.  The script will display a URL. Open it in your browser.
    3.  Log in to your Upstox account and authorize the application.
    4.  You'll be redirected to your `REDIRECT_URI` with an `auth_code` in the URL. Copy this code.
    5.  Paste the copied `auth_code` into the `UPSTOX_AUTH_CODE=` line in your `.env` file. This is crucial for future runs.

## 4. Running the System

1.  **Navigate to Project Root:**
    Open your terminal or command prompt and navigate to the main project directory:
    ```bash
    cd path/to/your/upstox_trading_bot
    ```

2.  **Run the Scheduler:**
    Execute the scheduler script, which manages the timing of all operations:
    ```bash
    python src/scheduler.py
    ```
    *   The scheduler will start and wait for the configured times (8:00 AM and 9:15 AM IST daily) to trigger the analysis and trading phases.
    *   The script will run continuously until you stop it (usually by pressing `Ctrl+C`).

## 5. Understanding the Output

*   **Console:** You'll see log messages detailing the script's progress, analysis results, VIX checks, regime determination, and any errors encountered.
*   **Log File:** All logs are also saved in `logs/trading_bot.log` for review.

## 6. Key Functionality Explanations

*   **Pre-Market (8:00 AM):** `run_premarket_intelligence` fetches macro data, OI levels, and EMA, then prints a summary.
*   **Market Open (9:15 AM):** `run_market_open_phase` checks the India VIX. If VIX is high, it freezes long entries. Otherwise, it determines the market regime and sets initial stop-losses.
*   **Trading Session (Post 9:15 AM):** `run_trading_session` (triggered by the scheduler shortly after market open) continuously monitors the market, checks the regime, updates trailing stops, and would execute trades (requires further implementation).

## 7. Next Steps & Further Development

*   **Trade Execution:** The current code focuses on analysis and monitoring. You **must** add the logic to place actual buy/sell orders using `upstox_client.place_order()` based on the determined regime and signals. This includes managing positions and handling exits.
*   **Token Refresh:** Implement automatic refreshing of the Upstox `access_token` using the `refresh_token` before it expires (typically daily).
*   **WebSocket Integration:** For real-time data needs (like continuous VIX monitoring or faster price updates), consider integrating Upstox's WebSocket feed.
*   **Robust Error Handling:** Enhance error handling with retry mechanisms for API calls and better failure recovery strategies.
*   **Backtesting:** Develop a separate backtesting framework to test your strategy's performance on historical data before live trading.
*   **Paper Trading:** Test the complete system thoroughly on a Upstox paper trading account before risking real capital.

## 8. Important Considerations

*   **API Rate Limits:** Be mindful of Upstox API rate limits. Add delays or backoff strategies if you encounter `429` errors.
*   **Security:** Never share your `.env` file or commit it to public repositories.
*   **Testing:** Thoroughly test all components, especially trading logic and risk management, in a simulated environment.