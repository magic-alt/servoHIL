#!/usr/bin/env python3
"""Check KiCad XML against independent carrier and AD3542R electrical contracts."""
import argparse
import importlib.util
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def carrier_oracle(root, carrier):
    """Read reviewed source binding, not generator-produced expected_connections."""
    spec = importlib.util.spec_from_file_location('revb_netlist_binding', root / 'tools/revb.py')
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    d, profile, physical, assignments = api.load(root, carrier)
    result = api.validate(d, profile, physical, assignments)
    if result['status'] == 'BLOCKED_VENDOR_BINDING':
        raise ValueError('UNBOUND carrier cannot pass a physical netlist check')
    refs = api.carrier_references(profile, physical)
    assigned = {(a['connector'], int(a['pin'])): a['net'] for a in assignments}
    pins = {}
    for row in physical:
        key = refs[row['connector']] + '.' + str(row['pin'])
        net = assigned.get((row['connector'], int(row['pin'])))
        pins[key] = 'GND' if row['kind'] == 'ground' else net
    return pins


def check(xml_path: Path, expectation_path: Path, *, carrier='axu2cgb', root=ROOT):
    document = ET.parse(xml_path).getroot()
    expected = json.loads(expectation_path.read_text())
    if not isinstance(expected, dict) or not expected or not all(
        isinstance(pin, str) and isinstance(net, str) and net for pin, net in expected.items()
    ):
        raise ValueError('missing/invalid generated pin expectations')
    actual, members = {}, {}
    for net in document.findall('./nets/net'):
        name = net.attrib['name']
        for node in net.findall('node'):
            key = node.attrib['ref'] + '.' + node.attrib['pin']
            if key in actual:
                raise ValueError('pin appears more than once in netlist: ' + key)
            actual[key] = name
            members.setdefault(name, set()).add(key)
    errors = []

    def required(pin, net):
        if actual.get(pin) != net:
            errors.append(f'{pin}: expected {net}, got {actual.get(pin)}')

    def unconnected(pin):
        name = actual.get(pin)
        if name is not None and not (name.startswith('unconnected-') and members[name] == {pin}):
            errors.append(f'{pin}: NC/DNC contact must not be connected to {name}')

    for pin, name in expected.items():
        required(pin, name)
    forbidden = re.compile(r'XC7A|FGG484|HL_TX|HL_RX|HLINK|1V0_FPGA|W25Q128', re.I)
    component_refs = set()
    for comp in document.findall('./components/comp'):
        ref = comp.attrib['ref']
        if ref in component_refs:
            errors.append('duplicate component reference: ' + ref)
        component_refs.add(ref)
        value = comp.findtext('value', '')
        if forbidden.search(value):
            errors.append('second-FPGA component: ' + value)
    for name in members:
        if forbidden.search(name):
            errors.append('legacy net: ' + name)

    # No hard-coded J12/J15 NC rules: use the selected carrier's physical facts.
    for pin, net in carrier_oracle(Path(root), carrier).items():
        if net is None:
            unconnected(pin)
        else:
            required(pin, net)

    # Independent AD3542R Rev.C pin oracle. GND, feedback, and DNC remain
    # checked even if the generated expectation omitted or misassigned them.
    for i in range(4):
        ref = 'U' + str(20 + i)
        pins = {
            '1': '1V8_D', '2': '1V8_D', '3': f'DAC_CS{i}_N', '4': 'DAC_SCLK',
            '5': f'DAC_SDIO{i*2}', '6': f'DAC_SDIO{i*2+1}',
            '7': 'DAC_LDAC_N', '8': 'DAC_RESET_N', '9': f'DAC_ALERT{i}_N',
            '10': 'GND', '11': f'DAC{i}_CAP1', '12': f'DAC{i}_VOUT1',
            '14': f'DAC{i}_VOUT1', '16': '+5V2_PVDD', '17': '+5V0_DAC',
            '18': 'VREF_2V5', '19': f'DAC{i}_CVREF', '20': f'DAC{i}_VOUT0',
            '22': f'DAC{i}_VOUT0', '24': f'DAC{i}_CAP0', '25': '-5V2_PVSS',
            '26': 'GND', '27': 'GND',
        }
        for pin, net in pins.items():
            required(ref + '.' + pin, net)
        for pin in ('13', '15', '21', '23', '28'):
            unconnected(ref + '.' + pin)
    if errors:
        raise ValueError('\n'.join(errors))
    return len(expected)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('netlist', type=Path)
    p.add_argument('expected', type=Path)
    p.add_argument('--carrier', choices=['axu2cgb', 'zu2cg_som'], default='axu2cgb')
    p.add_argument('--root', type=Path, default=ROOT, help='source binding root, not generated output')
    a = p.parse_args()
    print('Rev.B netlist contract PASS:', check(a.netlist, a.expected, carrier=a.carrier, root=a.root),
          'generated assertions plus independent carrier/converter checks')
