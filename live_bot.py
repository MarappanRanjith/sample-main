import time
import datetime
import os
import csv
import winsound
from src.data_fetcher import DataFetcher
from src.smc_analyzer import SMCAnalyzer
from src.utils import logger
from src.config import (
    CANDLE_FETCH_COUNT,
    CONFLUENCE_THRESHOLD,
    MARKET_OPEN_TIME,
    MARKET_CLOSE_TIME,
)

def format_upstox_time(iso_time_str):
    """Converts Upstox ISO timestamp to a readable format like 22-Jun-2026 11:33 AM."""
    try:
        # Parse the ISO format string (handles timezone offsets like +05:30)
        dt = datetime.datetime.fromisoformat(iso_time_str)
        return dt.strftime('%d-%b-%Y %I:%M %p')
    except Exception:
        return iso_time_str  # Fallback to original if parsing fails

def main():
    data_fetcher = DataFetcher()
    
    # 1. Track multiple instruments
    target_indices = ["NIFTY", "BANKNIFTY", "NIFTYIT"]
    
    # 2. Dictionary to track the last alerted time for EACH instrument separately
    last_alerted_fvg_time = {index: None for index in target_indices}
    
    alert_filename = "Live_Sniper_Alerts.csv"
    
    print("\n" + "="*60)
    print("🎯 Multi-Index SMC Sniper Bot Active")
    print(f"Tracking: {', '.join(target_indices)}")
    print(f"Threshold: Score >= {CONFLUENCE_THRESHOLD} (Dynamic from config)")
    print("Listening for High-Confluence Setups...")
    print("="*60 + "\n")

    while True:
        now = datetime.datetime.now()
        current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # --- MARKET HOURS CHECK ---
        if now.weekday() >= 5:
            print(f"[{current_time_str}] Weekend. Market is closed. Sleeping for 1 hour...")
            time.sleep(3600)
            continue
            
        market_start = now.replace(
        hour=MARKET_OPEN_TIME.hour,
        minute=MARKET_OPEN_TIME.minute,
        second=0, microsecond=0
        )
        market_end = now.replace(
            hour=MARKET_CLOSE_TIME.hour,
            minute=MARKET_CLOSE_TIME.minute,
            second=0, microsecond=0
        )
        
        if now < market_start or now > market_end:
            print(f"[{current_time_str}] Outside market hours (09:15 AM - 03:30 PM). Sleeping for 5 minutes...")
            time.sleep(300)
            continue

        # --- PARALLEL/SEQUENTIAL SCANNING ---
        for index_name in target_indices:
            print(f"[{current_time_str}] Scanning {index_name}...")
            
            symbol = data_fetcher.get_current_futures_symbol(index_name)
            
            if symbol:
                candles = data_fetcher.get_recent_candles(symbol, interval="1minute", count=CANDLE_FETCH_COUNT)
                
                if candles:
                    fvgs = SMCAnalyzer.analyze_fvgs(candles)
                    enriched_fvgs = SMCAnalyzer.enrich_with_confluence(candles, fvgs)
                    
                    # Threshold lowered from 3 to 2 to allow 3-5 entries per day
                    sniper_setups = [f for f in enriched_fvgs if f['confluence_count'] >= CONFLUENCE_THRESHOLD]
                    
                    if sniper_setups:
                        latest_setup = sniper_setups[-1] 
                        
                        # Check if we already alerted for this specific candle ON THIS SPECIFIC INDEX
                        if latest_setup['time'] != last_alerted_fvg_time[index_name]:
                            last_alerted_fvg_time[index_name] = latest_setup['time']
                            
                            c2_idx = latest_setup['creation_index'] - 1
                            if c2_idx < len(candles):
                                displacement_candle = candles[c2_idx]
                                vol_sma = max(displacement_candle.get('vol_sma_20', 1), 1) 
                                vol_surge = round(displacement_candle.get('volume', 0) / vol_sma, 1)
                            else:
                                vol_surge = 0.0

                            formatted_candle_time = format_upstox_time(latest_setup['time'])
                            
                            try:
                                winsound.Beep(1000, 1500) 
                            except Exception:
                                pass 
                                
                            # Build a string showing exactly WHICH confluences passed
                            passed_checks = []
                            if latest_setup['confluence']['htf_aligned']: passed_checks.append("HTF Bias")
                            if latest_setup['confluence']['zone_aligned']: passed_checks.append("PD Zone")
                            if latest_setup['confluence']['liquidity_sweep']: passed_checks.append("Sweep")
                            if latest_setup['confluence']['ob_confluence']: passed_checks.append("Order Block")
                            passed_str = ", ".join(passed_checks) if passed_checks else "None"

                            print("\n" + "🔥"*20)
                            print(f"🚨 {index_name} SNIPER SETUP DETECTED! 🚨")
                            print(f"Type: {latest_setup['type']}")
                            print(f"Candle Time: {formatted_candle_time}")
                            print(f"Entry Zone: {latest_setup['bottom']} - {latest_setup['top']}")
                            print(f"Volume Surge: {vol_surge}x")
                            print(f"Confluence Score: {latest_setup['confluence_count']}/4")
                            print(f"Passed Checks: [{passed_str}]")
                            print("🔥"*20 + "\n")
                            
                            file_exists = os.path.isfile(alert_filename)
                            try:
                                with open(alert_filename, mode='a', newline='') as file:
                                    writer = csv.writer(file)
                                    if not file_exists:
                                        writer.writerow(['Instrument', 'Detected Time', 'Candle Time', 'Type', 'Bottom (Entry)', 'Top (Entry)', 'Gap Size', 'Volume Surge', 'HTF Bias', 'Zone', 'Liquidity Sweep', 'OB Overlap', 'Score', 'Passed Checks'])
                                    
                                    writer.writerow([
                                        index_name,  # Added the instrument name to the CSV!
                                        current_time_str,
                                        formatted_candle_time,
                                        latest_setup['type'],
                                        latest_setup['bottom'],
                                        latest_setup['top'],
                                        latest_setup['gap_size'],
                                        f"{vol_surge}x",
                                        latest_setup['confluence']['htf_bias'],
                                        latest_setup['confluence']['zone'],
                                        latest_setup['confluence']['liquidity_sweep'],
                                        latest_setup['confluence']['ob_confluence'],
                                        latest_setup['confluence_count'],
                                        passed_str
                                    ])
                                print(f"💾 Saved {index_name} setup to {alert_filename}")
                            except Exception as e:
                                print(f"❌ Failed to save to CSV: {e}")
                                
                    else:
                        print(f"No new setups meeting Score >= 2 found for {index_name}.")
            
            # Brief 2-second pause between each index so we don't trigger Upstox API Rate Limits
            time.sleep(2)
            
        # Sleep for 60 seconds before scanning the next minute's candles for all 3 indices
        print("-" * 40)
        time.sleep(60)

if __name__ == "__main__":
    main()