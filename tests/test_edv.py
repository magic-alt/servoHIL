"""Electrical verification regression; no hardware qualification inferred."""
import importlib.util
import math
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load_analysis():
    spec=importlib.util.spec_from_file_location('edv_analysis',ROOT/'sim/power/analysis.py')
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

class ElectricalCalculations(unittest.TestCase):
    def setUp(self): self.a=load_analysis()
    def test_voltage_uses_actual_feedback_ratio(self):
        self.assertAlmostEqual(self.a.divider(.8,67300,10000),6.184)
    def test_full_condition_set_current_exposes_dac_span_risk(self):
        low,high=self.a.ldo_limits(52000,.001,98e-6,102e-6,.002)
        self.assertLess(low,5.2)
        self.assertGreater(high,5.3)
        self.assertGreater(2*high,10.6)
    def test_buck_inductor_rms_includes_reverse_current_ripple(self):
        r=self.a.buck_stress(15,1.792,4.7e-6*.8,450000,.30)
        self.assertLess(r['valley_a'],0)
        self.assertGreater(r['rms_a'],.30)
    def test_invalid_physical_inputs_fail(self):
        for v in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError): self.a.buck_stress(15,3.3,v,500000,.3)
        with self.assertRaises(ValueError): self.a.divider(.8,10000,0)
    def test_cuk_checks_sum_current_not_just_output_current(self):
        r=self.a.cuk_stress(8,6.242,10e-6,10e-6,2e6,.12,.5,.8)
        self.assertGreater(r['switch_peak_a'],r['output_average_a'])
        self.assertAlmostEqual(r['transfer_v'],14.742)
    def test_mlcc_missing_dc_bias_evidence_is_not_pass(self):
        r=self.a.mlcc_screen(22e-6,2,.1,.15,.03,20e-6,None)
        self.assertEqual(r['status'],'BLOCKED_DC_BIAS_EVIDENCE')
        self.assertGreater(r['required_bias_retention'],.60)
    def test_mlcc_derating_combines_all_factors(self):
        r=self.a.mlcc_screen(22e-6,2,.1,.15,.03,20e-6,.6)
        self.assertEqual(r['status'],'FAIL_ASSUMED_RETENTION')
        self.assertAlmostEqual(r['effective_f'],44e-6*.9*.85*.97*.6)
    def test_thermal_uses_input_ground_current(self):
        self.assertAlmostEqual(self.a.ldo_power(6.184,4.99,.2,.025),(6.184-4.99)*.2+6.184*.025)
    def test_native_binding_reads_real_values(self):
        v=self.a.native_values(ROOT)
        self.assertAlmostEqual(self.a.numeric(v['R210']),67300)
        self.assertAlmostEqual(self.a.numeric(v['L201']),10e-6)
        self.assertAlmostEqual(self.a.numeric(v['R420']),52000)
    def test_report_cannot_authorize_layout(self):
        r=self.a.build_report(ROOT)
        self.assertFalse(r['layout_allowed'])
        self.assertIn('DAC_SUPPLY_FULL_CONDITION',r['blocker_ids'])
        self.assertEqual(r['qualification'],'BLOCKED')
    def test_numeric_parser_understands_engineering_prefix_case(self):
        self.assertEqual(self.a.numeric('1M 0.1%'),1e6)
        self.assertEqual(self.a.numeric('499R / 300mA nominal'),499)
        with self.assertRaises(ValueError):self.a.numeric('DNP C0G')

if __name__=='__main__':unittest.main()
