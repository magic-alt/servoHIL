#!/usr/bin/env python3
"""Carrier-neutral Rev.B contracts and deterministic, non-release build entry point."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_ID = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
BALL = re.compile(r'^[A-Z]{1,2}[1-9][0-9]*$')
LEGACY = re.compile(r'XC7A|FGG484|HL_TX|HL_RX|HLINK|1V0_FPGA|FPGA_QSPI', re.I)

def read_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def read_csv(p):
    with Path(p).open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def csv_bytes(rows):
    s = io.StringIO(newline='')
    w = csv.DictWriter(s, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode('utf-8')

def load(root: Path, carrier: str):
    if carrier not in {'axu2cgb', 'zu2cg_som'}:
        raise ValueError('unknown carrier')
    d = read_json(root/'hardware/revB/io_contract.json')
    base = root/'hardware/carriers'/carrier
    p = read_json(base/'profile.json')
    phy = read_csv(base/p['physical_pinout']) if p['physical_pinout'] else []
    a = read_csv(base/p['assignments']) if p['assignments'] else []
    return d, p, phy, a

def expected_signals():
    result = {}
    def add(names, direction, voltage):
        for n in names: result[n] = (direction, voltage)
    add(['DAC_SCLK','DAC_LDAC_N']+[f'DAC_CS{i}_N' for i in range(4)], 'output', 1.8)
    add([f'DAC_SDIO{i}' for i in range(8)], 'inout', 1.8)
    add([f'DAC_ALERT{i}_N' for i in range(4)]+[f'ADC_DOUT{i}' for i in range(8)]+['ADC_BUSY'], 'input', 1.8)
    add(['ADC_SCLK','ADC_CS_N','ADC_SDI','ADC_CONVST','ADC_RESET'], 'output', 1.8)
    add(['PWM_'+p for p in ['UH','UL','VH','VL','WH','WL']], 'input', 3.3)
    for e in range(2):
        add([f'ENC{e}_IO{i}' for i in range(4)], 'inout', 3.3)
        add([f'ENC{e}_DIR{i}' for i in range(2)], 'output', 3.3)
    add([f'AUX_IO{i}' for i in range(6)]+['MGMT_SCL','MGMT_SDA'], 'inout', 3.3)
    add(['RS485_TX','RS485_DE','HIL_ARM','HIL_WDI'], 'output', 3.3)
    add(['RS485_RX','HIL_FAULT_N'], 'input', 3.3)
    return result

def validate(d, p, physical, assignments):
    if type(d.get('compute_soc_count')) is not int or d['compute_soc_count'] != 1:
        raise ValueError('single compute SoC is required')
    if type(d.get('programmable_devices_on_io_board')) is not int or d['programmable_devices_on_io_board'] != 0:
        raise ValueError('no programmable device on the I/O board')
    if type(p.get('soc_count')) is not int or p.get('soc_count') != 1 or p.get('id') not in {'axu2cgb','zu2cg_som'}:
        raise ValueError('invalid single-SoC carrier')
    nets = [s['net'] for s in d['signals']]
    ports = [s['port'] for s in d['signals']]
    if any(LEGACY.search(n) for n in nets):
        raise ValueError('legacy local-FPGA/HIL-Link net in active contract')
    if len(set(nets)) != len(nets) or len(set(ports)) != len(ports):
        raise ValueError('duplicate logical net/port')
    expected = expected_signals()
    if set(nets) != set(expected):
        raise ValueError('missing or unexpected logical signals')
    for s in d['signals']:
        if not SAFE_ID.fullmatch(s['port']):
            raise ValueError('invalid HDL port identifier')
        dr, v = expected[s['net']]
        if s['direction'] != dr: raise ValueError(f"{s['net']}: direction mismatch")
        if float(s['voltage']) != v: raise ValueError(f"{s['net']}: voltage mismatch")
    if p['status'] == 'UNBOUND':
        if p['id'] != 'zu2cg_som' or physical or assignments or p.get('module') or p.get('device'):
            raise ValueError('UNBOUND SoM must not contain invented physical binding')
        return {'status':'BLOCKED_VENDOR_BINDING', 'assigned':{}, 'signal_count':len(nets)}
    if p['status'] != 'BOUND_CANDIDATE': raise ValueError('unknown carrier binding status')
    if p['id'] == 'axu2cgb' and p['board_variant'] != 'AXU2CGB-original':
        raise ValueError('wrong board variant: original AXU2CGB only, not -I/-E')
    if p['id'] == 'zu2cg_som' and not all(p.get(k) for k in ['vendor','module','module_revision','device']):
        raise ValueError('SoM vendor binding incomplete')
    if not physical: raise ValueError('missing physical pinout')
    if hashlib.sha256(csv_bytes(physical)).hexdigest() != p['physical_sha256']:
        raise ValueError('physical pinout digest differs from reviewed transcription')
    positions = [(r['connector'],int(r['pin'])) for r in physical]
    if len(set(positions)) != len(positions): raise ValueError('duplicate physical connector pin')
    balls = [r['soc_ball'] for r in physical if r['kind']=='gpio']
    if len(set(balls)) != len(balls): raise ValueError('duplicate SoC ball')
    if any(not BALL.fullmatch(b) for b in balls): raise ValueError('invalid/unbound SoC ball')
    if p['id']=='axu2cgb':
        if len(physical)!=80: raise ValueError('AXU2CGB requires 80 physical contacts')
        for conn in ['J12','J15']:
            rows = [r for r in physical if r['connector']==conn]
            if {int(r['pin']) for r in rows} != set(range(1,41)):
                raise ValueError('connector pin coverage invalid')
            for r in rows:
                number=int(r['pin'])
                kind='gpio' if 3<=number<=36 else 'ground' if number in [1,37,38] else 'power'
                if r['kind']!=kind: raise ValueError('physical power/GPIO contact classification wrong')
                if kind=='gpio' and float(r['voltage']) != (1.8 if conn=='J12' else 3.3):
                    raise ValueError('bank voltage incompatible')
    assigned_pins=[(r['connector'],int(r['pin'])) for r in assignments]
    assigned_nets=[r['net'] for r in assignments]
    if len(set(assigned_pins)) != len(assigned_pins) or len(set(assigned_nets)) != len(assigned_nets):
        raise ValueError('duplicate assignment')
    if set(assigned_nets)!=set(nets): raise ValueError('missing or unexpected assignment')
    lookup = {(r['connector'],int(r['pin'])):r for r in physical}
    signal = {s['net']:s for s in d['signals']}
    for r in assignments:
        loc=(r['connector'],int(r['pin']))
        q=lookup.get(loc)
        if not q or q['kind']!='gpio': raise ValueError('power/ground/missing contact cannot be GPIO')
        if float(q['voltage']) != float(signal[r['net']]['voltage']):
            raise ValueError('voltage mismatch; a SoM translator needs an explicit reviewed circuit, not an alias')
    counts=dict(Counter(r['connector'] for r in assignments))
    for connector, count in counts.items():
        capacity=sum(r['kind']=='gpio' and r['connector']==connector for r in physical)
        if count>capacity: raise ValueError('carrier I/O capacity exceeded')
    return {'status':'MAPPING_CANDIDATE', 'assigned':counts, 'signal_count':len(nets),
            'unused_gpio':len(balls)-len(assignments), 'hardware_verified':False}

def source_digest(root: Path):
    """Bind evidence to content, not a moving branch name or inherited Rev.A verdict."""
    h=hashlib.sha256()
    files=[]
    for directory in ['hardware/revB','hardware/carriers','tools','bom','references']:
        files += [p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.suffix!='.pyc' and p.name!='gates.json']
    for p in sorted(files):
        h.update(str(p.relative_to(root)).encode()+b'\0'+p.read_bytes()+b'\0')
    return h.hexdigest()

def check_release(root: Path, carrier: str):
    d,p,phy,a=load(root,carrier)
    result=validate(d,p,phy,a)
    g=read_json(root/'hardware/revB/gates.json')
    blocked=[]
    if result['status']=='BLOCKED_VENDOR_BINDING': blocked.append('UNBOUND carrier')
    if g.get('layout_allowed') is not True: blocked.append('layout_allowed is not true')
    if p.get('physical_review')!='BOARD_REVISION_SIGNED_OFF' or p.get('timing_verified') is not True:
        blocked.append('carrier physical/timing review incomplete')
    digest=source_digest(root)
    required={'carrier_pinout_review','carrier_schematic_xdc_crosscheck','io_power_design',
              'power_off_backfeed','safety_hardware','converter_pin_package_review','dac_analog_stability',
              'adc_interface_timing','vivado_io_drc','vivado_timing','schematic_erc','foc_physical_loop'}
    if set(g.get('gates',{})) != required: blocked.append('gate coverage invalid')
    for name, gate in g.get('gates',{}).items():
        evidence=gate.get('evidence')
        if gate.get('status')!='PASS' or not evidence:
            blocked.append(name); continue
        path=(root/evidence).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            blocked.append(name+': missing evidence'); continue
        report=read_json(path)
        if (report.get('source_digest')!=digest or report.get('carrier')!=carrier or
            report.get('gate')!=name or report.get('result')!='PASS' or not report.get('raw_report')):
            blocked.append(name+': stale/incomplete evidence'); continue
        raw=(root/report['raw_report']).resolve()
        if (not raw.is_relative_to(root.resolve()) or not raw.is_file() or
            hashlib.sha256(raw.read_bytes()).hexdigest()!=report.get('raw_sha256')):
            blocked.append(name+': missing/changed raw report')
    if blocked: raise ValueError('BLOCKED: '+', '.join(blocked))
    return {'status':'REVIEWED_RELEASE_GATE', 'carrier':carrier, 'source_digest':digest}

def generate(root: Path, carrier: str, output: Path):
    d,p,physical,a=load(root,carrier)
    summary=validate(d,p,physical,a)
    if p['status']=='UNBOUND': raise ValueError('UNBOUND SoM: select vendor module/revision and physical binding first')
    output.mkdir(parents=True,exist_ok=True)
    phy={(r['connector'],int(r['pin'])):r for r in physical}
    sig={s['net']:s for s in d['signals']}
    rows=[]
    xdc=['# REVIEW PREVIEW ONLY - no bitstream or board timing approval.',
         '# Import into the EXISTING HOST project for I/O planning; not a standalone design.',
         '# Host clock architecture, I/O delays and bank DRC remain unverified.']
    for assignment in a:
        q=phy[(assignment['connector'],int(assignment['pin']))];s=sig[assignment['net']]
        standard='LVCMOS18' if float(q['voltage'])==1.8 else 'LVCMOS33'
        rows.append({**assignment, 'soc_ball':q['soc_ball'], 'port':s['port'],
                     'direction':s['direction'], 'iostandard':standard, 'bank_group':q['bank_group']})
        xdc += [f"set_property PACKAGE_PIN {q['soc_ball']} [get_ports {{{s['port']}}}]",
                f"set_property IOSTANDARD {standard} [get_ports {{{s['port']}}}]"]
    (output/'derived_pin_map.csv').write_bytes(csv_bytes(rows))
    (output/'carrier.xdc.preview').write_text('\n'.join(xdc)+'\n')
    summary.update(carrier=carrier, source_digest=source_digest(root), layout_allowed=False,
                   scope='interface-plus-DAC review; power/ADC/PHY/safety boundaries are not completed circuits')
    (output/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    # Import relative to this file, including when the module is loaded by unittest.
    import importlib.util
    spec=importlib.util.spec_from_file_location('revb_schematic',root/'tools/revb_schematic.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    builder.build(d,p,physical,a,output)
    return summary

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','generate','release'])
    parser.add_argument('--carrier',choices=['axu2cgb','zu2cg_som'],default='axu2cgb')
    parser.add_argument('--output',type=Path,default=ROOT/'build/revB')
    args=parser.parse_args(argv)
    try:
        if args.command=='generate': result=generate(ROOT,args.carrier,args.output)
        elif args.command=='release': result=check_release(ROOT,args.carrier)
        else: result=validate(*load(ROOT,args.carrier))
    except (ValueError,KeyError,FileNotFoundError) as exc:
        print(str(exc),file=sys.stderr);return 2
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__': raise SystemExit(main())
