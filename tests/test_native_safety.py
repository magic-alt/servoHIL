"""Independent device-pin and frozen-old-wiring safety regression."""
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from kicad_sexpr import parse, items, one, walk
NATIVE = ROOT / 'hardware/kicad/revB/axu2cgb_expansion'

class NativeSafetySourceTests(unittest.TestCase):
    def test_real_watchdog_and_permit_sheets_exist(self):
        root = parse((NATIVE/'servohil_io_revB.kicad_sch').read_text())
        names = {str(p[2]) for s in items(root, 'sheet') for p in items(s, 'property') if p[1]=='Sheetfile'}
        for name in ('50_watchdog_interlock.kicad_sch', '60_dut_permit.kicad_sch'):
            self.assertIn(name, names)
            self.assertTrue((NATIVE/name).is_file())

    def test_dac_to_dut_connector_no_longer_bypasses_disconnect(self):
        import json
        mapping = json.loads((NATIVE/'expected_connections.json').read_text())
        for n in range(8):
            self.assertEqual(mapping[f'J5.{n+1}'], f'DUT_AO{n}')

    def test_safety_native_has_real_components_and_editable_values(self):
        found = {}
        for name in ('50_watchdog_interlock', '06_analog_outputs', '60_dut_permit'):
            path = NATIVE/(name+'.kicad_sch')
            self.assertTrue(path.is_file(), str(path))
            tree = parse(path.read_text())
            for symbol in items(tree,'symbol'):
                props = {str(p[1]):p for p in items(symbol,'property')}
                ref = str(props['Reference'][2])
                if ref.startswith('#'):continue
                found[ref] = str(props['Value'][2])
                self.assertNotIn('hide', one(props['Value'],'effects',[]), ref)
        expected = {'U501':'TPS3430DRCR','U502':'TPS3808G33DBVR','U503':'TPS3808G33DBVR',
                    'U506':'SN74LVC1G74DCTR','U507':'SN74LVC1G74DCTR','U601':'ADG5412FBRUZ',
                    'U602':'ADG5412FBRUZ','U701':'AQY212GS','Q701':'MMBT3904'}
        for ref,value in expected.items():
            self.assertEqual(found.get(ref),value,ref)

class NativeSafetyNetlistTests(unittest.TestCase):
    def test_previous_complete_native_board_cannot_pass_new_safety_contract(self):
        from check_native_safety import check, BASELINE
        with self.assertRaisesRegex(ValueError,'component set'):
            check(BASELINE)

    @unittest.skipUnless(os.environ.get('NATIVE_NETLIST'), 'requires actual native KiCad export')
    def test_actual_native_safety_and_frozen_existing_wiring(self):
        from check_native_safety import check
        self.assertEqual(check(os.environ['NATIVE_NETLIST'])['new_components'],47)

    @unittest.skipUnless(os.environ.get('NATIVE_NETLIST'), 'requires actual native KiCad export')
    def test_actual_netlist_mutations_rejected(self):
        import tempfile
        import xml.etree.ElementTree as ET
        from check_native_safety import check
        source=os.environ['NATIVE_NETLIST']
        cases=[('U501','3','GND'),('U501','8','RAILS_OK'),('U503','1','WD_CLEAR_N'),
               ('U506','6','RAILS_OK'),('U507','2','3V3_AON'),('U601','3','AO0'),
               ('U601','4','+5V2_PVDD'),('J5','1','AO0'),('U701','3','GND'),
               ('Q701','2','PERMIT_LED_K'),('R702','1','HIL_ARM')]
        for ref,pin,name in cases:
            with self.subTest(ref=ref,pin=pin,net=name), tempfile.TemporaryDirectory() as tmp:
                tree=ET.parse(source)
                target=next(n for n in tree.findall('./nets/net') if n.get('name').rsplit('/',1)[-1]==name)
                old=next(n for n in tree.findall('./nets/net') if any(x.get('ref')==ref and x.get('pin')==pin for x in n.findall('node')))
                node=next(x for x in old.findall('node') if x.get('ref')==ref and x.get('pin')==pin)
                old.remove(node);target.append(node)
                path=Path(tmp)/'bad.xml';tree.write(path)
                with self.assertRaises(ValueError):check(path)

if __name__ == '__main__':unittest.main()
