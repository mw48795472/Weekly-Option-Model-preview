"""Proposal REV: signed close-to-next-session returns, with exact anchors.

This module does not infer a trading calendar or interpolate prices. Each run
uses one price instrument per underlying/date; expiry contracts are not samples.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median

EVENT_FIELDS = ["underlying_id", "event_date", "event_type", "price_kind",
                "price_symbol", "expiry_source", "product_codes", "contract_count"]
CALENDAR_FIELDS = ["price_symbol", "session_date", "open_at", "close_at", "source"]
PRICE_FIELDS = ["price_symbol", "timestamp", "price", "observation_type", "source"]
ANCHORS = ("preclose", "close", "open", "1m", "30m")
HORIZONS = {"open": "rev1", "1m": "rev2", "30m": "rev3"}
RESULT_FIELDS = EVENT_FIELDS + ["as_of", "next_session_date", "issues", "pre_return_bp"]
for _anchor in ANCHORS:
    RESULT_FIELDS += [f"{_anchor}_at", f"{_anchor}_price", f"{_anchor}_source",
                      f"{_anchor}_status"]
for _metric in HORIZONS.values():
    RESULT_FIELDS += [f"{_metric}_bp", f"{_metric}_status"]
SUMMARY_FIELDS = ["underlying_id", "price_kind", "event_type", "horizon", "n",
                  "distinct_dates", "mean_bp", "median_bp", "positive_share", "status"]


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(hours=9):
        raise ValueError("Timestamps must explicitly use KST (+09:00)")
    return parsed


def positive_price(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("Prices must be finite and positive")
    return number


def rev_bp(preclose, close, after, min_pre_move_bp=0.0):
    """Simple returns in bp. Positive=reversal; None=undefined reference sign."""
    if not math.isfinite(min_pre_move_bp) or min_pre_move_bp < 0:
        raise ValueError("min_pre_move_bp must be finite and nonnegative")
    preclose, close, after = map(positive_price, (preclose, close, after))
    pre = (close / preclose - 1) * 10000
    if pre == 0 or abs(pre) < min_pre_move_bp:
        return None
    return -math.copysign(1, pre) * (after / close - 1) * 10000


def candidate_events(contracts):
    """766 contracts in the saved snapshot collapse to six candidate events."""
    underlying = {"WKI": "KOSPI200", "WKM": "KOSPI200",
                  "WQI": "KOSDAQ150", "WQM": "KOSDAQ150"}
    groups = defaultdict(list)
    seen = set()
    for row in contracts:
        if row["series"] in seen:
            raise ValueError("Expected unique contracts, not session rows")
        seen.add(row["series"])
        groups[underlying[row["under_name"]], row["expiry_date"]].append(row)
    return [dict(underlying_id=u, event_date=d, event_type="expiry",
                 price_kind="cash_index", price_symbol="",
                 expiry_source="vendor/nh/2026-10-11/masters/fut_opt.mst.gz#exp_ym",
                 product_codes="|".join(sorted({r["under_name"] for r in rows})),
                 contract_count=len(rows))
            for (u, d), rows in sorted(groups.items())]


def analyze(events, calendar, prices, as_of, min_pre_move_bp=0.0):
    cutoff = timestamp(as_of)
    # Validate even when there are no prices or eligible events.
    rev_bp(100, 101, 100, min_pre_move_bp)
    calendars = defaultdict(list)
    sessions = {}
    for row in calendar:
        symbol, day = row["price_symbol"], date.fromisoformat(row["session_date"])
        opened, closed = timestamp(row["open_at"]), timestamp(row["close_at"])
        if (not symbol or not row["source"] or opened.date() != day or closed.date() != day
                or closed - opened <= timedelta(minutes=30)):
            raise ValueError("Calendar requires sourced daytime sessions longer than 30 minutes")
        key = (symbol, day)
        if key in sessions:
            raise ValueError("Duplicate calendar session")
        sessions[key] = (opened, closed)
        calendars[symbol].append(day)
    for days in calendars.values():
        days.sort()
    observations = {}
    for row in prices:
        key = (row["price_symbol"], timestamp(row["timestamp"]))
        if not key[0] or not row["source"] or row["observation_type"] != "observed":
            raise ValueError("Price input requires a symbol, source, and observed data")
        if key in observations:
            raise ValueError("Duplicate price timestamp; resolve conflicts before analysis")
        observations[key] = (positive_price(row["price"]), row["source"])
    seen, results = set(), []
    for event in events:
        key = (event["underlying_id"], date.fromisoformat(event["event_date"]))
        if not key[0] or not event["expiry_source"]:
            raise ValueError("Events require an underlying and dated-event source")
        if key in seen:
            raise ValueError("Duplicate underlying/date event (contracts are not independent events)")
        seen.add(key)
        if event["event_type"] not in {"expiry", "control"}:
            raise ValueError("event_type must be expiry or control")
        if event["price_kind"] not in {"cash_index", "future_proxy"}:
            raise ValueError("Use a cash index or a single unchanged future proxy, not an option")
        result = dict.fromkeys(RESULT_FIELDS, "")
        result.update({k: event.get(k, "") for k in EVENT_FIELDS})
        result["as_of"] = as_of
        symbol, day = event["price_symbol"], key[1]
        issues, anchors = [], {}
        if day > cutoff.date():
            issues.append("future_event")
        if not symbol:
            issues.append("missing_price_symbol")
        session = sessions.get((symbol, day))
        if session is None:
            issues.append("missing_calendar")
        else:
            _, closed = session
            anchors.update(preclose=closed - timedelta(minutes=30), close=closed)
            days = calendars[symbol]
            index = days.index(day)
            if index + 1 == len(days):
                issues.append("missing_next_session")
            else:
                next_day = days[index + 1]
                result["next_session_date"] = next_day.isoformat()
                opened, _ = sessions[symbol, next_day]
                anchors.update(open=opened, **{"1m": opened + timedelta(minutes=1),
                                              "30m": opened + timedelta(minutes=30)})
        for name in ANCHORS:
            at = anchors.get(name)
            status = "missing_anchor_schedule"
            if at is not None:
                result[f"{name}_at"] = at.isoformat()
                if at > cutoff:
                    status = "not_yet_observable"
                elif (symbol, at) not in observations:
                    status = "missing_exact_price"
                else:
                    value, source = observations[symbol, at]
                    result[f"{name}_price"], result[f"{name}_source"] = value, source
                    status = "observed"
            result[f"{name}_status"] = status
        base_ok = all(result[f"{a}_status"] == "observed" for a in ("preclose", "close"))
        if base_ok:
            result["pre_return_bp"] = (result["close_price"] / result["preclose_price"] - 1) * 10000
        for anchor, metric in HORIZONS.items():
            status = "missing_reference_prices"
            if base_ok:
                if result["pre_return_bp"] == 0:
                    status = "zero_reference_move"
                elif abs(result["pre_return_bp"]) < min_pre_move_bp:
                    status = "reference_below_threshold"
                elif result[f"{anchor}_status"] != "observed":
                    status = result[f"{anchor}_status"]
                else:
                    result[f"{metric}_bp"] = rev_bp(result["preclose_price"], result["close_price"],
                                                    result[f"{anchor}_price"], min_pre_move_bp)
                    status = "computed"
            result[f"{metric}_status"] = status
        result["issues"] = "|".join(issues)
        results.append(result)
    return sorted(results, key=lambda r: (r["underlying_id"], r["event_date"]))


def summarize(results):
    groups = defaultdict(list)
    for row in results:
        groups[row["underlying_id"], row["price_kind"], row["event_type"]].append(row)
    output = []
    for (underlying, kind, event_type), rows in sorted(groups.items()):
        for horizon, metric in HORIZONS.items():
            valid = [r for r in rows if r[f"{metric}_status"] == "computed"]
            values = [r[f"{metric}_bp"] for r in valid]
            output.append(dict(underlying_id=underlying, price_kind=kind, event_type=event_type,
                               horizon=horizon, n=len(valid),
                               distinct_dates=len({r["event_date"] for r in valid}),
                               mean_bp=mean(values) if values else "",
                               median_bp=median(values) if values else "",
                               positive_share=mean(v > 0 for v in values) if values else "",
                               status="descriptive_only" if values else "no_observations"))
    return output
