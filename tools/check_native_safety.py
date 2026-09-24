#!/usr/bin/env python3
"""Independent Rev.B physical-pin oracle and narrow, frozen-old-board delta.

Consumes actual KiCad XML. Does not generate circuits or bless a new baseline.
Pin tables are transcribed from the linked manufacturers' pin tables in the
safety design note, independently of the authoring helper. ERC is separate.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from check_native_readability import graph

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT/'docs/review/revb-readability/repair/corrected-baseline.xml'
AON, GND = '3V3_AON', 'GND'
PINS: dict[str, str | None] = {}
PARTS: dict[str, dict[str,str]] = {}

def part(ref, value, pins, footprint=''):
    PARTS[ref] = {'value':value, 'footprint':footprint}
    PINS.update({f'{ref}.{pin}':net for pin,net in pins.items()})

def passive(ref, value, first, second):
    fp = ('Resistor_SMD:R_0603_1608Metric' if ref.startswith('R')
          else 'Capacitor_SMD:C_0603_1608Metric')
    part(ref,value,{1:first,2:second},fp)

# TPS3430 DRC: pad 11 is the review-symbol convention for the exposed GND pad.
part('U501','TPS3430DRCR',{1:AON,10:AON,2:'WD_CWD',3:AON,6:AON,4:None,
                         5:GND,11:GND,7:'WD_INPUT',8:'WD_CLEAR_N',9:None})
for ref,mr,out in [('U502','INTERLOCK_OK','WD_CLEAR_N'),('U503','HB_VALID','RAILS_OK')]:
    part(ref,'TPS3808G33DBVR',{1:out,2:GND,3:mr,4:None,5:AON,6:AON},'Package_TO_SOT_SMD:SOT-23-6')
for ref,value,inp,out in [('U504','SN74LVC1G17DBVR','WD_HOST','WD_INPUT'),
                         ('U505','SN74LVC1G14DBVR','WD_INPUT','WD_CLK'),
                         ('U509','SN74LVC1G17DBVR','INTERLOCK_RAW','INTERLOCK_OK'),
                         ('U510','SN74LVC1G17DBVR','WD_CLEAR_N','HB_CLR_N')]:
    part(ref,value,{1:None,2:inp,3:GND,4:out,5:AON},'Package_TO_SOT_SMD:SOT-23-5')
for ref,d,q in [('U506',AON,'HB_FIRST'),('U507','HB_FIRST','HB_VALID')]:
    part(ref,'SN74LVC1G74DCTR',{1:'WD_CLK',2:d,3:None,4:GND,5:q,6:'HB_CLR_N',7:AON,8:AON})
part('U508','SN74LVC1G11DBVR',{1:'RAILS_OK',3:'ARM_LATCH',6:'HIL_ARM',
                              2:GND,5:AON,4:'SAFE_ENABLE'},'Package_TO_SOT_SMD:SOT-23-6')
part('J501','3.3V DRY CONTACT ONLY',{1:'INTERLOCK_FEED',2:'INTERLOCK_RAW'})
for ref,value,first,second in [
 ('R601','1k','HIL_WDI','WD_HOST'),('R602','10k','WD_HOST',GND),
 ('R603','10k','HB_VALID',GND),('R604','10k',AON,'WD_CWD'),
 ('R605','10k',AON,'WD_CLEAR_N'),('R606','1k',AON,'INTERLOCK_FEED'),
 ('R607','10k','INTERLOCK_RAW',GND),('R608','10k','SAFE_ENABLE',GND)]:
    passive(ref,value,first,second)
for n in range(601,611):passive(f'C{n}','100n',AON,GND)

# ADG5412F TSSOP-16: D pins on DAC side, protected S pins on DUT side.
for idx,ref in enumerate(['U601','U602']):
    pins = {13:'+5V2_PVDD',4:'-5V2_PVSS',5:GND,12:f'AO_FF{idx}_N'}
    for p in (1,16,9,8):pins[p] = f'AO_EN{idx}'
    for ch,(dp,sp) in enumerate(((2,3),(15,14),(10,11),(7,6))):
        pins[dp] = f'AO{idx*4+ch}'
        pins[sp] = f'DUT_AO{idx*4+ch}'
    part(ref,'ADG5412FBRUZ',pins,'Package_SO:TSSOP-16_4.4x5mm_P0.65mm')
    passive(f'R{651+2*idx}','10k',f'AO_EN{idx}',GND)
    passive(f'R{652+2*idx}','100','SAFE_ENABLE',f'AO_EN{idx}')
    part(f'TP{651+idx}',f'FF{idx}_N',{1:f'AO_FF{idx}_N'},'TestPoint:TestPoint_Pad_D1.0mm')
for n,rail in [(651,'+5V2_PVDD'),(652,'-5V2_PVSS'),(653,'+5V2_PVDD'),(654,'-5V2_PVSS')]:
    passive(f'C{n}','100n',rail,GND)

part('U701','AQY212GS',{1:'PERMIT_LED_A',2:'PERMIT_LED_K',3:'DUT_PERMIT_A',4:'DUT_PERMIT_B'})
part('Q701','MMBT3904',{1:'PERMIT_BASE',2:GND,3:'PERMIT_LED_K'},'Package_TO_SOT_SMD:SOT-23')
part('J701','DUT PERMIT - FLOATING NO',{1:'DUT_PERMIT_A',2:'DUT_PERMIT_B'})
passive('R701','220 1%',AON,'PERMIT_LED_A')
passive('R702','680 1%','SAFE_ENABLE','PERMIT_BASE')
passive('R703','10k','PERMIT_BASE',GND)


def check(source: str | Path, baseline: str | Path = BASELINE) -> dict:
    old, new = graph(baseline), graph(source)
    oldrefs=set(old['components'])
    if set(new['components']) != oldrefs | set(PARTS):
        raise ValueError('unexpected or missing physical component set')
    for ref,attributes in {**old['components'],**PARTS}.items():
        if new['components'][ref] != attributes:
            raise ValueError('component/value/footprint changed: '+ref)
    moved={f'J5.{p}' for p in range(1,9)}
    def projection(partition):
        result=[]
        for nodes in partition:
            group=tuple(sorted(p for p in nodes if p.rsplit('.',1)[0] in oldrefs and p not in moved))
            if group:result.append(group)
        return sorted(result)
    if projection(old['partition']) != projection(new['partition']):
        raise ValueError('frozen existing pin partition changed outside J5.1..8')
    root=ET.parse(source).getroot()
    nets={};members=defaultdict(set)
    for net in root.findall('./nets/net'):
        name=net.attrib['name'].rsplit('/',1)[-1]
        for node in net.findall('node'):
            key=node.attrib['ref']+'.'+node.attrib['pin']
            if key.startswith('#'):continue
            if key in nets:raise ValueError('duplicate physical pin: '+key)
            nets[key]=name;members[name].add(key)
    wanted={**PINS,**{f'J5.{i+1}':f'DUT_AO{i}' for i in range(8)}}
    for key,name in wanted.items():
        if name is None:
            if key in nets and members[nets[key]]!={key}:
                raise ValueError('required no-connect is wired: '+key)
        elif nets.get(key)!=name:
            raise ValueError(f'safety pin {key}: expected {name}, got {nets.get(key)}')
    extra={p for p in nets if p.rsplit('.',1)[0] in PARTS} - set(PINS)
    if extra:raise ValueError('unexpected safety physical pin: '+str(sorted(extra)))
    for ch,(dp,sp) in enumerate(((2,3),(15,14),(10,11),(7,6))*2):
        switch='U601' if ch<4 else 'U602'
        if members[f'DUT_AO{ch}'] != {f'J5.{ch+1}',f'{switch}.{sp}'}:
            raise ValueError('DUT AO parallel path or load: '+str(ch))
    for n,net in enumerate(('DUT_PERMIT_A','DUT_PERMIT_B')):
        if members[net] != {f'U701.{3+n}',f'J701.{1+n}'}:
            raise ValueError('permit contact not independently floating: '+net)
    return {'result':'PIN_CONTRACT_PASS_NOT_HARDWARE_QUALIFIED',
            'frozen_existing_components':len(oldrefs),'new_components':len(PARTS),
            'new_pin_assertions':len(PINS),'connector_delta_pins':8,
            'layout_allowed':False,'physical_validation':'NOT_RUN'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('netlist',type=Path)
    args=parser.parse_args()
    print(json.dumps(check(args.netlist),indent=2))
