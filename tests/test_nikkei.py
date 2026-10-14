"""Synthetic parser fixtures, never market observations."""
import unittest
import numpy as np
from nh_research.nikkei import parse_cash_prices,cash_baseline,readiness,required_data

class NikkeiTests(unittest.TestCase):
 def test_identity_and_ohlc_validation(self):
  raw='date,open,high,low,close\n2025-01-06,100,105,99,102\n'
  with self.assertRaises(ValueError):parse_cash_prices(raw,'TJF')
  with self.assertRaises(ValueError):parse_cash_prices(raw.replace('105','101'),'NIKKEI225_CASH')
  with self.assertRaises(ValueError):parse_cash_prices(raw+raw.splitlines()[1]+'\n','NIKKEI225_CASH')
 def test_cash_baseline_is_neither_futures_nor_option_test(self):
  data= parse_cash_prices('date,open,high,low,close\n2025-01-06,100,105,99,102\n2025-01-07,103,103,103,103\n','NIKKEI225_CASH')
  df,summary=cash_baseline(data)
  self.assertEqual(summary['zero_range_days'],1)
  self.assertAlmostEqual(df.log_return.iloc[1],np.log(103/102))
  self.assertEqual(df.parkinson.iloc[1],0)
  self.assertFalse(summary['h5_executed']);self.assertFalse(summary['h6_executed'])
 def test_transport_success_does_not_invent_nikkei_data(self):
  info=readiness({'requests':[{'complete':True}]})
  self.assertEqual(info['api_success'],0)
  self.assertEqual(info['api_requests'],0)
  self.assertEqual(info['data_provider'],'J-Quants')
  self.assertEqual(info['nikkei_observations'],0)
  self.assertFalse(info['taifex_audit_is_jquants_evidence']);self.assertFalse(info['h5_executed'])
  self.assertTrue(required_data().minimum_fields.str.contains('available_at').any())

if __name__=='__main__':unittest.main()
