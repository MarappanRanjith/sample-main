import json
import unittest
from pathlib import Path

from src.framework.data import CandleInputError, candles_from_csv, candles_from_json
from src.framework.engine import AnalysisFramework
from src.framework.strategies.smc import SMCStrategy


SAMPLE_CANDLES = [
    {"time": "t1", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 100},
    {"time": "t2", "open": 11, "high": 14, "low": 10, "close": 13, "volume": 120},
    {"time": "t3", "open": 15, "high": 17, "low": 15, "close": 16, "volume": 150},
]


class CandleDataTests(unittest.TestCase):
    def test_json_object_and_csv_share_normalized_data(self):
        json_data = candles_from_json(json.dumps({"candles": SAMPLE_CANDLES}))
        csv_data = candles_from_csv(
            "time,open,high,low,close,volume\n"
            "t1,10,12,9,11,100\n"
            "t2,11,14,10,13,120\n"
            "t3,15,17,15,16,150\n"
        )

        self.assertEqual(json_data, csv_data)
        self.assertEqual(json_data[0]["open"], 10.0)

    def test_invalid_ohlc_is_rejected(self):
        invalid = [*SAMPLE_CANDLES]
        invalid[0] = {**invalid[0], "high": 8}
        with self.assertRaises(CandleInputError):
            candles_from_json(json.dumps(invalid))

    def test_demo_dataset_uses_the_shared_json_contract(self):
        dataset = Path(__file__).resolve().parents[1] / "data" / "demo_candles.json"
        candles = candles_from_json(dataset.read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(candles), 3)


class FrameworkTests(unittest.TestCase):
    def test_smc_strategy_runs_through_registry(self):
        framework = AnalysisFramework()
        framework.register("SMC", SMCStrategy())

        result = framework.analyze("smc", SAMPLE_CANDLES)

        self.assertEqual(result["candle_count"], 3)
        self.assertEqual(result["fvg_count"], 1)
        self.assertEqual(result["alerts"][0]["type"], "BULLISH_FVG")

    def test_unknown_strategy_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown analysis strategy"):
            AnalysisFramework().analyze("missing", SAMPLE_CANDLES)


if __name__ == "__main__":
    unittest.main()