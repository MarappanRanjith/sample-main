# SMC Analysis and Live Bot

This repository contains three separate ways to run the project: a local dashboard, a live SMC alert scanner, and a broader live market-data loop. They are separate programs; do not run every Python file. Choose one command from the table below.

## 1. Set Up on Windows

Open PowerShell in the repository root (`C:\sample-main`) and create a virtual environment:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The execution-policy command only applies to the current PowerShell session. If the virtual environment is already active and dependencies are installed, skip setup and continue to the run commands.

## 2. Choose What to Run

| Command | What it runs | Upstox token needed? |
| --- | --- | --- |
| `python app.py` | Local dashboard. Load demo candles or upload JSON/CSV. | No |
| `python live_bot.py` | Live SMC scanner. Checks market data and writes alerts to `Live_Sniper_Alerts.csv`. | Yes |
| `python -m src.live_bot.main` | Broader live market-data checks and logging. Trade execution is disabled; it logs data-check signals only. | Yes |
| `python -m src.live_bot.backtester` | Historical-data backtest; writes an Excel report or a CSV fallback. | Yes |
| `python -m unittest discover -s tests` | Runs the local automated tests. | No |

For the dashboard, open <http://127.0.0.1:5000> after starting `python app.py`. Stop any running program with `Ctrl+C`. Live commands call Upstox; use a valid token and avoid running multiple live scanners at the same time.

## 3. Configure Live Access

Only the live scanner, full live data loop, and backtester need Upstox credentials. Create a `.env` file in the repository root with your own token:

```dotenv
UPSTOX_ACCESS_TOKEN=your_access_token
```

Keep the real token private. `.env` is ignored by Git and must not be committed. The token may expire; if Upstox returns an authorization error, obtain a current token from Upstox and update `.env`.

## 4. Candle Data Format

The dashboard's demo data is [data/demo_candles.json](data/demo_candles.json). JSON can be a candle array or an object with a `candles` array. Rows must be oldest first and include `time`, `open`, `high`, `low`, and `close`; `volume` is optional. At least 3 candles are required, and about 100 or more provide better premium/discount context. Existing CSV candle uploads are still supported.

```json
{
  "candles": [
    {"time": "2026-09-30T09:15:00+05:30", "open": 25000, "high": 25010, "low": 24990, "close": 25005, "volume": 1200},
    {"time": "2026-09-30T09:16:00+05:30", "open": 25005, "high": 25012, "low": 25001, "close": 25008, "volume": 1300},
    {"time": "2026-09-30T09:17:00+05:30", "open": 25008, "high": 25015, "low": 25006, "close": 25012, "volume": 1100}
  ]
}
```

## 5. Folder Guide

```text
app.py                    Dashboard launcher
live_bot.py               Live SMC scanner launcher
data/                     Shared JSON datasets
src/framework/            Shared candle validation and analysis engine
src/smc/                  SMC calculations, strategy, and dashboard service
src/live_bot/             Live scanner, full data loop, backtester, and support code
templates/ and static/    Dashboard page and browser assets
tests/                    Automated tests
```

Add another analysis strategy under `src/smc` or a future strategy package, using the shared candle contract in `src/framework`.

## Generated Files

Logs, `.env`, Python cache folders, live alert CSVs, and backtest reports are runtime output, not source code. Git ignores them so they will not be included when you commit. Existing logs and reports are left on disk; remove them manually only when you no longer need their contents.