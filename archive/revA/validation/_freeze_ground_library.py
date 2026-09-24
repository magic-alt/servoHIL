#!/usr/bin/env python3
"""One-shot namespace-only ground migration, with byte-semantic signature guard.

Do not replace an archived pin type merely to match a newer system library.
The original symbol is copied exactly, including its (power) global semantics,
and assigned a project-owned library ID. Normal validation never runs this edit.
"""
from __future__ import annotations
import copy
import hashlib
from _finish_review import save
from _apply_digital_drawing import pretty
from test_ground_library import NATIVE, ORIGINAL_SHA256, LIB_ID
from kicad_sexpr import parse, items, one, dump, expr


def run():
    source = parse((NATIVE / '01_power_entry.kicad_sch').read_text())
    original = next(s for s in items(one(source, 'lib_symbols'), 'symbol') if s[1] == 'power:GND')
    assert hashlib.sha256(dump(original).encode()).hexdigest() == ORIGINAL_SHA256
    lib = expr('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor") (generator_version "8.0"))')
    symbol = copy.deepcopy(original); symbol[1] = 'GND'; lib.append(symbol)
    (NATIVE / 'servohil_ground.kicad_sym').write_text(pretty(lib) + '\n')
    for path in NATIVE.glob('*.kicad_sch'):
        tree = parse(path.read_text())
        for definition in items(one(tree, 'lib_symbols'), 'symbol'):
            if definition[1] == 'power:GND':
                assert definition == original, 'Unexpected different ground drawing: ' + path.name
                definition[1] = LIB_ID
        for instance in items(tree, 'symbol'):
            if one(instance, 'lib_id')[1] == 'power:GND':
                one(instance, 'lib_id')[1] = LIB_ID
        save(path, tree)
    path = NATIVE / 'sym-lib-table'; table = parse(path.read_text())
    assert not any(one(lib, 'name')[1] == 'ServoHILGround' for lib in items(table, 'lib'))
    table.append(expr('(lib (name "ServoHILGround") (type "KiCad") (uri "${KIPRJMOD}/servohil_ground.kicad_sym") (options "") (descr "Exact archived global GND symbol; original power_in pin preserved"))'))
    path.write_text(pretty(table) + '\n')
    # The geometry assertion still requires at least 15 explicit ground symbols.
    # GroundLibraryTests independently checks their complete frozen definition.
    path = NATIVE.parents[3] / 'validation/test_digital_drawing.py'
    text = path.read_text()
    old = "one(s, 'lib_id')[1] == 'power:GND'"
    assert old in text
    path.write_text(text.replace(old, "one(s, 'lib_id')[1] == 'ServoHILGround:GND'"))


if __name__ == '__main__':
    run()
