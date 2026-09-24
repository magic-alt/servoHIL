#!/usr/bin/env python3
"""Independent assertions on actual native KiCad electrical connections."""
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
    def nc(ref,pin):
        if not nets.get(f'{ref}.{pin}','unconnected-').startswith('unconnected-'):raise ValueError(f'{ref}.{pin} must be NC')
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
    if stage in ('negative','supervision'):
        for pin,net in {6:'VIN_PROT',4:'INPUT_OK',2:'GND',1:'SW_NEG',3:'FB_NEG',5:'INTVCC_NEG'}.items():need('U301',pin,net)
        for ref,pin,net in [('L301',1,'VIN_PROT'),('L301',2,'SW_NEG'),('C410',1,'SW_NEG'),('C410',2,'NEG_X'),('L302',1,'NEG_X'),('L302',2,'-6V2_PRE'),('D301',1,'GND'),('D301',2,'NEG_X'),('R410',1,'-6V2_PRE'),('R410',2,'FB_NEG'),('R411',1,'FB_NEG'),('R411',2,'GND')]:need(ref,pin,net)
        for pin,net in {1:'-6V2_PRE',2:'-6V2_PRE',3:'-6V2_PRE',5:'PGFB_PVSS',6:'ILIM_PVSS',9:'GND',13:'-6V2_PRE',11:'-5V2_PVSS',12:'-5V2_PVSS',10:'-5V2_PVSS',8:'SET_PVSS',4:'PG_PVSS'}.items():need('U302',pin,net)
        nc('U302',7)
        for pin,net in {2:'+5V0_DAC',4:'GND',6:'VREF_2V5'}.items():need('U303',pin,net)
        for pin in (1,3,5,7,8):nc('U303',pin)
        for ref,prefix in [('R410','1M'),('R411','147k'),('R420','52.0k'),('R421','15k')]:
            if not values.get(ref,'').startswith(prefix):raise ValueError('wrong negative/reference component: '+ref)
        # Every DAC actually receives the on-board rails, not an external supply connector.
        for i in range(20,24):
            for pin,net in {1:'1V8_D',2:'1V8_D',16:'+5V2_PVDD',17:'+5V0_DAC',18:'VREF_2V5',25:'-5V2_PVSS',10:'GND',26:'GND',27:'GND'}.items():need(f'U{i}',pin,net)
        if 'J1' in values or 'J2' in values:raise ValueError('external power/safety placeholder reappeared')
    print('Native cumulative electrical check PASS:',stage)
    return nets,values


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('netlist');p.add_argument('--stage',choices=['input','positive','negative','supervision'],required=True)
    a=p.parse_args();verify(a.netlist,a.stage)
