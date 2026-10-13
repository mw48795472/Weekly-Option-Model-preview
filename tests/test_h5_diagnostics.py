import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from nh_research.h5_diagnostics import exposure_diagnostics,planning_precision,h5_design,primary_diagnostics,precision_scenarios,specification_design
from nh_research.single_stocks import calendar_hac
ROOT=Path(__file__).resolve().parents[1]

class H5DiagnosisTests(unittest.TestCase):
    def test_exposure_diagnoses_alias_not_sample_count(self):
        rng=np.random.default_rng(55)
        event=np.tile([0.,0.,1.,0.],50)
        independent=rng.normal(size=len(event))
        nearly_alias=event+.01*independent
        X=np.column_stack([np.ones(len(event)),event,independent])
        base,_=exposure_diagnostics(X,['constant','weekly_expiry','control'])
        aliased,_=exposure_diagnostics(np.column_stack([np.ones(len(event)),event,nearly_alias]),['constant','weekly_expiry','control'])
        exact,_=exposure_diagnostics(np.column_stack([np.ones(len(event)),event,event]),['constant','weekly_expiry','control'])
        self.assertGreater(base['expiry_information_fraction'],.95)
        self.assertGreater(aliased['expiry_vif'],100)
        self.assertFalse(exact['identified'])
        self.assertIsNone(exact['expiry_vif'])

    def test_planning_precision_does_not_use_fitted_effect(self):
        rng=np.random.default_rng(93);n=250
        d=np.tile([0.,0.,1.,0.,0.],50)
        X=np.column_stack([np.ones(n),d,rng.normal(size=n)])
        y=rng.normal(size=n);names=['constant','weekly_expiry','control']
        _,a=calendar_hac(y,X,names,np.arange(n))
        _,b=calendar_hac(y+2*d,X,names,np.arange(n))
        ca=next(r for r in a if r['term']=='weekly_expiry');cb=next(r for r in b if r['term']=='weekly_expiry')
        self.assertAlmostEqual(cb['coefficient']-ca['coefficient'],2)
        self.assertAlmostEqual(planning_precision(ca['hac_se']),planning_precision(cb['hac_se']),places=12)
        self.assertGreater(planning_precision(ca['hac_se'],21),planning_precision(ca['hac_se']))

    def test_zero_range_window_does_not_compress_calendar(self):
        n=80;date=pd.bdate_range('2025-01-01',periods=n)
        p=pd.DataFrame(dict(date=date.strftime('%Y-%m-%d'),parkinson=np.linspace(.001,.002,n),
            market_parkinson=np.linspace(.002,.004,n),weekday=date.weekday,
            weekly_expiry=(date.weekday==2).astype(int),before_weekly_expiry=(date.weekday==1).astype(int),
            after_weekly_expiry=(date.weekday==3).astype(int),monthly_expiry=np.zeros(n),post_launch=np.ones(n)))
        p.loc[40,'parkinson']=np.nan
        full,part,_,_=h5_design(p)
        self.assertEqual(len(full),n)
        self.assertNotIn(40,part.origin_index.to_list())
        self.assertTrue(full.loc[41:62,'past22'].isna().all())
        self.assertTrue(np.isfinite(full.loc[63,'past22']))

    def test_saved_diagnostics_reproduce_fixed_primary_and_counts(self):
        daily=pd.read_csv(ROOT/'data/analysis/single_stocks/daily_panel.csv',dtype={'stock_code':str})
        coefficients=pd.read_csv(ROOT/'data/analysis/single_stocks/h5_coefficients.csv',dtype={'stock_code':str})
        stored=pd.read_csv(ROOT/'data/analysis/h5_diagnostics/primary_diagnostics.csv',dtype={'asset_id':str})
        for aid in ['1303','2330','2454']:
            out,cells,audit=primary_diagnostics(daily.loc[daily.stock_code.eq(aid)],aid,aid,'stock',coefficients.loc[coefficients.stock_code.eq(aid)])
            for row in out.itertuples():
                self.assertEqual(row.model_days,row.event_days+row.non_event_days)
                self.assertEqual(row.raw_expiry_days,row.event_days+row.excluded_expiry_days)
                self.assertEqual(int(audit.retained.sum()),row.model_days)
                actual=stored.loc[(stored.asset_id==aid)&(stored.lags==row.lags)].iloc[0]
                self.assertAlmostEqual(actual.coefficient,row.coefficient,places=7)
                self.assertAlmostEqual(actual.expiry_information_fraction,row.expiry_information_fraction,places=7)
                self.assertLessEqual(row.unique_expiry_weeks,row.event_days)

    def test_post_launch_identification_requires_the_exceptional_calendar_date(self):
        daily=pd.read_csv(ROOT/'data/analysis/single_stocks/daily_panel.csv',dtype={'stock_code':str})
        original=pd.read_csv(ROOT/'data/analysis/single_stocks/h5_diagnostics.csv',dtype={'stock_code':str})
        for aid,g in daily.groupby('stock_code'):
            d=specification_design(g,aid,'stock')
            expected=original.loc[(original.stock_code==aid)&(original.lags==5)].set_index('variant')
            for row in d.itertuples():
                self.assertEqual(row.model_days,expected.loc[row.variant,'n'])
                self.assertEqual(row.rank,expected.loc[row.variant,'rank'])
            row=d.loc[d.variant=='post_launch_only'].iloc[0]
            self.assertEqual(row.dominant_information_date,'2026-02-23')
            self.assertFalse(row.identified_without_dominant_date)
            self.assertLess(row.expiry_information_fraction_without_dominant_date,1e-20)
            self.assertGreater(row.max_date_information_share,.6)

    def test_scenarios_are_information_not_fake_future_observations(self):
        p=pd.read_csv(ROOT/'data/analysis/h5_diagnostics/primary_diagnostics.csv',dtype={'asset_id':str})
        out=precision_scenarios(p)
        for asset in p.asset_id.unique():
            rows=out.loc[(out.asset_id==asset)&(out.lags==5)&(out.scenario=='fixed_sample_multiplier')].set_index('sample_multiplier')
            self.assertAlmostEqual(rows.loc[4,'planning_mde80_log']*2,rows.loc[1,'planning_mde80_log'])
        self.assertFalse(out.loc[out.scenario=='illustrative_target_not_SESOI','target_variance_increase_pct'].isna().any())

if __name__=='__main__':unittest.main()
