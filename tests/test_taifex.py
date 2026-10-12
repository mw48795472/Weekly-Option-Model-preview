"""TAIFEX parsing, identifier, source-quality and dashboard interaction checks."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from nh_research.taifex import (
    canonical_strike, contract_id, decode_response, normalize_market,
    describe_groups, decompose_oi, enrich, product_metadata, expiry_reference,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/analysis/taifex"


def observation(**overrides):
    return {
        "Date":"20261008", "Contract":"CDO", "ContractMonth(Week)":"202610W2",
        "StrikePrice":"2450.0000", "CallPut":"買權", "TradingSession":"一般",
        "Open":"-", "High":"-", "Low":"-", "Close":"-", "Volume":"0",
        "SettlementPrice":"3", "OpenInterest":"0", "BestBid":"-", "BestAsk":"-",
        **overrides,
    }


class TaifexParsingTests(unittest.TestCase):
    def test_actual_body_formats_and_error_page(self):
        self.assertEqual(decode_response(b'[{"Contract":"TXO"}]')[1], "json")
        raw = "交易日期,契約,到期月份(週別),\n2026/10/08,CDO,202610W2,\n".encode("cp950")
        rows, fmt = decode_response(raw)
        self.assertEqual(fmt, "csv")
        self.assertEqual(rows[0]["Date"], "2026/10/08")
        self.assertNotIn("", rows[0])
        for raw in [b"<html>Error</html>", b'{"error":"unavailable"}', b"error"]:
            with self.assertRaises(ValueError):
                decode_response(raw)

    def test_internal_identifier_is_canonical_and_rejects_invalid(self):
        self.assertEqual(canonical_strike("2450.0000"), "2450")
        self.assertEqual(contract_id("CDO","202610W2","P","2450.0"),
                         "TAIFEX:CDO:202610W2:P:2450")
        for value in ["NaN", "Infinity", "0", "-3"]:
            with self.assertRaises(ValueError):
                canonical_strike(value)
        with self.assertRaises(ValueError):
            contract_id("CDO","202613W2","P","2450")

    def test_all_missing_prices_remain_missing_real_zero_is_preserved(self):
        frame = normalize_market([observation()], "fixture")
        self.assertTrue(pd.isna(frame.close.iloc[0]))
        self.assertTrue(pd.isna(frame.bid.iloc[0]))
        self.assertEqual(frame.oi.iloc[0], 0)
        self.assertEqual(frame.volume.iloc[0], 0)
        self.assertEqual(frame.settlement.iloc[0], 3)
        self.assertFalse(frame.has_trade_price.iloc[0])
        with self.assertRaises(ValueError):
            normalize_market([observation(Volume="inf")], "fixture")
        with self.assertRaises(ValueError):
            normalize_market([observation(), observation()], "fixture")

    def test_after_hours_oi_not_summed_and_zero_ratio_undefined(self):
        frame = normalize_market([
            observation(OpenInterest="3"),
            observation(TradingSession="盤後", OpenInterest="999"),
            observation(CallPut="賣權", OpenInterest="1"),
        ], "fixture")
        frame["name"] = "台積電"
        stats = describe_groups(frame).iloc[0]
        self.assertEqual(stats.oi, 4)
        self.assertEqual(stats.put_call_oi_ratio, 1/3)
        self.assertEqual(stats.strike_oi_hhi, 1)
        zero = frame.loc[frame.session.eq("regular")].copy()
        zero["oi"] = 0
        stats = describe_groups(zero).iloc[0]
        self.assertIsNone(stats.put_call_oi_ratio)
        self.assertIsNone(stats.strike_oi_hhi)

    def test_oi_rollover_decomposition_and_missing_guard(self):
        frame = pd.DataFrame([
            ("2026-10-01","continuing",10), ("2026-10-01","exiting",20),
            ("2026-10-02","continuing",14), ("2026-10-02","entering",5),
        ], columns=["date","contract_id","oi"])
        frame["product"],frame["name"],frame["session"],frame["is_weekly"]="TXO","TAIEX","regular",True
        result = decompose_oi(frame).iloc[0]
        self.assertEqual(result.total_change, -11)
        self.assertEqual((result.matched_change,result.entering_oi,result.exiting_oi),(4,5,20))
        frame.loc[0,"oi"] = np.nan
        with self.assertRaises(ValueError):
            decompose_oi(frame)

    def test_explicit_adjusted_aliases_and_leading_zero_stock_code(self):
        sso = [dict(Contract="CBO", StockCode="0050", StockName="ETF", UnderlyingStock="ETF",
                    Type="ETF"), dict(Contract="CDO", StockCode="2330", StockName="台積電",
                                     UnderlyingStock="TSMC", Type="股票")]
        catalog = [dict(commodity_id="CDO", flag=1, marketids="CDO,CDA,CDB")]
        meta = product_metadata(sso,catalog,[])
        self.assertEqual(meta.set_index("product").loc["CBO","underlying_code"], "0050")
        self.assertTrue(meta.set_index("product").loc["CDA","adjusted"])
        self.assertNotIn("CDC", meta["product"].tolist())
        market = normalize_market([observation(Contract="TXO", **{"ContractMonth(Week)":"202610F2"})], "fixture")
        result = enrich(market,meta).iloc[0]
        self.assertEqual(result.trading_product_code, "TXV")
        self.assertTrue(result.contract_id.startswith("TAIFEX:TXO:"))
        refs = expiry_reference([dict(Contract="TXO", CallPut="C", StrikePrice="2450",
                    **{"ContractMonth(Week)":"202610F2","ContractSettlementDay":"20261012"})])
        self.assertEqual(refs[result.contract_id], "2026-10-12")  # Actual reference, not guessed Friday.


class TaifexCapturedDataTests(unittest.TestCase):
    def test_source_hashes_and_complete_flags(self):
        folder = ROOT / "data/source/taifex/20261012"
        manifest = json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
        for entry in manifest["requests"]:
            if entry.get("complete"):
                content = gzip.decompress((folder/entry["file"]).read_bytes())
                self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])

    def test_comparison_preserves_quote_differences(self):
        frame = pd.read_csv(DATA/"api_csv_comparison.csv")
        self.assertGreater(len(frame), 0)
        for field in ["open","high","low","close","volume","settlement","oi"]:
            a,b = frame[field+"_api"],frame[field+"_csv"]
            self.assertTrue((a.eq(b) | (a.isna() & b.isna())).all())
        self.assertTrue((frame.bid_api.isna() & frame.bid_csv.notna()).any())

    def test_unique_history_keys_and_decomposition_identity(self):
        history = pd.read_csv(DATA/"weekly_history.csv.gz")
        self.assertFalse(history.duplicated(["date","contract_id","session"]).any())
        self.assertGreater(history.date.nunique(), 1)
        self.assertTrue(history.loc[history.session.eq("after_hours"),"oi"].isna().all())
        changes = pd.read_csv(DATA/"oi_decomposition.csv")
        self.assertTrue(np.allclose(changes.matched_change+changes.entering_oi-changes.exiting_oi,
                                    changes.total_change))
        latest = pd.read_csv(DATA/"latest_weekly.csv")
        self.assertTrue(latest.session.eq("regular").all())
        self.assertTrue(latest.is_weekly.all())


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Streamlit not installed")
class TaifexDashboardTests(unittest.TestCase):
    def test_analysis_tickers_empty_search_and_download_page(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT/"streamlit_app.py"),default_timeout=45).run()
        app.radio(key="page").set_value("TAIFEX 실측 분석").run()
        self.assertFalse(app.exception)
        app.selectbox(key="taifex_product").set_value("TXO").run()
        self.assertFalse(app.exception)
        app.radio(key="taifex_view").set_value("개별 계약·티커").run()
        app.text_input(key="tai_ticker_search").set_value("2330").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.dataframe[0].value.underlying_code.eq("2330").all())
        self.assertGreater(len(app.dataframe[0].value),0)
        app.radio(key="tai_ticker_scope").set_value("전체 — 월물·조정계약 포함").run()
        app.text_input(key="tai_ticker_search").set_value("CDA").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.dataframe[0].value["product"].eq("CDA").all())
        app.text_input(key="tai_ticker_search").set_value("not-a-real-ticker").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value),0)
        app.radio(key="taifex_view").set_value("API 확인·다운로드").run()
        self.assertFalse(app.exception)
        self.assertGreater(len(app.get("download_button")),0)



class TaifexCollectorTests(unittest.TestCase):
    def test_bounded_keyless_collection_and_immutable_snapshot(self):
        import io
        import tempfile
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location("taifex_collector",ROOT/"scripts/collect_taifex.py")
        collector=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(collector)
        calls=[]
        class Response(io.BytesIO):
            status=200
            headers={"Content-Type":"application/octet-stream"}
        def response(request,timeout):
            calls.append(request)
            if request.full_url.endswith("swagger.json"):
                return Response(b'{}')
            if request.full_url.endswith("SSOLists"):
                return Response(b"x"*129)
            return Response(b'[{"Date":"20261008","Contract":"TXO"}]')
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/"snapshot"
            with patch.object(collector,"urlopen",side_effect=response), patch("builtins.print"):
                result=collector.collect(folder,max_bytes=128)
                with self.assertRaises(ValueError):
                    collector.collect(folder,max_bytes=128)
            self.assertFalse(any("authorization" in {k.lower() for k in req.headers} for req in calls))
            self.assertFalse(any("OptionsTimeAndSalesData" in req.full_url for req in calls))
            failed=next(r for r in result["requests"] if r["name"]=="SSOLists")
            self.assertFalse(failed["complete"])
            self.assertFalse((folder/"SSOLists.raw.gz").exists())
            self.assertIn("exceeds configured limit",failed["error"])
            good=next(r for r in result["requests"] if r["name"]=="DailyMarketReportOpt")
            self.assertTrue(good["complete"])
            self.assertEqual(gzip.decompress((folder/good["file"]).read_bytes()),
                             b'[{"Date":"20261008","Contract":"TXO"}]')

if __name__ == "__main__":
    unittest.main()
