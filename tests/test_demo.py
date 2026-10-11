import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pandas as pd
from nh_research.client import DemoClient, APIError, redact, paged_query
from nh_research.contracts import Credentials
from nh_research.market_analysis import analyze_snapshot, intraday_rv, number, observed_rows


class DemoTests(unittest.TestCase):
    def test_auth_and_redaction(self):
        client = DemoClient(Credentials('key','secret'), {}, transport=lambda plan: {
            'access_token':'private-token','token_type':'Bearer','scopes':'S','expires_in':'86400'})
        summary = client.authenticate()
        self.assertEqual(summary['status'],'authenticated')
        self.assertNotIn('private-token',str(summary))
        self.assertNotIn('secret',repr(client))
        self.assertEqual(redact({'access_token':'abc','message':'contains abc'},('abc',)),
                         {'access_token':'[REDACTED]','message':'contains [REDACTED]'})

    def test_live_scope_rejected(self):
        client = DemoClient(Credentials('key','secret'), {}, transport=lambda plan: {
            'access_token':'token','token_type':'Bearer','scopes':'R','expires_in':'86400'})
        with self.assertRaises(APIError):
            client.authenticate()

    def test_repeated_cursor_stops(self):
        class Stub:
            def query(self,*args):
                return {'Occurs1':[{}],'nxt_key':'99999999'}
        self.assertEqual(paged_query(Stub(),'x',{})['stop_reason'],'repeated_cursor')

    def test_missing_market_is_empty(self):
        result=analyze_snapshot({'auth':{'status':'authenticated'},'failures':[{'error':'403'}]})
        self.assertTrue(result['daily'].empty)
        self.assertTrue(result['minute'].empty)
        self.assertEqual(result['summary']['rv_days'],0)

    def test_partial_bins_not_used_as_five_minute_returns(self):
        frame=pd.DataFrame({'timestamp':pd.to_datetime(['2026-10-08 09:00','2026-10-08 09:05']),
                            'close':[100.,101.]})
        self.assertTrue(intraday_rv(frame).empty)

    def test_count_mismatch_and_nonfinite(self):
        rows,quality=observed_rows({'pages':[{'nrec':'2','Occurs1':[{}]}]})
        self.assertEqual(rows,[])
        self.assertEqual(quality['rejected_pages'],1)
        self.assertIsNone(number('Infinity'))
        self.assertEqual(number('0'),0)


if __name__ == '__main__':
    unittest.main()
