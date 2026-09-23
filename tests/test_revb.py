"""Mutation regressions: source data -> electrical mapping, not text-presence tests."""
from pathlib import Path
import copy
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RevBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = None
        path = ROOT / 'tools/revb.py'
        if path.exists():
            spec = importlib.util.spec_from_file_location('revb', path)
            cls.api = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.api)

    def setUp(self):
        self.assertIsNotNone(self.api, 'single-SoC contract implementation missing')
        self.design, self.profile, self.physical, self.assignments = self.api.load(ROOT, 'axu2cgb')

    def validate(self):
        return self.api.validate(self.design, self.profile, self.physical, self.assignments)

    def test_64_assignments_and_one_compute_soc(self):
        result = self.validate()
        self.assertEqual(result['assigned'], {'J12': 32, 'J15': 32})
        self.assertEqual(self.design['compute_soc_count'], 1)
        self.assertEqual(self.design['programmable_devices_on_io_board'], 0)

    def test_reject_duplicate_connector_pin(self):
        self.assignments[1]['pin'] = self.assignments[0]['pin']
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.validate()

    def test_reject_duplicate_soc_ball(self):
        self.physical[3]['soc_ball'] = self.physical[2]['soc_ball']
        with self.assertRaisesRegex(ValueError, 'duplicate|digest'):
            self.validate()

    def test_power_contact_cannot_become_gpio(self):
        self.assignments[0]['pin'] = '2'
        with self.assertRaisesRegex(ValueError, 'power|GPIO'):
            self.validate()

    def test_wrong_voltage_is_rejected(self):
        self.design['signals'][0]['voltage'] = 3.3
        with self.assertRaisesRegex(ValueError, 'voltage'):
            self.validate()

    def test_missing_critical_signal_is_rejected(self):
        self.assignments.pop(0)
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.validate()

    def test_duplicate_logical_net_is_rejected(self):
        self.assignments[1]['net'] = self.assignments[0]['net']
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.validate()

    def test_hil_link_cannot_reappear(self):
        self.design['signals'][0]['net'] = 'HL_TX0'
        with self.assertRaisesRegex(ValueError, 'legacy'):
            self.validate()

    def test_second_fpga_cannot_reappear(self):
        self.design['programmable_devices_on_io_board'] = 1
        with self.assertRaisesRegex(ValueError, 'single|programmable'):
            self.validate()

    def test_som_is_supported_but_physically_unbound(self):
        d, p, phy, a = self.api.load(ROOT, 'zu2cg_som')
        result = self.api.validate(d, p, phy, a)
        self.assertEqual(result['status'], 'BLOCKED_VENDOR_BINDING')
        with self.assertRaisesRegex(ValueError, 'UNBOUND|binding'):
            self.api.generate(ROOT, 'zu2cg_som', Path(tempfile.gettempdir()) / 'forbidden-som-output')

    def test_wrong_board_variant_is_rejected(self):
        self.profile['board_variant'] = 'AXU2CGB-I'
        with self.assertRaisesRegex(ValueError, 'variant'):
            self.validate()

    def test_direction_and_port_name_validation(self):
        self.design['signals'][0]['direction'] = 'automatic'
        with self.assertRaisesRegex(ValueError, 'direction'):
            self.validate()

    def test_reject_invalid_hdl_port(self):
        self.design['signals'][0]['port'] = 'x]; exec bad'
        with self.assertRaisesRegex(ValueError, 'port'):
            self.validate()

    def test_release_is_blocked(self):
        with self.assertRaisesRegex(ValueError, 'BLOCKED'):
            self.api.check_release(ROOT, 'axu2cgb')

    def test_generation_is_deterministic(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t)/'a', Path(t)/'b'
            self.api.generate(ROOT, 'axu2cgb', a)
            self.api.generate(ROOT, 'axu2cgb', b)
            af = {p.relative_to(a):p.read_bytes() for p in a.rglob('*') if p.is_file()}
            bf = {p.relative_to(b):p.read_bytes() for p in b.rglob('*') if p.is_file()}
            self.assertEqual(af, bf)
            self.assertIn(Path('servohil_io_revB.kicad_sch'), af)
            self.assertIn(Path('carrier.xdc.preview'), af)
            self.assertNotIn(b'XC7A35T', b'\n'.join(af.values()))

    def test_xdc_uses_exact_physical_balls(self):
        with tempfile.TemporaryDirectory() as t:
            self.api.generate(ROOT, 'axu2cgb', Path(t))
            xdc=(Path(t)/'carrier.xdc.preview').read_text()
            self.assertIn('PACKAGE_PIN F7 [get_ports {dac_sclk}]', xdc)
            self.assertIn('PACKAGE_PIN A11 [get_ports {pwm_uh}]', xdc)
            self.assertIn('LVCMOS18', xdc)
            self.assertIn('LVCMOS33', xdc)
            self.assertNotIn('set_input_delay', xdc)
            self.assertNotIn('create_clock', xdc)

    def test_all_legacy_gates_are_superseded_not_pass(self):
        g=json.loads((ROOT/'hardware/revB/gates.json').read_text())
        self.assertFalse(g['layout_allowed'])
        self.assertTrue(all(v['status']=='SUPERSEDED' for v in g['legacy'].values()))
        self.assertTrue(all(v['status']!='PASS' for v in g['gates'].values()))

