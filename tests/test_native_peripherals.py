"""Native peripheral source and actual-KiCad miswire regressions."""
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from kicad_sexpr import parse,items,one
P=ROOT/'hardware/kicad/revB/axu2cgb_expansion'

class PeripheralSourceTests(unittest.TestCase):
    def test_real_adc_encoder_and_pwm_sheets_replace_reserved_headers(self):
        for name in ('70_adc_frontend','80_encoder_phy','03_peripheral_boundaries'):
            path=P/(name+'.kicad_sch')
            self.assertTrue(path.is_file(),str(path))
        self.assertNotIn('PHY/ADC NOT POPULATED',(P/'03_peripheral_boundaries.kicad_sch').read_text())
        root=(P/'servohil_io_revB.kicad_sch').read_text()
        self.assertIn('70_adc_frontend.kicad_sch',root)
        self.assertIn('80_encoder_phy.kicad_sch',root)

    def test_parallel_reserved_module_headers_removed_from_contract(self):
        contract=json.loads((P/'expected_connections.json').read_text())
        self.assertFalse(any(k.startswith(('J3.','J4.')) for k in contract))

    def test_new_components_have_live_values_and_bound_footprints(self):
        self.assertTrue((ROOT/'tools/native_peripheral_rules.py').is_file(), 'missing independent pin oracle')
        from native_peripheral_rules import PARTS
        actual={}
        for name in ('70_adc_frontend','80_encoder_phy','03_peripheral_boundaries'):
            path=P/(name+'.kicad_sch')
            self.assertTrue(path.is_file(),str(path))
            for s in items(parse(path.read_text()),'symbol'):
                f={str(x[1]):x for x in items(s,'property')}
                ref=str(f['Reference'][2])
                if ref.startswith('#'):continue
                self.assertNotIn(ref,actual)
                actual[ref]={'value':str(f['Value'][2]),'footprint':str(f['Footprint'][2])}
                self.assertNotIn('hide',one(f['Value'],'effects',[]))
        self.assertEqual(actual,PARTS)
        self.assertTrue(all(x['footprint'] for x in actual.values()))

    def test_all_new_anchors_stay_in_a2_review_area(self):
        for name in ('70_adc_frontend','80_encoder_phy','03_peripheral_boundaries'):
            path=P/(name+'.kicad_sch');self.assertTrue(path.is_file(),str(path))
            t=parse(path.read_text());self.assertEqual(one(t,'paper')[1],'A2')
            for obj in items(t,'symbol')+items(t,'text')+items(t,'global_label'):
                a=one(obj,'at');x,y=map(float,a[1:3])
                self.assertTrue(10<=x<=580 and 10<=y<=390,(name,x,y))

class PeripheralNetlistTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('NATIVE_NETLIST'),'requires actual KiCad XML')
    def test_actual_board_has_complete_peripheral_contract(self):
        from check_native_safety import check
        self.assertGreater(check(os.environ['NATIVE_NETLIST']).get('peripheral_components',0),100)

    @unittest.skipUnless(os.environ.get('NATIVE_NETLIST'),'requires actual KiCad XML')
    def test_miswired_peripheral_pins_are_rejected(self):
        from check_native_safety import check
        source=os.environ['NATIVE_NETLIST']
        cases=[('U801','23','3V3_D'),('U801','1','+5V2_PVDD'),
               ('U801','39','ADC_REGCAP_A'),('U801','44','GND'),
               ('U801','3','GND'),('U801','6','GND'),('U801','24','ADC_DOUT1_RAW'),
               ('U801','49','AI1_P'),('C807','1','+5V0_DAC'),
               ('U901','6','ENC0_P0_B'),('U901','3','ENC0_DIR0'),
               ('U911','1','3V3_D'),('U1001','3','RS485_DE'),
               ('U1010','2','PWM_UH'),('U1010','19','3V3_D')]
        for ref,pin,dest in cases:
            with self.subTest(ref=ref,pin=pin),tempfile.TemporaryDirectory() as tmp:
                tree=ET.parse(source)
                netlist=tree.findall('./nets/net')
                target=next(n for n in netlist if n.get('name').rsplit('/',1)[-1]==dest)
                old=next(n for n in netlist if any(v.get('ref')==ref and v.get('pin')==pin for v in n.findall('node')))
                node=next(v for v in old.findall('node') if v.get('ref')==ref and v.get('pin')==pin)
                old.remove(node);target.append(node)
                path=Path(tmp)/'bad.xml';tree.write(path)
                with self.assertRaises(ValueError):check(path)

if __name__=='__main__':unittest.main()
