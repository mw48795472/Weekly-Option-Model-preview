"""Authenticate to NH demo, collect read-only quotes/charts, save locally."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nh_research.client import APIError, DemoClient, load_demo_credentials, paged_query
from nh_research.master import load_master, weekly_name_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--output", type=Path, default=ROOT / "data/private/demo_snapshot.json")
    parser.add_argument("--symbol")
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--auth-only", action="store_true")
    args = parser.parse_args()
    catalog = {r["metadata"]["document"]: r for r in
               json.loads((ROOT / "data/catalog/catalog.json").read_text(encoding="utf-8"))}
    snapshot = {"environment": "demo", "collected_at_utc": datetime.now(timezone.utc).isoformat(),
                "auth": {"status": "not_attempted"}, "failures": []}
    try:
        client = DemoClient(load_demo_credentials(args.env_file), catalog)
        snapshot["auth"] = client.authenticate()
        if not args.auth_only:
            rows = load_master(ROOT / "vendor/nh/2026-10-11/masters/fut_opt.mst.gz")
            today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d")
            futures = sorted((r for r in rows if r["under_name"] == "KOSPI" and r["fo_tp"] == "F"
                              and r["cme_tp"] == "day" and r["exp_ym"] >= today), key=lambda r: r["exp_ym"])
            if not args.symbol and not futures:
                raise ValueError("No non-expired KOSPI future in saved master; refresh the master or specify --symbol")
            symbol = args.symbol or futures[0]["series"]
            snapshot["symbol"] = symbol
            snapshot["master_snapshot"] = "2026-10-11"
            tasks = [("quote", "domestic/price", {"sym": symbol}, None),
                     ("daily", "domestic/chart-daily", {"sym": symbol, "nght_tp": "1", "req_qty": "300"}, "nxt_key"),
                     ("minute", "domestic/chart-minute", {"sym": symbol, "nght_tp": "1", "dcnt": "1", "req_qty": "9999"}, "nxt_key")]
            expiries = sorted({r["exp_ym"] for r in rows if weekly_name_candidate(r)
                               and r["under_name"] in {"WKI", "WKM"} and r["exp_ym"] >= today})[:2]
            for expiry in expiries:
                tasks.append(("chain_" + expiry, "domestic/price-all-option",
                              {"prd": "01", "exp_mon": expiry[2:]}, "nxt_stkr_pric"))
            for label, document, params, cursor in tasks:
                try:
                    snapshot[label] = (paged_query(client, document, params, cursor, args.max_pages)
                                       if cursor else client.query(document, params))
                except (APIError, ValueError) as exc:
                    snapshot["failures"].append({"stage": label, "error": str(exc)})
    except (APIError, ValueError, OSError) as exc:
        if snapshot["auth"]["status"] == "not_attempted":
            snapshot["auth"]["status"] = "failed"
        snapshot["failures"].append({"stage": "authentication_or_setup", "error": str(exc)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"auth": snapshot["auth"], "symbol": snapshot.get("symbol"),
                      "datasets": [k for k in snapshot if k in {"quote", "daily", "minute"} or k.startswith("chain_")],
                      "failures": snapshot["failures"], "saved": str(args.output)}, ensure_ascii=False, indent=2))
    return 0 if snapshot["auth"]["status"] == "authenticated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
