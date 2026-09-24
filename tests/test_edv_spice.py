"""No vendor or hardware PASS may be inferred from portable screening decks."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def engine():
    spec=importlib.util.spec_from_file_location('edv_spice',ROOT/'sim/power/spice.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class SpiceContract(unittest.TestCase):
    def setUp(self): self.s=engine()
    def test_measure_parser_requires_all_requested_values(self):
        with self.assertRaises(ValueError):self.s.parse_measures('output_mean = 5.2', ['output_mean','current_peak'])
    def test_nonfinite_measure_rejected(self):
        for bad in ['NaN','inf','1e999']:
            with self.assertRaises(ValueError):self.s.parse_measures('output_mean = '+bad,['output_mean'])
    def test_measure_failure_cannot_hide_behind_exit_zero(self):
        with self.assertRaises(ValueError):self.s.parse_measures('Error: measure startup_s failed!\noutput_mean = 5.2',['output_mean'])
    def test_real_ngspice_format(self):
        r=self.s.parse_measures('output_mean = 5.123456e+00\nstartup_s = 2.301e-03 targ=3e-3 trig=7e-4',['output_mean','startup_s'])
        self.assertAlmostEqual(r['startup_s'],.002301)
    def test_duplicate_measure_rejected(self):
        with self.assertRaises(ValueError):self.s.parse_measures('a = 1\na = 2',['a'])
    def test_all_cases_have_honest_fidelity_and_native_binding(self):
        cases=self.s.make_cases(ROOT)
        self.assertGreaterEqual(len(cases),20)
        self.assertEqual(len({c['id'] for c in cases}),len(cases))
        self.assertEqual({c['kind'] for c in cases},{'buck','cuk','ldo'})
        for c in cases:
            self.assertFalse(c['vendor_model'])
            self.assertTrue(c['bindings'])
            self.assertIn('NOT A VENDOR',c['deck'])
            self.assertIn('.tran',c['deck'])
            self.assertIn('.meas',c['deck'])
    def test_deck_has_actual_cuk_transfer_network(self):
        c=next(c for c in self.s.make_cases(ROOT) if c['kind']=='cuk')
        for token in ['Linput','Ctransfer','Loutput','Dfly']:
            self.assertIn(token,c['deck'])
    def test_unavailable_simulator_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(FileNotFoundError):
                self.s.run_cases(self.s.make_cases(ROOT)[:1],Path(t),executable='no-such-ngspice-edv-123',root=ROOT)
    def test_successful_measurement_is_not_electrical_pass(self):
        c=self.s.make_cases(ROOT)[0]
        m={key:1.0 for key in c['measures']}
        r=self.s.assess(c,m)
        self.assertEqual(r['qualification'],'NOT_QUALIFIED')
        self.assertFalse(r['layout_allowed'])

if __name__=='__main__':unittest.main()
