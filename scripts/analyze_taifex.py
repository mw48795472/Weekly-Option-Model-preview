"""Reproduce TAIFEX descriptive outputs from frozen, hashed public responses (offline)."""
from __future__ import annotations
import argparse
from datetime import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from nh_research.taifex import (decode_response, normalize_market, product_metadata, enrich,
                                expiry_reference, describe_groups, decompose_oi)


def write_csv(path, frame):
    raw=frame.to_csv(index=False, lineterminator="\n", float_format="%.10g").encode("utf-8-sig")
    if path.suffix==".gz":
        buffer=io.BytesIO()
        with gzip.GzipFile(filename="",mode="wb",fileobj=buffer,mtime=0) as handle: handle.write(raw)
        raw=buffer.getvalue()
    path.write_bytes(raw)


def clean_json(value):
    if isinstance(value,dict): return {str(k):clean_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean_json(v) for v in value]
    if isinstance(value,np.generic): value=value.item()
    if isinstance(value,float) and not np.isfinite(value): return None
    return value


def charts(latest, groups, changes, pcr, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    output.mkdir(parents=True,exist_ok=True)
    date=latest.date.max()
    stock=latest.loc[latest.asset_type.eq("stock")]
    coverage=stock.groupby("product").agg(contracts=("contract_id","size"),traded=("has_trade_price","sum"))
    fig,axs=plt.subplots(1,2,figsize=(12,4.5),layout="constrained")
    axs[0].bar(coverage.index,100*coverage.traded/coverage.contracts,color="#087F8C")
    axs[0].set(ylabel="Contracts with a trade price (%)",title="Single-stock weekly price coverage",ylim=(0,100))
    sub=latest.loc[latest["product"].eq("CDO")]
    for side,color in (("C","#087F8C"),("P","#C88B37")):
        part=sub.loc[sub.side.eq(side)].groupby("strike").oi.sum()
        axs[1].plot(part.index,part.values,label=side,color=color,marker=".",linewidth=1.3)
    axs[1].set(xlabel="Strike (TWD/share)",ylabel="Open interest (contracts)",title="TSMC weekly OI across strikes")
    axs[1].legend()
    for ax in axs: ax.spines[["top","right"]].set_visible(False)
    fig.suptitle(f"TAIFEX regular-session snapshot | {date} | no directional inference")
    fig.savefig(output/"taifex_stock_coverage.png",dpi=150)
    plt.close(fig)
    tx=changes.loc[changes["product"].eq("TXO")].copy()
    daily=groups.loc[groups["product"].eq("TXO")].groupby("date").oi.sum()
    fig,axs=plt.subplots(2,1,figsize=(12,7),layout="constrained")
    axs[0].plot(pd.to_datetime(daily.index),daily.values,color="#087F8C",marker=".")
    axs[0].set(ylabel="Weekly OI (contracts)",title="TXO weekly open interest | changing contract universe")
    x=pd.to_datetime(tx.date)
    for col,label,color in [("matched_change","Continuing contracts","#087F8C"),("entering_oi","Entering universe","#426DAD")]:
        axs[1].plot(x,tx[col],marker=".",label=label,color=color)
    axs[1].plot(x,-tx.exiting_oi,marker=".",label="Leaving universe (negative OI)",color="#C88B37")
    axs[1].plot(x,tx.total_change,label="Total OI change",color="#293C54",linestyle="--")
    axs[1].axhline(0,color="#B7C4CC",linewidth=.8)
    axs[1].set(ylabel="Change in contracts",title="Observed-universe decomposition; not investor flows")
    axs[1].legend(fontsize=8,ncol=2,loc="upper left")
    for ax in axs: ax.spines[["top","right"]].set_visible(False)
    for ax in axs:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4,maxticks=7))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.set_xlabel("Trading date (2026)")
    fig.savefig(output/"taifex_oi_decomposition.png",dpi=150)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.4),layout="constrained")
    x=pd.to_datetime(pcr.date)
    ax.plot(x,pcr.put_call_oi_ratio,label="Put OI / Call OI",color="#087F8C",marker=".")
    ax.plot(x,pcr.put_call_volume_ratio,label="Put volume / Call volume",color="#C88B37",marker=".")
    ax.axhline(1,color="#8D9EA9",linestyle="--",linewidth=.8)
    ax.set(ylabel="Ratio (1.0 = 100%)",title="TAIFEX published TXO put/call ratios | all expiries")
    ax.spines[["top","right"]].set_visible(False)
    ax.legend()
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4,maxticks=7))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.set_xlabel("Trading date (2026)")
    fig.savefig(output/"taifex_put_call.png",dpi=150)
    plt.close(fig)


