"""Read-only drawing regressions: a local label is not a continuous wire.

These geometry checks supplement, never replace, native KiCad netlist/ERC.
The contract is the pre-existing reviewed pin assignment, not a generator's
output. In particular, removing a wire and adding same-name labels must fail.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from kicad_sexpr import parse, items, one, walk, expr
NATIVE = ROOT / 'archive/revA/snapshot/hardware/kicad/revA'
CONTRACT = Path(__file__).with_name('remaining_pages_pin_contract.json')
SHEET = '03_digital_power.kicad_sch'


def point(node):
    return tuple(round(float(x), 4) for x in node[1:3])


def on_segment(p, a, b):
    return ((a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))
            or (a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])))


def terminals(tree):
    definitions = {d[1]: d for d in items(one(tree, 'lib_symbols'), 'symbol')}
    out = {}
    for symbol in items(tree, 'symbol'):
        ref = next(p[2] for p in items(symbol, 'property') if p[1] == 'Reference')
        x, y, angle = map(float, one(symbol, 'at')[1:])
        rad = math.radians(angle)
        for pin in walk(definitions[one(symbol, 'lib_id')[1]], 'pin'):
            px, py = map(float, one(pin, 'at')[1:3])
            mirror = one(symbol, 'mirror')
            if mirror and mirror[1] == 'x': py = -py
            if mirror and mirror[1] == 'y': px = -px
            out[ref + '.' + one(pin, 'number')[1]] = (
                round(x + px * math.cos(rad) - py * math.sin(rad), 4),
                round(y - px * math.sin(rad) - py * math.cos(rad), 4))
    return out


class WireGraph:
    """Orthogonal wire topology only: NO label, power-name, or net-name union."""
    def __init__(self, tree):
        self.pins = terminals(tree)
        self.segments = [tuple(point(p) for p in items(one(w, 'pts'), 'xy'))
                         for w in items(tree, 'wire')]
        points = set(self.pins.values())
        points.update(p for segment in self.segments for p in segment)
        points.update(point(one(j, 'at')) for j in items(tree, 'junction'))
        self.parent = {p: p for p in points}
        for a, b in self.segments:
            if a[0] != b[0] and a[1] != b[1]:
                raise ValueError('Nonorthogonal wire: ' + str((a, b)))
            for p in points:
                if on_segment(p, a, b): self.parent[self.find(p)] = self.find(a)

    def find(self, p):
        if self.parent[p] != p: self.parent[p] = self.find(self.parent[p])
        return self.parent[p]

    def same(self, pins):
        return len({self.find(self.pins[p]) for p in pins}) == 1


def private_groups():
    contract = json.loads(CONTRACT.read_text())['sheets'][SHEET]
    exempt = {'GND', '<NC>', '12V_PROT', '3V3_AON', '1V0_FPGA', '1V8_D', '3V3_D', '6V0_PRE'}
    groups = {}
    for ref, pins in contract.items():
        for pin, net in pins.items():
            if net not in exempt: groups.setdefault(net, []).append(ref + '.' + pin)
    return {n: p for n, p in groups.items() if len(p) > 1}


class DigitalDrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = parse((NATIVE / SHEET).read_text())
        cls.graph = WireGraph(cls.tree)

    def test_control_feedback_bootstrap_and_compensation_use_real_wires(self):
        failures = {net: pins for net, pins in private_groups().items() if not self.graph.same(pins)}
        self.assertEqual({}, failures, 'Sheet-local functional circuits are still label islands')

    def test_output_caps_dividers_and_flags_share_the_inductor_output_wire(self):
        groups = [
            ['L41.2', 'C43.1', 'R70.1', 'PWR301.1'],
            ['L42.2', 'C44.1', 'R80.1'],
            ['L43.2', 'C45.1', 'R90.1', 'PWR302.1'],
            ['L44.2', 'C46.1', 'R100.1', 'PWR303.1'],
        ]
        for pins in groups:
            with self.subTest(pins=pins): self.assertTrue(self.graph.same(pins))

    def test_input_bypass_and_ldo_are_continuously_wired(self):
        self.assertTrue(self.graph.same(['U9.1', 'U9.3', 'C40.1', 'U2.36', 'U2.22',
                                       'U2.6', 'U2.7', 'C151.1', 'C152.1', 'C153.1', 'C154.1']))
        self.assertTrue(self.graph.same(['U9.5', 'C41.1']))

    def test_no_ground_text_labels_and_explicit_ground_symbols(self):
        self.assertFalse([n for n in self.tree if isinstance(n, list) and n and
                          n[0] in ('label', 'global_label') and n[1] == 'GND'])
        self.assertGreaterEqual(sum(one(s, 'lib_id')[1] == 'power:GND'
                                    for s in items(self.tree, 'symbol')), 15)

    def test_all_connection_points_on_grid_and_inside_drawing_area(self):
        points = [(pin, p) for pin, p in self.graph.pins.items()]
        points += [('wire', p) for segment in self.graph.segments for p in segment]
        for kind in ('label', 'global_label', 'hierarchical_label', 'junction', 'no_connect'):
            points += [(kind, point(one(n, 'at'))) for n in items(self.tree, kind)]
        for name, (x, y) in points:
            with self.subTest(name=name, x=x, y=y):
                self.assertGreaterEqual(x, 12.7)
                self.assertLessEqual(x, 402.59)
                self.assertGreaterEqual(y, 12.7)
                self.assertLessEqual(y, 248.92)
                self.assertAlmostEqual(x / 1.27, round(x / 1.27), places=3)
                self.assertAlmostEqual(y / 1.27, round(y / 1.27), places=3)

    def test_wire_graph_does_not_accept_label_only_connection(self):
        t = expr('(kicad_sch (lib_symbols) (wire (pts (xy 0 0) (xy 1 0))) '
                 '(wire (pts (xy 2 0) (xy 3 0))) '
                 '(label "TEST" (at 1 0 0)) (label "TEST" (at 2 0 0)))')
        g = WireGraph(t)
        self.assertNotEqual(g.find((1.0, 0.0)), g.find((2.0, 0.0)))

    def test_symbol_library_y_axis_and_quarter_turns(self):
        # Library symbols use Cartesian Y; sheet coordinates grow downwards.
        for angle, expected in [(0, (12.0, 17.0)), (90, (7.0, 18.0)),
                                (180, (8.0, 23.0)), (270, (13.0, 22.0))]:
            t = expr('(kicad_sch (lib_symbols (symbol "Test:X" (symbol "X_1_1" '
                     '(pin passive line (at 2 3 0) (length 0) (name "P") (number "1"))))) '
                     f'(symbol (lib_id "Test:X") (at 10 20 {angle}) (property "Reference" "X1")))')
            with self.subTest(angle=angle): self.assertEqual(expected, terminals(t)['X1.1'])

    def test_wires_do_not_short_distinct_contract_nets(self):
        expected = json.loads(CONTRACT.read_text())['sheets'][SHEET]
        groups = {}
        for reference, pins in expected.items():
            for pin, net in pins.items():
                endpoint = self.graph.pins[reference + '.' + pin]
                groups.setdefault(self.graph.find(endpoint), set()).add(net)
        self.assertFalse({p: nets for p, nets in groups.items() if len(nets) > 1})

    def test_private_net_names_remain_single_annotations_not_aliases(self):
        private = set(private_groups())
        counts = {name: 0 for name in private}
        for n in items(self.tree, 'label') + items(self.tree, 'global_label') + items(self.tree, 'hierarchical_label'):
            if n[1] in private: counts[n[1]] += 1
        self.assertEqual({name: 1 for name in private}, counts)


if __name__ == '__main__':
    unittest.main(verbosity=2)
