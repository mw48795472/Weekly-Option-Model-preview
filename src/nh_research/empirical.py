"""Daily-proxy H5/H6 research. Never call these outputs intraday realized variance."""
from __future__ import annotations
from datetime import datetime
import html
import json
import math
import re
import numpy as np
import pandas as pd

FLOOR=1e-12

def parse_taiex(raw):
    obj=json.loads(raw)
    if obj.get("stat")!="OK" or obj.get("fields")!=["日期","開盤指數","最高指數","最低指數","收盤指數"]:
        raise ValueError("Unexpected TWSE schema/status")
    rows=[]
    for day,op,hi,lo,cl in obj["data"]:
        y,m,d=map(int,day.split("/"))
        rows.append(dict(date=f"{y+1911:04d}-{m:02d}-{d:02d}",
                         open=float(op.replace(",","")),high=float(hi.replace(",","")),
                         low=float(lo.replace(",","")),close=float(cl.replace(",",""))))
    df=pd.DataFrame(rows)
    if df.date.duplicated().any() or df.empty: raise ValueError("Invalid TWSE date coverage")
    values=df[["open","high","low","close"]]
    if not np.isfinite(values).all().all() or not values.gt(0).all().all(): raise ValueError("Invalid index price")
    if (df.high<df[["open","close","low"]].max(axis=1)).any() or (df.low>df[["open","close","high"]].min(axis=1)).any():
        raise ValueError("Invalid OHLC ordering")
    return df