class EvidenceAndNetlistTests(unittest.TestCase):
    def setUp(self):
        self.root=ROOT
        spec=importlib.util.spec_from_file_location('revb_extra',ROOT/'tools/revb.py')
        self.api=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.api)

    def test_claimed_pass_without_evidence_is_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)
            for name in ['hardware','tools','bom','references']:
                shutil.copytree(ROOT/name,dst/name,ignore=shutil.ignore_patterns('__pycache__'))
            p=dst/'hardware/revB/gates.json';g=json.loads(p.read_text())
            g['layout_allowed']=True
            for v in g['gates'].values(): v.update(status='PASS',evidence='absent.json')
            p.write_text(json.dumps(g))
            with self.assertRaisesRegex(ValueError,'missing evidence'):
                self.api.check_release(dst,'axu2cgb')

    def test_evidence_changes_with_hardware_content(self):
        import shutil
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)
            for name in ['hardware','tools','bom','references']:
                shutil.copytree(ROOT/name,dst/name,ignore=shutil.ignore_patterns('__pycache__'))
            a=self.api.source_digest(dst)
            p=dst/'hardware/revB/providers.json';p.write_text(p.read_text()+'\n')
            self.assertNotEqual(a,self.api.source_digest(dst))

    def test_erc_missing_schema_fails_closed(self):
        spec=importlib.util.spec_from_file_location('erc',ROOT/'tools/check_revb_erc.py')
        erc=importlib.util.module_from_spec(spec);spec.loader.exec_module(erc)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'report.json';p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'missing'):
                erc.check(p)

    def test_real_netlist_checker_catches_pin_swap(self):
        import xml.etree.ElementTree as ET
        spec=importlib.util.spec_from_file_location('net',ROOT/'tools/check_revb_netlist.py')
        api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)
            self.api.generate(ROOT,'axu2cgb',out)
            expected=json.loads((out/'expected_connections.json').read_text())
            x=ET.Element('export');nets=ET.SubElement(x,'nets');by={}
            for pin,name in expected.items():
                if name not in by:by[name]=ET.SubElement(nets,'net',name=name)
                ref,number=pin.split('.')
                ET.SubElement(by[name],'node',ref=ref,pin=number)
            path=out/'fixture.xml';ET.ElementTree(x).write(path)
            self.assertGreater(api.check(path,out/'expected_connections.json'),100)
            for node in by['DAC_SCLK'].findall('node'):
                if node.attrib['ref']=='J12':node.set('pin','4')
            ET.ElementTree(x).write(path)
            with self.assertRaises(ValueError):api.check(path,out/'expected_connections.json')

if __name__ == '__main__':
    unittest.main()
