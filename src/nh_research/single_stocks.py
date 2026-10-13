"""Single-stock daily-proxy research with explicit calendars and sparse-OI gates."""
from __future__ import annotations
import html,json,math,re
from statistics import NormalDist
import numpy as np
import pandas as pd
from .empirical import FLOOR,forward_mean

def parse_stock(raw,stock_code):
 obj=json.loads(raw)
 required=['日期','成交股數','成交金額','開盤價','最高價','最低價','收盤價','漲跌價差','成交筆數']
 if obj.get('stat')!='OK' or obj.get('fields',[])[:9]!=required or not re.search(r'\b'+re.escape(stock_code)+r'\b',obj.get('title','')):
  raise ValueError('Unexpected TWSE stock schema or identity')
 rows=[]
 for values in obj['data']:
  y,m,d=map(int,values[0].split('/'));row=dict(date=f'{y+1911:04d}-{m:02d}-{d:02d}',stock_code=stock_code)
  for col,i in [('volume',1),('open',3),('high',4),('low',5),('close',6)]:
   val=values[i].replace(',','').strip();row[col]=np.nan if val in ('--','-','') else float(val)
  row['reported_change']=values[7].strip();row['note']=values[9].strip() if len(values)>9 else ''
  row['non_comparable']='X' in values[7].upper() or bool(row['note'])
  rows.append(row)
 df=pd.DataFrame(rows)
 if df.empty or df.date.duplicated().any():raise ValueError('Empty/duplicate stock dates')
 valid=df[['open','high','low','close']].notna().all(axis=1)
 if ((df.loc[valid,['open','high','low','close']]<=0)|~np.isfinite(df.loc[valid,['open','high','low','close']])).any().any():raise ValueError('Invalid stock prices')
 if (df.loc[valid,'high']<df.loc[valid,['open','close','low']].max(axis=1)).any() or (df.loc[valid,'low']>df.loc[valid,['open','close','high']].min(axis=1)).any():raise ValueError('Invalid stock OHLC')
 return df

