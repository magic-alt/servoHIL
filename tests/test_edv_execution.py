"""Execution evidence must be fresh, attributable and numerically trustworthy."""
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_edv_spice import engine, ROOT

NGSPICE = shutil.which(os.environ.get('NGSPICE', 'ngspice'))


class ExecutionIntegrity(unittest.TestCase):
    def setUp(self):
        self.s = engine()
        self.case = self.s.make_cases(ROOT)[0]

    def test_empty_matrix_cannot_claim_execution(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                self.s.run_cases([], Path(t)/'run', executable=sys.executable)

    def test_duplicate_case_ids_rejected_before_simulator(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                self.s.run_cases([self.case, self.case], Path(t)/'run', executable=sys.executable)
            self.assertFalse((Path(t)/'run').exists())

    def test_case_identifier_cannot_escape_output_directory(self):
        for name in ['../escape', '/absolute', 'a/b', r'a\b', '.', '..']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as t:
                case = dict(self.case, id=name)
                with self.assertRaises(ValueError):
                    self.s.run_cases([case], Path(t)/'run', executable=sys.executable)
                self.assertFalse((Path(t)/'run').exists())

    def test_existing_output_is_never_reused(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)/'run'; out.mkdir()
            previous = '{"status":"EXECUTED_NOT_QUALIFIED"}\n'
            (out/'results.json').write_text(previous)
            with self.assertRaises(FileExistsError):
                self.s.run_cases([self.case], out, executable=sys.executable)
            self.assertEqual((out/'results.json').read_text(), previous)

    def test_failed_simulation_has_explicit_manifest(self):
        version = subprocess.CompletedProcess([], 0, 'SYNTHETIC RUNNER TEST', '')
        failed = subprocess.CompletedProcess([], 1, '', 'SYNTHETIC FAILURE')
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)/'run'
            with patch.object(self.s.subprocess, 'check_output', return_value='SYNTHETIC_SHA'), \
                    patch.object(self.s.subprocess, 'run', side_effect=[version, failed]):
                with self.assertRaises(RuntimeError):
                    self.s.run_cases([self.case], out, executable=sys.executable)
            self.assertTrue((out/'results.json').is_file(), 'failure lost its evidence manifest')
            report = json.loads((out/'results.json').read_text())
            self.assertEqual(report['status'], 'FAILED')
            self.assertEqual(report['failed_case'], self.case['id'])
            self.assertEqual(report['completed_case_count'], 0)
            self.assertFalse(report['layout_allowed'])
            self.assertTrue((out/self.case['id']/'process.txt').is_file())


@unittest.skipUnless(NGSPICE, 'ngspice unavailable: numerical regression NOT RUN')
class RealClockRegression(unittest.TestCase):
    def test_imposed_duty_and_timestep_convergence(self):
        s = engine(); case = s.make_cases(ROOT)[0]
        fine = copy.deepcopy(case); fine['id'] += '_half_step'
        def halve(match):
            return match[1] + str(float(match[2])/2)
        fine['deck'] = re.sub(r'(?m)^(\.tran\s+\S+\s+\S+\s+\S+\s+)(\S+)$', halve, fine['deck'])
        with tempfile.TemporaryDirectory() as t:
            try:
                r = s.run_cases([case, fine], Path(t)/'run', executable=NGSPICE)
            except ValueError as exc:
                self.fail('real switching-clock numerical regression: '+str(exc))
            coarse, refined = r['cases']
            for row in r['cases']:
                self.assertTrue(row['assessment']['solver_gate_ok'])
                self.assertFalse(row['assessment']['layout_allowed'])
            for key in ['output_mean', 'current_peak']:
                self.assertLess(abs(coarse['measured'][key]/refined['measured'][key]-1), .01, key)
            self.assertEqual(r['status'], 'EXECUTED_NOT_QUALIFIED')


if __name__ == '__main__':
    unittest.main()
