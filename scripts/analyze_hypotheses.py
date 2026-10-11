"""Read public saved masters only; never simulate market observations or call APIs."""
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = ROOT / "data/analysis/hypotheses"
OUTPUT.mkdir(parents=True, exist_ok=True)
# Fixed review cutoff: only expiry dates strictly before this date are complete.
SOURCE = ROOT / "data/analysis/contracts/weekly_contracts.csv"
with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
    contracts = list(csv.DictReader(handle))
if not contracts or len({r["series"] for r in contracts}) != len(contracts):
    raise ValueError("Expected a nonempty unique-contract saved master")
underlying = {"WKI": "KOSPI200", "WKM": "KOSPI200", "WQI": "KOSDAQ150", "WQM": "KOSDAQ150"}
events = sorted({(underlying[r["under_name"]], r["expiry_date"]) for r in contracts})
cells = sorted({(r["under_name"], r["expiry_date"]) for r in contracts})
design_rows = []
for product, expiry in cells:
    rows = [r for r in contracts if r["under_name"] == product and r["expiry_date"] == expiry]
    design_rows.append(dict(data_kind="observed saved-master design diagnostic", source="data/analysis/contracts/weekly_contracts.csv",
                            limitations="snapshot-only; future expiry candidates; no market outcomes or causal estimates",
                            product=product, expiry_date=expiry,
                            underlying=underlying[product], contracts=len(rows),
                            intercept=1, monday=int(date.fromisoformat(expiry).weekday() == 0),
                            WKM=int(product == "WKM"), WQI=int(product == "WQI"), WQM=int(product == "WQM")))
columns = ["intercept", "monday", "WKM", "WQI", "WQM"]
matrix = np.array([[row[c] for c in columns] for row in design_rows], dtype=float)
event_matrix = np.ones((len(events), 2))

# Integer index markers demonstrate the original indexing expression, NOT prices,
# market outcomes, fitted coefficients or synthetic hypothesis evidence.
markers = pd.Series(np.arange(25, dtype=float))
original_label_marker = markers.shift(-3).rolling(5).mean().shift(-5)
binary_marker = (original_label_marker > 0).astype(float)
catalog = json.loads((ROOT / "data/catalog/catalog.json").read_text(encoding="utf-8"))
rfq_entries = [a["metadata"] for a in catalog if "rfq" in json.dumps(a, ensure_ascii=False).lower()]
endpoints = []
for a in catalog:
    metadata = a["metadata"]
    text = json.dumps(metadata, ensure_ascii=False)
    if any(s in text for s in ("domestic/price-bid", "domestic/price", "domestic/chart")):
        endpoints.append({"metadata": metadata, "output": a.get("output", [])})
result = dict(
    limitations=["Rank restrictions apply to these saved-snapshot rows only, not every possible historical design",
                 "No prices, OI, market labels, effect coefficients, p-values, or model scores were fabricated",
                 "Original-label index audit is deterministic integer-marker software validation, not market analysis",
                 "No RFQ match in 49 archived catalog entries does not prove NH can never provide RFQ logs"],
    diagnostic_kind="saved-master identifiability and index alignment only; no market hypothesis tests",
    source=SOURCE.relative_to(ROOT).as_posix(),
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    as_of="2026-10-11", unique_contracts=len(contracts),
    session_rows=sum(int(r["session_rows"]) for r in contracts),
    candidate_underlying_date_events=len(events), distinct_event_dates=len({d for _, d in events}),
    completed_candidate_events=sum(d < "2026-10-11" for _, d in events),
    control_event_rows=0,
    expiry_only_design=dict(row_unit="underlying/date candidate event", columns=["intercept", "expiry_event"],
                            shape=list(event_matrix.shape), rank=int(np.linalg.matrix_rank(event_matrix)),
                            identity="expiry_event == intercept == 1; no observed non-expiry control"),
    product_weekday_design=dict(row_unit="product/expiry-date cell (not independent market return)",
                               columns=columns, shape=list(matrix.shape), rank=int(np.linalg.matrix_rank(matrix)),
                               identity="monday == WKM + WQM; WKI omitted as reference",
                               identity_verified=all(r["monday"] == r["WKM"] + r["WQM"] for r in design_rows)),
    product_weekday_counts=dict(Counter(r["under_name"] + ":" + r["expiry_weekday"] for r in contracts)),
    observed_required_fields={k: sum(r.get(k, "") != "" for r in contracts)
                              for k in ("last_pric", "bid_pric", "ask_pric", "opint", "pd_opint", "rv_daily", "rv_forward_5d")},
    original_h9_index_audit=dict(marker_length=25, source_expression="shift(-3).rolling(5).mean().shift(-5)",
                                 implied_window="t+4 through t+8 inclusive", example_t=5,
                                 example_marker_mean=float(original_label_marker.iloc[5]),
                                 incomplete_labels=int(original_label_marker.isna().sum()),
                                 incomplete_converted_to_zero=int(((original_label_marker.isna()) & (binary_marker == 0)).sum()),
                                 warning="Index markers only: these are not market or model-performance data"),
    documented_api_entries=len(catalog), rfq_catalog_entry_matches=rfq_entries,
)
with (OUTPUT / "forecast_design_matrix.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(design_rows[0]))
    writer.writeheader()
    writer.writerows(design_rows)
(OUTPUT / "forecast_diagnostics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OUTPUT / "forecast_api_fields.json").write_text(json.dumps(dict(data_kind="documented schema, not observed API responses",
        source="data/catalog/catalog.json", limitations="Archived on 2026-10-11; no live permission check or API request; example values are not observations",
        endpoints=endpoints), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

investor = [a for a in catalog if a["metadata"].get("document") == "domestic/trend-investor"]
if len(investor) != 1:
    raise ValueError("Expected one archived domestic/trend-investor definition")
(OUTPUT / "position_mechanisms_nh_fields.json").write_text(json.dumps(dict(
    review_date="2026-10-11", status="official_documentation_only_not_live_response",
    source="data/catalog/catalog.json", metadata=investor[0]["metadata"],
    input=investor[0].get("input", []), output=investor[0].get("output", [])),
    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"output": OUTPUT.relative_to(ROOT).as_posix(), "unique_contracts": len(contracts), "candidate_events": len(events), "market_hypothesis_tests": False}, ensure_ascii=False))
