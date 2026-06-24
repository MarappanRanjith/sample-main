# Terminal Navigation & Setup Guide

## 1. Find Your Local Repository Path

Your workspace is stored locally. Find it using PowerShell:

```powershell
# Search for the sample_practise folder
Get-ChildItem -Path C:\Users\RanjithkumarMarappan -Directory -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq 'sample_practise' }
```

Once found, note the **FullName** path (it will look like `C:\Users\...\sample\sample_practise`).

## 2. Open Terminal in Project Folder

### Option A: Using VS Code
1. Open VS Code
2. File → Open Folder
3. Navigate to the `sample_practise` folder
4. Terminal → New Terminal (Ctrl + `)
5. You're now in the project directory

### Option B: Using PowerShell Manually
```powershell
cd C:\path\to\sample_practise
```

## 3. Install Dependencies

From inside the `sample_practise` folder:

```powershell
pip install -r requirements.txt
```

This installs:
- requests
- pandas
- numpy
- yfinance
- apscheduler
- python-dotenv
- pytz

## 4. Configure Your Upstox API Credentials

Edit the `.env` file in the `sample_practise` folder:

```env
# .env
# Upstox API Credentials (get these from https://upstox.com/developer)
UPSTOX_API_KEY=YOUR_CLIENT_ID_HERE
UPSTOX_API_SECRET=YOUR_CLIENT_SECRET_HERE
UPSTOX_ACCESS_TOKEN=YOUR_BEARER_TOKEN_HERE
UPSTOX_REDIRECT_URI=http://localhost:8080/callback

# Trading Parameters (adjust as needed)
VIX_FREEZE_THRESHOLD=16.5
BRENT_CAUTION_LEVEL=90.0
USD_INR_HIGH_RATE=84.5
EMA_PERIOD=50
```

### How to Get Your Access Token:

1. Go to [Upstox Developer Console](https://upstox.com/developer)
2. Create an API application
3. Get your `Client ID` and `Client Secret`
4. Use the OAuth flow to get an `access_token` (or you can generate one manually via their docs)
5. Paste the access token into the `.env` file

## 5. Run the Bot (Data Validation Mode)

From the `sample_practise` folder:

```powershell
python src/main.py
```

### What to Expect:

- The bot will run through pre-market analysis at 8:00 AM IST
- During market hours (9:15 AM - 3:30 PM IST), it will:
  - Fetch live Nifty LTP every 5 seconds
  - Fetch live India VIX every 5 seconds
  - Log all data received to `logs/trading_bot.log` and console
  - Print trading mode decisions (Momentum, Mean-Reversion, Neutral)
  - **NOT execute any trades** (data validation mode only)

### Example Output:

```
2026-01-15 08:00:00 - INFO - ============================================================
2026-01-15 08:00:00 - INFO - 🟢 PRE-MARKET ANALYSIS (8:00 AM IST)
2026-01-15 08:00:00 - INFO - ============================================================
2026-01-15 08:00:05 - INFO - ✓ Brent Crude price: $88.45
2026-01-15 08:00:06 - INFO - ✓ USD/INR rate: 84.32
2026-01-15 08:00:07 - INFO - ✓ System Bias: Risk-On / Buy on Dips
2026-01-15 08:00:15 - INFO - ✓ Max Call OI Strike: 23100
2026-01-15 08:00:15 - INFO - ✓ Max Put OI Strike: 22900
2026-01-15 08:00:25 - INFO - ✓ 50-day EMA calculated: 22980.45
```

## 6. Check the Logs

All trading bot activity is logged to:

```
sample_practise/logs/trading_bot.log
```

View in PowerShell:
```powershell
Get-Content logs/trading_bot.log -Tail 50  # Last 50 lines
Get-Content logs/trading_bot.log -Wait    # Real-time follow
```

## 7. Troubleshooting

### Error: ModuleNotFoundError (yfinance, requests, etc.)
```powershell
pip install --upgrade -r requirements.txt
```

### Error: UPSTOX_ACCESS_TOKEN not set
- Make sure your `.env` file is in the `sample_practise` folder (not in `src/`)
- Verify the token is not empty

### Error: API returns 401 Unauthorized
- Your access token is expired or invalid
- Get a fresh one from Upstox Developer Console

### Bot not running at market times
- Verify your system timezone is set to IST (Asia/Kolkata)
- Or manually adjust the times in `src/config.py`

## Next Steps After Data Validation

Once you've confirmed data is flowing correctly:

1. Check the logs for accuracy of Brent Crude, USD/INR, EMA, OI levels
2. Verify VIX and LTP are updating every 5 seconds
3. Confirm trading mode decisions make sense
4. Then implement actual order placement in `execute_trade_signal()`
