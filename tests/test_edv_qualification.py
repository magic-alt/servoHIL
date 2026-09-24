"""Selection tools must not confuse catalog screening with hardware approval."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def module(name):
    path=ROOT/'sim/power'/(name+'.py')
    spec=importlib.util.spec_from_file_location('edv_'+name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class ComponentScreening(unittest.TestCase):
    def test_magnetic_selection_covers_all_five_native_inductors(self):
        r=module('qualification').report(ROOT)
        self.assertEqual({x['reference'] for x in r['magnetics']},{'L201','L202','L203','L301','L302'})
        self.assertTrue(all(x['part_number'] and x['source_url'].startswith('https://www.coilcraft.com/') for x in r['magnetics']))
        self.assertTrue(all(x['qualification']=='NOT_QUALIFIED' for x in r['magnetics']))
    def test_dcr_temperature_and_rms_loss(self):
        m=module('qualification')
        self.assertAlmostEqual(m.copper_loss(.5,.045,125),.5**2*.045*(1+.00393*100))
    def test_mlcc_no_curve_no_pass(self):
        self.assertEqual(module('qualification').curve_retention(None,6.2,'MPN'),'BLOCKED_MISSING_CURVE')
    def test_curve_rejects_mpn_mismatch(self):
        with self.assertRaises(ValueError):
            module('qualification').curve_retention({'part_number':'A','points':[[0,1],[10,.5]]},6,'B')
    def test_curve_must_not_extrapolate(self):
        with self.assertRaises(ValueError):
            module('qualification').curve_retention({'part_number':'A','points':[[0,1],[5,.8]]},6,'A')
    def test_curve_interpolation(self):
        self.assertAlmostEqual(module('qualification').curve_retention({'part_number':'A','points':[[0,1],[10,.5]]},6,'A'),.7)

class VendorBenchPreparation(unittest.TestCase):
    def test_pin_order_is_read_from_vendor_symbol_not_package_numbers(self):
        text='SYMATTR Prefix X\nSYMATTR Value LT3045\nPIN 0 0 NONE 0\nPINATTR PinName OUT\nPINATTR SpiceOrder 2\nPIN 0 0 NONE 0\nPINATTR PinName IN\nPINATTR SpiceOrder 1\n'
        p=module('vendor_ltspice').parse_symbol(text,'LT3045')
        self.assertEqual(p,['IN','OUT'])
    def test_duplicate_or_missing_spice_order_rejected(self):
        text='SYMATTR Prefix X\nSYMATTR Value LT3045\nPIN 0 0 NONE 0\nPINATTR PinName IN\nPINATTR SpiceOrder 2\n'
        with self.assertRaises(ValueError): module('vendor_ltspice').parse_symbol(text,'LT3045')
    def test_wrong_vendor_model_name_rejected(self):
        text='SYMATTR Prefix X\nSYMATTR Value LT3045-1\nPIN 0 0 NONE 0\nPINATTR PinName IN\nPINATTR SpiceOrder 1\n'
        with self.assertRaises(ValueError): module('vendor_ltspice').parse_symbol(text,'LT3045')
    def test_missing_vendor_files_produce_no_fake_model(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'generated'
            with self.assertRaises((ValueError,FileNotFoundError)):
                module('vendor_ltspice').prepare(ROOT,'LT3045',Path(t)/'missing.asy',Path(t)/'missing.lib',out)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
