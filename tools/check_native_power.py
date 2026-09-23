#!/usr/bin/env python3
"""Independent pin-level assertions on the committed power design's KiCad netlist."""
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET

REQUIRED={
'input':{'U101.5':'VIN_EFUSE','U101.6':'VIN_PROT','U101.1':'UVLO_IN','U101.2':'OVLO_IN','U101.3':'INPUT_OK','U101.4':'PGTH_IN','U101.8':'GND','U101.9':'ILIM_IN','U102.1':'VIN_PROT','U102.2':'GND','U102.5':'3V3_AON','D101.1':'VIN_EFUSE','D101.2':'VIN_FUSED','D102.1':'VIN_EFUSE','D102.2':'GND','F101.1':'VIN_RAW','F101.2':'VIN_FUSED','R107.1':'3V3_AON','R107.2':'INPUT_OK'},
}


def check(path,stage):
    root=ET.parse(path).getroot();actual={};values={}
    for net in root.findall('./nets/net'):
        for node in net.findall('node'):
            pin=node.attrib['ref']+'.'+node.attrib['pin']
            if pin in actual: raise ValueError('duplicate netlist pin: '+pin)
            actual[pin]=net.attrib['name']
    for comp in root.findall('./components/comp'):
        ref=comp.attrib['ref']
        if ref in values: raise ValueError('duplicate reference: '+ref)
        values[ref]=comp.findtext('value','')
    for name,rules in REQUIRED.items():
        for pin,net in rules.items():
            if actual.get(pin)!=net: raise ValueError(f'{name}: {pin}: expected {net}, got {actual.get(pin)}')
        if name==stage: break
    if actual.get('U102.3','unconnected-').startswith('unconnected-') is False:
        raise ValueError('TPS709 EN must remain open; no 12V connection')
    for ref in ('J12','J15'):
        for pin in ('2','39','40'):
            if not actual.get(ref+'.'+pin,'unconnected-').startswith('unconnected-'):
                raise ValueError('AXU power pin backfeed: '+ref+'.'+pin)
    assert values['U101'].startswith('TPS259474LRPWR')
    assert values['R106'].startswith('2.21k')
    assert values['C108'].startswith('4.7uF')
    print('Native power pin/net check PASS:',stage,len(actual),'connected pins')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('netlist',type=Path);p.add_argument('--stage',choices=REQUIRED,required=True)
    a=p.parse_args();check(a.netlist,a.stage)
