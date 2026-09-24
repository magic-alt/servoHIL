"""An executed subset, stale source or edited artifact is not a complete EDV run."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_edv_qualification import module, ROOT


class EvidenceIntegrity(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'sim/power/evidence.py').is_file(),'missing complete-run evidence verifier')
        self.m=module('evidence');self.s=module('spice')

    def fixture(self,out):
        case=self.s.make_cases(ROOT)[0];path=out/case['id'];path.mkdir()
        values={k:1. for k in case['measures']}
        values['output_mean']=case['nominal_v']
        values['gate_duty']=case['conditions']['expected_gate_duty']
        files={'bench.cir':case['deck'],'ngspice.cir':'SYNTHETIC WRAPPER',
               'process.txt':'SYNTHETIC PROCESS',
               'ngspice.log':'\n'.join(k+' = '+str(v) for k,v in values.items()),
               'waveform.dat':'SYNTHETIC TEST WAVEFORM NOT ENGINEERING EVIDENCE\n'}
        for name,text in files.items():(path/name).write_text(text)
        row={k:v for k,v in case.items() if k!='deck'}
        row.update(measured=values,assessment=self.s.assess(case,values),
                   deck_sha256=hashlib.sha256(case['deck'].encode()).hexdigest(),
                   artifact_sha256={name:hashlib.sha256((path/name).read_bytes()).hexdigest() for name in files})
        report={'status':'EXECUTED_NOT_QUALIFIED','layout_allowed':False,
                'source_worktree_dirty':False,'source_commit':'1'*40,
                'source_digest':self.s.analysis(ROOT).content_digest(ROOT),
                'planned_case_ids':[case['id']],'completed_case_count':1,'cases':[row],
                'vendor_model_cases':0,'bench_measurements':0}
        (out/'results.json').write_text(json.dumps(report))
        return case,report

    def test_complete_synthetic_single_case_contract_verifies_but_not_qualifies(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);case,_=self.fixture(out)
            with patch.object(self.m,'expected_cases',return_value=[case]):
                r=self.m.verify(out,ROOT,'1'*40)
            self.assertEqual(r['integrity'],'VERIFIED_NOT_QUALIFIED')
            self.assertFalse(r['layout_allowed'])

    def test_subset_rejected_against_real_matrix(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);self.fixture(out)
            with self.assertRaisesRegex(ValueError,'matrix'):self.m.verify(out,ROOT)

    def test_incomplete_stale_dirty_and_wrong_sha_rejected(self):
        for key,value in [('status','RUNNING'),('source_digest','0'*64),
                          ('source_worktree_dirty',True),('completed_case_count',0),
                          ('layout_allowed',True),('source_commit','2'*40)]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as t:
                out=Path(t);case,r=self.fixture(out);r[key]=value
                (out/'results.json').write_text(json.dumps(r))
                with patch.object(self.m,'expected_cases',return_value=[case]):
                    with self.assertRaises(ValueError):self.m.verify(out,ROOT,'1'*40)

    def test_altered_or_missing_artifacts_rejected(self):
        for name in ['bench.cir','ngspice.cir','process.txt','ngspice.log','waveform.dat']:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as t:
                out=Path(t);case,r=self.fixture(out)
                (out/case['id']/name).write_text('ALTERED')
                with patch.object(self.m,'expected_cases',return_value=[case]):
                    with self.assertRaises(ValueError):self.m.verify(out,ROOT)

    def test_json_measurements_cannot_disagree_with_raw_log(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);case,r=self.fixture(out)
            r['cases'][0]['measured']['output_mean']+=.01
            (out/'results.json').write_text(json.dumps(r))
            with patch.object(self.m,'expected_cases',return_value=[case]):
                with self.assertRaisesRegex(ValueError,'measures'):self.m.verify(out,ROOT)

    def test_unexpected_artifact_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);case,r=self.fixture(out)
            r['cases'][0]['artifact_sha256']['../outside']='0'*64
            (out/'results.json').write_text(json.dumps(r))
            with patch.object(self.m,'expected_cases',return_value=[case]):
                with self.assertRaises(ValueError):self.m.verify(out,ROOT)


if __name__=='__main__':unittest.main()
