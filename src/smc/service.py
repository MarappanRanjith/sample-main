"""Application service for running SMC analysis from uploaded or live candles."""

from typing import Any

from src.framework.data import (
    CandleInputError,
    candles_from_csv,
    candles_from_file,
    candles_from_json,
    normalize_candles,
)
from src.framework.engine import AnalysisFramework
from src.smc.strategy import SMCStrategy

analysis_framework = AnalysisFramework()
analysis_framework.register("smc", SMCStrategy())


def analyze_candles(candles: list[dict[str, Any]], minimum_score: int = 2) -> dict[str, Any]:
    """Run the registered SMC strategy through the common analysis framework."""
    return analysis_framework.analyze("smc", candles, minimum_score=minimum_score)
