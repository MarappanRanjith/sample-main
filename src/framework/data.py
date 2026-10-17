"""Shared candle data contracts and file parsers."""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from typing import Any


class CandleInputError(ValueError):
    """Raised when candle data does not match the shared OHLCV contract."""


REQUIRED_CANDLE_FIELDS = ("time", "open", "high", "low", "close")
NUMERIC_CANDLE_FIELDS = ("open", "high", "low", "close", "volume")


def normalize_candles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate candles and return a consistent oldest-first OHLCV structure."""
    if not isinstance(rows, list):
        raise CandleInputError("Candle data must be an array of objects.")
    if len(rows) < 3:
        raise CandleInputError("At least 3 candles are required to detect an FVG.")

    normalized: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise CandleInputError(f"Candle row {row_number} must be an object.")

        missing = [field for field in REQUIRED_CANDLE_FIELDS if field not in row]
        if missing:
            raise CandleInputError(
                f"Candle row {row_number} is missing: {', '.join(missing)}."
            )

        timestamp = row["time"]
        if timestamp is None or str(timestamp).strip() == "":
            raise CandleInputError("Every candle must include a time value.")

        candle: dict[str, Any] = {"time": str(timestamp).strip()}
        try:
            for field in NUMERIC_CANDLE_FIELDS:
                value = row.get(field, 0 if field == "volume" else None)
                if value is None or str(value).strip() == "":
                    if field == "volume":
                        value = 0
                    else:
                        raise ValueError
                numeric_value = float(value)
                if not math.isfinite(numeric_value):
                    raise ValueError
                candle[field] = numeric_value
        except (TypeError, ValueError) as exc:
            raise CandleInputError(
                f"Candle row {row_number} contains a non-numeric OHLCV value."
            ) from exc

        if candle["high"] < max(candle["open"], candle["close"]):
            raise CandleInputError(f"Candle row {row_number} has invalid OHLC bounds.")
        if candle["low"] > min(candle["open"], candle["close"]):
            raise CandleInputError(f"Candle row {row_number} has invalid OHLC bounds.")
        if candle["high"] < candle["low"]:
            raise CandleInputError(f"Candle row {row_number} has high below low.")
        normalized.append(candle)

    return normalized


def candles_from_json(contents: str) -> list[dict[str, Any]]:
    """Load candles from a JSON array or an object containing a candles array."""
    try:
        payload = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise CandleInputError("The JSON file is not valid JSON.") from exc

    rows = payload.get("candles") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise CandleInputError("JSON must be a candle array or contain a 'candles' array.")
    return normalize_candles(rows)


def candles_from_csv(contents: str) -> list[dict[str, Any]]:
    """Load candles from CSV; retained for existing datasets."""
    reader = csv.DictReader(io.StringIO(contents))
    if not reader.fieldnames:
        raise CandleInputError("The CSV must include a header row.")

    aliases = {name.strip().lower(): name for name in reader.fieldnames if name}
    field_map = {
        "time": aliases.get("time") or aliases.get("timestamp") or aliases.get("datetime"),
        "open": aliases.get("open"),
        "high": aliases.get("high"),
        "low": aliases.get("low"),
        "close": aliases.get("close"),
        "volume": aliases.get("volume"),
    }
    missing = [field for field in REQUIRED_CANDLE_FIELDS if not field_map[field]]
    if missing:
        raise CandleInputError(f"CSV is missing columns: {', '.join(missing)}.")

    rows = [
        {field: row[source] for field, source in field_map.items() if source is not None}
        for row in reader
    ]
    return normalize_candles(rows)


def candles_from_file(contents: str, filename: str) -> list[dict[str, Any]]:
    """Load JSON or legacy CSV candle data based on its file extension."""
    extension = Path(filename).suffix.lower()
    if extension == ".json":
        return candles_from_json(contents)
    if extension == ".csv":
        return candles_from_csv(contents)
    raise CandleInputError("Choose a JSON or CSV candle file.")


def load_candles(path: Path) -> list[dict[str, Any]]:
    """Load a candle dataset from a JSON file on disk."""
    try:
        return candles_from_json(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CandleInputError(f"Could not read candle data file: {path.name}.") from exc