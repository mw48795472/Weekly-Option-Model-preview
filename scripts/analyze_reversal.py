"""Run public REV feasibility, or analyze explicitly supplied observed prices."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nh_research.contract_exports import csv_bytes
from nh_research.reversal import (ANCHORS, EVENT_FIELDS, CALENDAR_FIELDS, PRICE_FIELDS,
                                  RESULT_FIELDS, SUMMARY_FIELDS, analyze, candidate_events,
                                  rev_bp, summarize)

AS_OF = "2026-10-11T09:00:00+09:00"


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(csv_bytes(rows, fields))


def plot_feasibility(results, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4.4), layout="constrained")
    counts = [sum(r[f"{a}_status"] == "observed" for a in ANCHORS) for r in results]
    labels = [r["underlying_id"] + " | " + r["event_date"] for r in results]
    ax.barh(labels, [5] * len(results), color="#e3eaf1", label="Required anchors")
    ax.barh(labels, counts, color="#148d77", label="Observed exact anchors")
    for i, n in enumerate(counts):
        ax.text(.1, i, f"{n}/5 observed", va="center", color="#243d59")
    ax.set(xlim=(0, 5.5), xticks=range(6), xlabel="Price anchors per underlying/date event",
           title="REV feasibility | snapshot 2026-10-11 | no completed price sample")
    ax.invert_yaxis()
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def mathematical_examples():
    # Explicit hand-specified calculation cases: never statistical samples.
    paths = [("rise_then_reversal", 100, 101, 100.5, 100.25, 100),
             ("fall_then_reversal", 100, 99, 99.5, 99.75, 100),
             ("continuation", 100, 101, 101.5, 101.75, 102),
             ("no_reference_move", 100, 100, 100.5, 100.25, 100)]
    rows = []
    for name, pre, close, opened, m1, m30 in paths:
        row = dict(scenario=name, observation_type="mathematical_example",
                   preclose=pre, close=close, open=opened, **{"1m": m1, "30m": m30})
        for i, after in enumerate((opened, m1, m30), 1):
            value = rev_bp(pre, close, after)
            row[f"rev{i}_bp"] = value if value is not None else ""
        rows.append(row)
    return rows


def plot_examples(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), layout="constrained")
    for row, color in zip(rows[:3], ("#148d77", "#3577c9", "#d99b25")):
        label = row["scenario"].replace("_", " ")
        axes[0].plot(range(5), [row[a] for a in ANCHORS], "o-", label=label, color=color)
        axes[1].plot(range(3), [row[f"rev{i}_bp"] for i in range(1, 4)], "o-", color=color)
    axes[0].set(xticks=range(5), xticklabels=["Close -30m", "Close", "Next open", "+1m", "+30m"],
                ylabel="Assumed price (not market data)", title="Hand-specified price paths")
    axes[0].legend(fontsize=8)
    axes[1].axhline(0, color="#5f7285", linewidth=1)
    axes[1].set(xticks=range(3), xticklabels=["REV1", "REV2", "REV3"], ylabel="REV (bp)",
                title="Positive = reversal; negative = continuation")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.15)
    fig.suptitle("FORMULA DEMONSTRATION ONLY — no empirical estimates", fontsize=12)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def build_public():
    output = ROOT / "data/analysis/reversal"
    events = candidate_events(read_csv(ROOT / "data/analysis/contracts/weekly_contracts.csv"))
    results = analyze(events, [], [], AS_OF)
    summary = summarize(results)
    write_csv(output / "event_candidates.csv", events, EVENT_FIELDS)
    write_csv(output / "event_results.csv", results, RESULT_FIELDS)
    write_csv(output / "summary.csv", summary, SUMMARY_FIELDS)
    for name, fields in (("calendar_template", CALENDAR_FIELDS), ("prices_template", PRICE_FIELDS)):
        write_csv(output / (name + ".csv"), [], fields)
    examples = mathematical_examples()
    write_csv(output / "formula_examples.csv", examples, list(examples[0]))
    manifest = dict(as_of=AS_OF, input_contracts=sum(r["contract_count"] for r in events),
                    candidate_events=len(events), distinct_expiry_dates=len({r["event_date"] for r in events}),
                    future_events=sum("future_event" in r["issues"] for r in results),
                    supplied_calendar_rows=0, supplied_price_rows=0,
                    observed_anchor_cells=sum(r[f"{a}_status"] == "observed" for r in results for a in ANCHORS),
                    required_anchor_cells=len(events) * 5,
                    empirical_n={f"rev{i}": sum(r[f"rev{i}_status"] == "computed" for r in results)
                                 for i in range(1, 4)},
                    effect_estimate=None, p_value=None,
                    status="blocked_missing_historical_prices_and_calendar",
                    scope="Public saved-master feasibility; does not read credentials or private snapshots")
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plot_feasibility(results, ROOT / "docs/images/reversal_feasibility.png")
    plot_examples(examples, ROOT / "docs/images/reversal_formula_examples.png")
    return dict(manifest=manifest, events=results, summary=summary, examples=examples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--calendar", type=Path)
    parser.add_argument("--prices", type=Path)
    parser.add_argument("--as-of", help="KST timestamp with +09:00, e.g. 2026-10-20T10:00:00+09:00")
    parser.add_argument("--min-pre-move-bp", type=float, default=0)
    args = parser.parse_args()
    supplied = [args.events, args.calendar, args.prices, args.as_of]
    if any(supplied):
        if not all(supplied):
            parser.error("Provide --events, --calendar, --prices and --as-of together")
        results = analyze(read_csv(args.events), read_csv(args.calendar), read_csv(args.prices),
                          args.as_of, args.min_pre_move_bp)
        output = ROOT / "artifacts/private/reversal"
        write_csv(output / "event_results.csv", results, RESULT_FIELDS)
        write_csv(output / "summary.csv", summarize(results), SUMMARY_FIELDS)
        manifest = dict(as_of=args.as_of, min_pre_move_bp=args.min_pre_move_bp,
                        inputs={label: {"filename": path.name,
                                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                                for label, path in (("events", args.events), ("calendar", args.calendar),
                                                    ("prices", args.prices))},
                        events=len(results), statistical_inference="not_implemented_descriptive_only")
        (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")
        print(json.dumps({"output": str(output), "events": len(results),
                          "computed": {f"rev{i}": sum(r[f"rev{i}_status"] == "computed" for r in results)
                                       for i in range(1, 4)}}, ensure_ascii=False))
    else:
        if args.min_pre_move_bp:
            parser.error("Threshold applies to observed input runs only")
        print(json.dumps(build_public()["manifest"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
