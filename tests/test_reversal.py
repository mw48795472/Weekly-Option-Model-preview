"""Hand-specified fixtures check calculations, not market effect size."""
import csv
import math
import unittest
from copy import deepcopy
from pathlib import Path

from nh_research.reversal import analyze, candidate_events, rev_bp, summarize

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    events = [dict(underlying_id="TEST_INDEX", event_date="2026-01-02", event_type="expiry",
                   price_kind="cash_index", price_symbol="TEST", expiry_source="unit_test")]
    # Jan 5 is intentionally excluded as a fictitious closure in this test calendar.
    calendar = [dict(price_symbol="TEST", session_date=d, open_at=d + "T09:00:00+09:00",
                     close_at=d + "T15:30:00+09:00", source="fictitious_unit_test_calendar")
                for d in ("2026-01-02", "2026-01-06")]
    prices = [dict(price_symbol="TEST", timestamp=at + "+09:00", price=value,
                   observation_type="observed", source="unit_test_fixture_not_market_data")
              for at, value in (("2026-01-02T15:00:00", 100), ("2026-01-02T15:30:00", 101),
                                ("2026-01-06T09:00:00", 100.5), ("2026-01-06T09:01:00", 100.25),
                                ("2026-01-06T09:30:00", 100))]
    return events, calendar, prices


class ReversalTests(unittest.TestCase):
    def test_sign_and_basis_points(self):
        self.assertAlmostEqual(rev_bp(100, 101, 100), 10000 / 101)
        self.assertAlmostEqual(rev_bp(100, 99, 100), 10000 / 99)
        self.assertLess(rev_bp(100, 101, 102), 0)
        self.assertEqual(rev_bp(100, 101, 101), 0)
        self.assertIsNone(rev_bp(100, 100, 101))
        self.assertIsNone(rev_bp(100, 100.0001, 101, 1))

    def test_invalid_prices_and_threshold(self):
        for value in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                rev_bp(100, 101, value)
        for value in (-1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                rev_bp(100, 101, 100, value)

    def test_next_session_comes_from_calendar_not_weekday_arithmetic(self):
        result = analyze(*fixture(), "2026-01-06T10:00:00+09:00")[0]
        self.assertEqual(result["next_session_date"], "2026-01-06")
        self.assertAlmostEqual(result["rev3_bp"], 10000 / 101)
        self.assertEqual(result["rev3_status"], "computed")
        self.assertIn("unit_test", result["close_source"])

    def test_partial_horizons_and_no_lookahead(self):
        result = analyze(*fixture(), "2026-01-06T09:01:00+09:00")[0]
        self.assertEqual(result["rev2_status"], "computed")
        self.assertEqual(result["rev3_status"], "not_yet_observable")
        self.assertEqual(result["30m_price"], "")
        self.assertEqual(result["rev3_bp"], "")
        summary = summarize([result])
        self.assertEqual([r["n"] for r in summary], [1, 1, 0])
        self.assertEqual(summary[-1]["mean_bp"], "")

    def test_missing_exact_anchor_is_not_forward_filled(self):
        events, calendar, prices = fixture()
        prices[0]["timestamp"] = "2026-01-02T14:59:00+09:00"
        result = analyze(events, calendar, prices, "2026-01-06T10:00:00+09:00")[0]
        self.assertEqual(result["preclose_status"], "missing_exact_price")
        self.assertEqual(result["rev1_bp"], "")

    def test_future_contract_roll_cannot_supply_next_day_anchors(self):
        events, calendar, prices = fixture()
        events[0]["price_kind"] = "future_proxy"
        for row in prices[2:]:
            row["price_symbol"] = "DIFFERENT_CONTRACT"
        result = analyze(events, calendar, prices, "2026-01-06T10:00:00+09:00")[0]
        self.assertEqual(result["rev1_status"], "missing_exact_price")

    def test_duplicate_data_is_rejected_instead_of_arbitrary_selection(self):
        for index in range(3):
            items = list(fixture())
            items[index].append(deepcopy(items[index][0]))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                analyze(*items, "2026-01-06T10:00:00+09:00")

    def test_calendar_boundary_and_zero_reference(self):
        events, calendar, prices = fixture()
        result = analyze(events, calendar[:1], prices, "2026-01-06T10:00:00+09:00")[0]
        self.assertIn("missing_next_session", result["issues"])
        self.assertEqual(result["rev1_status"], "missing_anchor_schedule")
        prices[1]["price"] = 100
        result = analyze(events, calendar, prices, "2026-01-06T10:00:00+09:00")[0]
        self.assertEqual(result["rev1_status"], "zero_reference_move")
        self.assertEqual(result["rev1_bp"], "")

    def test_unverified_time_and_synthetic_input_rejected(self):
        events, calendar, prices = fixture()
        with self.assertRaisesRegex(ValueError, "KST"):
            analyze(events, calendar, prices, "2026-01-06T10:00:00")
        prices[0]["observation_type"] = "mathematical_example"
        with self.assertRaisesRegex(ValueError, "observed"):
            analyze(events, calendar, prices, "2026-01-06T10:00:00+09:00")
        events, calendar, prices = fixture()
        calendar[0]["close_at"] = "2026-01-02T09:30:00+09:00"
        with self.assertRaisesRegex(ValueError, "longer than 30"):
            analyze(events, calendar, prices, "2026-01-06T10:00:00+09:00")

    def test_saved_master_has_six_future_events_and_no_prices(self):
        with (ROOT / "data/analysis/contracts/weekly_contracts.csv").open(encoding="utf-8-sig") as f:
            contracts = list(csv.DictReader(f))
        events = candidate_events(contracts)
        self.assertEqual(len(events), 6)
        self.assertEqual(sum(e["contract_count"] for e in events), 766)
        results = analyze(events, [], [], "2026-10-11T09:00:00+09:00")
        self.assertTrue(all("future_event" in r["issues"] for r in results))
        self.assertTrue(all(r["n"] == 0 and r["mean_bp"] == "" for r in summarize(results)))


if __name__ == "__main__":
    unittest.main()
