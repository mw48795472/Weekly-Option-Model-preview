"""Post-hoc H6 diagnostics; existing confirmatory outputs are read, never replaced."""
from __future__ import annotations

import numpy as np
import pandas as pd
from .empirical import FLOOR
from .single_stocks import loss_intervals, predict_mean

GATES = [
    "pre_launch", "history_initial_22", "history_missing_price",
    "history_zero_range", "history_non_comparable", "history_other_proxy_missing",
    "oi_warmup_or_source_missing", "oi_zero_denominator_or_no_overlap",
    "oi_other_missing", "target_end_boundary", "target_missing_price",
    "target_zero_range", "target_non_comparable", "target_other_missing",
    "calendar_missing", "initial_train_below_100",
    "purge_train_below_100", "rank_unidentified", "evaluated",
]


def prepare(panel, proxy="parkinson", family="matched"):
    df = panel.reset_index(drop=True).copy()
    if df.date.duplicated().any() or not df.date.is_monotonic_increasing:
        raise ValueError("Expected one complete ordered market calendar")
    df["origin_index"] = np.arange(len(df))
    if "post_launch" not in df:
        df["post_launch"] = 1
    if "price_missing" not in df:
        df["price_missing"] = df[["open", "high", "low", "close"]].isna().any(axis=1)
    if "non_comparable" not in df:
        df["non_comparable"] = False
    for n in (1, 5, 22):
        df[f"log{n}"] = np.log(df[proxy].rolling(n).mean().clip(lower=FLOOR))
    calendar = ["log1", "log5", "log22", "next5_weekly", "next5_monthly"]
    if "friday_regime" in df:
        calendar.append("friday_regime")
    for lag in (1, 2):
        if f"oi_level_lag{lag}" not in df:
            df[f"oi_level_lag{lag}"] = np.log1p(df.weekly_oi).shift(lag)
    extras = (["oi_matched_lag1", "oi_matched_lag2", "oi_total_lag1"]
              if family == "matched" else ["oi_level_lag1", "oi_level_lag2"])
    required = calendar + extras + [proxy + "_forward5", "label_end"]
    eligible = df[required].notna().all(axis=1) & df.post_launch.eq(1)
    return df, calendar, extras, eligible


def _history_any(values):
    return values.fillna(False).rolling(22, min_periods=1).max().astype(bool)


def _future_any(values):
    return pd.concat([values.shift(-n).fillna(False) for n in range(1, 6)], axis=1).any(axis=1)


