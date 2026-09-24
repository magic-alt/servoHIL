"""Project-local legacy ground remains globally named GND with its original pin.

The installed KiCad library is not allowed to silently replace the archived
power_in pin with a different signature. No physical component is exempted from
native pin-partition checking.
"""
from __future__ import annotations
import copy
import hashlib
import unittest
from test_digital_drawing import NATIVE
from kicad_sexpr import parse, items, one, walk, dump

ORIGINAL_SHA256 = '2cf89eeddbeb5fa29b118c86406b7a39a4221f7a077fc8a5eb541d31015ac121'
LIB_ID = 'ServoHILGround:GND'

class GroundLibraryTests(unittest.TestCase):
    def test_ground_library_is_an_exact_copy_of_the_reviewed_original(self):
        path = NATIVE / 'servohil_ground.kicad_sym'
        self.assertTrue(path.exists(), 'Ground symbol must have a portable matching project library')
        symbol = copy.deepcopy(items(parse(path.read_text()), 'symbol')[0])
        symbol[1] = 'power:GND'
        self.assertEqual(ORIGINAL_SHA256, hashlib.sha256(dump(symbol).encode()).hexdigest())
        self.assertIsNotNone(one(symbol, 'power'))
        pins = list(walk(symbol, 'pin'))
        self.assertEqual(1, len(pins))
        self.assertEqual(('1', 'GND', 'power_in', 'line'),
                         (one(pins[0], 'number')[1], one(pins[0], 'name')[1], pins[0][1], pins[0][2]))

    def test_every_ground_instance_resolves_to_that_exact_project_definition(self):
        count = 0
        for path in NATIVE.glob('*.kicad_sch'):
            tree = parse(path.read_text())
            definitions = {d[1]: d for d in items(one(tree, 'lib_symbols'), 'symbol')}
            for symbol in items(tree, 'symbol'):
                reference = next(p[2] for p in items(symbol, 'property') if p[1] == 'Reference')
                value = next(p[2] for p in items(symbol, 'property') if p[1] == 'Value')
                if not reference.startswith('#') or value != 'GND':
                    continue
                count += 1
                self.assertEqual(LIB_ID, one(symbol, 'lib_id')[1])
                definition = copy.deepcopy(definitions[LIB_ID]); definition[1] = 'power:GND'
                self.assertEqual(ORIGINAL_SHA256, hashlib.sha256(dump(definition).encode()).hexdigest())
        self.assertGreaterEqual(count, 80)

if __name__ == '__main__':
    unittest.main(verbosity=2)