def parse_stock_settlements(raw,stock_code,allowed_products=None):
 rows=[]
 for tr in re.split(r'<tr\b[^>]*>',raw.decode('utf-8'),flags=re.I)[1:]:
  cells=[html.unescape(re.sub('<[^>]+>','',v)).strip() for v in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',tr,re.S|re.I)]
  if len(cells)!=7 or not re.fullmatch(r'\d{4}/\d{2}/\d{2}',cells[3]):continue
  name,product,stock,day,expiry,settlement,value=cells
  if stock!=stock_code:raise ValueError('Wrong underlying in settlement query')
  if allowed_products is not None and product not in allowed_products:raise ValueError('Unmapped settlement alias '+product)
  if not re.fullmatch(r'\d{6}(?:[WF][1-5])?',expiry):raise ValueError('Invalid expiry code')
  rows.append(dict(product=product,stock_code=stock,expiry_code=expiry,expiry_date=day.replace('/','-'),is_weekly=bool(re.search('[WF]',expiry)),final_settlement=float(settlement.replace(',',''))))
 df=pd.DataFrame(rows)
 if df.empty or df.duplicated(['product','expiry_code']).any():raise ValueError('Empty/duplicate stock settlement calendar')
 return df

def stock_oi(weekly,dates):
 if weekly.duplicated(['date','contract_id']).any() or weekly.oi.isna().any():raise ValueError('Duplicate/missing stock OI')
 snapshots={d:g.set_index('contract_id').oi for d,g in weekly.groupby('date')}
 if set(snapshots)-set(dates):raise ValueError('Option dates outside validated calendar')
 rows=[];empty=pd.Series(dtype=float)
 for i,day in enumerate(dates):
  current=snapshots.get(day,empty);row=dict(date=day,weekly_oi=float(current.sum()),weekly_contracts=len(current))
  if i>=5:
   previous=snapshots.get(dates[i-5],empty);common=previous.index.intersection(current.index)
   old=float(previous.loc[common].sum());new=float(current.loc[common].sum())
   enter=float(current.loc[current.index.difference(previous.index)].sum());leave=float(previous.loc[previous.index.difference(current.index)].sum())
   total=float(current.sum()-previous.sum());change=new-old
   if not np.isclose(total,change+enter-leave):raise ValueError('OI accounting failed')
   row.update(oi_lag_date=dates[i-5],oi_matched_5d=change/old if old>0 else np.nan,oi_total_5d=total/previous.sum() if previous.sum()>0 else np.nan,
    matched_previous_oi=old,matched_oi_change=change,entering_oi=enter,exiting_oi=leave,total_oi_change=total,
    continuing_previous_coverage=old/previous.sum() if previous.sum()>0 else np.nan)
  rows.append(row)
 return pd.DataFrame(rows)

def stock_panel(prices,oi,settlements,market,launch):
 if prices.date.duplicated().any() or oi.date.duplicated().any():raise ValueError('Duplicate daily data')
 if set(prices.date)-set(market.date):raise ValueError('Stock date outside market calendar')
 df=market[['date','parkinson']].rename(columns={'parkinson':'market_parkinson'}).merge(prices,on='date',how='left',validate='one_to_one').merge(oi,on='date',how='left',validate='one_to_one')
 df['origin_index']=np.arange(len(df));df['post_launch']=df.date.ge(launch).astype(int)
 if df.loc[df.post_launch.eq(1),'weekly_oi'].isna().any():raise ValueError('Missing post-launch option sessions')
 if df.loc[df.post_launch.eq(0),'weekly_oi'].notna().any():raise ValueError('Pre-launch OI must remain missing')
 observed_change=pd.to_numeric(df.reported_change.str.replace(',','',regex=False),errors='coerce')
 discrepancy=observed_change.notna() & df.close.shift().notna() & ((df.close-df.close.shift()-observed_change).abs()>0.025)
 df['non_comparable']=df.non_comparable.eq(True)|df.reported_change.fillna('').str.contains('X',case=False)|discrepancy
 df['price_missing']=df[['open','high','low','close']].isna().any(axis=1)
 df['parkinson']=(np.log(df.high/df.low)**2/(4*np.log(2))).where(df.high.gt(df.low))
 df['close_squared_return']=(np.log(df.close/df.close.shift())**2).where(~df.non_comparable & ~df.price_missing)
 df['parkinson_clean']=df.parkinson.where(~df.non_comparable)
 weekly=set(settlements.loc[settlements.is_weekly,'expiry_date']);monthly=set(settlements.loc[~settlements.is_weekly,'expiry_date'])
 df['weekly_expiry']=df.date.isin(weekly).astype(int);df['monthly_expiry']=df.date.isin(monthly).astype(int)
 df['before_weekly_expiry']=df.weekly_expiry.shift(-1);df['after_weekly_expiry']=df.weekly_expiry.shift(1)
 df['weekday']=pd.to_datetime(df.date).dt.dayofweek
 for proxy in ['parkinson','close_squared_return','parkinson_clean']:df[proxy+'_forward5']=forward_mean(df[proxy])
 for lag in [1,2]:
  df[f'oi_matched_lag{lag}']=df.oi_matched_5d.shift(lag)
  df[f'oi_total_lag{lag}']=df.oi_total_5d.shift(lag)
  df[f'oi_level_lag{lag}']=np.log1p(df.weekly_oi).shift(lag)
  df[f'oi_source_date_lag{lag}']=df.date.shift(lag).where(df.weekly_oi.shift(lag).notna())
 df['label_start']=df.date.shift(-1);df['label_end']=df.date.shift(-5)
 for kind in ['weekly','monthly']:
  df[f'next5_{kind}']=pd.concat([df[kind+'_expiry'].shift(-n) for n in range(1,6)],axis=1).sum(axis=1,min_count=5)
 return df

def calendar_hac(y,X,names,positions,lags=5):
 y=np.asarray(y,float);X=np.asarray(X,float);positions=np.asarray(positions,int)
 rank=int(np.linalg.matrix_rank(X));n,k=X.shape
 info=dict(n=n,rank=rank,columns=k,identified=bool(rank==k and n>k+5),lags=lags)
 if not info['identified']:return info,[]
 beta=np.linalg.lstsq(X,y,rcond=None)[0];u=y-X@beta;xu=X*u[:,None];meat=xu.T@xu
 lookup={p:i for i,p in enumerate(positions)}
 for lag in range(1,lags+1):
  pairs=[(i,lookup[p-lag]) for i,p in enumerate(positions) if p-lag in lookup]
  if not pairs:continue
  left,right=zip(*pairs);cross=xu[list(left)].T@xu[list(right)];meat+=(1-lag/(lags+1))*(cross+cross.T)
 bread=np.linalg.inv(X.T@X);se=np.sqrt(np.maximum(np.diag(bread@meat@bread)*n/(n-k),0));z=NormalDist().inv_cdf(1-.05/(2*21))
 rows=[dict(term=term,coefficient=float(b),hac_se=float(s),ci_low=float(b-1.96*s),ci_high=float(b+1.96*s),family_ci_low=float(b-z*s),family_ci_high=float(b+z*s)) for term,b,s in zip(names,beta,se)]
 return info,rows

def stock_h5(panel):
 df=panel.copy()
 for n in [1,5,22]:df[f'past{n}']=np.log(df.parkinson.rolling(n).mean().shift(1))
 df['market_lag1']=np.log(df.market_parkinson.shift(1))
 for d in range(1,5):df[f'dow{d}']=df.weekday.eq(d).astype(int)
 base=['weekly_expiry','before_weekly_expiry','after_weekly_expiry','monthly_expiry','post_launch','past1','past5','past22','market_lag1']+[f'dow{d}' for d in range(1,5)]
 rows=[];diagnostics=[]
 for variant in ['primary','weekday_by_launch','post_launch_only','exclude_non_comparable']:
  part=df.copy();cols=base.copy()
  if variant=='weekday_by_launch':
   for d in range(1,5):part[f'dow{d}_post']=part[f'dow{d}']*part.post_launch;cols.append(f'dow{d}_post')
  elif variant=='post_launch_only':part=part.loc[part.post_launch.eq(1)];cols.remove('post_launch')
  elif variant=='exclude_non_comparable':part=part.loc[~part.non_comparable]
  part=part.dropna(subset=cols+['parkinson'])
  for lag in [5,20]:
   X=np.column_stack([np.ones(len(part)),part[cols].to_numpy(float)])
   info,result=calendar_hac(np.log(part.parkinson),X,['constant']+cols,part.origin_index,lag)
   diagnostics.append(dict(variant=variant,**info));rows.extend(dict(variant=variant,**info,**r) for r in result)
 cells=df.groupby(['post_launch','weekday','weekly_expiry','monthly_expiry']).agg(days=('date','size'),mean_proxy=('parkinson','mean')).reset_index()
 return pd.DataFrame(rows),pd.DataFrame(diagnostics),cells

def predict_mean(train_x,y,test_x):
 # Standardize using training only; singular coefficients do not automatically invalidate a prediction.
 mean=train_x.mean(axis=0);scale=train_x.std(axis=0);scale=np.where(scale>1e-12,scale,1)
 X=np.column_stack([np.ones(len(y)),(train_x-mean)/scale]);z=np.r_[1.,(test_x-mean)/scale]
 pinv=np.linalg.pinv(X);rank=int(np.linalg.matrix_rank(X))
 if not np.allclose(z,z@pinv@X,atol=1e-7,rtol=1e-7):return None,rank
 logy=np.log(np.maximum(y,FLOOR));beta=pinv@logy;res=logy-X@beta
 value=float(np.exp(z@beta)*np.exp(res).mean())
 if not np.isfinite(value) or value<=0:raise ValueError('Invalid stock variance prediction')
 return value,rank

def stock_forecast(panel,proxy='parkinson',family='matched',minimum_train=100):
 df=panel.copy()
 for n in [1,5,22]:df[f'log{n}']=np.log(df[proxy].rolling(n).mean().clip(lower=FLOOR))
 har=['log1','log5','log22'];calendar=har+['next5_weekly','next5_monthly']
 if family=='matched':extra={'OI_lag1':['oi_matched_lag1'],'OI_lag2':['oi_matched_lag2'],'total_OI_lag1':['oi_total_lag1']}
 elif family=='level':extra={'OI_level_lag1':['oi_level_lag1'],'OI_level_lag2':['oi_level_lag2']}
 else:raise ValueError('Unknown forecast family')
 models={'persistence':None,'HAR':har,'HAR_calendar':calendar,**{k:calendar+v for k,v in extra.items()}}
 needed=list(dict.fromkeys(calendar+[c for cols in extra.values() for c in cols]+[proxy+'_forward5','label_end']))
 eligible=df[needed].notna().all(axis=1)&df.post_launch.eq(1)
 rows=[];skipped=0
 for i in range(len(df)):
  if not eligible.iloc[i]:continue
  train=df.loc[eligible & df.label_end.lt(df.date.iloc[i])]
  if len(train)<minimum_train:continue
  actual=float(df[proxy+'_forward5'].iloc[i]);current=[]
  for model,cols in models.items():
   if cols is None:value=max(FLOOR,float(df[proxy].iloc[i]));rank=0
   else:value,rank=predict_mean(train[cols].to_numpy(float),train[proxy+'_forward5'].to_numpy(float),df.loc[i,cols].to_numpy(float))
   if value is None:skipped+=1;current=[];break
   current.append(dict(date=df.date.iloc[i],origin_index=int(df.origin_index.iloc[i]),proxy=proxy,family=family,model=model,actual=actual,forecast=value,
    qlike=float(np.log(max(value,FLOOR))+actual/max(value,FLOOR)),absolute_error=abs(actual-value),train_n=len(train),train_last_label_end=train.label_end.max(),
    label_start=df.label_start.iloc[i],label_end=df.label_end.iloc[i],design_rank=rank))
  rows.extend(current)
 diag=dict(proxy=proxy,family=family,eligible_days=int(eligible.sum()),test_days=len({r['date'] for r in rows}),minimum_train=minimum_train,unidentified_forecast_origins=skipped)
 return pd.DataFrame(rows),diag

def loss_intervals(values,block=10,repeats=2000,seed=4879):
 values=np.asarray(values,float);n=len(values)
 if not n or not np.isfinite(values).any():raise ValueError('No finite paired loss')
 rng=np.random.default_rng(seed)
 starts=rng.integers(0,max(n-block+1,1),size=(repeats,math.ceil(n/block)))
 indices=(starts[:,:,None]+np.arange(min(block,n))[None,None,:]).reshape(repeats,-1)[:,:n]
 samples=values[indices];counts=np.isfinite(samples).sum(axis=1)
 means=np.nansum(samples,axis=1)[counts>0]/counts[counts>0]
 return np.quantile(means,[.025,.975,.05/(2*7),1-.05/(2*7)])

def stock_compare(predictions):
 scores=predictions.groupby(['stock_code','proxy','family','model']).agg(n=('date','size'),qlike=('qlike','mean'),mae=('absolute_error','mean')).reset_index()
 rows=[]
 for (stock,proxy,family),group in predictions.groupby(['stock_code','proxy','family']):
  pivot=group.pivot(index='date',columns='model',values='qlike')
  if pivot.isna().any().any():raise ValueError('Unequal dates between models')
  positions=group.drop_duplicates('date').set_index('date').origin_index
  for model in [c for c in pivot if c not in ['HAR','persistence']]:
   base='HAR' if model=='HAR_calendar' else 'HAR_calendar';diff=pivot[model]-pivot[base]
   full=pd.Series(diff.to_numpy(),index=positions.loc[diff.index].to_numpy());full=full.reindex(range(int(full.index.min()),int(full.index.max())+1))
   for block in [5,10,20]:
    lo,hi,flo,fhi=loss_intervals(full.to_numpy(),block)
    rows.append(dict(stock_code=stock,proxy=proxy,family=family,model=model,baseline=base,block=block,n=len(diff),test_start=diff.index.min(),test_end=diff.index.max(),qlike_difference=float(diff.mean()),ci_low=lo,ci_high=hi,family_ci_low=flo,family_ci_high=fhi,
     improved=bool(hi<0),family_improved=bool(fhi<0),short_test=bool(len(diff)<30)))
 return scores,pd.DataFrame(rows)
