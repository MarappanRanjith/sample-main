"""SMC strategy adapter for the shared analysis framework."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from src.smc.analyzer import SMCAnalyzer


def _volume_surge(candles: list[dict[str, Any]], index: int) -> float:
    if index < 0 or index >= len(candles):
        return 0.0
    start = max(0, index - 20)
    volumes = [candle["volume"] for candle in candles[start:index] if candle["volume"] > 0]
    average = sum(volumes) / len(volumes) if volumes else 0.0
    return round(candles[index]["volume"] / average, 2) if average else 0.0


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class SMCStrategy:
    """Run SMC detection and return the dashboard's standard result shape."""

    def analyze(
        self, candles: list[dict[str, Any]], minimum_score: int = 2
    ) -> dict[str, Any]:
        fvgs = SMCAnalyzer.enrich_with_confluence(
            candles, SMCAnalyzer.analyze_fvgs(candles)
        )
        order_blocks = SMCAnalyzer.analyze_order_blocks(candles)

        alerts = []
        for fvg in fvgs:
            displacement_index = fvg["creation_index"] - 1
            confluence = fvg.get("confluence", {})
            passed_checks = [
                label
                for label, key in (
                    ("HTF bias", "htf_aligned"),
                    ("PD zone", "zone_aligned"),
                    ("Liquidity sweep", "liquidity_sweep"),
                    ("Order block", "ob_confluence"),
                )
                if confluence.get(key)
            ]
            alerts.append(
                {
                    **fvg,
                    "time": _json_value(fvg["time"]),
                    "volume_surge": _volume_surge(candles, displacement_index),
                    "passed_checks": passed_checks,
                    "passes_threshold": fvg["confluence_count"] >= minimum_score,
                }
            )

        return {
            "candle_count": len(candles),
            "fvg_count": len(alerts),
            "setup_count": sum(alert["passes_threshold"] for alert in alerts),
            "order_block_count": len(order_blocks),
            "latest_candle": candles[-1],
            "alerts": alerts,
            "order_blocks": order_blocks,
        }