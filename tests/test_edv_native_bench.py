"""Regress failures exposed by real ngspice and native pin/value review."""
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from test_edv_spice import engine, ROOT

class NativeBenchBinding(unittest.TestCase):
    def test_shutdown_measure_inside_stop_time(self):
        for case in engine().make_cases(ROOT):
            stop=re.search(r'(?m)^\.tran\s+\S+\s+(\S+)',case['deck'])[1]
            end=float(stop[:-1])*1e-3 if stop.endswith('m') else float(stop)
            at=float(re.search(r'shutdown_v.*AT=(\S+)',case['deck'])[1])
            self.assertLess(at,end,case['id'])
            self.assertGreater(at,end*.95,case['id'])
    def test_set_capacitors_not_input_bypass_caps(self):
        for case in engine().make_cases(ROOT):
            if case['kind']=='ldo':
                expected='C240' if case['id'].startswith('ldo_5v0_') else 'C260' if case['id'].startswith('ldo_5v2_') else 'C420'
                self.assertIn(expected,case['bindings'])
                self.assertAlmostEqual(float(re.search(r'Cset set 0 (\S+)',case['deck'])[1]),470e-9)
    def test_cuk_transfer_value_is_native_not_hardcoded(self):
        s=engine();a=s.analysis(ROOT);values=a.native_values(ROOT)
        with patch.object(s,'analysis',return_value=a), patch.object(a,'native_values',return_value=dict(values,C410='2.2uF / test mutation')):
            case=next(c for c in s.make_cases(ROOT) if c['kind']=='cuk')
            self.assertAlmostEqual(float(re.search(r'Ctransfer sw xcap (\S+)',case['deck'])[1]),2.2e-6)
    def test_both_output_capacitors_read_independently(self):
        s=engine();a=s.analysis(ROOT);values=a.native_values(ROOT)
        with patch.object(s,'analysis',return_value=a), patch.object(a,'native_values',return_value=dict(values,C214='10uF / test mutation')):
            c=next(c for c in s.make_cases(ROOT) if c['id']=='buck_6V2_PRE_8V')
            self.assertAlmostEqual(float(re.search(r'Cout cout 0 (\S+)',c['deck'])[1]),32e-6)

if __name__=='__main__':unittest.main()
