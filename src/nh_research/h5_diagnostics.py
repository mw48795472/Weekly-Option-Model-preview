"""H5 precision/design diagnostics; never infer absence from nonsignificance.

Existing primary estimates are read separately and checked, not overwritten.
Planning scenarios condition on estimated nuisance variation and unchanged design.
They are not observed power, equivalence tests, or promises about future samples.
"""
from __future__ import annotations
from statistics import NormalDist
import math
import numpy as np
import pandas as pd
from .single_stocks import calendar_hac

EVENTS = ['weekly_expiry', 'before_weekly_expiry', 'after_weekly_expiry']


def h5_design(panel, kind='stock'):
    """Reconstruct the fixed primary design on the original trading calendar."""
    if kind not in {'stock', 'index'}:
        raise ValueError('Unknown asset kind')
    df = panel.copy().reset_index(drop=True)
    if df.date.duplicated().any() or not df.date.is_monotonic_increasing:
        raise ValueError('Daily panel must have unique ordered dates')
    df['origin_index'] = np.arange(len(df))
    for n in [1, 5, 22]:
        df[f'past{n}'] = np.log(df.parkinson.rolling(n).mean().shift(1))
    cols = EVENTS + ['monthly_expiry']
    cols += ['post_launch'] if kind == 'stock' else ['friday_regime']
    cols += ['past1', 'past5', 'past22']
    if kind == 'stock':
        df['market_lag1'] = np.log(df.market_parkinson.shift(1))
        cols += ['market_lag1']
    for day in range(1, 5):
        df[f'dow{day}'] = df.weekday.eq(day).astype(int)
    cols += [f'dow{day}' for day in range(1, 5)]
    retained = df[cols + ['parkinson']].notna().all(axis=1) & df.parkinson.gt(0)
    part = df.loc[retained].copy()
    X = np.column_stack([np.ones(len(part)), part[cols].to_numpy(float)])
    if not np.isfinite(X).all():
        raise ValueError('Non-finite primary design')
    return df, part, X, ['constant'] + cols


def exposure_diagnostics(X, names, term='weekly_expiry'):
    """Frisch-Waugh residual exposure and standardized numeric conditioning."""
    X = np.asarray(X, float)
    j = names.index(term)
    d = X[:, j]
    others = np.delete(X, j, axis=1)
    residual = d - others @ np.linalg.lstsq(others, d, rcond=None)[0]
    total_ss = float(np.sum((d-d.mean())**2))
    residual_ss = float(residual @ residual)
    fraction = residual_ss/total_ss if total_ss > 0 else 0.0
    rank = int(np.linalg.matrix_rank(X))
    scale = X[:, 1:].std(axis=0)
    z = (X[:, 1:] - X[:, 1:].mean(axis=0))/np.where(scale > 1e-12, scale, 1)
    standardized = np.column_stack([np.ones(len(X)), z])
    condition = float(np.linalg.cond(standardized)) if rank == X.shape[1] else None
    correlations = []
    for i, name in enumerate(names):
        if i != j and X[:, i].std() > 1e-12 and d.std() > 1e-12:
            correlations.append((name, float(np.corrcoef(d, X[:, i])[0, 1])))
    largest = max(correlations, key=lambda v: abs(v[1])) if correlations else ('', 0.0)
    weights = residual**2/residual_ss if residual_ss > 1e-12 else np.zeros(len(d))
    return dict(rank=rank, columns=X.shape[1], identified=rank == X.shape[1],
                expiry_residual_ss=residual_ss, expiry_total_ss=total_ss,
                expiry_information_fraction=fraction,
                expiry_vif=1/fraction if fraction > 1e-12 else None,
                standardized_condition=condition,
                strongest_expiry_correlation_term=largest[0], strongest_expiry_correlation=largest[1],
                max_date_information_share=float(weights.max()) if len(weights) else None), residual


def planning_precision(se, comparisons=1, power=.8, alpha=.05):
    """Normal planning approximation for *assumed* nonzero future effects.

    se is a nuisance precision scenario, not a coefficient-derived effect.
    The two-sided approximation ignores the tiny opposite-tail contribution.
    """
    if not np.isfinite(se) or se <= 0 or comparisons < 1:
        raise ValueError('Positive finite SE and comparison count required')
    if not 0 < alpha < 1 or not .5 < power < 1:
        raise ValueError('Invalid design error rates')
    z = NormalDist().inv_cdf(1-alpha/(2*comparisons))
    return float((z+NormalDist().inv_cdf(power))*se)


def variance_scale(beta):
    """Log daily-variance geometric-mean ratio, not mean RV or a return."""
    return float(100*np.expm1(beta))


