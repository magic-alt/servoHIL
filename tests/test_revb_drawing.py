"""Protect readable labels: connected nets sit outside components, not on symbols."""
from pathlib import Path
import importlib.util
import re
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class DrawingTests(unittest.TestCase):
    def test_wires_offset_net_labels_without_changing_pin_contract(self):
        spec=importlib.util.spec_from_file_location('revb_draw_test',ROOT/'tools/revb.py')
        api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
        with tempfile.TemporaryDirectory() as t:
            out=Path(t);api.generate(ROOT,'axu2cgb',out)
            text=(out/'01_carrier_interface.kicad_sch').read_text()
            self.assertIn('(wire ',text)
            # J12 pin 3 ends at x=68.58. Wire extends LEFT to x=63.5.
            label=re.search(r'\(global_label "DAC_SCLK".*?\(at ([\d.]+) ([\d.]+) (\d+)\)',text,re.S)
            self.assertIsNotNone(label)
            self.assertEqual(float(label[1]),63.5)
            self.assertEqual(label[3],'180')
            right=re.search(r'\(global_label "DAC_LDAC_N".*?\(at ([\d.]+) ([\d.]+) (\d+)\)',text,re.S)
            self.assertIsNotNone(right)
            self.assertEqual(float(right[1]),114.3)
            self.assertEqual(right[3],'0')
            self.assertNotIn('(name "VCC_3V3_BUCK4"',text)

if __name__=='__main__':unittest.main()
