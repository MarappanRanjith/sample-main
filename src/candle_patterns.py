# src/candle_patterns.py

class CandlestickAnalyzer:
    @staticmethod
    def analyze_level_interaction(open_p, high_p, low_p, close_p, floor, ceiling):
        """
        Analyze if a candle breaks above ceiling or below floor.
        Returns signal string or None.
        """
        try:
            # Bullish breakout: candle closes above ceiling
            if close_p > ceiling and open_p <= ceiling:
                return "BULLISH_BREAKOUT"
            # Bearish breakout: candle closes below floor
            elif close_p < floor and open_p >= floor:
                return "BEARISH_BREAKOUT"
            # Rejection at ceiling (bearish wick)
            elif high_p > ceiling and close_p < ceiling:
                return "CEILING_REJECTION"
            # Bounce off floor (bullish wick)
            elif low_p < floor and close_p > floor:
                return "FLOOR_BOUNCE"
            else:
                return None
        except Exception:
            return None