def audit_origins(panel, predictions, proxy="parkinson", family="matched", minimum_train=100):
    """Each row has exactly one first-failing gate; overlapping flags stay separate."""
    df, calendar, extras, eligible = prepare(panel, proxy, family)
    missing = df.price_missing.eq(True)
    zero = df.high.eq(df.low) & ~missing
    event = df.non_comparable.eq(True)
    history_bad = df[["log1", "log5", "log22"]].isna().any(axis=1)
    target_bad = df[proxy + "_forward5"].isna()
    oi_bad = df[extras].isna().any(axis=1)
    # Need lags 1 and 2 plus a five-session matched denominator in the primary family.
    source_bad = pd.Series(False, index=df.index)
    denominator_bad = pd.Series(False, index=df.index)
    for lag in (1, 2):
        source_bad |= df.weekly_oi.shift(lag).isna()
        if family == "matched":
            source_bad |= df.weekly_oi.shift(lag + 5).isna()
            denominator_bad |= df.matched_previous_oi.shift(lag).le(0)
    if family == "matched":
        denominator_bad |= df.weekly_oi.shift(6).le(0)
    # A missing previous close also makes a squared-return proxy unavailable.
    history_missing = _history_any(missing | (missing.shift(1, fill_value=False)
                                               if proxy == "close_squared_return" else False))
    target_missing = _future_any(missing | (missing.shift(1, fill_value=False)
                                              if proxy == "close_squared_return" else False))
    flags = {
        "pre_launch": df.post_launch.ne(1),
        "history_initial_22": df.origin_index.lt(21),
        "history_missing_price": history_bad & history_missing,
        "history_zero_range": history_bad & _history_any(zero) & (proxy != "close_squared_return"),
        "history_non_comparable": history_bad & _history_any(event) & (proxy != "parkinson"),
        "history_other_proxy_missing": history_bad,
        "oi_warmup_or_source_missing": oi_bad & source_bad,
        "oi_zero_denominator_or_no_overlap": oi_bad & denominator_bad,
        "oi_other_missing": oi_bad,
        "target_end_boundary": df.label_end.isna(),
        "target_missing_price": target_bad & target_missing,
        "target_zero_range": target_bad & _future_any(zero) & (proxy != "close_squared_return"),
        "target_non_comparable": target_bad & _future_any(event) & (proxy != "parkinson"),
        "target_other_missing": target_bad,
        "calendar_missing": df[[c for c in calendar if not c.startswith("log")]].isna().any(axis=1),
    }
    pred_dates = set(predictions.date) if not predictions.empty else set()
    rows = []
    for i, row in df.iterrows():
        prior = eligible & df.date.lt(row.date)
        completed = eligible & df.label_end.lt(row.date)
        n_prior, n_complete = int(prior.sum()), int(completed.sum())
        gate = next((name for name in GATES if name in flags and bool(flags[name].iloc[i])), None)
        if gate is None:
            if not eligible.iloc[i]:
                raise ValueError("Unclassified eligibility failure")
            if n_prior < minimum_train:
                gate = "initial_train_below_100"
            elif n_complete < minimum_train:
                gate = "purge_train_below_100"
            elif row.date in pred_dates:
                gate = "evaluated"
            else:
                # Existing stock forecast rejects a joint origin if any model is unidentified.
                # Verify the rank explanation rather than treating arbitrary missing output as rank.
                if "friday_regime" in df:
                    raise ValueError("Unexpected missing index forecast")
                invalid = False
                for columns in (["log1", "log5", "log22"], calendar,
                                *[calendar + [extra] for extra in extras]):
                    value, _ = predict_mean(df.loc[completed, columns].to_numpy(float),
                                            df.loc[completed, proxy + "_forward5"].to_numpy(float),
                                            df.loc[i, columns].to_numpy(float))
                    invalid |= value is None
                if not invalid:
                    raise ValueError("Forecast absent without an identification failure")
                gate = "rank_unidentified"
        if (gate == "evaluated") != (row.date in pred_dates):
            raise ValueError("Diagnostic gates do not reproduce saved forecasts")
        rows.append(dict(date=row.date, origin_index=i, proxy=proxy, family=family,
                         gate=gate, eligible=bool(eligible.iloc[i]), prior_eligible=n_prior,
                         completed_train=n_complete, purged_labels=n_prior - n_complete,
                         **{"flag_" + key: bool(value.iloc[i]) for key, value in flags.items()}))
    audit = pd.DataFrame(rows)
    remaining = len(audit)
    flow = []
    for order, gate in enumerate(GATES):
        count = int(audit.gate.eq(gate).sum())
        if gate != "evaluated":
            remaining -= count
        flow.append(dict(order=order, gate=gate, count=count, remaining=remaining,
                         proxy=proxy, family=family))
    if remaining != len(pred_dates) or int(audit.gate.eq("evaluated").sum()) != len(pred_dates):
        raise ValueError("Funnel must reconcile exactly")
    return audit, pd.DataFrame(flow)


def information(panel):
    df = panel.copy()
    post = df.loc[df.get("post_launch", pd.Series(1, index=df.index)).eq(1)]
    valid = post.oi_matched_5d.dropna()
    cover = post.continuing_previous_coverage.dropna()
    vals = dict(calendar_days=len(df), option_days=len(post),
                zero_oi_days=int(post.weekly_oi.eq(0).sum()),
                missing_price_days=int(df[["open", "high", "low", "close"]].isna().any(axis=1).sum()),
                zero_range_days=int(df.high.eq(df.low).sum()),
                non_comparable_days=int(df.get("non_comparable", pd.Series(False, index=df.index)).eq(True).sum()),
                matched_defined_days=len(valid), matched_undefined_days=len(post) - len(valid),
                coverage_defined_days=len(cover), coverage_below_10pct_days=int(cover.lt(.1).sum()),
                nonzero_oi_days=int(post.weekly_oi.gt(0).sum()))
    for name, series in [("weekly_oi", post.weekly_oi), ("coverage", cover),
                         ("matched_denominator", post.matched_previous_oi),
                         ("matched_change", valid)]:
        for q, label in [(.05, "p05"), (.5, "median"), (.95, "p95")]:
            vals[name + "_" + label] = float(series.quantile(q)) if series.notna().any() else np.nan
    vals["matched_change_abs_gt_100pct_days"] = int(valid.abs().gt(1).sum())
    vals["matched_change_abs_gt_1000pct_days"] = int(valid.abs().gt(10).sum())
    return vals


