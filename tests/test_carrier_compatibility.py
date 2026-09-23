"""Synthetic SoM fixtures test plumbing only; none represents a vendor module."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def fixture(root, api, names=('J1', 'J2', 'J3'), contacts_per_connector=None):
    """Create an isolated fake binding from existing logical signals, not vendor pin claims."""
    for dirname in ('hardware', 'tools', 'bom', 'references'):
        shutil.copytree(ROOT / dirname, root / dirname, ignore=shutil.ignore_patterns('__pycache__'))
    d, p, phy, assignments = api.load(root, 'axu2cgb')
    lookup = {(r['connector'], r['pin']): r for r in phy}
    physical, bound = [], []
    count = (len(assignments) + len(names) - 1) // len(names)
    for index, a in enumerate(assignments):
        conn = names[index // count]
        pin = str(index % count + 1)
        row = dict(lookup[(a['connector'], a['pin'])], connector=conn, pin=pin, source='SYNTHETIC_TEST_ONLY')
        physical.append(row)
        bound.append(dict(a, connector=conn, pin=pin))
    if contacts_per_connector:
        template = next(r for r in phy if r['kind'] == 'ground')
        for conn in names:
            used = sum(r['connector'] == conn for r in physical)
            for number in range(used + 1, contacts_per_connector + 1):
                physical.append(dict(template, connector=conn, pin=str(number)))
    p.update(id='zu2cg_som', status='BOUND_CANDIDATE', board_variant='SYNTHETIC_TEST_ONLY',
             vendor='TEST_FIXTURE_NOT_A_VENDOR', module='SYNTHETIC_TEST_ONLY',
             module_revision='TEST', device='TEST_ZU2CG_NOT_FOR_HARDWARE',
             power_contacts='NC_REVIEW_ONLY', physical_pinout='physical_pinout.csv',
             assignments='assignments.csv', physical_review='TEST_ONLY', timing_verified=False)
    p['physical_sha256'] = hashlib.sha256(api.csv_bytes(physical)).hexdigest()
    directory = root / 'hardware/carriers/zu2cg_som'
    (directory / 'profile.json').write_text(json.dumps(p))
    (directory / 'physical_pinout.csv').write_bytes(api.csv_bytes(physical))
    (directory / 'assignments.csv').write_bytes(api.csv_bytes(bound))
    return d, p, physical, bound


def xml_from_expected(out):
    expected = json.loads((out / 'expected_connections.json').read_text())
    doc = ET.Element('export')
    nets = ET.SubElement(doc, 'nets')
    grouped = {}
    for pin, net in expected.items():
        if net not in grouped:
            grouped[net] = ET.SubElement(nets, 'net', name=net)
        ref, number = pin.split('.')
        ET.SubElement(grouped[net], 'node', ref=ref, pin=number)
    path = out / 'synthetic_netlist.xml'
    ET.ElementTree(doc).write(path)
    return path, doc


class CarrierCompatibilityTests(unittest.TestCase):
    maxDiff = 500
    def setUp(self):
        self.api = module('revb')

    def test_bound_som_must_not_duplicate_common_connector_refs(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, self.api)
            out = root / 'build'
            self.api.generate(root, 'zu2cg_som', out)
            refs = []
            for page in out.glob('*.kicad_sch'):
                refs += re.findall(r'\(reference "([^"]+)"\)', page.read_text())
            self.assertEqual(len(refs), len(set(refs)), 'SoM physical names collide with common J1/J2/J3')

    def test_som_review_does_not_claim_axu2cgb_connectors(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, self.api)
            out = root / 'build'
            self.api.generate(root, 'zu2cg_som', out)
            pages = '\n'.join(p.read_text() for p in out.glob('*carrier*.kicad_sch'))
            self.assertNotIn('ORIGINAL AXU2CGB', pages)
            self.assertIn('SYNTHETIC_TEST_ONLY', pages)

    def test_multiple_connectors_are_not_placed_outside_sheet(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, self.api)
            out = root / 'build'
            self.api.generate(root, 'zu2cg_som', out)
            for page in out.glob('*carrier*.kicad_sch'):
                text = page.read_text()
                for match in re.finditer(r'\(symbol\s+\(lib_id "RevB:HOST_[^"]+"\)\s+\(at ([\d.]+) ([\d.]+)', text):
                    self.assertLess(float(match[1]), 390, page.name)

    def test_large_connector_page_is_sized_for_all_contacts(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, self.api, names=('J100',), contacts_per_connector=160)
            out = root / 'build'
            self.api.generate(root, 'zu2cg_som', out)
            page = next(out.glob('*carrier*.kicad_sch')).read_text()
            self.assertIn('(paper "A1")', page, '160-pin connector overflows an A3 sheet')

    def test_bound_som_netlist_uses_som_pin_rules_not_axu_power_pins(self):
        checker = module('check_revb_netlist')
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, self.api, names=('J12', 'J15'))
            out = root / 'build'
            self.api.generate(root, 'zu2cg_som', out)
            path, _ = xml_from_expected(out)
            self.assertGreater(checker.check(path, out / 'expected_connections.json',
                                             carrier='zu2cg_som', root=root), 100)

    def test_carrier_identity_must_match_selected_directory(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fixture(root, self.api)
            path = root / 'hardware/carriers/zu2cg_som/profile.json'
            data = json.loads(path.read_text())
            data['id'] = 'axu2cgb'
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'carrier|identity'):
                self.api.load(root, 'zu2cg_som')

    def test_generated_bom_covers_every_physical_component(self):
        import csv
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)
            self.api.generate(ROOT, 'axu2cgb', out)
            self.assertTrue((out / 'generated_bom.csv').is_file())
            with (out / 'generated_bom.csv').open(newline='') as handle:
                rows = list(csv.DictReader(handle))
            refs = set()
            for page in out.glob('*.kicad_sch'):
                refs.update(re.findall(r'\(reference "([^"]+)"\)', page.read_text()))
            self.assertEqual({r['reference'] for r in rows}, refs)
            self.assertEqual(len(rows), len(refs))
            self.assertTrue(any(r['dnp'] == 'true' for r in rows))

    def test_common_bom_has_no_axu_connector_reference(self):
        text = (ROOT / 'bom/revb-common.csv').read_text()
        self.assertNotIn('J12/J15', text)

    def test_unknown_contact_kind_fails_even_with_matching_digest(self):
        with tempfile.TemporaryDirectory() as t:
            d, p, physical, a = fixture(Path(t), self.api)
            physical.append(dict(physical[0], connector='RESERVE', pin='1', kind='mystery'))
            p['physical_sha256'] = hashlib.sha256(self.api.csv_bytes(physical)).hexdigest()
            with self.assertRaisesRegex(ValueError, 'kind|classification'):
                self.api.validate(d, p, physical, a)

    def test_mixed_bank_voltages_fail_even_if_each_net_matches(self):
        with tempfile.TemporaryDirectory() as t:
            d, p, physical, a = fixture(Path(t), self.api)
            for row in physical:
                row['bank_group'] = 'SAME_BANK'
            p['physical_sha256'] = hashlib.sha256(self.api.csv_bytes(physical)).hexdigest()
            with self.assertRaisesRegex(ValueError, 'bank|Bank'):
                self.api.validate(d, p, physical, a)

    def test_zero_pin_number_is_not_a_physical_binding(self):
        with tempfile.TemporaryDirectory() as t:
            d, p, physical, a = fixture(Path(t), self.api)
            physical[0]['pin'] = a[0]['pin'] = '0'
            p['physical_sha256'] = hashlib.sha256(self.api.csv_bytes(physical)).hexdigest()
            with self.assertRaisesRegex(ValueError, 'pin|contact'):
                self.api.validate(d, p, physical, a)

    def test_host_binding_checked_independently_of_generated_expectation(self):
        checker = module('check_revb_netlist')
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)
            self.api.generate(ROOT, 'axu2cgb', out)
            expected_path = out / 'expected_connections.json'
            expected = json.loads(expected_path.read_text())
            expected['J12.3'] = 'DAC_LDAC_N'
            expected_path.write_text(json.dumps(expected))
            path, _ = xml_from_expected(out)
            with self.assertRaisesRegex(ValueError, 'J12.3|carrier'):
                checker.check(path, expected_path)

    def test_converter_ground_short_not_hidden_by_generated_expectation(self):
        checker = module('check_revb_netlist')
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)
            self.api.generate(ROOT, 'axu2cgb', out)
            expected_path = out / 'expected_connections.json'
            expected = json.loads(expected_path.read_text())
            expected['U20.10'] = '1V8_D'
            expected_path.write_text(json.dumps(expected))
            path, _ = xml_from_expected(out)
            with self.assertRaisesRegex(ValueError, 'U20.10|ground|converter'):
                checker.check(path, expected_path)

    def test_missing_feedback_pins_cannot_pass_by_none_equality(self):
        checker = module('check_revb_netlist')
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)
            self.api.generate(ROOT, 'axu2cgb', out)
            expected_path = out / 'expected_connections.json'
            expected = json.loads(expected_path.read_text())
            for pin in ('U20.20', 'U20.22'):
                expected.pop(pin)
            expected_path.write_text(json.dumps(expected))
            path, _ = xml_from_expected(out)
            with self.assertRaisesRegex(ValueError, 'U20|feedback'):
                checker.check(path, expected_path)

    def test_dnc_short_rejected_even_if_not_in_generated_expectation(self):
        checker = module('check_revb_netlist')
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)
            self.api.generate(ROOT, 'axu2cgb', out)
            expected_path = out / 'expected_connections.json'
            path, doc = xml_from_expected(out)
            net = doc.find("./nets/net[@name='GND']")
            ET.SubElement(net, 'node', ref='U20', pin='28')
            ET.ElementTree(doc).write(path)
            with self.assertRaisesRegex(ValueError, 'DNC|NC|U20.28'):
                checker.check(path, expected_path)


if __name__ == '__main__':
    unittest.main()