def parse_settlements(raw):
    text=raw.decode("utf-8")
    rows=[]
    for tr in re.split(r"<tr\b[^>]*>",text,flags=re.I)[1:]:
        cells=[html.unescape(re.sub("<[^>]+>","",x)).strip() for x in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>",tr,re.S|re.I)]
        if len(cells)>=3 and re.fullmatch(r"\d{4}/\d{2}/\d{2}",cells[0]) and re.fullmatch(r"\d{6}(?:[WF]\d)?",cells[1]):
            # Only TXO column requested by commodityIds=2.
            value=cells[2].replace(",","")
            if re.fullmatch(r"\d+(?:\.\d+)?",value):
                rows.append(dict(expiry_code=cells[1],expiry_date=cells[0].replace("/","-"),final_settlement=float(value)))
    result=pd.DataFrame(rows)
    if result.empty or result.expiry_code.duplicated().any(): raise ValueError("Invalid settlement calendar response")
    result["is_weekly"]=result.expiry_code.str.contains("[WF]",regex=True)
    return result

def parse_hkex(raw, expected_date):
    text=html.unescape(re.sub("<[^>]+>","",raw.decode("latin-1")))
    if "WEEKLY HANG SENG INDEX OPTIONS DAILY MARKET REPORT (Final)" not in text: raise ValueError("Not a final weekly HSI report")
    header=text.split("CONTRACT    STRIKE")[0]
    dates=re.findall(r"\b(\d{2} [A-Z]{3} \d{4}),",header)
    if not dates or datetime.strptime(dates[-1],"%d %b %Y").date().isoformat()!=expected_date:
        raise ValueError("HKEX business date differs from request")
    rows=[]
    for line in text.splitlines():
        if not re.match(r"^\s*\d{2}-[A-Z]{3}-\d{2}\s+\d+",line): continue
        sections=line.split("|")
        if len(sections)!=3: raise ValueError("Unknown HKEX session layout")
        left,day,combined=[s.split() for s in sections]
        if len(left)!=8 or len(day)!=7 or len(combined)!=5: raise ValueError("Unknown HKEX field count")
        expiry,strike,side=left[:3]
        expiry=datetime.strptime(expiry,"%d-%b-%y").date().isoformat()
        def number(x):
            if x in ("-","--"): return np.nan
            return float(x.replace(",",""))
        vals=list(map(number,left[3:]+day+combined))
        if not all(np.isfinite(vals)): raise ValueError("Missing HKEX numeric observation")
        aopen,ahi,alo,aclose,avol,dopen,dhi,dlo,oqp,change,iv,dvol,chi,clo,vol,oi,doi=vals
        if vol!=avol+dvol or min(vol,oi,avol,dvol)<0: raise ValueError("HKEX session count mismatch")
        rows.append(dict(date=expected_date,expiry_date=expiry,strike=float(strike),side=side,
                         contract_id=f"HKEX:HSI:W:{expiry}:{side}:{strike}",name="Hang Seng Index weekly option",
                         oqp=oqp,iv_pct=iv,day_open=dopen if dvol>0 else np.nan,
                         day_high=dhi if dvol>0 else np.nan,day_low=dlo if dvol>0 else np.nan,
                         after_close=aclose if avol>0 else np.nan,day_volume=dvol,
                         after_volume=avol,volume=vol,oi=oi,oi_change=doi))
    df=pd.DataFrame(rows)
    if df.empty or df.contract_id.duplicated().any(): raise ValueError("Missing/duplicate HKEX contracts")
    total=re.search(r"MARKET TOTAL\s+([\d,]+)\s+([\d,]+)\s+([+\-\d,]+)",text)
    if not total: raise ValueError("Missing HKEX report total")
    for col,number in zip(["volume","oi","oi_change"],total.groups()):
        if int(df[col].sum())!=int(number.replace(",","")): raise ValueError("HKEX market total reconciliation: "+col)
    return df

def oi_five_day(weekly):
    """Matched-contract OI change and entry/exit decomposition across five observed sessions."""
    if weekly.duplicated(["date","contract_id"]).any() or weekly.oi.isna().any():
        raise ValueError("Incomplete or duplicated OI panel")
    snapshots={d:g.set_index("contract_id").oi for d,g in weekly.groupby("date",sort=True)}
    dates=list(snapshots)
    rows=[]
    for i,day in enumerate(dates):
        cur=snapshots[day]
        row=dict(date=day,weekly_oi=float(cur.sum()),weekly_contracts=len(cur))
        if i>=5:
            old=snapshots[dates[i-5]]
            keys=old.index.intersection(cur.index)
            old_matched=float(old.loc[keys].sum());new_matched=float(cur.loc[keys].sum())
            entering=float(cur.loc[cur.index.difference(old.index)].sum())
            exiting=float(old.loc[old.index.difference(cur.index)].sum())
            change=new_matched-old_matched
            total=float(cur.sum()-old.sum())
            if not np.isclose(total,change+entering-exiting): raise ValueError("OI decomposition does not balance")
            row.update(oi_lag_date=dates[i-5],matched_oi_change=change,entering_oi=entering,exiting_oi=exiting,
                       total_oi_change=total,matched_previous_oi=old_matched,
                       oi_matched_5d=change/old_matched if old_matched>0 else np.nan,
                       oi_total_5d=total/old.sum() if old.sum()>0 else np.nan,
                       continuing_previous_coverage=old_matched/old.sum() if old.sum()>0 else np.nan)
        rows.append(row)
    return pd.DataFrame(rows)

def forward_mean(series,horizon=5):
    # concat requires every future session; never skip missing observations.
    return pd.concat([series.shift(-h) for h in range(1,horizon+1)],axis=1).mean(axis=1,skipna=False)

def make_panel(prices,oi,settlements):
    prices=prices.sort_values("date").copy()
    if prices.date.duplicated().any() or oi.date.duplicated().any(): raise ValueError("Duplicate daily panel")
    df=prices.merge(oi,on="date",how="left",validate="one_to_one")
    if df.weekly_oi.isna().any(): raise ValueError("Missing option sessions: do not compress the trading calendar")
    df["parkinson"]=np.log(df.high/df.low)**2/(4*np.log(2))
    df["close_squared_return"]=np.log(df.close/df.close.shift())**2
    if (df.parkinson<=0).any(): raise ValueError("Zero/nonpositive range proxy")
    df["weekday"]=pd.to_datetime(df.date).dt.dayofweek
    weekly=set(settlements.loc[settlements.is_weekly,"expiry_date"])
    monthly=set(settlements.loc[~settlements.is_weekly,"expiry_date"])
    df["weekly_expiry"]=df.date.isin(weekly).astype(int)
    df["monthly_expiry"]=df.date.isin(monthly).astype(int)
    df["before_weekly_expiry"]=df.weekly_expiry.shift(-1)
    df["after_weekly_expiry"]=df.weekly_expiry.shift(1)
    df["friday_regime"]=df.date.ge("2025-06-27").astype(int)
    for col in ["parkinson","close_squared_return"]:
        df[col+"_forward5"]=forward_mean(df[col])
    for lag in (1,2):
        df[f"oi_matched_lag{lag}"]=df.oi_matched_5d.shift(lag)
        df[f"oi_total_lag{lag}"]=df.oi_total_5d.shift(lag)
        df[f"oi_source_date_lag{lag}"]=df.date.shift(lag)
    df["label_start"]=df.date.shift(-1);df["label_end"]=df.date.shift(-5)
    df["next5_weekly"]=pd.concat([df.weekly_expiry.shift(-j) for j in range(1,6)],axis=1).sum(axis=1,min_count=5)
    df["next5_monthly"]=pd.concat([df.monthly_expiry.shift(-j) for j in range(1,6)],axis=1).sum(axis=1,min_count=5)
    return df

def hac_ols(y,X,names,lags=5):
    y=np.asarray(y,float);X=np.asarray(X,float)
    rank=int(np.linalg.matrix_rank(X))
    info=dict(n=len(y),rank=rank,columns=X.shape[1],identified=rank==X.shape[1],lags=lags)
    if rank<X.shape[1]: return info,[]
    beta=np.linalg.lstsq(X,y,rcond=None)[0];u=y-X@beta
    xu=X*u[:,None];meat=xu.T@xu
    for lag in range(1,min(lags,len(y)-1)+1):
        covariance=xu[lag:].T@xu[:-lag]
        meat+=(1-lag/(lags+1))*(covariance+covariance.T)
    inv=np.linalg.inv(X.T@X)
    se=np.sqrt(np.maximum(np.diag(inv@meat@inv)*len(y)/(len(y)-X.shape[1]),0))
    rows=[dict(term=name,coefficient=float(b),hac_se=float(s),ci_low=float(b-1.96*s),ci_high=float(b+1.96*s))
          for name,b,s in zip(names,beta,se)]
    return info,rows

def h5_analysis(panel):
    df=panel.copy()
    # Explanatory model uses only lagged daily range controls.
    for n in [1,5,22]: df[f"past{n}"]=np.log(df.parkinson.rolling(n).mean().shift(1))
    needed=["before_weekly_expiry","after_weekly_expiry","past1","past5","past22"]
    df=df.dropna(subset=needed).copy()
    base=["weekly_expiry","before_weekly_expiry","after_weekly_expiry","monthly_expiry","friday_regime","past1","past5","past22"]
    for d in range(1,5): df[f"dow{d}"]=(df.weekday==d).astype(int)
    base += [f"dow{d}" for d in range(1,5)]
    rows=[];diagnostics=[]
    for variant in ["primary","weekday_by_regime","exclude_monthly","placebo_shift2"]:
        part=df.copy();cols=base.copy()
        if variant=="weekday_by_regime":
            for d in range(1,5):
                part[f"dow{d}_regime"]=part[f"dow{d}"]*part.friday_regime
                cols.append(f"dow{d}_regime")
        elif variant=="exclude_monthly":
            part=part.loc[part.monthly_expiry.eq(0)].copy();cols.remove("monthly_expiry")
        elif variant=="placebo_shift2":
            # Diagnostic, not a second confirmatory hypothesis or a tuning candidate.
            shifted=["weekly_expiry","before_weekly_expiry","after_weekly_expiry"]
            part[shifted]=part[shifted].shift(2)
            part=part.dropna(subset=shifted)
        for lags in [5,20]:
            X=np.column_stack([np.ones(len(part)),part[cols].to_numpy(float)])
            info,coeff=hac_ols(np.log(part.parkinson),X,["constant"]+cols,lags)
            diagnostics.append(dict(variant=variant,**info))
            rows.extend(dict(variant=variant,lags=lags,**r) for r in coeff)
    # Same weekday descriptions, with actual day as the unit.
    cells=(df.groupby(["weekday","weekly_expiry"]).agg(days=("date","size"),mean_proxy=("parkinson","mean"),
                 median_proxy=("parkinson","median")).reset_index())
    return pd.DataFrame(rows),pd.DataFrame(diagnostics),cells

def _predict(train_x,train_y,test_x):
    mu=train_x.mean(axis=0);scale=train_x.std(axis=0);scale[scale<1e-10]=1
    X=np.column_stack([np.ones(len(train_x)),(train_x-mu)/scale])
    z=np.r_[1,(test_x-mu)/scale]
    beta=np.linalg.lstsq(X,np.log(np.maximum(train_y,FLOOR)),rcond=None)[0]
    residual=np.log(np.maximum(train_y,FLOOR))-X@beta
    # Duan smearing estimates the conditional mean needed by QLIKE.
    result=float(np.exp(z@beta)*np.exp(residual).mean())
    if not np.isfinite(result) or result<=0: raise ValueError("Invalid positive variance forecast")
    return result,int(np.linalg.matrix_rank(X))

def forecast(panel,proxy="parkinson",minimum_train=100):
    df=panel.copy()
    for n in [1,5,22]: df[f"log{n}"]=np.log(df[proxy].rolling(n).mean().clip(lower=FLOOR))
    har=["log1","log5","log22"]
    calendar=har+["next5_weekly","next5_monthly","friday_regime"]
    models={"persistence":None,"HAR":har,"HAR_calendar":calendar,
            "HAR_calendar_OI_lag1":calendar+["oi_matched_lag1"],
            "HAR_calendar_OI_lag2":calendar+["oi_matched_lag2"],
            "HAR_calendar_totalOI_lag1":calendar+["oi_total_lag1"]}
    needed=calendar+["oi_matched_lag1","oi_matched_lag2","oi_total_lag1",proxy+"_forward5","label_end"]
    eligible=df[needed].notna().all(axis=1)
    rows=[]
    for i in range(len(df)):
        if not eligible.iloc[i]: continue
        # Strictly earlier label end: five overlapping future days are purged.
        mask=eligible & df.label_end.lt(df.date.iloc[i])
        train=df.loc[mask]
        if len(train)<minimum_train: continue
        y=float(df[proxy+"_forward5"].iloc[i])
        for model,cols in models.items():
            if cols is None: value=float(df[proxy].iloc[i]);rank=0
            else: value,rank=_predict(train[cols].to_numpy(float),train[proxy+"_forward5"].to_numpy(float),df.loc[i,cols].to_numpy(float))
            rows.append(dict(date=df.date.iloc[i],origin_index=i,proxy=proxy,model=model,actual=y,forecast=value,
                             qlike=float(np.log(max(value,FLOOR))+y/max(value,FLOOR)),
                             absolute_error=abs(y-value),log_squared_error=float((np.log(max(y,FLOOR))-np.log(max(value,FLOOR)))**2),
                             train_n=len(train),train_last_label_end=train.label_end.max(),design_rank=rank,
                             label_start=df.label_start.iloc[i],label_end=df.label_end.iloc[i]))
    return pd.DataFrame(rows)

def block_interval(values,block=10,repeats=2000,seed=4879):
    values=np.asarray(values,float);n=len(values)
    if not n or np.isinf(values).any() or not np.isfinite(values).any(): raise ValueError("Invalid losses")
    rng=np.random.default_rng(seed);means=[]
    # Moving blocks do not wrap the last date to the first date.
    for _ in range(repeats):
        starts=rng.integers(0,max(n-block+1,1),size=math.ceil(n/block))
        indices=np.concatenate([np.arange(s,min(s+block,n)) for s in starts])[:n]
        sample=values[indices]
        if np.isfinite(sample).any(): means.append(np.nanmean(sample))
    low,high=np.quantile(means,[.025,.975])
    return float(low),float(high)

def compare_forecasts(predictions):
    scores=predictions.groupby(["proxy","model"]).agg(n=("date","size"),qlike=("qlike","mean"),
        mae=("absolute_error","mean"),log_mse=("log_squared_error","mean")).reset_index()
    comparisons=[]
    pairs=[("HAR_calendar","HAR"),("HAR_calendar_OI_lag1","HAR_calendar"),
           ("HAR_calendar_OI_lag2","HAR_calendar"),("HAR_calendar_totalOI_lag1","HAR_calendar")]
    for proxy,group in predictions.groupby("proxy"):
        pivot=group.pivot(index="date",columns="model",values="qlike")
        if pivot.isna().any().any(): raise ValueError("Models have unequal evaluation dates")
        for model,base in pairs:
            differences=pivot[model]-pivot[base]
            for block in [5,10,20]:
                positions=group.drop_duplicates("date").set_index("date").origin_index
                aligned=pd.Series(differences.to_numpy(),index=positions.loc[differences.index].to_numpy())
                aligned=aligned.reindex(range(int(aligned.index.min()),int(aligned.index.max())+1))
                low,high=block_interval(aligned.to_numpy(),block)
                comparisons.append(dict(proxy=proxy,model=model,baseline=base,block=block,n=len(differences),
                    qlike_difference=float(differences.mean()),ci_low=low,ci_high=high,
                    improved=bool(high<0)))
    return scores,pd.DataFrame(comparisons)
