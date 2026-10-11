import copy
import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))

from nh_research.contract_exports import NEEDED, FUTURE_DERIVED, csv_bytes, prepare_contracts
from nh_research.master import HEADER, load_master, weekly_name_candidate


class ContractExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.raw = [r for r in load_master(root/'vendor/nh/2026-10-11/masters/fut_opt.mst.gz') if weekly_name_candidate(r)]

    def test_no_market_values_or_source_fields_are_invented(self):
        rows, contracts = prepare_contracts(self.raw)
        original = {(r['cme_tp'],r['series']):r for r in self.raw}
        self.assertEqual(len(contracts),766)
        self.assertEqual(len(rows),1258)
        for r in rows:
            self.assertEqual({k:r[k] for k in HEADER},original[r['cme_tp'],r['series']])
        for r in rows+contracts:
            self.assertTrue(all(r[k]=='' for k in [*NEEDED,*FUTURE_DERIVED]))

    def test_conflicting_identity_is_not_silently_selected(self):
        series = self.raw[0]['series']
        sample = copy.deepcopy([r for r in self.raw if r['series']==series])
        self.assertEqual(len(sample),2)
        sample[1]['ctrt_size']='999'
        _, contracts = prepare_contracts(sample)
        self.assertEqual(contracts[0]['ctrt_size'],'')
        self.assertIn('ctrt_size',contracts[0]['identity_conflict_fields'])

    def test_duplicate_session_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            prepare_contracts([self.raw[0],self.raw[0]])

    def test_ambiguous_pair_has_no_arbitrary_counterpart(self):
        rows,_=prepare_contracts(self.raw)
        first=rows[0]
        sample=copy.deepcopy([r for r in self.raw if r['cme_tp']==first['cme_tp'] and r['series'] in (first['series'],first['opposite_series'])])
        other=copy.deepcopy(next(r for r in sample if r['series']==first['opposite_series']))
        other['series']='TESTPAIR'
        sample.append(other)
        exported,_=prepare_contracts(sample)
        selected=next(r for r in exported if r['series']==first['series'])
        self.assertEqual(selected['pair_status'],'ambiguous')
        self.assertEqual(selected['opposite_series'],'')

    def test_csv_roundtrip_preserves_codes_and_empty_values(self):
        rows,_=prepare_contracts([self.raw[0]])
        output=csv_bytes(rows)
        self.assertTrue(output.startswith(b'\xef\xbb\xbf'))
        saved=list(csv.DictReader(io.StringIO(output.decode('utf-8-sig'))))[0]
        self.assertEqual(saved['inst_grp_cd'],self.raw[0]['inst_grp_cd'])
        self.assertEqual(saved['last_pric'],'')
        self.assertEqual(saved['name_kor'],self.raw[0]['name_kor'])


if __name__=='__main__':
    unittest.main()
