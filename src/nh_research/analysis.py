"""Small, dependency-free guards for converting research prototypes to real data."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from math import isfinite


def decimal_or_none(value) -> Decimal | None:
    if value is None or isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric market value")
    try:
        result = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError("Invalid numeric market value") from exc
    if not result.is_finite():
        raise ValueError("Nonfinite numeric market value")
    return result


def chart_rows(response: dict) -> list[dict]:
    """Fail closed on flattened/object examples until a genuine schema is captured."""
    records = response.get("Occurs1")
    count = decimal_or_none(response.get("nrec"))
    if (count is None or count < 0 or count != count.to_integral_value() or
            not isinstance(records, list) or len(records) != int(count) or
            any(not isinstance(row, dict) for row in records)):
        raise ValueError("Expected Occurs1 array matching nrec; vendor examples are not live fixtures")
    return records


def oi_change(current, previous) -> Decimal | None:
    now, before = decimal_or_none(current), decimal_or_none(previous)
    if now is None or before is None:
        return None
    if now < 0 or before < 0:
        raise ValueError("Open interest cannot be negative")
    if before == 0:
        return None
    return (now - before) / before


def relative_spread(bid, ask) -> Decimal | None:
    bid, ask = decimal_or_none(bid), decimal_or_none(ask)
    if bid is None or ask is None or bid <= 0 or ask <= 0 or bid > ask:
        return None
    return (ask - bid) / ((ask + bid) / 2)


def forward_mean(values: list[float | None], horizon: int) -> list[float | None]:
    """At t, average t+1..t+h; incomplete horizons stay missing, never class 0."""
    if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    result = []
    for index in range(len(values)):
        window = values[index + 1:index + 1 + horizon]
        if len(window) != horizon or any(v is None or not isfinite(v) for v in window):
            result.append(None)
        else:
            result.append(sum(window) / horizon)
    return result


def purged_training_indices(decision_times, label_end_times, test_start):
    """Keep only completed, pre-test labels. Group all contracts at a time in one fold."""
    if len(decision_times) != len(label_end_times):
        raise ValueError("Mismatched time arrays")
    for start, end in zip(decision_times, label_end_times):
        if end is not None and end < start:
            raise ValueError("Label end precedes decision time")
    return [i for i, (start, end) in enumerate(zip(decision_times, label_end_times))
            if start < test_start and end is not None and end < test_start]
