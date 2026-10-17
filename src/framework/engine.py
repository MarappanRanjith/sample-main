"""Strategy registry and common analysis entry point."""

from __future__ import annotations

from typing import Any, Protocol

from src.framework.data import normalize_candles


class AnalysisStrategy(Protocol):
    def analyze(self, candles: list[dict[str, Any]], **options: Any) -> dict[str, Any]: ...


class AnalysisFramework:
    """Run registered strategies against the shared normalized candle data."""

    def __init__(self) -> None:
        self._strategies: dict[str, AnalysisStrategy] = {}

    def register(self, name: str, strategy: AnalysisStrategy) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("Strategy name cannot be empty.")
        if key in self._strategies:
            raise ValueError(f"Strategy '{key}' is already registered.")
        self._strategies[key] = strategy

    def analyze(
        self, name: str, candles: list[dict[str, Any]], **options: Any
    ) -> dict[str, Any]:
        key = name.strip().lower()
        try:
            strategy = self._strategies[key]
        except KeyError as exc:
            raise ValueError(f"Unknown analysis strategy: {key}.") from exc
        return strategy.analyze(normalize_candles(candles), **options)