def build(source, output, make_charts=True):
    source=Path(source); output=Path(output); output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/"manifest.json").read_text(encoding="utf-8"))
    entries={m["name"]:m for m in manifest["requests"] if m.get("complete")}
    def raw(name):
        meta=entries[name]; content=gzip.decompress((source/meta["file"]).read_bytes())
        if hashlib.sha256(content).hexdigest()!=meta["sha256"]: raise ValueError(f"Hash mismatch: {name}")
        return content
    def rows(name): return decode_response(raw(name))[0]
    sso=rows("SSOLists")
    historical_catalog=json.loads(raw("history_contracts"))["commodityList"]
    metadata=product_metadata(sso,historical_catalog,rows("SSFAdjustedInfo"))
    api=normalize_market(rows("DailyMarketReportOpt"),"TAIFEX OpenAPI DailyMarketReportOpt")
    expiry_map=expiry_reference(rows("DailyOptionsDelta"))
    api["expiry_date"]=api.contract_id.map(expiry_map).fillna("")
    api["expiry_date_source"]=np.where(api.expiry_date.ne(""),"undated_DailyOptionsDelta_reference","")
    api=enrich(api,metadata)
    history=pd.concat([normalize_market(rows(n),n) for n in sorted(entries) if n.startswith("history_") and n!="history_contracts"],ignore_index=True)
    if history.duplicated(["date","contract_id","session"]).any(): raise ValueError("Overlapping history files")
    history=enrich(history,metadata)
    dates=sorted(history.date.unique())
    # Reconcile overlapping actual fields, keeping source datasets separate.
    keys=["date","contract_id","session"]
    fields=["open","high","low","close","volume","settlement","oi","bid","ask"]
    matched=api[keys+fields].merge(history[keys+fields],on=keys,how="inner",suffixes=("_api","_csv"),validate="one_to_one")
    discrepancies={}
    for field in fields:
        a,b=matched[field+"_api"],matched[field+"_csv"]
        discrepancies[field]=int((~(a.eq(b)|(a.isna()&b.isna()))).sum())
    if any(discrepancies[k] for k in fields if k not in ("bid","ask")):
        raise ValueError(f"API/CSV price or OI disagreement: {discrepancies}")
    weekly_history=history.loc[history.is_weekly].copy()
    latest=api.loc[api.session.eq("regular")&api.is_weekly].copy()
    groups=describe_groups(history)
    changes=decompose_oi(history)
    catalog=pd.concat([history,api],ignore_index=True).sort_values(["date","session"]).drop_duplicates("contract_id",keep="last")
    catalog=catalog[["contract_id","product","underlying_code","name","asset_type","adjusted","expiry_code",
                     "expiry_date","expiry_date_source","side","strike_text","trading_product_code","label"]].sort_values("contract_id")
    counts=api.groupby("product").agg(api_rows=("contract_id","size"),api_unique_contracts=("contract_id","nunique"))
    week_counts=latest.groupby("product").agg(latest_weekly_contracts=("contract_id","size"))
    product_map=metadata.merge(counts,on="product",how="left").merge(week_counts,on="product",how="left")
    pcr=pd.DataFrame(rows("PutCallRatio"))
    pcr["date"]=pd.to_datetime(pcr.Date,format="%Y%m%d").dt.strftime("%Y-%m-%d")
    pcr["put_call_oi_ratio"]=pd.to_numeric(pcr["PutCallOIRatio%"])/100
    pcr["put_call_volume_ratio"]=pd.to_numeric(pcr["PutCallVolumeRatio%"])/100
    pcr=pcr.sort_values("date")
    # Rounded official percentages should agree with the underlying integer ratios.
    for numerator,denominator,metric in [("PutOI","CallOI","put_call_oi_ratio"),("PutVolume","CallVolume","put_call_volume_ratio")]:
        calculated=pd.to_numeric(pcr[numerator])/pd.to_numeric(pcr[denominator])
        if not np.allclose(calculated,pcr[metric],atol=.000051,rtol=0): raise ValueError("PCR units mismatch")
    api_coverage=[]
    for name,meta in entries.items():
        if name.startswith("history_") or name=="swagger": continue
        values,fmt=decode_response(raw(name))
        date_fields=[f for f in ("Date","TheFinalSettlementDay","AdjustmentDate") if values and f in values[0]]
        observed_dates=sorted({str(r[f]) for r in values for f in date_fields if r.get(f)})
        api_coverage.append(dict(endpoint=name,http_status=meta["status"],actual_format=fmt,rows=len(values),
                                 date_field=";".join(date_fields),min_date=observed_dates[0] if observed_dates else "",
                                 max_date=observed_dates[-1] if observed_dates else "",distinct_dates=len(observed_dates),
                                 retrieved_at=meta["retrieved_at"],date_query_documented=False))
    exported={
        "latest_weekly.csv":latest.sort_values(["product","expiry_code","side","strike"]),
        "weekly_history.csv.gz":weekly_history.sort_values(["date","product","expiry_code","side","strike","session"]),
        "ticker_catalog.csv":catalog,"product_tickers.csv":product_map.sort_values("product"),
        "expiry_summary.csv":groups,"oi_decomposition.csv":changes,"put_call_history.csv":pcr,
        "api_coverage.csv":pd.DataFrame(api_coverage),
        "api_csv_comparison.csv":matched,
    }
    for file,frame in exported.items(): write_csv(output/file,frame)
    overview=latest.groupby(["product","name","underlying_code"]).agg(
        contracts=("contract_id","size"),oi=("oi","sum"),volume=("volume","sum"),
        traded_contracts=("has_trade_price","sum"),two_sided_quotes=("valid_two_sided_quote","sum")).reset_index()
    overview["trade_price_coverage_pct"]=100*overview.traded_contracts/overview.contracts
    summary=dict(
        provider="TAIFEX",collected_date_kst=manifest.get("checked_date_kst", manifest.get("collected_date_kst")),api_market_date=api.date.max(),
        api_rows=len(api),api_unique_contracts=api.contract_id.nunique(),
        regular_rows=int(api.session.eq("regular").sum()),after_hours_rows=int(api.session.eq("after_hours").sum()),
        history_start=dates[0],history_end=dates[-1],history_dates=len(dates),history_rows=len(history),
        history_source_files=sum(n.startswith("history_") and n!="history_contracts" for n in entries),weekly_history_rows=len(weekly_history),
        weekly_unique_contracts=weekly_history.contract_id.nunique(),
        latest_weekly_contracts=len(latest),latest_stock_weekly_contracts=int(latest.asset_type.eq("stock").sum()),
        weekly_products=sorted(latest["product"].unique()),stock_master_rows=len(sso),
        total_ticker_catalog_rows=len(catalog),
        api_csv_overlap_rows=len(matched),api_csv_discrepancies=discrepancies,
        after_hours_oi_observed=int(api.loc[api.session.eq("after_hours"),"oi"].notna().sum()),
        pcr_dates=len(pcr),pcr_start=pcr.date.min(),pcr_end=pcr.date.max(),
        current_products=overview.to_dict("records"),prediction_performance=None,
        limits=["No underlying intraday prices: RV/HAR/REV and transfer performance not estimated",
                "Daily quotes are closing snapshots, not synchronized order-book history",
                "Delta reference has no observation date; not used as a predictive feature",
                "Short historical sample and OI changes are descriptive, not causal",
                "Tick request exceeded 30 MB guard; prefix inspected, no complete tick sample"],
        internal_id_is_order_symbol=False,source_manifest=(source.relative_to(ROOT)/"manifest.json").as_posix())
    (output/"summary.json").write_text(json.dumps(clean_json(summary),ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    if make_charts: charts(latest,groups,changes,pcr,ROOT/"docs/images/taifex")
    archive=ROOT/"docs/downloads/taifex_weekly_data.zip"
    attribution=(ROOT/"data/source/taifex/README.md").read_bytes()
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as handle:
        for name in sorted([*exported,"summary.json"]):
            info=zipfile.ZipInfo(name,date_time=(2026,10,12,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            handle.writestr(info,(output/name).read_bytes())
        info=zipfile.ZipInfo("SOURCE_AND_LICENSE.md",date_time=(2026,10,12,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
        handle.writestr(info,attribution)
    print(json.dumps(clean_json(summary),ensure_ascii=False))
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=ROOT/"data/source/taifex/20261012")
    parser.add_argument("--output",type=Path,default=ROOT/"data/analysis/taifex")
    parser.add_argument("--no-charts",action="store_true")
    args=parser.parse_args()
    build(args.source,args.output,not args.no_charts)