def label_overlap(rows):
    """Maximum disjoint target intervals, not an estimated independent sample size."""
    unique = rows.drop_duplicates("date").sort_values("label_end")
    chosen = []
    last_end = ""
    for row in unique.itertuples():
        if row.label_start > last_end:
            chosen.append(row.date)
            last_end = row.label_end
    positions = unique.origin_index.astype(int).to_numpy()
    span = int(positions.max() - positions.min() + 1) if len(positions) else 0
    return dict(n=len(unique), calendar_span=span, calendar_gaps=span - len(unique),
                disjoint_target_windows=len(chosen),
                disjoint_dates=";".join(chosen),
                test_start=unique.date.min() if len(unique) else "",
                test_end=unique.date.max() if len(unique) else "",
                occupied_nonoverlapping_10session_bins=len(set((positions - positions.min()) // 10))
                if len(positions) else 0)


def paired_loss(rows, model, baseline, block=10):
    pivot = rows.pivot(index="date", columns="model", values="qlike")
    pair = pivot[[model, baseline]].dropna()
    dates = pair.index
    selected = rows[rows.date.isin(dates)]
    positions = selected.drop_duplicates("date").set_index("date").origin_index
    delta = pair[model] - pair[baseline]
    full = pd.Series(delta.to_numpy(), index=positions.loc[dates].astype(int)).sort_index()
    full = full.reindex(range(int(full.index.min()), int(full.index.max()) + 1))
    low, high, family_low, family_high = loss_intervals(full.to_numpy(), block=block)
    return dict(model=model, baseline=baseline, block=block, qlike_difference=float(delta.mean()),
                ci_low=float(low), ci_high=float(high), family7_ci_low=float(family_low),
                family7_ci_high=float(family_high), ci_width=float(high - low),
                bootstrap_possible_calendar_starts=max(len(full) - block + 1, 1),
                bootstrap_blocks_per_draw=int(np.ceil(len(full) / block)),
                short_span_for_block=bool(len(full) < 2 * block),
                compatible_gain_upper_pointwise95=float(max(0, -low)),
                gain_estimate=float(-delta.mean()), **label_overlap(selected))


def common_refit(panel, proxy="parkinson", minimum_train=100):
    """Fixed post-hoc feature diagnostic with identical training and test observations."""
    df, calendar, _, eligible = prepare(panel, proxy, "matched")
    models = {"HAR_calendar": calendar,
              "matched_OI_lag1": calendar + ["oi_matched_lag1"],
              "level_OI_lag1": calendar + ["oi_level_lag1"]}
    rows = []
    for i, row in df.iterrows():
        if not eligible.iloc[i]:
            continue
        train = eligible & df.label_end.lt(row.date)
        if int(train.sum()) < minimum_train:
            continue
        trial = []
        for model, columns in models.items():
            value, rank = predict_mean(df.loc[train, columns].to_numpy(float),
                                      df.loc[train, proxy + "_forward5"].to_numpy(float),
                                      row[columns].to_numpy(float))
            if value is None:
                trial = []
                break
            actual = float(row[proxy + "_forward5"])
            trial.append(dict(date=row.date, origin_index=i, proxy=proxy, model=model,
                              actual=actual, forecast=value, qlike=float(np.log(value) + actual / value),
                              train_n=int(train.sum()), train_last_label_end=df.loc[train, "label_end"].max(),
                              label_start=row.label_start, label_end=row.label_end, design_rank=rank))
        rows.extend(trial)
    return pd.DataFrame(rows)
