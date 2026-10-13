"""Offline single-stock H5/H6: observed histories, no live trading or keys."""
from __future__ import annotations
import argparse,gzip,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nh_research.taifex import decode_response,normalize_market
from nh_research.single_stocks import parse_stock,parse_stock_settlements,stock_oi,stock_panel,stock_h5,stock_forecast,stock_compare
from analyze_empirical import raw,stable_json
from analyze_taifex import write_csv

def build(source,output,charts=True):
 output.mkdir(parents=True,exist_ok=True)
 manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'));metas={m['name']:m for m in manifest['requests']}
 if any(not m['complete'] for m in metas.values()):raise ValueError('Incomplete source collection')
 market=pd.read_csv(ROOT/'data/analysis/empirical/daily_panel.csv')
 market=market.loc[market.date.between(manifest['start'],manifest['end'])].copy()
 frames={k:[] for k in ['daily_panel','weekly_contracts','expiry_calendar','expiry_audit','h5_coefficients','h5_diagnostics','h5_cells','h6_forecasts','h6_diagnostics','coverage','price_events','alias_map','source_coverage']}
 for stock in manifest['stocks']:
  code=stock['roster_code'];sid=stock['stock_code'];launch=stock['weekly_launch'];print('Build',sid,stock['name_en'],flush=True)
  prices=[];options=[];aliases=[];calendars=[];raw_count=0
  for name,meta in metas.items():
   if name.startswith('stock_'+sid+'_'):
    p=parse_stock(raw(source,meta),sid)
    if not p.date.str.replace('-','').str.startswith(name[-6:]).all():raise ValueError('Wrong stock month')
    prices.append(p);frames['source_coverage'].append(pd.DataFrame([dict(source=name,stock_code=sid,rows=len(p),start=p.date.min(),end=p.date.max())]))
   elif name.startswith('options_'+code+'_'):
    month=name[-6:];cat=json.loads(raw(source,metas['catalog_'+month]))
    item=next(r for r in cat['commodityList'] if r['marketid'].strip()==code)
    allowed=[x.strip() for x in item['marketids'].split(',')]
    frame=normalize_market(decode_response(raw(source,meta))[0],name)
    fields=meta['request_fields']
    if not frame.date.between(fields['queryStartDate'].replace('/','-'),fields['queryEndDate'].replace('/','-')).all():raise ValueError('Wrong option date range')
    if set(frame['product'])-set(allowed):raise ValueError('Unmapped option product')
    if frame.loc[frame.session.eq('regular'),'oi'].isna().any():raise ValueError('Missing regular OI')
    raw_count+=len(frame);options.append(frame.loc[frame.session.eq('regular')].copy())
    aliases.extend(dict(stock_code=sid,roster_code=code,product=p,month=month,mapping_source='historical commodityList',adjusted=p!=item['commodity_id'].strip()) for p in allowed)
    frames['source_coverage'].append(pd.DataFrame([dict(source=name,stock_code=sid,rows=len(frame),start=frame.date.min(),end=frame.date.max())]))
   elif name.startswith('settlements_'+code+'_'):
    calendars.append(parse_stock_settlements(raw(source,meta),sid))
  price=pd.concat(prices,ignore_index=True).sort_values('date');price=price.loc[price.date.between(manifest['start'],manifest['end'])]
  option=pd.concat(options,ignore_index=True).sort_values(['date','contract_id'])
  if option.duplicated(['date','contract_id']).any():raise ValueError('Duplicated option sessions')
  calendar=pd.concat(calendars,ignore_index=True).sort_values(['expiry_date','product'])
  selected_aliases={r['product'] for r in aliases}
  calendar=calendar.loc[calendar['product'].isin(selected_aliases)].copy()
  if calendar.duplicated(['product','expiry_code']).any():raise ValueError('Duplicated final settlements')
  # Every underlying session from launch is covered by an actual full-chain option response.
  dates=market.loc[market.date.ge(launch),'date'].tolist()
  observed=set(option.loc[option.date.ge(launch),'date'])
  if observed!=set(dates):raise ValueError('Missing/excess post-launch option dates '+str(sorted(observed.symmetric_difference(dates))))
  weekly=option.loc[option.is_weekly].copy()
  if weekly.date.lt(launch).any():raise ValueError('Unexpected weekly data before announced launch')
  schedule=option.loc[option.expiry_date.ne(''),['product','expiry_code','expiry_date']].drop_duplicates()
  if schedule.duplicated(['product','expiry_code']).any():raise ValueError('Changed scheduled date; needs review')
  audit=schedule.merge(calendar[['product','expiry_code','expiry_date']],on=['product','expiry_code'],how='left',suffixes=('_scheduled','_actual'))
  ended=audit.expiry_date_scheduled.le(manifest['end'])
  if audit.loc[ended,'expiry_date_actual'].isna().any():raise ValueError('Missing ended contract settlement')
  audit['mismatch']=audit.expiry_date_actual.notna() & audit.expiry_date_scheduled.ne(audit.expiry_date_actual)
  oi=stock_oi(weekly,dates);panel=stock_panel(price,oi,calendar,market,launch)
  panel['stock_code']=sid
  coeff,diagnostics,cells=stock_h5(panel)
  frames['h5_coefficients'].append(coeff.assign(stock_code=sid));frames['h5_diagnostics'].append(diagnostics.assign(stock_code=sid));frames['h5_cells'].append(cells.assign(stock_code=sid))
  stock_preds=[];stock_diags=[]
  for proxy in ['parkinson','close_squared_return','parkinson_clean']:
   for family in ['matched','level']:
    pred,diag=stock_forecast(panel,proxy,family);stock_diags.append(dict(stock_code=sid,**diag))
    if len(pred):stock_preds.append(pred.assign(stock_code=sid))
  frames['h6_forecasts'].extend(stock_preds);frames['h6_diagnostics'].append(pd.DataFrame(stock_diags))
  frames['daily_panel'].append(panel);frames['weekly_contracts'].append(weekly.assign(stock_code=sid,name_en=stock['name_en'],name_cn=stock['name_cn']))
  frames['expiry_calendar'].append(calendar);frames['expiry_audit'].append(audit.assign(stock_code=sid));frames['alias_map'].append(pd.DataFrame(aliases))
  frames['price_events'].append(panel.loc[panel.non_comparable|panel.price_missing|panel.parkinson.isna(),['date','stock_code','open','high','low','close','reported_change','note','non_comparable','price_missing']])
  post=panel.loc[panel.post_launch.eq(1)]
  base_diag=next(d for d in stock_diags if d['proxy']=='parkinson' and d['family']=='matched');level_diag=next(d for d in stock_diags if d['proxy']=='parkinson' and d['family']=='level')
  frames['coverage'].append(pd.DataFrame([dict(**stock,price_start=price.date.min(),price_end=price.date.max(),price_days=int(panel.close.notna().sum()),weekly_start=weekly.date.min(),weekly_end=weekly.date.max(),option_days=len(post),raw_option_rows=raw_count,weekly_rows=len(weekly),weekly_contracts=weekly.contract_id.nunique(),traded_weekly_share=float(weekly.has_trade_price.mean()),weekly_expiry_days=int(panel.weekly_expiry.sum()),price_event_days=int(panel.non_comparable.sum()),zero_range_days=int(panel.high.eq(panel.low).sum()),missing_price_days=int(panel.price_missing.sum()),zero_oi_days=int(post.weekly_oi.eq(0).sum()),undefined_matched_days=int(post.oi_matched_5d.isna().sum()),matched_coverage_median=float(post.continuing_previous_coverage.median()),matched_test_days=base_diag['test_days'],level_test_days=level_diag['test_days'],expiry_mismatches=int(audit.mismatch.sum()))]))
  for name,frame in [('daily_panel',panel),('weekly_contracts',weekly)]:write_csv(output/(sid+'_'+name+'.csv.gz'),frame)
 data={name:pd.concat(parts,ignore_index=True) for name,parts in frames.items() if parts}
 if 'h6_forecasts' not in data:raise ValueError('No stock forecasts in either prespecified family')
 data['h6_scores'],data['h6_comparison']=stock_compare(data['h6_forecasts'])
 # HAC inversion differs at ~1e-13 across BLAS platforms; publish coefficients/CIs to 8 decimal places.
 data['h5_coefficients']=data['h5_coefficients'].round(8)
 for name,df in data.items():write_csv(output/(name+('.csv.gz' if name=='weekly_contracts' else '.csv')),df)
 summary=dict(version='single-stocks-20261012',start=market.date.min(),end=market.date.max(),underlyings=len(manifest['stocks']),price_dates=len(market),source_requests=len(metas),stocks=data['coverage'].to_dict('records'),
  primary_h6=data['h6_comparison'].query("proxy == 'parkinson' and family == 'matched' and model == 'OI_lag1' and block == 10").to_dict('records'),
  secondary_h6=data['h6_comparison'].query("proxy == 'parkinson' and family == 'level' and model == 'OI_level_lag1' and block == 10").to_dict('records'),
  limitations=['Daily proxy, NOT intraday RV','Ex-post calendar and final revisions; OI availability lags assumed','Seven selected underlying stocks, not seven independent market experiments','Adjusted contract counts are not shares or notional; no synthetic alias continuity','Close-return sensitivity masks non-comparable dates; not adjusted total returns','Family intervals approximate Bonferroni; no performance-based tuning'])
 (output/'summary.json').write_text(json.dumps(stable_json(summary),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if charts:make_charts(data,ROOT/'docs/images/single-stocks')
 print(json.dumps(stable_json(summary),ensure_ascii=False,indent=2))
 return data

def make_charts(data,out):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 import matplotlib.dates as mdates
 out.mkdir(parents=True,exist_ok=True);plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 coverage=data['coverage'];labels=dict(zip(coverage.stock_code,coverage.name_en));teal='#087F8C';blue='#426DAD'
 fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained')
 for sid,g in data['daily_panel'].groupby('stock_code'):
  axes[0].plot(pd.to_datetime(g.date),g.close/g.close.iloc[0]*100,label=labels[sid],lw=1)
 axes[0].set(title='Seven underlying stock price paths | unadjusted close, start = 100',ylabel='Price index (not total return)');axes[0].legend(ncol=4,fontsize=8)
 x=np.arange(len(coverage));axes[1].bar(x-.2,coverage.option_days,width=.4,label='Option history sessions',color=teal);axes[1].bar(x+.2,coverage.matched_test_days,width=.4,label='Matched OI OOS dates',color=blue)
 axes[1].set_xticks(x,coverage.name_en,rotation=15);axes[1].set(ylabel='Trading days',title='More history does not equal more eligible forecast dates');axes[1].legend()
 axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'));fig.savefig(out/'stock_history_coverage.png',dpi=150);plt.close(fig)
 fig,ax=plt.subplots(figsize=(11,5.5),layout='constrained')
 c=data['h5_coefficients'].query("variant == 'primary' and lags == 5 and term == 'weekly_expiry'").sort_values('stock_code')
 y=np.arange(len(c));ax.hlines(y,c.family_ci_low,c.family_ci_high,color='#9CB7CA',lw=5,label='Family interval (21 comparisons)');ax.errorbar(c.coefficient,y,xerr=[c.coefficient-c.ci_low,c.ci_high-c.coefficient],fmt='o',color=teal,capsize=4,label='Marginal 95% HAC')
 ax.set_yticks(y,[labels[s] for s in c.stock_code]);ax.axvline(0,color='#777',ls='--');ax.set(title='H5 weekly expiry | conditional association, not causality',xlabel='Log daily range-variance coefficient');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2);fig.savefig(out/'stock_h5.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(13,5.5),layout='constrained')
 for ax,family,model,title in [(axes[0],'matched','OI_lag1','Primary: matched-contract OI change'),(axes[1],'level','OI_level_lag1','Secondary: log(1 + total weekly OI)')]:
  c=data['h6_comparison'].query("proxy == 'parkinson' and family == @family and model == @model and block == 10").sort_values('stock_code');y=np.arange(len(c))
  ax.hlines(y,c.family_ci_low,c.family_ci_high,color='#9CB7CA',lw=5,label='7-stock family interval');ax.errorbar(c.qlike_difference,y,xerr=[np.maximum(c.qlike_difference-c.ci_low,0),np.maximum(c.ci_high-c.qlike_difference,0)],fmt='o',color=blue,capsize=4,label='95% block interval')
  ax.set_yticks(y,[f'{labels[r.stock_code]} (n={r.n})' for r in c.itertuples()]);ax.axvline(0,color='#777',ls='--');ax.set(title=title,xlabel='Paired QLIKE difference (negative = improvement)');ax.legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.14))
 fig.suptitle('H6: within-stock comparisons; different date samples must not be ranked');fig.savefig(out/'stock_h6.png',dpi=150);plt.close(fig)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'data/source/single_stocks/20261012');p.add_argument('--output',type=Path,default=ROOT/'data/analysis/single_stocks');p.add_argument('--no-charts',action='store_true');a=p.parse_args();build(a.source,a.output,not a.no_charts)
