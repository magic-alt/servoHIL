#!/usr/bin/env python3
"""Prepare LTspice vendor-model benches WITHOUT inventing pin order or copying IP.

Requires the user's installed/downloaded official .asy AND a matching .SUBCKT
library. Missing/incompatible models fail closed. PREPARED is NOT SIMULATED.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
DEVICES=('LT3045','LT3094','LT8330')


def parse_symbol(text,device):
    attrs={};pins=[];current=None
    for line in text.splitlines():
        bits=line.strip().split(None,2)
        if not bits:continue
        if bits[0]=='SYMATTR' and len(bits)==3:attrs[bits[1]]=bits[2]
        elif bits[0]=='PIN':
            current={};pins.append(current)
        elif bits[0]=='PINATTR' and len(bits)==3:
            if current is None:raise ValueError('PINATTR without PIN')
            if bits[1] in current:raise ValueError('duplicate PINATTR')
            current[bits[1]]=bits[2]
    if attrs.get('Prefix')!='X':raise ValueError('vendor symbol is not an X subcircuit')
    if attrs.get('SpiceModel',attrs.get('Value'))!=device:
        raise ValueError('wrong vendor model, do not substitute a similarly named variant')
    try:
        ordered=sorted((int(p['SpiceOrder']),p['PinName']) for p in pins)
    except (ValueError,KeyError) as exc:raise ValueError('incomplete vendor pin order') from exc
    if not ordered or [x[0] for x in ordered]!=list(range(1,len(ordered)+1)):
        raise ValueError('SpiceOrder must cover 1..N exactly once')
    names=[x[1] for x in ordered]
    if len(set(names))!=len(names):raise ValueError('ambiguous repeated pin name')
    return names


def subckt_count(text,device):
    logical=[]
    for line in text.splitlines():
        if line.lstrip().startswith('+') and logical:logical[-1]+=' '+line.lstrip()[1:]
        else:logical.append(line)
    for line in logical:
        bits=line.split()
        if len(bits)>2 and bits[0].lower()=='.subckt' and bits[1].upper()==device:
            nodes=[]
            for word in bits[2:]:
                if '=' in word or word.lower().startswith('params:'):break
                nodes.append(word)
            return len(nodes)
    raise ValueError('matching readable .SUBCKT header missing; use official demo/built-in LTspice workflow')


def prepare(root,device,symbol_path,model_path,output,rail='5v2'):
    if device not in DEVICES:raise ValueError('unsupported device')
    # Check model availability before creating anything that resembles a completed bench.
    symbol_bytes=symbol_path.read_bytes();model_bytes=model_path.read_bytes()
    names=parse_symbol(symbol_bytes.decode('utf-8-sig',errors='replace'),device)
    if subckt_count(model_bytes.decode('utf-8-sig',errors='replace'),device)!=len(names):
        raise ValueError('model header and symbol pin counts differ')
    normalized=[re.sub(r'[^A-Z0-9]','',p.upper()) for p in names]
    if len(set(normalized))!=len(normalized):raise ValueError('normalized pin aliases collide')
    spec=importlib.util.spec_from_file_location('edv_vendor_analysis',root/'sim/power/analysis.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    values=a.native_values(root);val=lambda r:a.numeric(values[r])
    prereg=a.divider(.8,val('R210'),val('R211'))
    negprereg=a.divider(.8,val('R410'),val('R411'))
    include=str(model_path.resolve()).replace('\\','/')
    if any(c in include for c in ['"','\n','\r']):raise ValueError('unsafe include pathname')
    if device=='LT8330':
        mapping={'VIN':'vin','ENUVLO':'enable','GND':'0','SW':'sw','FBX':'fb','INTVCC':'intvcc'}
        mandatory=set(mapping)
        nominal=negprereg
        refs=['R410','R411','C416','L301','L302','C410','C411','C412','C413','C414','C415','R412']
        sources=f'''
.param VIN=12
.step param VIN list 8 12 15
Vinput vin 0 PWL(0 0 1m {{VIN}} 20m {{VIN}} 20.1m 0 30m 0)
Venable enable 0 PWL(0 0 1m 0 1.01m 3.3 20m 3.3 20.01m 0 30m 0)
Linput vin sw {val('L301')} Rser=0.045
Ctransfer sw negx {val('C410')} Rser=0.03
Loutput negx out {val('L302')} Rser=0.045
Dfly negx 0 DSCH_SCREEN
.model DSCH_SCREEN D(Is=1u Rs=0.08 N=1.1)
Rupper out fb {val('R410')}
Rlower fb 0 {val('R411')}
Cff out fb {val('C416')}
Cin vin 0 {val('C411')+val('C412')}
Cint intvcc 0 {val('C413')}
Cout out 0 {val('C414')+val('C415')} Rser=0.02
Rbleed out 0 {val('R412')}
Vstep loadstep 0 PWL(0 0 10m 0 10.01m 1 15m 1 15.01m 0 30m 0)
Bload out 0 I=V(out)*({.075/nominal}+{.075/nominal}*V(loadstep))
Bmag mag 0 V=-V(out)
.tran 0 30m 0 20n
.meas tran mean_v AVG V(mag) FROM=18m TO=19m
.meas tran ripple_v PP V(mag) FROM=18m TO=19m
.meas tran startup_s WHEN V(mag)={nominal*.9} RISE=1
.meas tran step_min MIN V(mag) FROM=10m TO=15m
.meas tran shutdown_v FIND V(mag) AT=29.9m
'''
    else:
        negative=device=='LT3094'
        if rail not in ('5v0','5v2'):raise ValueError('LT3045 rail must be 5v0 or 5v2')
        base=420 if negative else 240 if rail=='5v0' else 260
        rs=f'R{base}';cs=f'C{base}';ilim=f'R{base+1}'
        rpu=f'R{base+2}';rpl=f'R{base+3}'
        cin1=f'C{base+1}';cin2=f'C{base+2}';co1=f'C{base+3}';co2=f'C{base+4}'
        nominal=100e-6*val(rs);supply=negprereg if negative else prereg
        refs=[rs,cs,ilim,rpu,rpl,cin1,cin2,co1,co2]
        mapping={'IN':'vin','VIN':'vin','OUT':'out','VOUT':'out','OUTS':'out','GND':'0',
                 'ENUV':'vin' if negative else 'enable','ENUVLO':'vin' if negative else 'enable',
                 'SET':'set','ILIM':'ilim','PG':'pg','PGFB':'pgfb','VIOC':'vioc_nc'}
        mandatory={'OUTS','GND','SET','ILIM','PG','PGFB'}
        if not any(n in normalized for n in ('IN','VIN')) or not any(n in normalized for n in ('OUT','VOUT')):
            raise ValueError('vendor IN/OUT mapping missing')
        if not any(n in normalized for n in ('ENUV','ENUVLO')):raise ValueError('vendor enable mapping missing')
        budget=.2 if not negative and rail=='5v0' else .12
        sign='-' if negative else ''
        sources=f'''
.param VIN={supply}
.step param VIN list 5.8 {supply} 6.6
Vinput vin 0 PWL(0 0 5m {sign}{{VIN}} 80m {sign}{{VIN}} 80.1m 0 100m 0)
Venable enable 0 PWL(0 0 5m 0 5.01m 3.3 80m 3.3 80.01m 0 100m 0)
Vaon aon 0 3.3
Rset set 0 {val(rs)}
Cset set 0 {val(cs)}
Rlimit ilim 0 {val(ilim)}
Rpgup out pgfb {val(rpu)}
Rpglo pgfb 0 {val(rpl)}
Rpgpull aon pg 10k
Cin vin 0 {val(cin1)+val(cin2)}
Cout out 0 {val(co1)+val(co2)} Rser=0.02
Vstep loadstep 0 PWL(0 0 50m 0 50.01m 1 70m 1 70.01m 0 100m 0)
Bload out 0 I=V(out)*({budget/2/nominal}+{budget/2/nominal}*V(loadstep))
Bmag mag 0 V={sign}V(out)
.tran 0 100m 0 2u
.meas tran mean_v AVG V(mag) FROM=75m TO=79m
.meas tran ripple_v PP V(mag) FROM=75m TO=79m
.meas tran startup_s WHEN V(mag)={nominal*.9} RISE=1
.meas tran step_min MIN V(mag) FROM=50m TO=70m
.meas tran shutdown_v FIND V(mag) AT=99.9m
'''
    if set(normalized)-set(mapping):raise ValueError('unrecognized vendor pin names: '+str(set(normalized)-set(mapping)))
    if mandatory-set(normalized):raise ValueError('required vendor pin names missing: '+str(mandatory-set(normalized)))
    ordered_nodes=[mapping[n] for n in normalized]
    deck=f'''ServoHIL isolated {device} VENDOR BENCH - PREPARED NOT RUN
* Subcircuit order read from supplied official .asy SpiceOrder, not package numbering.
* Manufacturer model is referenced in place. No redistribution permission is assumed.
* Passives, effective capacitance, diode and parasitics remain engineering assumptions.
* Temperature stepping does not prove model temperature accuracy; inspect vendor limitations.
.include "{include}"
XREG {' '.join(ordered_nodes)} {device}
.step temp list -40 25 85
{sources}
.end
'''
    if output.exists():raise ValueError('refuse to overwrite an existing vendor bench/evidence directory')
    output.mkdir(parents=True)
    (output/'bench.cir').write_text(deck)
    manifest={'status':'PREPARED_NOT_RUN','device':device,'rail':rail if device=='LT3045' else None,
              'vendor_model_executed':False,'qualification':'NOT_QUALIFIED','layout_allowed':False,
              'symbol_file':str(symbol_path.resolve()),'model_file':str(model_path.resolve()),
              'symbol_sha256':hashlib.sha256(symbol_bytes).hexdigest(),
              'model_sha256':hashlib.sha256(model_bytes).hexdigest(),
              'deck_sha256':hashlib.sha256(deck.encode()).hexdigest(),
              'ordered_pin_names':names,'ordered_nodes':ordered_nodes,
              'native_values':{ref:values[ref] for ref in refs},'native_source_digest':a.content_digest(root)}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device',choices=DEVICES,required=True)
    p.add_argument('--rail',choices=['5v0','5v2'],default='5v2')
    p.add_argument('--symbol',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:r=prepare(ROOT,args.device,args.symbol,args.model,args.output,args.rail)
    except (OSError,ValueError,KeyError) as exc:
        print('VENDOR BENCH BLOCKED:',exc,file=sys.stderr);return 2
    print(json.dumps(r,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
