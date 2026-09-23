#!/usr/bin/env python3
"""CI ONLY: exercise native KiCad with synthetic SoM bindings, never a vendor design."""
import argparse
import json
from pathlib import Path
from test_carrier_compatibility import ROOT, fixture, module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=['multi', 'large'], required=True)
    args = parser.parse_args()
    if args.binding_root.resolve().is_relative_to((ROOT / 'hardware').resolve()):
        parser.error('never replace production carrier bindings with a test fixture')
    production = json.loads((ROOT / 'hardware/carriers/zu2cg_som/profile.json').read_text())
    if production['status'] != 'UNBOUND':
        parser.error('review this synthetic fixture workflow when a real SoM is selected')
    api = module('revb')
    options = dict(names=('J100',), contacts_per_connector=160) if args.case == 'large' else {}
    fixture(args.binding_root, api, **options)
    api.generate(args.binding_root, 'zu2cg_som', args.output)
    (args.output / 'SYNTHETIC_TEST_ONLY.txt').write_text(
        'NO VENDOR HARDWARE BINDING. Test connector geometry/netlist only. NOT FOR FABRICATION.\n')
    print('Generated synthetic SoM', args.case, 'fixture at', args.output)


if __name__ == '__main__':
    main()
