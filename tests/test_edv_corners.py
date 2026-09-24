"""Corner coverage tests: native changes and model limitations must be visible."""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
from test_edv import load_analysis, ROOT
from test_edv_qualification import module


class CornerCoverage(unittest.TestCase):
    def test_second_parallel_capacitor_changes_analytical_result(self):
        a=load_analysis(); before=a.build_report(ROOT)
        values=a.native_values(ROOT); values['C214']='10uF / 16V X7R, 1210'
        with patch.object(a,'native_values',return_value=values):
            after=a.build_report(ROOT)
        self.assertAlmostEqual(after['mlcc']['buck_6v2']['unbiased_derated_f'] /
                               before['mlcc']['buck_6v2']['unbiased_derated_f'],32/44)

    def test_all_power_capacitor_banks_are_bound_individually(self):
        banks=load_analysis().build_report(ROOT)['mlcc']
        self.assertEqual(len(banks),9)
        refs={ref for bank in banks.values() for ref in bank['references']}
        self.assertTrue({'C105','C213','C214','C224','C234','C244','C264',
                         'C410','C414','C415','C423','C424'} <= refs)
        self.assertIsNone(banks['cuk_transfer']['target_f'])
        self.assertTrue(all(bank['status'].startswith('BLOCKED') for bank in banks.values()))

    def test_cuk_light_load_rejects_ccm_stress_as_guarantee(self):
        a=load_analysis()
        light=a.cuk_stress(15,6.24,10e-6,10e-6,2e6,.075,.5,.8)
        heavy=a.cuk_stress(8,6.24,10e-6,10e-6,2e6,.30,.5,.8)
        self.assertLess(light.get('switch_valley_a',1),0)
        self.assertFalse(light['ccm_consistent'])
        self.assertTrue(heavy['ccm_consistent'])
        self.assertFalse(light['stress_is_guaranteed_bound'])

    def test_cuk_individual_current_zero_is_not_itself_a_diode_dcm_test(self):
        # Unequal inductors: one current may reverse while diode sum stays positive.
        r=load_analysis().cuk_stress(8,6.24,3e-6,100e-6,2e6,.30,.5,.8)
        self.assertLess(r.get('lin_valley_a',1),0)
        self.assertGreater(r['switch_valley_a'],0)
        self.assertTrue(r['ccm_consistent'])

    def test_cuk_bounds_include_resistors_bias_and_line_regulation(self):
        a=load_analysis(); r=a.build_report(ROOT); c=r['cuk']
        ideal_lo,ideal_hi=a.divider_limits(.78,.82,1e6,147e3,.001)
        self.assertLess(c.get('magnitude_limits_v',[100,0])[0],ideal_lo)
        self.assertGreater(c['magnitude_limits_v'][1],ideal_hi)
        self.assertEqual(c['load_fractions'],[.5,1.0])
        self.assertGreater(c['ccm_invalid_case_count'],0)
        self.assertIn('CUK_CCM_MODEL_LIMIT',r['blocker_ids'])
        self.assertFalse(c['stress_is_guaranteed_bound'])

    def test_thermal_over_limit_is_explicit_not_hidden_in_rows(self):
        r=load_analysis().build_report(ROOT)
        self.assertIn('THERMAL_SENSITIVITY_OVER_DESIGN_LIMIT',r['blocker_ids'])
        summary={row['device']:row for row in r['thermal_summary']}
        self.assertLess(summary['U201']['margin_c'],0)
        self.assertEqual(summary['U201']['status'],'FAIL_ASSUMED_THERMAL_CORNER')
        self.assertFalse(r['layout_allowed'])

    def test_parser_changes_invalidate_source_digest(self):
        a=load_analysis()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            shutil.copytree(ROOT/a.NATIVE,root/a.NATIVE)
            shutil.copytree(ROOT/'sim',root/'sim',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'tools').mkdir()
            parser=root/'tools/kicad_sexpr.py'
            shutil.copy2(ROOT/'tools/kicad_sexpr.py',parser)
            before=a.content_digest(root)
            parser.write_text(parser.read_text()+'\n# parser changed\n')
            self.assertNotEqual(before,a.content_digest(root))

    def test_selection_exposes_cuk_model_validity(self):
        rows=module('qualification').report(ROOT)['magnetics']
        cuk=[r for r in rows if r['reference'] in ('L301','L302')]
        self.assertTrue(all(r.get('stress_model_status')=='CCM_NOT_VALID_ALL_CORNERS' for r in cuk))
        self.assertTrue(all(r['qualification']=='NOT_QUALIFIED' for r in cuk))


if __name__=='__main__':unittest.main()
