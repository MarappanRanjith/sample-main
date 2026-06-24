# src/signal_engine.py — Simplified skeleton

from src.smc_analyzer import SMCAnalyzer
from src.config import CONFLUENCE_THRESHOLD

class SignalEngine:
    def __init__(self):
        self.analyzer = SMCAnalyzer()
        self.seen_fvg_ids = set()  # For dedup using ENH #2

    def process_candles(self, candles, symbol="NIFTY"):
        # 1. Filter to current session only (ENH #9)
        session_candles = self.analyzer.filter_current_session_candles(candles)

        # 2. Detect FVGs
        fvgs = self.analyzer.analyze_fvgs(session_candles, symbol=symbol)

        # 3. Filter: valid + not seen before
        active_fvgs = []
        for fvg in fvgs:
            if fvg['fvg_id'] in self.seen_fvg_ids:
                continue
            if not self.analyzer.is_fvg_still_valid(fvg, session_candles):
                continue
            active_fvgs.append(fvg)

        # 4. Enrich with confluence
        enriched = self.analyzer.enrich_with_confluence(session_candles, active_fvgs)

        # 5. Score and filter
        signals = []
        for fvg in enriched:
            if fvg.get('passes_confluence', False):
                score = self.analyzer.score_entry_quality(fvg, session_candles)
                fvg['entry_score'] = score
                signals.append(fvg)
                self.seen_fvg_ids.add(fvg['fvg_id'])

        return signals