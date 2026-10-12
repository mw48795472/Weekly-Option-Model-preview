"""Empirical time alignment, official parser and interpretation safeguards."""
import gzip
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from nh_research.empirical import (parse_taiex,parse_settlements,parse_hkex,oi_five_day,
                                  forward_mean,hac_ols,forecast,compare_forecasts)
ROOT=Path(__file__).resolve().parents[1]

class EmpiricalTests(unittest.TestCase):
    def test_roc_dates_and_invalid_ohlc(self):
        obj=dict(stat="OK",fields=["日期","開盤指數","最高指數","最低指數","收盤指數"],
                 data=[["114/01/02","1,000","1,010","990","1,005"]])
        self.assertEqual(parse_taiex(json.dumps(obj)).date.iloc[0],"2025-01-02")
        obj["data"][0][2]="900"
        with self.assertRaises(ValueError):parse_taiex(json.dumps(obj))

    def test_settlement_html_with_omitted_row_end(self):
        raw=b"<table><TR><TD>2025/01/02</TD><TD>202501W1</TD><TD>100</TD><TR><TD>2025/01/15</TD><TD>202501</TD><TD>102</TD></TR></table>"
        result=parse_settlements(raw)
        self.assertEqual(len(result),2)
        self.assertEqual(result.is_weekly.tolist(),[True,False])

    def test_rollover_does_not_invert_matched_change(self):
        rows=[]
        for i,date in enumerate(pd.bdate_range("2025-01-01",periods=6).strftime("%Y-%m-%d")):
            rows.append((date,"continuing",10+i))
            rows.append((date,"exiting" if i<5 else "entering",90 if i<5 else 1))
        panel=pd.DataFrame(rows,columns=["date","contract_id","oi"])
        result=oi_five_day(panel).iloc[-1]
        self.assertEqual(result.oi_matched_5d,.5)
        self.assertEqual(result.total_oi_change,-84)
        self.assertEqual(result.matched_oi_change+result.entering_oi-result.exiting_oi,-84)
        panel.loc[0,"oi"]=np.nan
        with self.assertRaises(ValueError):oi_five_day(panel)

    def test_future_mean_requires_five_completed_sessions(self):
        y=pd.Series(np.arange(11,dtype=float))
        actual=forward_mean(y)
        self.assertEqual(actual.iloc[0],3)
        self.assertTrue(actual.tail(5).isna().all())
        y.iloc[3]=np.nan
        self.assertTrue(np.isnan(forward_mean(y).iloc[0]))

    def test_rank_deficiency_is_not_reported_as_an_identified_effect(self):
        info,rows=hac_ols(np.arange(20),np.ones((20,2)),["constant","always_expiry"])
        self.assertFalse(info["identified"])
        self.assertEqual(rows,[])

    def test_hkex_synthetic_schema_and_totals(self):
        # Synthetic fixture, no HKEX market observations redistributed.
        raw=b"""WEEKLY HANG SENG INDEX OPTIONS DAILY MARKET REPORT (Final)
01 JAN 2026, THURSDAY 02 JAN 2026, FRIDAY
CONTRACT    STRIKE
09-JAN-26 20000 C 1 2 1 2 3 | 2 3 2 3 +1 20 4 | 3 1 7 10 +2
MARKET TOTAL 7 10 +2"""
        df=parse_hkex(raw,"2026-01-02")
        self.assertEqual(df.oi.iloc[0],10)
        self.assertEqual(df.oqp.iloc[0],3)
        self.assertNotIn("close",df.columns)
        with self.assertRaises(ValueError):parse_hkex(raw,"2026-01-05")
        with self.assertRaises(ValueError):parse_hkex(raw.replace(b"MARKET TOTAL 7",b"MARKET TOTAL 8"),"2026-01-02")

    def test_saved_oos_dates_and_purged_labels(self):
        path=ROOT/"data/analysis/empirical"
        pred=pd.read_csv(path/"h6_forecasts.csv")
        self.assertTrue((pred.train_last_label_end<pred.date).all())
        self.assertTrue((pred.date<pred.label_start).all())
        self.assertTrue((pred.label_start<pred.label_end).all())
        self.assertTrue((pred.forecast>0).all())
        for _,group in pred.groupby("proxy"):
            self.assertTrue(group.groupby("model").date.apply(tuple).map(tuple).nunique()==1)
        panel=pd.read_csv(path/"daily_panel.csv")
        self.assertTrue(panel.parkinson_forward5.tail(5).isna().all())
        self.assertTrue((panel.oi_source_date_lag1.dropna()<panel.loc[panel.oi_source_date_lag1.notna(),"date"]).all())
        self.assertGreater(len(panel),350)
        summary=json.loads((path/"summary.json").read_text())
        self.assertIn("NOT intraday RV",summary["target"])

    def test_future_prices_cannot_change_earlier_forecasts(self):
        source=pd.read_csv(ROOT/"data/analysis/empirical/daily_panel.csv").iloc[:100].copy()
        before=forecast(source,minimum_train=35)
        changed=source.copy()
        # Change outcomes starting at day 85 and rederive targets as a future-data leakage test.
        changed.loc[85:,"parkinson"]*=7
        changed["parkinson_forward5"]=forward_mean(changed.parkinson)
        after=forecast(changed,minimum_train=35)
        a=before.loc[before.date<source.date.iloc[80],["date","model","forecast"]].reset_index(drop=True)
        b=after.loc[after.date<source.date.iloc[80],["date","model","forecast"]].reset_index(drop=True)
        pd.testing.assert_frame_equal(a,b)

    def test_empirical_dashboard_views(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/"streamlit_app.py"),default_timeout=40).run()
        app.radio(key="page").set_value("H5·H6 실측 연구").run()
        for view in ["기초자산·데이터","H5 만기 검토","H6 예측 검증","HKEX 확보 현황"]:
            app.radio(key="empirical_view").set_value(view).run()
            self.assertFalse(app.exception)
        app.radio(key="empirical_view").set_value("H6 예측 검증").run()
        app.selectbox(key="empirical_proxy").set_value("close_squared_return").run()
        self.assertFalse(app.exception)
        self.assertGreater(len(app.get("download_button")),0)

if __name__=="__main__":unittest.main()
