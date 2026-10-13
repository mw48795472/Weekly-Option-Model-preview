"""Reproduce post-hoc H6 diagnostics entirely from committed offline panels."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nh_research.h6_diagnostics import audit_origins, common_refit, information, paired_loss

OUT = ROOT / "data/analysis/h6_diagnostics"


def save(name, frame):
    frame.to_csv(OUT / name, index=False, encoding="utf-8-sig", float_format="%.9g")


def load():
    index = pd.read_csv(ROOT / "data/analysis/empirical/daily_panel.csv")
    stocks = pd.read_csv(ROOT / "data/analysis/single_stocks/daily_panel.csv",
                         dtype={"stock_code": str})
    index_predictions = pd.read_csv(ROOT / "data/analysis/empirical/h6_forecasts.csv")
    index_predictions["family"] = "matched"
    stock_predictions = pd.read_csv(ROOT / "data/analysis/single_stocks/h6_forecasts.csv",
                                    dtype={"stock_code": str})
    coverage = pd.read_csv(ROOT / "data/analysis/single_stocks/coverage.csv",
                           dtype={"stock_code": str}).set_index("stock_code")
    items = [("TXO", "TAIEX / TXO", index, index_predictions,
              ["parkinson", "close_squared_return"], ["matched"])]
    for stock, panel in stocks.groupby("stock_code"):
        items.append((stock, coverage.loc[stock, "name_en"], panel.reset_index(drop=True),
                      stock_predictions.loc[stock_predictions.stock_code.eq(stock)],
                      ["parkinson", "close_squared_return", "parkinson_clean"], ["matched", "level"]))
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-charts", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    audits, flows, infos, comparisons, refits, refit_comparisons, existing_family_pairs = [], [], [], [], [], [], []
    for unit, name, panel, predictions, proxies, families in load():
        infos.append(dict(unit=unit, name=name, **information(panel)))
        for proxy in proxies:
            for family in families:
                chosen = predictions.loc[predictions.proxy.eq(proxy) & predictions.family.eq(family)]
                audit, flow = audit_origins(panel, chosen, proxy, family)
                for result, store in [(audit, audits), (flow, flows)]:
                    result.insert(0, "unit", unit)
                    result.insert(1, "name", name)
                    store.append(result)
                if not chosen.empty:
                    for model in sorted(set(chosen.model) - {"persistence", "HAR", "HAR_calendar"}):
                        for block in [5, 10, 20]:
                            comparisons.append(dict(unit=unit, name=name, proxy=proxy, family=family,
                                                    **paired_loss(chosen, model, "HAR_calendar", block)))
            # Existing family comparison pairs same target dates; train histories remain different.
            if unit != "TXO":
                matched = predictions.loc[predictions.proxy.eq(proxy) & predictions.family.eq("matched")]
                level = predictions.loc[predictions.proxy.eq(proxy) & predictions.family.eq("level")]
                dates = sorted(set(matched.date) & set(level.date))
                if dates:
                    a = matched[matched.date.isin(dates) & matched.model.eq("OI_lag1")].copy()
                    b = level[level.date.isin(dates) & level.model.eq("OI_level_lag1")].copy()
                    if not np.allclose(a.sort_values("date").actual, b.sort_values("date").actual):
                        raise ValueError("Cross-family target mismatch")
                    a["model"], b["model"] = "matched_existing", "level_existing"
                    result = paired_loss(pd.concat([a, b]), "level_existing", "matched_existing")
                    existing_family_pairs.append(dict(unit=unit, name=name, proxy=proxy,
                                                      training_dates_equal=False, **result))
        # Main target only: a fixed same-training/dates comparison of two existing OI definitions.
        refit = common_refit(panel)
        if not refit.empty:
            refit.insert(0, "unit", unit)
            refit.insert(1, "name", name)
            refits.append(refit)
            for model, baseline in [("matched_OI_lag1", "HAR_calendar"),
                                    ("level_OI_lag1", "HAR_calendar"),
                                    ("level_OI_lag1", "matched_OI_lag1")]:
                for block in [5, 10, 20]:
                    refit_comparisons.append(dict(unit=unit, name=name, proxy="parkinson",
                                                  training_dates_equal=True,
                                                  **paired_loss(refit, model, baseline, block)))
    tables = {
        "origin_audit.csv": pd.concat(audits, ignore_index=True),
        "sample_attrition.csv": pd.concat(flows, ignore_index=True),
        "information.csv": pd.DataFrame(infos),
        "precision.csv": pd.DataFrame(comparisons),
        "common_refit_forecasts.csv": pd.concat(refits, ignore_index=True),
        "common_refit_comparison.csv": pd.DataFrame(refit_comparisons),
        "existing_family_common_dates.csv": pd.DataFrame(existing_family_pairs),
    }
    for name, frame in tables.items():
        save(name, frame)
    requirements = [
        (1, "P0", "Continued weekly-option observations", "Same-contract daily OI, all listed strikes/expiries, contracts entering/exiting, source publication and revision timestamps",
         "Cannot invent prelaunch history; accumulate future origins under the frozen >=100/purged protocol", "TAIFEX regular-session downloads / licensed historical file", "https://www.taifex.com.tw/enl/eng3/optDailyMarketView"),
        (2, "P0", "Intraday underlying prices", "Timestamped 1/5-minute trades or bars, sessions, overnight prices, halts and price limits",
         "Daily H=L and overlapping 5-day proxies lose information; build realized variance with microstructure checks", "TWSE licensed intraday stock/index history; internal-use files are not public redistribution rights", "https://eshop.twse.com.tw/en/category/main/41"),
        (3, "P0", "Corporate actions", "Cash/stock dividends, splits, ex-right dates, adjustment factors known at each date, trading halts",
         "Separate genuine price moves, non-comparable close returns and changes in option deliverable", "TWSE official corporate action announcements + TAIFEX adjusted-contract notices", "https://www.taifex.com.tw/enl/eng2/sSO"),
        (4, "P1", "Complete option-risk inputs", "Contract OI, bid/ask, underlying timestamp, strikes, maturity, multiplier/deliverable, rates/dividends, quote flags",
         "Test moneyness/DTE/gamma or notional weighted OI without interpreting unsigned contract counts as dealer position", "TAIFEX option chain and contract specifications; licensed historical quotes", "https://www.taifex.com.tw/enl/eng2/sSO"),
        (5, "P1", "Information events", "Point-in-time earnings/financial releases, dividend dates, macro/market event timestamps, announcement surprises",
         "Distinguish event volatility and liquidity regimes from OI activity; avoid retrospective event labels", "TWSE/MOPS official filings + relevant policy announcement calendars", "https://mops.twse.com.tw/"),
        (6, "P1", "Historical schedule and availability versions", "Listing/expiry calendar announcements as issued, holiday revisions, field publication time and corrections",
         "Current final calendars and 1/2-day lag assumptions are not an operational as-of dataset", "TAIFEX/TWSE dated notices or documented vendor as-of feeds", "https://www.taifex.com.tw/enl/eng11/announcement"),
        (7, "P2", "Comparison products and periods", "Monthly stock options and more eligible underlyings with matching underlying prices and identical field definitions",
         "Estimate proxy performance and regime transport; monthly results cannot create prelaunch weekly treatment data", "TAIFEX option daily history matched to TWSE securities master", "https://www.taifex.com.tw/enl/eng3/optDailyMarketView"),
    ]
    data = pd.DataFrame(requirements, columns=["order", "priority", "dataset", "fields", "reason", "source", "url"])
    save("additional_data.csv", data)
    summary = {
        "version": "h6-diagnostics-20261013",
        "classification": "post-hoc diagnostics, not new confirmatory proof",
        "inputs": "Committed 20261012 empirical and single-stock outputs",
        "units": 8, "date_start": "2025-01-02", "date_end": "2026-10-08",
        "sample_gates": "Ordered, mutually exclusive first failure; overlap flags retained in origin_audit.csv",
        "common_refit": "Parkinson only; matched-family eligibility; same train dates; >=100 completed labels; strict label_end < origin; no tuning",
        "loss_interval": "Calendar-preserving moving-block bootstrap 5/10/20, 2000 draws, seed4879",
        "disjoint_windows": "Maximum nonoverlapping target intervals, NOT independent/effective sample size",
        "precision": "Intervals are uncertainty for mean paired loss, not prediction intervals for future volatility; QLIKE units are not percent return",
        "multiple_comparison": "Pointwise 95% and approximate 7-comparison intervals; all proxy/model diagnostics were not globally multiplicity adjusted",
        "caution": "No causal attribution of non-significance; do not directly rank different proxies or unequal test dates; no promised sample size guaranteeing significance",
        "outputs": sorted(tables),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.no_charts:
        charts(tables)
    primary = tables["sample_attrition.csv"]
    primary = primary.loc[primary.proxy.eq("parkinson") & primary.family.eq("matched")]
    print(primary.pivot(index=["unit", "name"], columns="gate", values="count").to_string())
    print("\nSAME-TRAIN/SAME-DATE REFIT")
    print(tables["common_refit_comparison.csv"].query("block==10")[["unit", "model", "baseline", "n", "disjoint_target_windows", "qlike_difference", "ci_low", "ci_high"]].to_string(index=False))


def charts(tables):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out = ROOT / "docs/images/h6_diagnostics"
    out.mkdir(parents=True, exist_ok=True)
    flow = tables["sample_attrition.csv"].query("proxy=='parkinson' and family=='matched'")
    order = tables["information.csv"].unit.tolist()
    labels = tables["information.csv"].name.tolist()
    groups = [
        ("pre_launch", ["pre_launch"]),
        ("Price/HAR window", ["history_initial_22", "history_missing_price", "history_zero_range", "history_non_comparable", "history_other_proxy_missing"]),
        ("OI definition", ["oi_warmup_or_source_missing", "oi_zero_denominator_or_no_overlap", "oi_other_missing"]),
        ("Future target/calendar", ["target_end_boundary", "target_missing_price", "target_zero_range", "target_non_comparable", "target_other_missing", "calendar_missing"]),
        ("Training/purge/rank", ["initial_train_below_100", "purge_train_below_100", "rank_unidentified"]),
        ("Evaluated", ["evaluated"]),
    ]
    fig, ax = plt.subplots(figsize=(11, 5.8))
    left = np.zeros(len(order))
    for label, gates in groups:
        values = flow[flow.gate.isin(gates)].groupby("unit")["count"].sum().reindex(order).to_numpy()
        ax.barh(labels, values, left=left, label=label, height=.68)
        left += values
    ax.set(xlabel="Market-calendar origins (sequential first failure)", title="H6: where 428 calendar observations become 0–263 forecasts")
    ax.invert_yaxis()
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.12), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "sample_attrition.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    info = tables["information.csv"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.3))
    axes[0].barh(labels, info.coverage_median * 100, color="#278c98")
    axes[0].set(title="Median surviving previous OI", xlabel="Five-session matched coverage (%)")
    axes[1].barh(labels, info.matched_undefined_days / info.option_days * 100, color="#df9b42")
    axes[1].set(title="Undefined five-session OI growth", xlabel="Post-launch observed sessions (%)")
    for ax in axes:
        ax.invert_yaxis()
    fig.suptitle("OI availability and continuity are different from contract-row counts")
    fig.tight_layout()
    fig.savefig(out / "oi_information.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    comp = tables["common_refit_comparison.csv"].query("block==10 and baseline=='HAR_calendar'")
    fig, ax = plt.subplots(figsize=(10, 5.8))
    units = comp.unit.drop_duplicates().tolist()
    names = comp.drop_duplicates("unit").set_index("unit").name
    for offset, model, color in [(-.14, "matched_OI_lag1", "#307eae"), (.14, "level_OI_lag1", "#d99338")]:
        p = comp[comp.model.eq(model)].set_index("unit").loc[units]
        y = np.arange(len(units)) + offset
        ax.hlines(y, p.ci_low, p.ci_high, color=color, lw=2)
        ax.scatter(p.qlike_difference, y, color=color, label=model)
    ax.axvline(0, color="#555555", lw=1)
    counts = comp.drop_duplicates("unit").set_index("unit")
    ticklabels = [f"{names.loc[u]} (n={int(counts.loc[u, 'n'])}, disjoint={int(counts.loc[u, 'disjoint_target_windows'])})" for u in units]
    ax.set_yticks(np.arange(len(units)), ticklabels)
    ax.invert_yaxis()
    ax.set(title="Post-hoc variable check: identical training rows and target dates",
           xlabel="Paired QLIKE loss difference vs HAR + calendar (negative = better)")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.13), ncol=2, frameon=False)
    fig.text(.5, .005, "Pointwise 95% block-10 intervals; no global model-search adjustment. Small tests remain exploratory.", ha="center", fontsize=9)
    fig.tight_layout(rect=[0, .04, 1, 1])
    fig.savefig(out / "common_refit.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
