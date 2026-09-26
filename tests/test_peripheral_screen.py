"""Native-value incremental IO electrical screening, not hardware qualification."""
from pathlib import Path
import importlib.util
import math
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'sim/peripherals/screen.py'

def load():
    spec=importlib.util.spec_from_file_location('peripheral_screen',MODULE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class PeripheralScreenTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(),'missing native peripheral electrical screen')
        self.s=load()

    def test_report_cannot_authorize_layout(self):
        r=self.s.build_report()
        self.assertEqual(r['qualification'],'BLOCKED')
        self.assertFalse(r['layout_allowed'])
        self.assertIn('ACTUAL_DUT_ADAPTER_INHIBIT',r['blockers'])
        self.assertEqual(r['physical_tests'],'NOT_RUN')
        self.assertIn('PARTIAL_POWER_AND_BACKFEED',r['physical_evidence_required'])
        self.assertIn('PHY_LOADED_DYNAMIC_AND_FAULT_THERMAL',r['physical_evidence_required'])
        self.assertIn('AON_SAFETY_LOAD_AND_THERMAL',r['physical_evidence_required'])

    def test_adc_supply_screen_uses_actual_regulator_values(self):
        r=self.s.build_report()
        self.assertAlmostEqual(r['adc']['avcc_v'][0],4.8833098)
        self.assertTrue(r['adc']['static_supply_screen_pass'])
        self.assertEqual(len(r['adc']['rc_channels']),8)

    def test_every_input_rc_component_is_native_bound(self):
        original=self.s.power.native_values(ROOT)
        with patch.object(self.s.power,'native_values',return_value=dict(original,R852='200')):
            r=self.s.build_report()
        self.assertAlmostEqual(r['adc']['rc_channels'][1]['external_rc_pole_hz'],1/(2*math.pi*300e-9))
        self.assertAlmostEqual(r['adc']['rc_channels'][0]['external_rc_pole_hz'],1/(2*math.pi*200e-9))

    def test_series_resistance_has_visible_uncalibrated_error(self):
        ch=self.s.build_report()['adc']['rc_channels'][0]
        self.assertGreater(ch['dc_gain_loss_ppm_screen'],99)
        self.assertGreater(ch['positive_endpoint_error_lsb_screen'],3)
        self.assertLess(ch['nyquist_500khz_attenuation_db'],0)
        self.assertGreater(ch['external_full_step_half_lsb_s'],2e-6)

    def test_loaded_driver_budget_is_not_quiescent_current(self):
        r=self.s.build_report()
        self.assertEqual(len(r['phy']['drivers']),5)
        self.assertGreater(r['phy']['all_enabled_resistive_load_screen_a'],.3)
        self.assertGreater(r['phy']['new_3v3_provisional_allocation_a'],.64)

    def test_smaller_termination_increases_required_budget(self):
        original=self.s.power.native_values(ROOT)
        old=self.s.build_report()['phy']['drivers'][0]
        with patch.object(self.s.power,'native_values',return_value=dict(original,R950='60')):
            new=self.s.build_report()['phy']['drivers'][0]
        self.assertGreater(new['loaded_current_screen_a'],old['loaded_current_screen_a'])

    def test_power_edv_loads_include_new_peripherals(self):
        r=self.s.build_report()
        self.assertTrue(r['power_budget_allocated'])
        self.assertGreaterEqual(r['allocated_loads_a']['3V3_D'],.7)
        self.assertGreaterEqual(r['allocated_loads_a']['+5V0_DAC'],.25)
        self.assertGreaterEqual(r['allocated_loads_a']['6V2_PRE'],.55)
        self.assertGreaterEqual(r['allocated_loads_a']['1V8_D'],.32)

    def test_wrong_part_does_not_reuse_device_bounds(self):
        values=self.s.power.native_values(ROOT)
        with patch.object(self.s.power,'native_values',return_value=dict(values,U801='AD7606')):
            with self.assertRaises(ValueError):self.s.build_report()

    def test_invalid_physical_parameters_fail(self):
        for value in (0,-1,math.nan,math.inf):
            with self.assertRaises(ValueError):self.s.rc_screen(value,100,1e-9)
        with self.assertRaises(ValueError):self.s.driver_screen(3.3,0)

if __name__=='__main__':unittest.main()
