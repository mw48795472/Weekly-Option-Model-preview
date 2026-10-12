"""Reproduce daily-proxy H5/H6 from hashed official Taiwan observations, offline."""
from __future__ import annotations
import argparse,gzip,hashlib,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from nh_research.taifex import decode_response,normalize_market
from nh_research.empirical import (parse_taiex,parse_settlements,oi_five_day,make_panel,
                                  h5_analysis,forecast,compare_forecasts)
from analyze_taifex import write_csv,clean_json

def stable_json(value):
    value=clean_json(value)
    if isinstance(value,dict): return {k:stable_json(v) for k,v in value.items()}
    if isinstance(value,list): return [stable_json(v) for v in value]
    if isinstance(value,float): return float(f"{value:.10g}")
    return value

def raw(source,meta):
    body=gzip.decompress((source/meta["file"]).read_bytes())
    if hashlib.sha256(body).hexdigest()!=meta["sha256"]: raise ValueError("Source hash mismatch "+meta["name"])
    return body

def build(source,output,charts=True):
    output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/"manifest.json").read_text(encoding="utf-8"))
    if any(not m["complete"] for m in manifest["requests"]): raise ValueError("Incomplete source collection")
    prices=[];weekly=[];settlements=[];coverage=[];scheduled=[];raw_rows=0
    for meta in manifest["requests"]:
        content=raw(source,meta);name=meta["name"]
        print("Validate",name,flush=True)
        if name.startswith("taiex_"):
            frame=parse_taiex(content);prices.append(frame)
            coverage.append(dict(source=name,rows=len(frame),dates=frame.date.nunique(),start=frame.date.min(),end=frame.date.max()))
        elif name.startswith("txo_"):
            frame=normalize_market(decode_response(content)[0],name)
            if not frame["product"].eq("TXO").all(): raise ValueError("Unexpected product")
            raw_rows+=len(frame)
            regular=frame.loc[frame.session.eq("regular")].copy()
            if regular.oi.isna().any(): raise ValueError("Missing regular-session OI")
            scheduled.append(regular.loc[regular.expiry_date.ne(""),["expiry_code","expiry_date"]].drop_duplicates())
            part=regular.loc[regular.is_weekly].copy()
            weekly.append(part[["date","contract_id","expiry_code","side","strike","oi","volume","close","settlement"]])
            coverage.append(dict(source=name,rows=len(frame),regular_weekly_rows=len(part),dates=frame.date.nunique(),start=frame.date.min(),end=frame.date.max()))
        elif name.startswith("settlements_"):
            settlements.append(parse_settlements(content))
    prices=pd.concat(prices,ignore_index=True).sort_values("date")
    prices=prices.loc[prices.date.between(manifest["start"],manifest["end"])].reset_index(drop=True)
    weekly=pd.concat(weekly,ignore_index=True).sort_values(["date","contract_id"]).reset_index(drop=True)
    calendar=pd.concat(settlements,ignore_index=True).sort_values("expiry_date")
    if calendar.expiry_code.duplicated().any(): raise ValueError("Duplicate expiry calendar")
    schedule=pd.concat(scheduled).drop_duplicates()
    if schedule.expiry_code.duplicated().any(): raise ValueError("Changed scheduled expiry: review source revisions")
    join=schedule.merge(calendar[["expiry_code","expiry_date"]],on="expiry_code",suffixes=("_scheduled","_actual"))
    conflicts=join.loc[join.expiry_date_scheduled.ne(join.expiry_date_actual)]
    # Actual final settlements override scheduled last-trading dates. Every mismatch is audited.
    write_csv(output/"expiry_schedule_audit.csv",conflicts)
    ended=weekly.loc[weekly.expiry_code.str[:6].lt(manifest["end"][:7].replace("-","")),"expiry_code"].unique()
    missing=set(ended)-set(calendar.expiry_code)
    if missing: raise ValueError("Completed expiries missing from official settlement calendar: "+str(missing))
    oi=oi_five_day(weekly)
    # Preserve exact TWSE trading calendar; reject missing option dates.
    extra=sorted(set(oi.date)-set(prices.date))
    if extra: raise ValueError("Unmatched TAIFEX underlying sessions: "+str(extra))
    panel=make_panel(prices,oi,calendar)
    coefficients,diagnostics,cells=h5_analysis(panel)
    prediction=pd.concat([forecast(panel,p) for p in ["parkinson","close_squared_return"]],ignore_index=True)
    scores,comparisons=compare_forecasts(prediction)
    if prediction.empty: raise ValueError("No out-of-sample predictions")
    exports={"daily_panel.csv":panel,"expiry_calendar.csv":calendar,
             "h5_coefficients.csv":coefficients,"h5_design_diagnostics.csv":diagnostics,
             "h5_weekday_comparison.csv":cells,"h6_forecasts.csv":prediction,
             "h6_scores.csv":scores,"h6_loss_comparison.csv":comparisons,"source_coverage.csv":pd.DataFrame(coverage)}
    for name,df in exports.items(): write_csv(output/name,df)
    # Contract-level compressed observations remain separately downloadable.
    write_csv(output/"txo_weekly_history.csv.gz",weekly)
    primary=comparisons.loc[comparisons.proxy.eq("parkinson")&comparisons.model.eq("HAR_calendar_OI_lag1")&comparisons.block.eq(10)].iloc[0].to_dict()
    first=prediction.loc[prediction.proxy.eq("parkinson")]
    summary=dict(version="empirical-20261012",market="TAIFEX TXO / TWSE TAIEX",start=panel.date.min(),end=panel.date.max(),
        trading_days=len(panel),previous_trading_days=20,raw_option_rows=raw_rows,regular_weekly_rows=len(weekly),
        unique_weekly_contracts=weekly.contract_id.nunique(),
        undefined_matched_oi_days=int(panel.oi_matched_5d.isna().sum()),
        continuing_previous_coverage_median=float(panel.continuing_previous_coverage.median()),weekly_expiry_days=int(panel.weekly_expiry.sum()),
        monthly_expiry_days=int(panel.monthly_expiry.sum()),scheduled_actual_conflicts=len(conflicts),
        test_start=first.date.min(),test_end=first.date.max(),test_days=first.date.nunique(),
        target="next five trading days mean Parkinson daily range variance; NOT intraday RV",
        h6_primary=primary,h5_design=diagnostics.to_dict("records"),
        hkex_status="Public daily report access verified; automated collection/derived datasets/public redistribution require permission under HKEX terms section 5. No HKEX market data included.",
        limitations=["Daily proxy, not intraday RV","Retrospective final data, publication/revision timestamps unavailable",
                     "OI lag scenarios are assumptions, not validated availability","Expiry calendar is ex post, historical schedule revisions unavailable",
                     "One index, no single-stock or domestic-transfer conclusion"])
    (output/"summary.json").write_text(json.dumps(stable_json(summary),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if charts: make_charts(panel,coefficients,comparisons,prediction,ROOT/"docs/images/empirical")
    print(json.dumps(stable_json(summary),ensure_ascii=False,indent=2))

def make_charts(panel,coef,comparisons,predictions,out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    teal,blue,amber="#087F8C","#426DAD","#C88B37"
    fig,axes=plt.subplots(2,1,figsize=(12,7),layout="constrained")
    x=pd.to_datetime(panel.date)
    axes[0].plot(x,panel.close,color=blue,lw=1.3)
    axes[0].set(title="TWSE TAIEX underlying | observed daily close",ylabel="Index points")
    axes[1].plot(x,np.sqrt(panel.parkinson)*100,color=teal,lw=1)
    expiry=panel.weekly_expiry.eq(1)
    axes[1].scatter(x[expiry],np.sqrt(panel.loc[expiry,"parkinson"])*100,s=12,c=amber,label="Weekly expiry")
    axes[1].set(title="Daily high-low range proxy | NOT intraday realized volatility",ylabel="sqrt(Parkinson variance) (%)")
    axes[1].legend()
    for ax in axes: ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.savefig(out/"taiex_history.png",dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
    labels=["weekly_expiry","before_weekly_expiry","after_weekly_expiry"]
    chosen=coef.loc[coef.variant.eq("primary")&coef.lags.eq(5)&coef.term.isin(labels)].set_index("term").reindex(labels)
    if chosen.coefficient.notna().all():
        y=np.arange(len(chosen))
        axes[0].errorbar(chosen.coefficient,y,xerr=[chosen.coefficient-chosen.ci_low,chosen.ci_high-chosen.coefficient],fmt="o",color=teal,capsize=4)
        axes[0].set_yticks(y,["Expiry","Previous session","Next session"])
        axes[0].axvline(0,color="#888",ls="--")
        axes[0].set(xlabel="Log range-variance coefficient (HAC 95% CI)",title="H5: conditional association, not causality")
    else: axes[0].text(.1,.5,"H5 design not separately identified")
    subset=comparisons.loc[comparisons.proxy.eq("parkinson")&comparisons.block.eq(10)]
    y=np.arange(len(subset))
    axes[1].errorbar(subset.qlike_difference,y,xerr=[subset.qlike_difference-subset.ci_low,subset.ci_high-subset.qlike_difference],fmt="o",color=blue,capsize=4)
    axes[1].set_yticks(y,["Calendar vs HAR","Matched OI lag 1","Matched OI lag 2","Total OI lag 1"])
    axes[1].axvline(0,color="#888",ls="--")
    axes[1].set(xlabel="QLIKE difference (negative = improvement)",title="H6: paired OOS loss | 10-session block CI")
    fig.savefig(out/"h5_h6_evidence.png",dpi=150);plt.close(fig)
    selected=predictions.loc[predictions.proxy.eq("parkinson")]
    pivot=selected.pivot(index="date",columns="model",values="qlike")
    fig,ax=plt.subplots(figsize=(12,4.5),layout="constrained")
    for col,color,label in [("HAR_calendar_OI_lag1",teal,"Matched OI, lag 1"),("HAR_calendar_OI_lag2",blue,"Matched OI, lag 2"),("HAR_calendar_totalOI_lag1",amber,"Changing-universe OI, lag 1")]:
        ax.plot(pd.to_datetime(pivot.index),(pivot[col]-pivot.HAR_calendar).cumsum(),color=color,label=label)
    ax.axhline(0,color="#888",ls="--")
    ax.set(title="Cumulative out-of-sample QLIKE difference vs HAR + calendar",ylabel="Cumulative difference (lower is better)",xlabel="Forecast origin | expanding window, labels purged")
    ax.legend(ncol=3,fontsize=9);fig.savefig(out/"h6_cumulative_loss.png",dpi=150);plt.close(fig)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,default=ROOT/"data/source/extended_taiwan/20261012")
    p.add_argument("--output",type=Path,default=ROOT/"data/analysis/empirical")
    p.add_argument("--no-charts",action="store_true")
    a=p.parse_args();build(a.source,a.output,not a.no_charts)
