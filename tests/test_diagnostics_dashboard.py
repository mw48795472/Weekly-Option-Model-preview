"""Exercise new diagnostic choices, including non-estimable stock branches."""
import importlib.util
from pathlib import Path
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HAS_STREAMLIT = importlib.util.find_spec("streamlit") is not None


@unittest.skipUnless(HAS_STREAMLIT, "Streamlit required")
class DiagnosticsUITests(unittest.TestCase):
    def app(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=40).run()
        app.radio(key="page").set_value("H5·H6 심화 진단").run()
        self.assertFalse(app.exception)
        return app

    def test_h5_all_assets_scenarios_and_fragile_design(self):
        app = self.app()
        app.radio(key="deep_view").set_value("H5 정밀도·설계").run()
        for asset in ["TXO_TAIEX", "1303", "2303", "2317", "2330", "2454", "2603", "3231"]:
            app.selectbox(key="deep_h5_asset").set_value(asset).run()
            self.assertFalse(app.exception, asset)
        for view in ["표본 계획 시나리오", "기존 사양 민감도"]:
            app.radio(key="deep_h5_view").set_value(view).run()
            self.assertFalse(app.exception)
        self.assertTrue(any("2026-02-23" in x.value for x in app.markdown))
        app.selectbox(key="deep_h5_lag").set_value(20).run()
        self.assertFalse(app.exception)

    def test_h6_zero_evaluation_and_common_refit_branches(self):
        app = self.app()
        app.radio(key="deep_view").set_value("H6 표본·변수").run()
        for unit in ["TXO", "1303", "2303", "2317", "2330", "2454", "2603", "3231"]:
            app.selectbox(key="deep_h6_asset").set_value(unit).run()
            self.assertFalse(app.exception, unit)
        app.selectbox(key="deep_h6_asset").set_value("1303").run()
        self.assertEqual(app.metric[1].value, "0")
        app.radio(key="deep_h6_view").set_value("평가창·정밀도").run()
        self.assertTrue(any("평가 표본이 없습니다" in x.value for x in app.warning))
        app.radio(key="deep_h6_view").set_value("같은 훈련·평가 날짜 비교").run()
        self.assertFalse(app.exception)
        app.selectbox(key="deep_h6_asset").set_value("2317").run()
        self.assertTrue(any("사후 탐색" in x.value for x in app.warning))
        app.selectbox(key="deep_h6_proxy").set_value("close_squared_return").run()
        self.assertTrue(any("선택과 별개" in x.value for x in app.markdown))
        self.assertFalse(app.exception)
        app.radio(key="deep_view").set_value("추가 데이터").run()
        self.assertFalse(app.exception)
        self.assertGreater(len(app.get("download_button")), 0)

    def test_nikkei_status_does_not_claim_empirical_estimates(self):
        app = self.app()
        app.radio(key="page").set_value("닛케이225 확장").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "0")
        self.assertEqual(app.metric[2].value, "미실행")
        app.radio(key="nikkei_view").set_value("분석 입력·실행 조건").run()
        self.assertFalse(app.exception)
        self.assertGreater(len(app.get("download_button")), 0)
        self.assertEqual(len(app.get("plotly_chart")), 0)

    def test_intervals_never_clip_percentile_endpoints(self):
        from nh_research.diagnostics_dashboard import intervals
        frame = pd.DataFrame([{"low":1., "high":2., "estimate":0., "label":"outside CI"}])
        fig = intervals(frame, "low", "high", "estimate", "label", "test", "loss")
        self.assertEqual(list(fig.data[0].x), [1., 2.])
        self.assertEqual(list(fig.data[1].x), [0.])


if __name__ == "__main__":
    unittest.main()
