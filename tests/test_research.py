import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs

from nh_research.analysis import (chart_rows, decimal_or_none, forward_mean, oi_change,
                                  purged_training_indices, relative_spread)
from nh_research.catalog import compare_specs, read_workbook, sha256
from nh_research.contracts import (Credentials, classify_message, market_request, session_init,
                                   subscription_plan, token_request, websocket_key_request)
from nh_research.master import load_master, summarize_master

ROOT = Path(__file__).resolve().parents[1]
CATALOG = {r["metadata"]["document"]: r for r in
           json.loads((ROOT / "data/catalog/catalog.json").read_text(encoding="utf-8"))}


class ContractTests(unittest.TestCase):
    def test_token_form_encodes_reserved_characters(self):
        creds = Credentials("dummy +&", "dummy=secret& value")
        plan = token_request(creds)
        self.assertEqual(parse_qs(plan.body.decode()), {
            "grant_type": ["client_credentials"], "appkey": [creds.appkey], "appsecret": [creds.appsecret]})
        self.assertEqual(plan.headers["Content-Type"], "application/x-www-form-urlencoded")
        self.assertNotIn(creds.appsecret, repr(creds) + repr(plan) + json.dumps(plan.public_summary()))

    def test_demo_default_and_live_explicit(self):
        for env, domain in [("demo", "apidemo"), ("live", "api")]:
            plan = market_request(CATALOG["domestic/price"], {"sym": "TEST"}, "DUMMY_TOKEN", env)
            self.assertEqual(plan.url, f"https://{domain}.futures.co.kr/trade/v1/domestic/price")
            self.assertEqual(plan.headers["Authorization"], "Bearer DUMMY_TOKEN")
            self.assertEqual(json.loads(plan.body), {"sym": "TEST"})
            self.assertNotIn("DUMMY_TOKEN", repr(plan) + json.dumps(plan.public_summary()))

    def test_unknown_environment(self):
        with self.assertRaises(ValueError):
            token_request(Credentials("dummy", "dummy"), "https://untrusted.example")

    def test_order_and_account_requests_rejected(self):
        for name in ("domestic/order", "domestic/cancel", "domestic/open-interest",
                     "overseas/open-interest-expiry", "overseas/deposit"):
            with self.subTest(api=name), self.assertRaises(ValueError):
                market_request(CATALOG[name], {}, "DUMMY")

    def test_missing_unknown_and_wrong_type_fields(self):
        for params in ({}, {"sym": "T", "unknown": "1"}, {"sym": 1}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                market_request(CATALOG["domestic/price"], params, "DUMMY")

    def test_chart_defaults_and_explicit_one_minute(self):
        plan = market_request(CATALOG["domestic/chart-minute"],
                              {"sym": "T", "nght_tp": "1", "dcnt": "1"}, "DUMMY")
        self.assertEqual(json.loads(plan.body)["dcnt"], "1")
        self.assertEqual(json.loads(plan.body)["nxt_key"], "99999999")
        self.assertEqual(json.loads(plan.body)["req_qty"], "300")

    def test_demo_night_and_oversized_page_rejected(self):
        for params in ({"sym": "T", "nght_tp": "2"},
                       {"sym": "T", "nght_tp": "1", "req_qty": "10000"}):
            with self.assertRaises(ValueError):
                market_request(CATALOG["domestic/chart-minute"], params, "DUMMY")

    def test_websocket_key_and_init(self):
        plan = websocket_key_request("DUMMY")
        self.assertEqual(plan.method, "GET")
        self.assertIsNone(plan.body)
        self.assertTrue(plan.url.endswith("/permission/v1/web-socket-key"))
        self.assertEqual(session_init("DUMMY")["body"]["action_code"], "session_init")

    def test_subscription_account_budget(self):
        pairs = [(code, f"T{i}") for i in range(9) for code in ("KA", "KB")]
        self.assertEqual(len(subscription_plan(pairs, 2)), 18)
        with self.assertRaises(ValueError):
            subscription_plan(pairs, 3)
        with self.assertRaises(ValueError):
            subscription_plan([("O1_K", "T")])
        self.assertEqual(len(subscription_plan([("KA", "T"), ("KA", "T")])), 1)

    def test_control_messages_and_data_are_distinct(self):
        cases = [({"code": "pingpong", "msg": "pingpong"}, "echo_pingpong"),
                 ({"code": "INIT", "msg": "INIT_SUCCESS"}, "session_ready"),
                 ({"code": "INIT", "msg": "DENIED"}, "session_failed"),
                 ({"rt_cd": "RT_FAIL"}, "subscription_failed"),
                 ({"header": {"x": "1"}, "body": {"sym": "T"}}, "market_event"),
                 ({"rt_cd": "RT_INIT"}, "subscription_ok"), ({}, "unknown")]
        for value, expected in cases:
            self.assertEqual(classify_message(value), expected)


class DataTests(unittest.TestCase):
    def test_empty_zero_and_invalid_numbers(self):
        self.assertIsNone(decimal_or_none(" "))
        self.assertEqual(decimal_or_none("0"), Decimal(0))
        self.assertEqual(decimal_or_none("123.4500"), Decimal("123.4500"))
        for value in ("NaN", "Infinity", "--", True):
            with self.assertRaises(ValueError):
                decimal_or_none(value)

    def test_reject_flattened_and_object_chart_examples(self):
        for response in ({"nrec": "1", "Occurs1": {}}, {"nrec": "1", "Occurs1": ""},
                         {"nrec": "2", "Occurs1": [{}]}, {"nrec": "1.5", "Occurs1": [{}]}):
            with self.assertRaises(ValueError):
                chart_rows(response)
        self.assertEqual(chart_rows({"nrec": "1", "Occurs1": [{"price": "1"}]}), [{"price": "1"}])
        self.assertEqual(chart_rows({"nrec": "0", "Occurs1": []}), [])

    def test_oi_uses_previous_denominator(self):
        self.assertEqual(oi_change("120", "100"), Decimal("0.2"))
        self.assertIsNone(oi_change("10", "0"))
        self.assertIsNone(oi_change("", "100"))
        with self.assertRaises(ValueError):
            oi_change("-1", "100")
        with self.assertRaises(ValueError):
            oi_change("-1", "0")

    def test_crossed_or_zero_quotes_excluded(self):
        self.assertEqual(relative_spread("99", "101"), Decimal("0.02"))
        for bid, ask in [("101", "99"), ("0", "1"), (None, "1")]:
            self.assertIsNone(relative_spread(bid, ask))

    def test_forward_label_is_t_plus_one_through_h(self):
        self.assertEqual(forward_mean(list(range(10)), 5),
                         [3, 4, 5, 6, 7, None, None, None, None, None])

    def test_incomplete_and_gapped_labels_remain_missing(self):
        self.assertEqual(forward_mean([1, 2, None, 4], 2), [None, None, None, None])
        self.assertEqual(forward_mean([1, float("nan"), 3], 1), [None, 3, None])

    def test_purge_excludes_overlapping_or_missing_labels(self):
        self.assertEqual(purged_training_indices([1, 2, 3, 4], [2, 4, 5, None], 4), [0])

    def test_master_invalid_width_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.mst"
            path.write_text("a;b\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_master(path)


class EvidenceTests(unittest.TestCase):
    def test_all_49_downloads_cover_uploaded_specs(self):
        uploaded = read_workbook(ROOT / "vendor/nh/2026-10-11/uploaded/전체_API_문서.xlsx")
        self.assertEqual(len(uploaded), 49)
        self.assertEqual(set(CATALOG), {s["metadata"]["document"] for s in uploaded})
        # Metadata and INPUT/OUTPUT field definitions match; examples may differ.
        for record in uploaded:
            differences = compare_specs(record, CATALOG[record["metadata"]["document"]])
            self.assertTrue(all(d["location"].endswith("_example") for d in differences))

    def test_preserved_source_hashes(self):
        manifest = json.loads((ROOT / "data/catalog/source_manifest.json").read_text(encoding="utf-8"))
        for source in [manifest["uploaded"], *manifest["individual"]]:
            self.assertEqual(sha256(ROOT / source["file"]), source["sha256"])

    def test_public_master_report_reproduces(self):
        summaries = json.loads((ROOT / "data/analysis/master_summary.json").read_text(encoding="utf-8"))
        for expected in summaries:
            path = ROOT / expected["file"]
            self.assertEqual(sha256(path), expected["sha256"])
            computed = summarize_master(load_master(path))
            for key, value in computed.items():
                self.assertEqual(value, expected[key])


if __name__ == "__main__":
    unittest.main()
