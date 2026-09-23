#!/usr/bin/env python3
"""Check actual KiCad XML connectivity against carrier and converter contracts."""
import argparse
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

def check(xml_path: Path, expectation_path: Path):
    root=ET.parse(xml_path).getroot()
    expected=json.loads(expectation_path.read_text())
    actual={}
    for net in root.findall('./nets/net'):
        name=net.attrib['name']
        for node in net.findall('node'):
            key=node.attrib['ref']+'.'+node.attrib['pin']
            if key in actual and actual[key]!=name:
                raise ValueError('pin appears in multiple nets: '+key)
            actual[key]=name
    errors=[]
    for pin,name in expected.items():
        if actual.get(pin)!=name:
            errors.append(f'{pin}: expected {name}, got {actual.get(pin)}')
    forbidden=re.compile(r'XC7A|FGG484|HL_TX|HL_RX|HLINK|1V0_FPGA|W25Q128', re.I)
    for comp in root.findall('./components/comp'):
        value=comp.findtext('value','')
        if forbidden.search(value): errors.append('second-FPGA component: '+value)
    for net in root.findall('./nets/net'):
        if forbidden.search(net.attrib['name']): errors.append('legacy net: '+net.attrib['name'])
    # Independent board-pin oracle: powered host contacts are never wired.
    for ref in ['J12','J15']:
        for pin in [2,39,40]:
            value=actual.get(f'{ref}.{pin}','')
            if value and not value.startswith('unconnected-'):
                errors.append(f'{ref}.{pin}: host power contact must be NC')
    # Converter pin numbers are from AD3542R Rev.C, not generated expectation.
    for i in range(4):
        ref='U'+str(20+i)
        for pin,name in {'1':'1V8_D','2':'1V8_D','3':f'DAC_CS{i}_N','4':'DAC_SCLK',
                         '5':f'DAC_SDIO{i*2}','6':f'DAC_SDIO{i*2+1}',
                         '7':'DAC_LDAC_N','8':'DAC_RESET_N','16':'+5V2_PVDD',
                         '17':'+5V0_DAC','18':'VREF_2V5','25':'-5V2_PVSS'}.items():
            if actual.get(ref+'.'+pin)!=name: errors.append(f'{ref}.{pin}: wrong converter net')
        for a,b in [('20','22'),('12','14')]:
            if actual.get(ref+'.'+a)!=actual.get(ref+'.'+b): errors.append(ref+': broken RFB2 feedback')
    if errors: raise ValueError('\n'.join(errors))
    return len(expected)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('netlist',type=Path);p.add_argument('expected',type=Path)
    a=p.parse_args()
    print('Rev.B netlist contract PASS:',check(a.netlist,a.expected),'pin/net assertions')
