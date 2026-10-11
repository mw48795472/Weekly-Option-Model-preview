"""Observed market-data normalization and descriptive analysis, never synthetic data."""
from __future__ import annotations

import math
import pandas as pd
import numpy as np

from .analysis import decimal_or_none


def number(value):
    try:
        parsed = decimal_or_none(value)
        result = float(parsed) if parsed is not None else None
        return result if result is not None and math.isfinite(result) else None
    except ValueError:
        return None


def observed_rows(dataset: dict) -> tuple[list[dict], dict]:
    rows, rejected = [], 0
    for page in dataset.get("pages", []):
        records = page.get("Occurs1")
        if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
            rejected += 1
            continue
        count = number(page.get("nrec"))
        if count is not None and count != len(records):
            rejected += 1
            continue
        rows.extend(records)
    return rows, {"raw_rows": len(rows), "rejected_pages": rejected,
                  "stop_reason": dataset.get("stop_reason", "not_collected")}


def normalize_bars(dataset, minute=False):
    raw, quality = observed_rows(dataset)
    normalized = []
    for row in raw:
        date = str(row.get("occurs1_ref_dt", "")).strip()
        clock = str(row.get("occurs1_exch_tm", "")).strip().zfill(6) if minute else ""
        timestamp = pd.to_datetime(date + clock, format="%Y%m%d%H%M%S" if minute else "%Y%m%d", errors="coerce")
        values = {key: number(row.get("occurs1_" + field)) for key, field in {
            "open": "open_pric", "high": "high_pric", "low": "low_pric", "close": "close_pric",
            "volume": "cum_trd_qty", "oi": "opint"}.items()}
        valid_price = all(values[key] is not None and values[key] > 0 for key in ("open", "high", "low", "close"))
        if (pd.isna(timestamp) or not valid_price or values["high"] < max(values["open"], values["close"], values["low"])
                or values["low"] > min(values["open"], values["close"], values["high"])):
            continue
        normalized.append({"timestamp": timestamp, **values})
    frame = pd.DataFrame(normalized, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
    quality["invalid_rows"] = len(raw) - len(frame)
    quality["duplicate_timestamps"] = int(frame.duplicated("timestamp").sum())
    # Pages are requested newest first; keep first received value if pages overlap.
    frame = frame.drop_duplicates("timestamp", keep="first").sort_values("timestamp").reset_index(drop=True)
    quality["valid_rows"] = len(frame)
    return frame, quality


def intraday_rv(frame):
    """Observed 5-minute close-to-close RV; gaps and session boundaries excluded."""
    result = []
    if frame.empty:
        return pd.DataFrame(columns=["date", "rv", "returns", "observed_minutes", "first", "last"])
    for date, group in frame.groupby(frame.timestamp.dt.date):
        bins = group.set_index("timestamp").close.resample("5min", label="right", closed="right")
        prices = bins.last().where(bins.count() == 5)
        # No forward-fill: missing 5-minute bins prevent both adjacent returns.
        returns = np.log(prices).diff()
        valid = returns.dropna()
        if valid.empty:
            continue
        result.append({"date": str(date), "rv": float((valid ** 2).sum()), "returns": len(valid),
                       "observed_minutes": len(group), "first": group.timestamp.min().isoformat(),
                       "last": group.timestamp.max().isoformat()})
    return pd.DataFrame(result)


def normalize_chain(dataset, expiry):
    raw, quality = observed_rows(dataset)
    rows = []
    for record in raw:
        strike = number(record.get("occurs1_strk_pric"))
        if strike is None or strike <= 0:
            continue
        for side, prefix in [("Call", "c"), ("Put", "p")]:
            field = lambda name: record.get(f"occurs1_{prefix}_{name}")
            code = str(field("sym_exch") or "").strip()
            if not code:
                continue
            bid, ask = number(field("bid_pric")), number(field("ask_pric"))
            midpoint = (bid + ask) / 2 if bid is not None and ask is not None and 0 < bid <= ask else None
            rows.append({"expiry": expiry, "side": side, "symbol": code, "strike": strike,
                         "bid": bid, "ask": ask, "mid": midpoint, "last": number(field("last_pric")),
                         "spread_bps": (ask - bid) / midpoint * 10000 if midpoint else None,
                         "oi": number(field("opint")), "iv_vendor": number(field("vol")),
                         "delta": number(field("delta")), "gamma": number(field("gamma"))})
    frame = pd.DataFrame(rows, columns=["expiry", "side", "symbol", "strike", "bid", "ask", "mid", "last",
                                        "spread_bps", "oi", "iv_vendor", "delta", "gamma"])
    frame = frame.drop_duplicates("symbol", keep="first").sort_values(["side", "strike"])
    quality["contracts"] = len(frame)
    quality["two_sided_valid_quotes"] = int(frame.mid.notna().sum())
    return frame, quality


def analyze_snapshot(snapshot):
    daily, daily_quality = normalize_bars(snapshot.get("daily", {}))
    minute, minute_quality = normalize_bars(snapshot.get("minute", {}), minute=True)
    rv = intraday_rv(minute)
    chains, chain_quality = [], {}
    for key, dataset in snapshot.items():
        if key.startswith("chain_"):
            frame, quality = normalize_chain(dataset, key[6:])
            chains.append(frame)
            chain_quality[key[6:]] = quality
    chain = pd.concat(chains, ignore_index=True) if chains else pd.DataFrame()
    daily["log_return"] = np.log(daily.close).diff() if not daily.empty else pd.Series(dtype=float)
    daily["rolling_vol_20d"] = daily.log_return.rolling(20, min_periods=20).std(ddof=1) * math.sqrt(252) * 100
    summary = {"environment": snapshot.get("environment"), "auth": snapshot.get("auth", {"status": "not_attempted"}),
               "collected_at_utc": snapshot.get("collected_at_utc"), "symbol": snapshot.get("symbol"),
               "daily": daily_quality, "minute": minute_quality, "chains": chain_quality,
               "rv_days": len(rv), "failures": snapshot.get("failures", []),
               "model_evaluation": "not_run: descriptive analysis; complete-session and independent-event validation required"}
    return {"summary": summary, "daily": daily, "minute": minute, "rv": rv, "chain": chain}
