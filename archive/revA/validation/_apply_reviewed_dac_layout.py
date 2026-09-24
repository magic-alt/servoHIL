#!/usr/bin/env python3
"""One-shot PR #18 repair; remove after native files are reviewed and committed.

Reuse the already reviewed U20/U21 physical drawing for U22/U23, preserving
all destination references, values, symbol IDs, pin IDs and hierarchy paths.
This is not a project generator and is never called by ordinary validation.
"""
import copy
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from kicad_sexpr import parse, items, one, walk, dump, expr
N = ROOT / 'archive/revA/snapshot/hardware/kicad/revA'


def uid(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'servoHIL/revA/edits/' + seed))


def props(symbol):
    return {p[1]: p for p in items(symbol, 'property')}


def reference(symbol):
    return props(symbol)['Reference'][2]


def replace(node, tag, value):
    for i, child in enumerate(node):
        if isinstance(child, list) and child and child[0] == tag:
            node[i] = copy.deepcopy(value)
            return
    node.append(copy.deepcopy(value))


def pretty(node, indent=0):
    text = dump(node)
    if len(text) < 150 or not isinstance(node, list):
        return ' ' * indent + text
    i = 1
    while i < len(node) and not isinstance(node[i], list):
        i += 1
    return (' ' * indent + '(' + ' '.join(dump(v) for v in node[:i]) + '\n'
            + '\n'.join(pretty(v, indent + 2) for v in node[i:])
            + '\n' + ' ' * indent + ')')


def label(name, x, y, seed, global_=False, angle=0):
    side = 'left' if angle == 0 else 'right'
    if global_:
        return expr(f'(global_label {json.dumps(name)} (shape bidirectional) (at {x} {y} {angle}) (effects (font (size 1.27 1.27)) (justify {side})) (uuid "{uid(seed)}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x} {y} {angle}) (effects (font (size 1.27 1.27)) hide)))')
    return expr(f'(label {json.dumps(name)} (at {x} {y} {angle}) (effects (font (size 1.27 1.27)) (justify {side} bottom)) (uuid "{uid(seed)}"))')


def main():
    path = N / '07_dac_4_7.kicad_sch'
    old = parse(path.read_text())
    src = parse((N / '06_dac_0_3.kicad_sch').read_text())
    lookup = {reference(s): s for s in items(old, 'symbol')}
    keep = {'version', 'generator', 'generator_version', 'uuid', 'paper', 'title_block'}
    dest = [old[0]] + [copy.deepcopy(x) for x in old[1:] if str(x[0]) in keep]
    library = copy.deepcopy(one(src, 'lib_symbols'))
    library.append(copy.deepcopy(next(x for x in items(one(old, 'lib_symbols'), 'symbol') if x[1] == 'ServoHILCore:AO_CONN10')))
    dest.append(library)
    netmap = {'AO0_IA': 'AO4_TORQUE', 'AO1_IB': 'AO5_TEMP', 'AO2_IC': 'AO6_AUX0', 'AO3_VBUS': 'AO7_AUX1'}
    netmap.update({f'DAC_SDIO{i}': f'DAC_SDIO{i+4}' for i in range(4)})
    netmap.update({f'DAC_CS{i}_N': f'DAC_CS{i+2}_N' for i in range(2)})
    netmap.update({f'DAC_ALERT{i}_N': f'DAC_ALERT{i+2}_N' for i in range(2)})
    for symbol in items(src, 'symbol'):
        ref = reference(symbol)
        target = 'U' + str(int(ref[1:]) + 2) if ref.startswith('U') else ref[0] + str(int(ref[1:]) + 40)
        d = copy.deepcopy(lookup[target])
        replace(d, 'at', one(symbol, 'at'))
        replace(d, 'lib_id', one(symbol, 'lib_id'))
        for name, source_property in props(symbol).items():
            destination_property = props(d).get(name)
            if destination_property:
                value = destination_property[2]
                destination_property[:] = copy.deepcopy(source_property)
                destination_property[2] = value
        dest.append(d)
    for node in src[1:]:
        if not isinstance(node, list) or node[0] not in {'wire', 'label', 'global_label', 'junction', 'no_connect'}:
            continue
        d = copy.deepcopy(node)
        for u in walk(d, 'uuid'):
            u[1] = uid('07/template/' + str(u[1]))
        if d[0] in {'label', 'global_label'}:
            name = str(d[1])
            d[1] = netmap.get(name, name.replace('DAC0_', 'DAC2_').replace('DAC1_', 'DAC3_'))
            if str(d[1]).startswith(('AO4_', 'AO5_', 'AO6_', 'AO7_')) and d[0] == 'global_label':
                a = one(d, 'at')
                d = label(d[1], a[1], a[2], '07/local/' + d[1])
        dest.append(d)
    connector = copy.deepcopy(lookup['J20'])
    dest.append(connector)
    definition = next(x for x in items(library, 'symbol') if x[1] == 'ServoHILCore:AO_CONN10')
    cx, cy, angle = map(float, one(connector, 'at')[1:])
    assert angle == 0
    for index, name in enumerate(['AO0_IA', 'AO1_IB', 'AO2_IC', 'AO3_VBUS', 'AO4_TORQUE', 'AO5_TEMP', 'AO6_AUX0', 'AO7_AUX1', 'GND', 'GND'], 1):
        pin = next(p for p in walk(definition, 'pin') if str(one(p, 'number')[1]) == str(index))
        a = one(pin, 'at')
        x, y = round(cx + float(a[1]), 4), round(cy - float(a[2]), 4)
        lx = x - 10.16
        dest.append(expr(f'(wire (pts (xy {lx} {y}) (xy {x} {y})) (stroke (width 0.1524) (type solid)) (uuid "{uid("07/connector/" + str(index) + "0")}"))'))
        dest.append(label(name, lx, y, '07/connector-label/' + str(index), global_=index <= 4, angle=180))
    notes = [
        ('DAC 2 / AO4 torque and AO5 temperature', 25.4, 16.51, 1.5),
        ('DAC 3 / AO6 AUX0 and AO7 AUX1', 228.6, 16.51, 1.5),
        ('CFB tuning remains DNP; output resistors and feedback are wired locally.', 25.4, 195.58, 1.1),
        ('Same circuit and pin contract as U20/U21; channel functions are metadata.', 25.4, 205.74, 1.1),
        ('DUT interface J20: AO0-AO7 plus two grounds. Connector/package not frozen.', 25.4, 231.14, 1.1),
        ('PRELIMINARY: no stability, package, thermal or fabrication approval.', 25.4, 248.92, 1.1),
    ]
    for i, (text, x, y, size) in enumerate(notes):
        dest.append(expr(f'(text {json.dumps(text)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid "{uid("07/note" + str(i))}"))'))
    path.write_text(pretty(dest) + '\n')


if __name__ == '__main__':
    main()
