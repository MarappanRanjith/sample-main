# SMC Analysis Framework

The project shares one validated OHLCV candle format across analysis strategies. SMC is the first registered strategy and detects fair value gaps, order blocks, higher-timeframe bias, liquidity sweeps, and premium/discount confluence. The dashboard runs in analysis-only mode and does not place orders.

## Project Map

```text
data/                         Shared JSON datasets
src/framework/data.py         Candle schema, validation, JSON and CSV readers
src/framework/engine.py       Strategy registry and common analysis entry point
src/framework/strategies/     Strategy implementations (currently SMC)
src/smc_analyzer.py           SMC pattern calculations
src/smc_service.py            Compatibility entry point used by the dashboard
src/live_bot/runner.py        Live SMC scanner implementation
live_bot.py                   Executable launcher for the live scanner
templates/                    Dashboard HTML
static/                       Dashboard styles and browser code
tests/                        Framework contract tests
```

To add another analysis type, implement an `analyze(candles, **options)` strategy and register it with `AnalysisFramework`. It receives the same normalized candles as SMC.

## Candle JSON Format

JSON can be either a candle array or an object with a `candles` array. Rows must be oldest first and use `time`, `open`, `high`, `low`, `close`, and optional `volume` fields. The built-in example is [data/demo_candles.json](data/demo_candles.json).

```json
{
	"candles": [
		{"time": "2026-09-30T09:15:00+05:30", "open": 25000, "high": 25010, "low": 24990, "close": 25005, "volume": 1200},
		{"time": "2026-09-30T09:16:00+05:30", "open": 25005, "high": 25012, "low": 25001, "close": 25008, "volume": 1300},
		{"time": "2026-09-30T09:17:00+05:30", "open": 25008, "high": 25015, "low": 25006, "close": 25012, "volume": 1100}
	]
}
```

At least three candles are required. About 100 or more candles provide better premium/discount context. CSV upload remains available for existing datasets.

## Run

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. For the live SMC scanner, configure `.env` with an Upstox access token and run `python live_bot.py`. The separate full trading-data loop can be run with `python src/main.py`. The dashboard itself does not place orders.

## Test

```powershell
python -m unittest discover -s tests
```