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
    def test_reviewed_component_deltas_are_exact_and_narrow(self):
        from check_native_safety import REVIEWED_COMPONENT_DELTAS
        expected = {
            ref: {
                'value': 'AD3542RBCPZ16',
                'footprint': 'Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R',
            }
            for ref in ('U20', 'U21', 'U22', 'U23')
        }
        expected['C105'] = {
            'value': '47uF / 35V X7R / TDK C5750X7R1V476M230KC',
            'footprint': 'Capacitor_SMD:TDK_C5750X7R1V476M230KC',
        }
        expected['J101'] = {
            'value': 'Phoenix MSTBA 2,5/2-G-5,08 / 1757242 / 9-15V INPUT',
            'footprint': 'Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_2-G-5,08_1x02_P5.08mm_Horizontal',
        }
        expected['SW101'] = {
            'value': 'PTS645SM43SMTR92 LFS / POWER RESET / SPST-NO',
            'footprint': 'Button_Switch_SMD:SW_Push_PTS645SM43SMTR92',
        }
        expected['J5'] = {
            'value': 'Phoenix MC 1,5/10-G-3,5 / 1844294 / AO0..AO7+2GND',
            'footprint': 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_10-G-3.5_1x10_P3.50mm_Horizontal',
        }
        self.assertEqual(REVIEWED_COMPONENT_DELTAS, expected)

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
    def test_mechanical_layout_deltas_reject_generic_or_wrong_parts(self):
        import tempfile
        import xml.etree.ElementTree as ET
        from check_native_safety import check
        source = os.environ['NATIVE_NETLIST']
        cases = (
            ('J101', '9-15V INPUT', 'Connector_Generic:Conn_01x02'),
            ('SW101', 'POWER RESET', 'Button_Switch_SMD:SW_Push'),
            ('J5', '8-AO DUT interface', 'Connector_Generic:Conn_01x10'),
        )
        for ref, bad_value, bad_footprint in cases:
            with self.subTest(ref=ref), tempfile.TemporaryDirectory() as tmp:
                tree = ET.parse(source)
                comp = next(x for x in tree.findall('./components/comp') if x.get('ref') == ref)
                comp.find('value').text = bad_value
                comp.find('footprint').text = bad_footprint
                path = Path(tmp) / ('bad-' + ref + '.xml')
                tree.write(path)
                with self.assertRaisesRegex(ValueError, 'component/value/footprint changed'):
                    check(path)

    @unittest.skipUnless(os.environ.get('NATIVE_NETLIST'), 'requires actual native KiCad export')
    def test_new_safety_connectors_are_exact_parts(self):
        from check_native_safety import PARTS
        self.assertEqual(
            PARTS['J501'],
            {
                'value': 'Phoenix MC 1,5/2-G-3,5 / 1844210 / 3.3V DRY CONTACT ONLY',
                'footprint': 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_2-G-3.5_1x02_P3.50mm_Horizontal',
            },
        )
        self.assertEqual(
            PARTS['J701'],
            {
                'value': 'Molex Micro-Fit 3.0 43045-0212 / DUT PERMIT FLOATING NO',
                'footprint': 'Connector_Molex:Molex_Micro-Fit_3.0_43045-0212_2x01_P3.00mm_Vertical',
            },
        )

    @unittest.skipUnless(os.environ.get('NATIVE_NETLIST'), 'requires actual native KiCad export')
    def test_c105_delta_rejects_generic_or_wrong_part(self):
        import tempfile
        import xml.etree.ElementTree as ET
        from check_native_safety import check
        source = os.environ['NATIVE_NETLIST']
        for bad_value, bad_footprint in (
            ('47uF / 35V X7R / TDK C5750X7R1V476M230KC', 'Capacitor_SMD:C_2220_5750Metric'),
            ('47uF / 35V X7R', 'Capacitor_SMD:TDK_C5750X7R1V476M230KC'),
        ):
            with self.subTest(value=bad_value, footprint=bad_footprint), tempfile.TemporaryDirectory() as tmp:
                tree = ET.parse(source)
                comp = next(x for x in tree.findall('./components/comp') if x.get('ref') == 'C105')
                comp.find('value').text = bad_value
                comp.find('footprint').text = bad_footprint
                path = Path(tmp) / 'bad-c105.xml'
                tree.write(path)
                with self.assertRaisesRegex(ValueError, 'component/value/footprint changed'):
                    check(path)

    @unittest.skipUnless(os.environ.get('NATIVE_NETLIST'), 'requires actual native KiCad export')
    def test_ad3542r_delta_rejects_generic_or_wrong_footprint(self):
        import tempfile
        import xml.etree.ElementTree as ET
        from check_native_safety import check
        source = os.environ['NATIVE_NETLIST']
        for ref, bad_value, bad_footprint in (
            ('U20', 'AD3542RBCPZ16', 'Package_DFN_QFN:QFN-28-1EP_4x4mm_P0.4mm'),
            ('U21', 'AD3542R', 'Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R'),
        ):
            with self.subTest(ref=ref), tempfile.TemporaryDirectory() as tmp:
                tree = ET.parse(source)
                comp = next(x for x in tree.findall('./components/comp') if x.get('ref') == ref)
                comp.find('value').text = bad_value
                comp.find('footprint').text = bad_footprint
                path = Path(tmp) / 'bad-ad3542r.xml'
                tree.write(path)
                with self.assertRaisesRegex(ValueError, 'component/value/footprint changed'):
                    check(path)

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
