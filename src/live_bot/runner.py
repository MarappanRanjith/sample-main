import time
import datetime
import os
import csv
import winsound
from src.live_bot.data_fetcher import DataFetcher
from src.smc.analyzer import SMCAnalyzer
from src.live_bot.utils import logger


def format_upstox_time(iso_time_str):
    """Convert an Upstox timestamp to a readable 12-hour format."""
    try:
        dt = datetime.datetime.fromisoformat(iso_time_str)
        return dt.strftime('%d-%b-%Y %I:%M %p')
    except Exception:
        return iso_time_str


def main():
    data_fetcher = DataFetcher()
    target_indices = ["NIFTY", "BANKNIFTY", "NIFTYIT"]
    last_alerted_fvg_time = {index: None for index in target_indices}
    alert_filename = "Live_Sniper_Alerts.csv"

    print("\n" + "=" * 60)
    print("🎯 Multi-Index SMC Sniper Bot Active")
    print(f"Tracking: {', '.join(target_indices)}")
    print("Threshold: Score >= 2 (Target: 3-5 trades/day per index)")
    print("Listening for High-Confluence Setups...")
    print("=" * 60 + "\n")

    while True:
        now = datetime.datetime.now()
        current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

        if now.weekday() >= 5:
            print(f"[{current_time_str}] Weekend. Market is closed. Sleeping for 1 hour...")
            time.sleep(3600)
            continue

        market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)

        if now < market_start or now > market_end:
            print(f"[{current_time_str}] Outside market hours (09:15 AM - 03:30 PM). Sleeping for 5 minutes...")
            time.sleep(300)
            continue

        for index_name in target_indices:
            print(f"[{current_time_str}] Scanning {index_name}...")
            symbol = data_fetcher.get_current_futures_symbol(index_name)

            if symbol:
                candles = data_fetcher.get_recent_candles(symbol, interval="1minute", count=150)

                if candles:
                    fvgs = SMCAnalyzer.analyze_fvgs(candles)
                    enriched_fvgs = SMCAnalyzer.enrich_with_confluence(candles, fvgs)
                    sniper_setups = [fvg for fvg in enriched_fvgs if fvg['confluence_count'] >= 2]

                    if sniper_setups:
                        latest_setup = sniper_setups[-1]
                        if latest_setup['time'] != last_alerted_fvg_time[index_name]:
                            last_alerted_fvg_time[index_name] = latest_setup['time']
                            displacement_index = latest_setup['creation_index'] - 1

                            if displacement_index < len(candles):
                                displacement_candle = candles[displacement_index]
                                volume_average = max(displacement_candle.get('vol_sma_20', 1), 1)
                                volume_surge = round(displacement_candle.get('volume', 0) / volume_average, 1)
                            else:
                                volume_surge = 0.0

                            formatted_candle_time = format_upstox_time(latest_setup['time'])
                            try:
                                winsound.Beep(1000, 1500)
                            except Exception:
                                pass

                            confluence = latest_setup['confluence']
                            passed_checks = []
                            if confluence['htf_aligned']:
                                passed_checks.append("HTF Bias")
                            if confluence['zone_aligned']:
                                passed_checks.append("PD Zone")
                            if confluence['liquidity_sweep']:
                                passed_checks.append("Sweep")
                            if confluence['ob_confluence']:
                                passed_checks.append("Order Block")
                            passed_text = ", ".join(passed_checks) if passed_checks else "None"

                            print("\n" + "🔥" * 20)
                            print(f"🚨 {index_name} SNIPER SETUP DETECTED! 🚨")
                            print(f"Type: {latest_setup['type']}")
                            print(f"Candle Time: {formatted_candle_time}")
                            print(f"Entry Zone: {latest_setup['bottom']} - {latest_setup['top']}")
                            print(f"Volume Surge: {volume_surge}x")
                            print(f"Confluence Score: {latest_setup['confluence_count']}/4")
                            print(f"Passed Checks: [{passed_text}]")
                            print("🔥" * 20 + "\n")

                            file_exists = os.path.isfile(alert_filename)
                            try:
                                with open(alert_filename, mode='a', newline='') as alert_file:
                                    writer = csv.writer(alert_file)
                                    if not file_exists:
                                        writer.writerow([
                                            'Instrument', 'Detected Time', 'Candle Time', 'Type',
                                            'Bottom (Entry)', 'Top (Entry)', 'Gap Size', 'Volume Surge',
                                            'HTF Bias', 'Zone', 'Liquidity Sweep', 'OB Overlap',
                                            'Score', 'Passed Checks'
                                        ])

                                    writer.writerow([
                                        index_name,
                                        current_time_str,
                                        formatted_candle_time,
                                        latest_setup['type'],
                                        latest_setup['bottom'],
                                        latest_setup['top'],
                                        latest_setup['gap_size'],
                                        f"{volume_surge}x",
                                        confluence['htf_bias'],
                                        confluence['zone'],
                                        confluence['liquidity_sweep'],
                                        confluence['ob_confluence'],
                                        latest_setup['confluence_count'],
                                        passed_text
                                    ])
                                print(f"💾 Saved {index_name} setup to {alert_filename}")
                            except Exception as exc:
                                print(f"❌ Failed to save to CSV: {exc}")
                    else:
                        print(f"No new setups meeting Score >= 2 found for {index_name}.")

            time.sleep(2)

        print("-" * 40)
        time.sleep(60)


if __name__ == "__main__":
    main()
