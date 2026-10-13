import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from nh_research.empirical import forward_mean
from nh_research.h6_diagnostics import audit_origins, common_refit, label_overlap, prepare

ROOT = Path(__file__).resolve().parents[1]


class H6DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.panel = pd.read_csv(ROOT / "data/analysis/empirical/daily_panel.csv")

    def test_saved_funnels_reconcile_and_match_primary_counts(self):
        frame = pd.read_csv(ROOT / "data/analysis/h6_diagnostics/sample_attrition.csv", dtype={"unit": str})
        self.assertTrue(frame.groupby(["unit", "proxy", "family"])["count"].sum().eq(428).all())
        primary = frame.query("proxy=='parkinson' and family=='matched' and gate=='evaluated'").set_index("unit")
        expected = {"TXO": 263, "1303": 0, "2303": 0, "2317": 30, "2330": 36, "2454": 0, "2603": 12, "3231": 12}
        self.assertEqual(primary["count"].to_dict(), expected)
        audit = pd.read_csv(ROOT / "data/analysis/h6_diagnostics/origin_audit.csv", dtype={"unit": str})
        self.assertFalse(audit.duplicated(["unit", "proxy", "family", "date"]).any())
        evaluated = audit[audit.gate.eq("evaluated")]
        self.assertTrue(evaluated.completed_train.ge(100).all())
        self.assertTrue(evaluated.eligible.all())

    def test_gap_and_overlap_count_is_interval_based(self):
        rows = pd.DataFrame([
            dict(date="2025-01-01", origin_index=0, label_start="2025-01-02", label_end="2025-01-06"),
            dict(date="2025-01-03", origin_index=2, label_start="2025-01-04", label_end="2025-01-08"),
            dict(date="2025-01-08", origin_index=7, label_start="2025-01-09", label_end="2025-01-13"),
            dict(date="2025-01-10", origin_index=9, label_start="2025-01-11", label_end="2025-01-15"),
        ])
        result = label_overlap(rows)
        self.assertEqual(result["n"], 4)
        self.assertEqual(result["calendar_span"], 10)
        self.assertEqual(result["calendar_gaps"], 6)
        self.assertEqual(result["disjoint_target_windows"], 2)
        self.assertEqual(result["disjoint_dates"], "2025-01-01;2025-01-08")

    def test_price_zero_is_distinct_from_source_missing(self):
        panel = self.panel.iloc[:90].copy()
        panel.loc[30, "high"] = panel.loc[30, "low"]
        panel.loc[30, "parkinson"] = np.nan
        panel.loc[60, ["open", "high", "low", "close", "parkinson"]] = np.nan
        panel["parkinson_forward5"] = forward_mean(panel.parkinson)
        audit, flow = audit_origins(panel, pd.DataFrame(), minimum_train=1000)
        self.assertEqual(audit.loc[30, "gate"], "history_zero_range")
        self.assertEqual(audit.loc[60, "gate"], "history_missing_price")
        self.assertTrue(audit.loc[30, "flag_history_zero_range"])
        self.assertFalse(audit.loc[30, "flag_history_missing_price"])
        self.assertEqual(flow["count"].sum(), len(panel))

    def test_common_refit_is_purged_paired_and_preserves_primary(self):
        forecast = pd.read_csv(ROOT / "data/analysis/h6_diagnostics/common_refit_forecasts.csv", dtype={"unit": str})
        self.assertTrue((forecast.train_last_label_end < forecast.date).all())
        self.assertTrue(forecast.train_n.ge(100).all())
        self.assertTrue(forecast.groupby(["unit", "date"]).model.nunique().eq(3).all())
        self.assertTrue(forecast.groupby(["unit", "date"]).train_n.nunique().eq(1).all())
        self.assertTrue(forecast.groupby(["unit", "date"]).actual.nunique().eq(1).all())
        primary = pd.read_csv(ROOT / "data/analysis/empirical/h6_forecasts.csv")
        primary = primary.query("proxy=='parkinson' and model=='HAR_calendar_OI_lag1'")
        fitted = forecast.query("unit=='TXO' and model=='matched_OI_lag1'")
        self.assertEqual(primary.date.tolist(), fitted.date.tolist())
        np.testing.assert_allclose(primary.forecast, fitted.forecast, rtol=1e-7, atol=1e-12)

    def test_future_mutation_cannot_change_earlier_forecasts(self):
        panel = self.panel.iloc[:205].copy()
        panel["oi_level_lag1"] = np.log1p(panel.weekly_oi).shift(1)
        before = common_refit(panel)
        altered = panel.copy()
        altered.loc[190:, ["parkinson", "parkinson_forward5", "oi_matched_lag1", "oi_level_lag1"]] *= 7
        after = common_refit(altered)
        cutoff = panel.date.iloc[185]
        first = before[before.date.lt(cutoff)].reset_index(drop=True)
        second = after[after.date.lt(cutoff)].reset_index(drop=True)
        pd.testing.assert_frame_equal(first, second)

    def test_unordered_calendar_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ordered market calendar"):
            prepare(self.panel.iloc[::-1])


if __name__ == "__main__":
    unittest.main()
