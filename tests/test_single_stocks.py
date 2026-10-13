"""Corporate-action, calendar, forecast leakage and dashboard safeguards."""
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from nh_research.single_stocks import parse_stock,parse_stock_settlements,stock_oi,stock_panel,calendar_hac,stock_forecast,loss_intervals
from nh_research.empirical import forward_mean
ROOT=Path(__file__).resolve().parents[1]

class StockTests(unittest.TestCase):
 def test_stock_identity_and_corporate_action_marker(self):
  obj=dict(stat='OK',title='114年12月 2330 台積電 各日成交資訊',fields=['日期','成交股數','成交金額','開盤價','最高價','最低價','收盤價','漲跌價差','成交筆數','註記'],data=[['114/12/11','1,000','2,000','10','12','9','11','X0.00','10','']])
  df=parse_stock(json.dumps(obj),'2330');self.assertTrue(df.non_comparable.iloc[0]);self.assertEqual(df.date.iloc[0],'2025-12-11')
  with self.assertRaises(ValueError):parse_stock(json.dumps(obj),'2317')
  obj['data'][0][4]='8'
  with self.assertRaises(ValueError):parse_stock(json.dumps(obj),'2330')

 def test_settlement_keeps_adjusted_alias_identity(self):
  raw='<table><tr><td>Test</td><td>CDO</td><td>2330</td><td>2025/12/24</td><td>202512W4</td><td>100</td><td>200000</td><tr><td>Test</td><td>CDA</td><td>2330</td><td>2025/12/24</td><td>202512W4</td><td>100</td><td>201000</td></tr></table>'.encode()
  result=parse_stock_settlements(raw,'2330');self.assertEqual(result['product'].tolist(),['CDO','CDA'])
  with self.assertRaises(ValueError):parse_stock_settlements(raw,'2317')

 def test_zero_listed_weekly_days_do_not_compress_calendar(self):
  dates=list(pd.bdate_range('2026-01-01',periods=7).strftime('%Y-%m-%d'))
  rows=pd.DataFrame([(d,'CDO:W:C:100',10+i) for i,d in enumerate(dates) if i!=2],columns=['date','contract_id','oi'])
  oi=stock_oi(rows,dates);self.assertEqual(len(oi),7);self.assertEqual(oi.weekly_oi.iloc[2],0);self.assertEqual(oi.oi_lag_date.iloc[5],dates[0]);self.assertEqual(oi.oi_matched_5d.iloc[5],.5)

 def test_prelaunch_missing_and_adjustment_not_return_jump(self):
  dates=list(pd.bdate_range('2026-01-01',periods=10).strftime('%Y-%m-%d'))
  prices=pd.DataFrame(dict(date=dates,open=100.,high=102.,low=99.,close=100.,reported_change='0',non_comparable=False,note=''))
  prices.loc[5,['open','high','low','close']]=[50,51,49,50];prices.loc[5,'reported_change']='X0.00'
  oi=pd.DataFrame(dict(date=dates[3:],weekly_oi=1.,oi_matched_5d=1.,oi_total_5d=1.))
  calendar=pd.DataFrame(dict(expiry_date=[dates[4]],is_weekly=[True]))
  market=pd.DataFrame(dict(date=dates,parkinson=.001))
  panel=stock_panel(prices,oi,calendar,market,dates[3]);self.assertTrue(panel.weekly_oi.iloc[:3].isna().all());self.assertTrue(np.isnan(panel.close_squared_return.iloc[5]));self.assertTrue(np.isfinite(panel.parkinson.iloc[5]))
  with self.assertRaises(ValueError):stock_panel(prices,oi.iloc[1:],calendar,market,dates[3])

 def test_unidentified_h5_no_coefficients_and_hac_calendar_gaps(self):
  info,rows=calendar_hac(np.arange(30),np.ones((30,2)),['a','b'],np.arange(30));self.assertFalse(info['identified']);self.assertEqual(rows,[])
  rng=np.random.default_rng(6);x=rng.normal(size=30);X=np.c_[np.ones(30),x];y=.5*x+rng.normal(size=30)
  _,a=calendar_hac(y,X,['constant','x'],np.arange(30),5);_,b=calendar_hac(y,X,['constant','x'],np.arange(30)*10,5)
  self.assertAlmostEqual(a[1]['coefficient'],b[1]['coefficient']);self.assertNotAlmostEqual(a[1]['hac_se'],b[1]['hac_se'])

 def test_saved_panel_calendar_and_purged_forecasts(self):
  folder=ROOT/'data/analysis/single_stocks';panel=pd.read_csv(folder/'daily_panel.csv');pred=pd.read_csv(folder/'h6_forecasts.csv')
  self.assertEqual(panel.stock_code.nunique(),7)
  self.assertTrue(panel.loc[panel.post_launch.eq(0),'weekly_oi'].isna().all())
  self.assertTrue((pred.train_last_label_end<pred.date).all());self.assertTrue((pred.date<pred.label_start).all());self.assertTrue(pred.train_n.ge(100).all());self.assertTrue(pred.forecast.gt(0).all())
  for _,g in pred.groupby(['stock_code','proxy','family']):self.assertEqual(g.groupby('model').date.apply(tuple).nunique(),1)
  for _,g in panel.groupby('stock_code'):self.assertTrue(g.parkinson_forward5.tail(5).isna().all())

 def test_future_outcomes_cannot_change_earlier_stock_forecasts(self):
  df=pd.read_csv(ROOT/'data/analysis/single_stocks/daily_panel.csv');df=df.loc[df.stock_code.eq(2330)].reset_index(drop=True)
  before,_=stock_forecast(df,minimum_train=45,family='level');cut=len(df)-30;changed=df.copy();changed.loc[cut:,'parkinson']*=9;changed['parkinson_forward5']=forward_mean(changed.parkinson)
  after,_=stock_forecast(changed,minimum_train=45,family='level');cols=['date','model','forecast']
  a=before.loc[before.date<df.date.iloc[cut-5],cols].reset_index(drop=True);b=after.loc[after.date<df.date.iloc[cut-5],cols].reset_index(drop=True)
  self.assertGreater(len(a),0);pd.testing.assert_frame_equal(a,b)

 def test_vectorized_blocks_preserve_calendar_gaps_and_draws(self):
  import math
  values=np.array([.1,np.nan,.2,-.3,.4,np.nan,-.2,.15,.3])
  for block in [3,12]:
   rng=np.random.default_rng(4879);means=[]
   for _ in range(100):
    starts=rng.integers(0,max(len(values)-block+1,1),size=math.ceil(len(values)/block));idx=np.concatenate([np.arange(s,min(s+block,len(values))) for s in starts])[:len(values)]
    if np.isfinite(values[idx]).any():means.append(np.nanmean(values[idx]))
   expected=np.quantile(means,[.025,.975,.05/14,1-.05/14])
   np.testing.assert_allclose(loss_intervals(values,block,repeats=100),expected,rtol=1e-12,atol=1e-12)

 def test_stock_dashboard(self):
  from streamlit.testing.v1 import AppTest
  app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=40).run();app.radio(key='page').set_value('개별주식 H5·H6').run()
  for view in ['종목·데이터','H5 만기 검토','H6 예측 검증','비교·다운로드']:
   app.radio(key='stock_view').set_value(view).run();self.assertFalse(app.exception)
  app.radio(key='stock_view').set_value('H6 예측 검증').run()
  for sid in ['1303','2303','2330','2603','2317','2454','3231']:
   app.selectbox(key='stock_code').set_value(sid).run();self.assertFalse(app.exception)
  app.selectbox(key='stock_family').set_value('level').run();app.selectbox(key='stock_proxy').set_value('close_squared_return').run();self.assertFalse(app.exception)

if __name__=='__main__':unittest.main()
