#!/usr/bin/env python3
"""Compare actual KiCad connectivity with the reviewed Rev.A pin contract.

Checks physical pin partitions, not XML net names. Renaming a local node is
legal; splitting a feedback node or joining unrelated nodes is not. This is
not a substitute for native ERC, datasheet review, or physical qualification.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET

CONTRACT = Path(__file__).with_name('remaining_pages_pin_contract.json')


def check(netlist: Path, contract: Path = CONTRACT, sheets=()):
    spec = json.loads(contract.read_text(encoding='utf-8'))
    selected = set(sheets) or set(spec['sheets'])
    unknown = selected - set(spec['sheets'])
    if unknown:
        raise ValueError('Unknown contract sheets: ' + ', '.join(sorted(unknown)))
    expected = {}
    for sheet in selected:
        for ref, pins in spec['sheets'][sheet].items():
            for pin, name in pins.items():
                key = ref + '.' + pin
                if key in expected:
                    raise ValueError('Duplicate contract pin: ' + key)
                expected[key] = name
    actual = {}
    members = defaultdict(set)
    for index, net in enumerate(ET.parse(netlist).getroot().findall('./nets/net')):
        for node in net.findall('node'):
            if node.attrib['ref'].startswith('#'):
                continue
            key = node.attrib['ref'] + '.' + node.attrib['pin']
            if key in actual:
                raise ValueError('Duplicate native pin: ' + key)
            actual[key] = index
            members[index].add(key)
    issues = []
    by_name = defaultdict(list)
    for pin, name in sorted(expected.items()):
        if pin not in actual:
            issues.append({'kind': 'missing_pin', 'pin': pin})
        elif name == spec['no_connect']:
            if len(members[actual[pin]]) != 1:
                issues.append({'kind': 'connected_nc', 'pin': pin,
                               'members': sorted(members[actual[pin]])})
        else:
            by_name[name].append(pin)
    for name, pins in sorted(by_name.items()):
        groups = defaultdict(list)
        for pin in pins:
            groups[actual[pin]].append(pin)
        if len(groups) > 1:
            issues.append({'kind': 'split', 'expected_net': name,
                           'pin_groups': sorted(groups.values())})
    for group in members.values():
        names = {expected[p] for p in group if p in expected}
        names.discard(spec['no_connect'])
        if len(names) > 1:
            issues.append({'kind': 'short', 'expected_nets': sorted(names),
                           'members': sorted(group)})
    return {'checked_pins': len(expected), 'sheets': sorted(selected),
            'result': 'FAIL' if issues else 'PASS', 'issues': issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('netlist', type=Path)
    parser.add_argument('--contract', type=Path, default=CONTRACT)
    parser.add_argument('--sheet', action='append', default=[])
    args = parser.parse_args()
    try:
        result = check(args.netlist, args.contract, args.sheet)
    except (ValueError, KeyError, OSError, ET.ParseError) as exc:
        parser.exit(2, f'Invalid verification input: {exc}\n')
    print(json.dumps(result, indent=2))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