def primary_diagnostics(panel, asset_id, name, kind, stored_coefficients):
    df, part, X, names = h5_design(panel, kind)
    design, residual = exposure_diagnostics(X, names)
    retained = df.origin_index.isin(part.origin_index)
    period = 'post_launch' if kind == 'stock' else 'friday_regime'
    weekly = part.loc[part.weekly_expiry.eq(1)]
    iso_weeks = pd.to_datetime(weekly.date).dt.to_period('W-SUN').astype(str)
    all_weeks = pd.to_datetime(part.date).dt.to_period('W-SUN').astype(str)
    info_weight = pd.Series(residual**2, index=part.index)
    total_info = float(info_weight.sum())
    period_information = float(info_weight[part[period].eq(1)].sum()/total_info) if total_info > 0 else np.nan
    groups = part.assign(_week=all_weeks.to_numpy(), _information=residual**2).groupby('_week')._information.sum()
    max_week_share = float(groups.max()/groups.sum()) if groups.sum() else np.nan
    current_missing = df[['open','high','low','close']].isna().any(axis=1)
    zero_range = df.high.eq(df.low) & ~current_missing
    non_comparable = df.non_comparable.eq(True) if kind == 'stock' else pd.Series(False, index=df.index)
    current_proxy_missing = df.parkinson.isna() | ~df.parkinson.gt(0)
    history_missing = df[['past1','past5','past22']].isna().any(axis=1)
    warmup = df.origin_index.lt(22)
    after_warmup_history_missing = history_missing & ~warmup
    clean = df.parkinson.where(~non_comparable)
    clean_history = pd.concat([clean.rolling(n).mean().shift(1) for n in [1,5,22]],axis=1).notna().all(axis=1)
    calendar_boundary = df[EVENTS].isna().any(axis=1)
    audit = pd.DataFrame(dict(asset_id=asset_id, date=df.date, retained=retained,
                             weekly_expiry=df.weekly_expiry, current_price_missing=current_missing,
                             zero_range=zero_range, non_comparable=non_comparable,
                             current_proxy_unavailable=current_proxy_missing,
                             warmup=warmup, history_window_unavailable=history_missing,
                             after_warmup_history_unavailable=after_warmup_history_missing,
                             calendar_boundary=calendar_boundary,
                             clean_current_and_history_available=clean_history & ~current_proxy_missing & ~non_comparable))
    cells = df.assign(retained=retained).groupby([period,'weekday','weekly_expiry','monthly_expiry']).agg(
        raw_dates=('date','size'), retained_dates=('retained','sum')).reset_index().rename(columns={period:'period'})
    cells.insert(0,'asset_id',asset_id);cells['period_name']=period
    rows=[]
    for lag in [5,20]:
        fit, coefficients = calendar_hac(np.log(part.parkinson), X, names, part.origin_index, lag)
        if not fit['identified']:
            raise ValueError('Primary design is not identified: '+asset_id)
        calculated = next(r for r in coefficients if r['term']=='weekly_expiry')
        original = stored_coefficients.loc[(stored_coefficients.variant=='primary') &
            (stored_coefficients.lags==lag) & (stored_coefficients.term=='weekly_expiry')]
        if len(original)!=1:
            raise ValueError('Missing/duplicated saved primary result')
        old=original.iloc[0]
        # Saved estimates are rounded to 8 decimals on stocks; calendar positions preserve gaps.
        for field in ['coefficient','hac_se','ci_low','ci_high']:
            if not np.isclose(calculated[field],old[field],atol=1e-7,rtol=1e-7):
                raise ValueError('Primary reproduction differs: '+asset_id+' '+field)
        family=21 if kind=='stock' else 3
        family_z=NormalDist().inv_cdf(1-.05/(2*family))
        calculated['family_ci_low']=calculated['coefficient']-family_z*calculated['hac_se']
        calculated['family_ci_high']=calculated['coefficient']+family_z*calculated['hac_se']
        mde=planning_precision(calculated['hac_se'])
        family_mde=planning_precision(calculated['hac_se'],family)
        rows.append(dict(asset_id=asset_id,asset_name=name,asset_kind=kind,lags=lag,
            start=part.date.min(),end=part.date.max(),raw_days=len(df),model_days=len(part),
            event_days=len(weekly),non_event_days=int(part.weekly_expiry.eq(0).sum()),
            unique_expiry_weeks=iso_weeks.nunique(),unique_model_weeks=all_weeks.nunique(),
            raw_expiry_days=int(df.weekly_expiry.sum()),excluded_expiry_days=int((df.weekly_expiry.eq(1)&~retained).sum()),
            missing_price_days=int(current_missing.sum()),zero_range_days=int(zero_range.sum()),
            non_comparable_days=int(non_comparable.sum()),warmup_days=int(warmup.sum()),
            after_warmup_history_unavailable_days=int(after_warmup_history_missing.sum()),
            excluded_after_initial_boundary_days=int((~retained & ~warmup & ~calendar_boundary).sum()),
            retained_non_comparable_days=int((retained&non_comparable).sum()),
            stricter_clean_current_history_days=int((retained & clean_history & ~non_comparable).sum()),
            period_name=period,period1_information_share=period_information,
            max_week_information_share=max_week_share,**design,**calculated,
            variance_effect_pct=variance_scale(calculated['coefficient']),
            variance_ci_low_pct=variance_scale(calculated['ci_low']),variance_ci_high_pct=variance_scale(calculated['ci_high']),
            volatility_effect_pct=variance_scale(calculated['coefficient']/2),
            volatility_ci_low_pct=variance_scale(calculated['ci_low']/2),volatility_ci_high_pct=variance_scale(calculated['ci_high']/2),
            planning_mde80_log=mde,planning_mde80_variance_pct=variance_scale(mde),
            planning_comparisons=family,planning_family_mde80_log=family_mde,
            planning_family_mde80_variance_pct=variance_scale(family_mde)))
    return pd.DataFrame(rows),cells,audit


