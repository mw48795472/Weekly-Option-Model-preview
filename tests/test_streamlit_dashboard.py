"""User-facing research invariants and Streamlit interaction smoke tests."""
import importlib.util
from pathlib import Path
import unittest

import pandas as pd

from nh_research.dashboard_data import filter_contracts, csv_bytes, gamma_curve

ROOT = Path(__file__).resolve().parents[1]
HAS_STREAMLIT = importlib.util.find_spec("streamlit") is not None


class DashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = pd.read_csv(ROOT / "data/analysis/contracts/weekly_contracts.csv", dtype=str, keep_default_na=False)

    def test_filters_compose_and_empty_selection_stays_empty(self):
        selected = filter_contracts(self.frame, ["WKI"], ["2026-10-15"], ["C"], "코스피")
        self.assertGreater(len(selected), 0)
        self.assertEqual(set(selected.option_side), {"C"})
        self.assertEqual(set(selected.under_name), {"WKI"})
        self.assertEqual(len(filter_contracts(self.frame, [], self.frame.expiry_date, ["C", "P"])), 0)
        self.assertEqual(len(filter_contracts(self.frame, self.frame.under_name, self.frame.expiry_date, ["C", "P"], ".*")), 0)

    def test_download_preserves_identifiers_and_missing_market_values(self):
        selected = self.frame.iloc[:1]
        data = csv_bytes(selected)
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        from io import BytesIO
        restored = pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
        self.assertEqual(restored.iloc[0]["series"], selected.iloc[0]["series"])
        self.assertEqual(restored.iloc[0]["last_pric"], "")

    def test_gamma_scenario_rejects_undefined_inputs(self):
        self.assertGreater(gamma_curve(400, 400, 25, [1])[0], gamma_curve(400, 400, 25, [30])[0])
        with self.assertRaises(ValueError):
            gamma_curve(400, 400, 0, [1])
        with self.assertRaises(ValueError):
            gamma_curve(400, 400, 25, [0])


@unittest.skipUnless(HAS_STREAMLIT, "Install the streamlit extra for UI checks")
class DashboardUITests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def test_all_five_pages_render(self):
        app = self.app()
        self.assertEqual(app.metric[0].value, "766")
        for page in ["종목·변수 탐색", "가설 검토", "PoC 실험실", "진단·다운로드"]:
            with self.subTest(page=page):
                app.radio(key="page").set_value(page).run()
                self.assertFalse(app.exception)
                self.assertGreater(len(app.get("download_button")), 0)

    def test_search_with_no_match_is_explicit(self):
        app = self.app()
        app.radio(key="page").set_value("종목·변수 탐색").run()
        app.text_input(key="contract_search").set_value("no-such-contract").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("해당하는 계약이 없습니다" in item.value for item in app.info))
        app.text_input(key="contract_search").set_value("B09FG925").run()
        self.assertEqual(app.selectbox(key="selected_contract").value, "B09FG925")

    def test_poc_zero_denominators_and_all_experiments(self):
        app = self.app()
        app.radio(key="page").set_value("PoC 실험실").run()
        app.radio(key="experiment").set_value("H6 OI와 미래창").run()
        app.number_input(key="previous_oi").set_value(0).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "정의 불가")
        app.radio(key="experiment").set_value("REV 가격회귀율").run()
        app.number_input(key="rev_1").set_value(400.0).run()
        self.assertFalse(app.exception)
        self.assertTrue(all(metric.value == "정의 불가" for metric in app.metric))
        app.radio(key="experiment").set_value("H9b 비용과 실행").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "+4.0 bp")

    def test_all_hypothesis_details_are_available(self):
        app = self.app()
        app.radio(key="page").set_value("가설 검토").run()
        for item in ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "H9", "H9b"]:
            app.selectbox(key="hypothesis").set_value(item).run()
            self.assertFalse(app.exception)
            self.assertTrue(any(f"### {item}:" in x.value for x in app.markdown))


if __name__ == "__main__":
    unittest.main()
