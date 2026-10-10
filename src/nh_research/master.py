"""Parse the public NH domestic master snapshot using its documented 26 fields."""
from __future__ import annotations

import gzip
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HEADER = ("mrkt_tp fo_tp opt_tp under_name exp_ym cme_tp class kospi_key series "
          "rank_series name_kor name_eng upper_p_lv1 lower_p_lv1 strike_p inst_grp_cd "
          "p_dec ctrt_size rem_cnt dynmc_yn dynmc_up_p dynmc_dn_p real_Code kofex_Code "
          "mrkt_code trd_code").split()


def load_master(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    if raw.startswith(b"\x1f\x8b"):
        raw = gzip.decompress(raw)
    result = []
    for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        values = line.split(";")
        if len(values) != len(HEADER):
            raise ValueError(f"Master line {number}: expected 26 fields, got {len(values)}")
        result.append(dict(zip(HEADER, values)))
    return result


def weekly_name_candidate(row: dict) -> bool:
    """Name heuristic, NOT an exchange-certified weekly product flag."""
    text = f"{row['name_kor']} {row['name_eng']}".upper()
    return row["fo_tp"] == "O" and ("위클리" in text or "WEEK" in text)


def summarize_master(rows: list[dict]) -> dict:
    weekly = [r for r in rows if weekly_name_candidate(r)]
    count = lambda rs, key: dict(sorted(Counter(r[key] for r in rs).items()))
    by_session = {}
    for session in sorted({r["cme_tp"] for r in rows}):
        selected = [r for r in rows if r["cme_tp"] == session]
        inferred = Counter()
        for row in selected:
            try:
                expiry = datetime.strptime(row["exp_ym"], "%Y%m%d").date()
                inferred[str(expiry - timedelta(days=int(row["rem_cnt"])))] += 1
            except ValueError:
                inferred["unparseable"] += 1
        by_session[session] = dict(sorted(inferred.items()))
    keys = [(r["cme_tp"], r["series"]) for r in rows]
    return {
        "rows": len(rows), "unique_series": len({r["series"] for r in rows}),
        "duplicate_session_series": len(keys) - len(set(keys)),
        "types": count(rows, "fo_tp"), "sessions": count(rows, "cme_tp"),
        "market_codes": count(rows, "mrkt_tp"),
        "underlying_count": len({r["under_name"] for r in rows}),
        "weekly_name_candidate_rows": len(weekly),
        "weekly_unique_series": len({r["series"] for r in weekly}),
        "weekly_underlyings": count(weekly, "under_name"),
        "weekly_expiries": count(weekly, "exp_ym"),
        "weekly_sessions": count(weekly, "cme_tp"),
        "implied_expiry_minus_remaining_days_by_session": by_session,
        "freshness_note": "Diagnostic only: expiry minus rem_cnt is not a vendor publication timestamp.",
        "weekly_note": "Name-based candidates; absence of matching names does not prove no weekly listings.",
    }