def precision_scenarios(primary):
    """Pure planning conditional on stable design, HAC nuisance, and dependence."""
    rows=[]
    for r in primary.itertuples():
        for factor in [1,2,4]:
            projected=r.planning_mde80_log/math.sqrt(factor)
            rows.append(dict(asset_id=r.asset_id,lags=r.lags,scenario='fixed_sample_multiplier',
                target_variance_increase_pct=np.nan,sample_multiplier=factor,
                model_days_scenario=r.model_days*factor,expiry_dates_scenario=r.event_days*factor,
                planning_mde80_log=projected,planning_mde80_variance_pct=variance_scale(projected),
                planning_family_mde80_log=r.planning_family_mde80_log/math.sqrt(factor)))
        for pct in [10,25,50]:
            target=math.log1p(pct/100)
            factor=max(1.,(r.planning_mde80_log/target)**2)
            rows.append(dict(asset_id=r.asset_id,lags=r.lags,scenario='illustrative_target_not_SESOI',
                target_variance_increase_pct=pct,sample_multiplier=factor,
                model_days_scenario=math.ceil(r.model_days*factor),expiry_dates_scenario=math.ceil(r.event_days*factor),
                planning_mde80_log=r.planning_mde80_log/math.sqrt(factor),
                planning_mde80_variance_pct=variance_scale(r.planning_mde80_log/math.sqrt(factor)),
                planning_family_mde80_log=r.planning_family_mde80_log/math.sqrt(factor)))
    return pd.DataFrame(rows)


def existing_sensitivity(coefficients, asset_id, kind):
    """Expose every already specified event sensitivity; no best-model selection."""
    result=coefficients.loc[coefficients.term.isin(EVENTS)].copy()
    result.insert(0,'asset_id',asset_id)
    result['asset_kind']=kind
    result['variance_effect_pct']=result.coefficient.map(variance_scale)
    result['variance_ci_low_pct']=result.ci_low.map(variance_scale)
    result['variance_ci_high_pct']=result.ci_high.map(variance_scale)
    result['marginal_ci_includes_zero']=result.ci_low.le(0)&result.ci_high.ge(0)
    result['source']='saved_original_fixed_specification'
    return result


def specification_design(panel,asset_id,kind):
    """Diagnose each original specification, without changing its coefficient result."""
    full,primary,_,names=h5_design(panel,kind)
    variants=(['primary','weekday_by_launch','post_launch_only','exclude_non_comparable'] if kind=='stock'
              else ['primary','weekday_by_regime','exclude_monthly','placebo_shift2'])
    rows=[]
    for variant in variants:
        part=primary.copy();cols=names[1:].copy()
        if variant in ['weekday_by_launch','weekday_by_regime']:
            period='post_launch' if kind=='stock' else 'friday_regime'
            for day in range(1,5):
                term=f'dow{day}_interaction';part[term]=part[f'dow{day}']*part[period];cols.append(term)
        elif variant=='post_launch_only':
            part=part.loc[part.post_launch.eq(1)];cols.remove('post_launch')
        elif variant=='exclude_non_comparable':part=part.loc[~part.non_comparable]
        elif variant=='exclude_monthly':
            part=part.loc[part.monthly_expiry.eq(0)];cols.remove('monthly_expiry')
        elif variant=='placebo_shift2':
            part[EVENTS]=part[EVENTS].shift(2);part=part.dropna(subset=EVENTS)
        X=np.column_stack([np.ones(len(part)),part[cols].to_numpy(float)])
        info,residual=exposure_diagnostics(X,['constant']+cols)
        dominant=int(np.argmax(residual**2))
        reduced=np.delete(X,dominant,axis=0)
        reduced_rank=int(np.linalg.matrix_rank(reduced))
        reduced_info,_=exposure_diagnostics(reduced,['constant']+cols)
        rows.append(dict(asset_id=asset_id,variant=variant,model_days=len(part),event_days=int(part.weekly_expiry.sum()),
            dominant_information_date=part.date.iloc[dominant],dominant_information_is_expiry=int(part.weekly_expiry.iloc[dominant]),
            rank_without_dominant_date=reduced_rank,identified_without_dominant_date=reduced_rank==X.shape[1],
            expiry_information_fraction_without_dominant_date=reduced_info['expiry_information_fraction'],**info))
    return pd.DataFrame(rows)
