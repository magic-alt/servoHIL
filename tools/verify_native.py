#!/usr/bin/env python3
"""Cumulative independent electrical assertions for native power development."""
import argparse
import xml.etree.ElementTree as ET
from check_native_power import check as input_check


def verify(path,stage):
    input_check(path,'input')
    root=ET.parse(path).getroot();nets={};values={}
    for net in root.findall('./nets/net'):
        for node in net.findall('node'): nets[node.attrib['ref']+'.'+node.attrib['pin']]=net.attrib['name']
    for comp in root.findall('./components/comp'): values[comp.attrib['ref']]=comp.findtext('value','')
    def need(ref,pin,net):
        if nets.get(f'{ref}.{pin}')!=net: raise ValueError(f'{ref}.{pin}: expected {net}, got {nets.get(f"{ref}.{pin}")}')
    if stage in ('positive','negative','supervision'):
        for i,rail in [(201,'6V2_PRE'),(202,'3V3_D'),(203,'1V8_D')]:
            for pin,net in {3:'VIN_PROT',2:'INPUT_OK',4:'GND',6:f'BST_{i}',5:f'SW_{i}',1:f'FB_{i}'}.items(): need(f'U{i}',pin,net)
            need(f'L{i}',1,f'SW_{i}');need(f'L{i}',2,rail)
            base=210+(i-201)*10
            need(f'C{base}',1,f'BST_{i}');need(f'C{base}',2,f'SW_{i}')
            need(f'R{base}',1,rail);need(f'R{base}',2,f'FB_{i}');need(f'R{base+1}',2,'GND')
        for i,rail,pg in [(211,'+5V0_DAC','PG_5V0'),(212,'+5V2_PVDD','PG_PVDD')]:
            for pin,net in {1:'6V2_PRE',2:'6V2_PRE',3:'6V2_PRE',4:'INPUT_OK',6:f'ILIM_{i}',9:'GND',13:'GND',12:rail,11:rail,10:rail,8:f'SET_{i}',5:pg,7:f'PGFB_{i}'}.items():need(f'U{i}',pin,net)
        for ref,prefix in [('R210','67.3k'),('R220','31.2k'),('R230','12.4k'),('R240','49.9k'),('R260','52.0k')]:
            if not values.get(ref,'').startswith(prefix):raise ValueError('wrong rail setpoint: '+ref)
    print('Native cumulative electrical check PASS:',stage)
    return nets,values


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('netlist');p.add_argument('--stage',choices=['input','positive','negative','supervision'],required=True)
    a=p.parse_args();verify(a.netlist,a.stage)
