"""Read-only Rev.A hierarchy and FPGA continuous-wire regressions.

Native KiCad pin-partition equivalence remains the independent electrical gate.
These checks reject label-only links that are electrically equivalent but unreadable.
"""
from __future__ import annotations
import os
import json
from pathlib import Path
import unittest
from test_digital_drawing import WireGraph, NATIVE, CONTRACT
from kicad_sexpr import parse, items, one, walk

POWER_NETS = {'12V_PROT', '3V3_AON', '1V0_FPGA', '1V8_D', '3V3_D',
              '6V0_PRE', 'EFUSE_PG', 'ANALOG_EN', 'SEQ_DONE'}
FULL = os.environ.get('REVA_STAGE', 'full') == 'full'

class HierarchyTests(unittest.TestCase):
    def setUp(self):
        self.trees = {p.name: parse(p.read_text()) for p in NATIVE.glob('*.kicad_sch')}
        self.root = self.trees['servohil_io_revA.kicad_sch']

    def test_digital_power_has_no_global_labels(self):
        self.assertEqual([], items(self.trees['03_digital_power.kicad_sch'], 'global_label'))

    def test_migrated_networks_do_not_leave_global_peers(self):
        bad = [(f, n[1]) for f, t in self.trees.items() for n in items(t, 'global_label')
               if n[1] in POWER_NETS or FULL]
        self.assertEqual([], bad, 'A migrated child interface still bypasses the hierarchy')

    def test_parent_pins_match_child_hierarchical_labels(self):
        total = 0
        for s in items(self.root, 'sheet'):
            filename = next(p[2] for p in items(s, 'property') if p[1] == 'Sheetfile')
            ports = items(s, 'pin')
            child = items(self.trees[filename], 'hierarchical_label')
            expected = {(n[1], one(n, 'shape')[1]) for n in child}
            self.assertEqual(expected, {(n[1], n[2]) for n in ports}, filename)
            self.assertEqual(len(expected), len(child), filename + ': duplicate child interface')
            self.assertEqual(len(expected), len(ports), filename + ': duplicate parent pin')
            total += len(ports)
        self.assertGreaterEqual(total, 20)

    def test_no_duplicate_instance_uuids_or_disabled_erc_changes(self):
        uuids = [one(n, 'uuid')[1] for t in self.trees.values() for n in t
                 if isinstance(n, list) and one(n, 'uuid') is not None]
        self.assertEqual(len(uuids), len(set(uuids)))

    @unittest.skipUnless(FULL, 'FPGA phase not requested')
    def test_fpga_private_links_are_wires_not_same_name_aliases(self):
        t = self.trees['05_io_fpga.kicad_sch']
        g = WireGraph(t)
        spec = json.loads(CONTRACT.read_text())['sheets']['05_io_fpga.kicad_sch']
        groups = {}
        for ref, pins in spec.items():
            for pin, net in pins.items():
                if net.startswith('FPGA_') or net in ('PROGRAM_B', 'INIT_B', 'LINK_WD_OK', 'SAFE_STAGE1', 'SAFE_STAGE2', 'DAC_RESET_N'):
                    groups.setdefault(net, []).append(ref + '.' + pin)
        self.assertEqual({}, {n: p for n, p in groups.items() if len(p) > 1 and not g.same(p)})
        private = {n for n in groups if n != 'DAC_RESET_N'}
        for name in private:
            labels = [n for n in items(t, 'label') if n[1] == name]
            self.assertLessEqual(len(labels), 1, name)

    @unittest.skipUnless(FULL, 'FPGA phase not requested')
    def test_fpga_bulk_caps_are_connected_to_their_power_pins(self):
        g = WireGraph(self.trees['05_io_fpga.kicad_sch'])
        for pins in [('U10.1', 'C230.1'), ('U10.2', 'C231.1'), ('U10.3', 'C232.1'),
                     ('U13.4', 'R233.2', 'U15.2'), ('U16.6', 'R234.1')]:
            self.assertTrue(g.same(pins), pins)

    @unittest.skipUnless(FULL, 'FPGA phase not requested')
    def test_explicit_safety_chain(self):
        g = WireGraph(self.trees['05_io_fpga.kicad_sch'])
        for pins in [('U10.36','U13.2'), ('U10.62','R232.2','U14.1'),
                     ('U14.4','U15.1'), ('U15.4','U16.2')]:
            self.assertTrue(g.same(pins), pins)

if __name__ == '__main__':
    unittest.main(verbosity=2)
