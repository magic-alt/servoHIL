#!/usr/bin/env python3
"""One-shot PR17 sheet migration. Never regenerates an existing editable child sheet.
Normal development edits the committed .kicad_sch files directly. This migration
only creates a named new sheet; existing sheets are copied byte-for-byte.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import revb
import revb_schematic as k
DST = ROOT/'hardware/kicad/revB/axu2cgb_expansion'


def expressions(text):
    quoted=escaped=False;depth=0;start=0
    for i,c in enumerate(text):
        if quoted:
            if escaped: escaped=False
            elif c=='\\': escaped=True
            elif c=='"': quoted=False
        elif c=='"': quoted=True
        elif c=='(':
            if depth==1: start=i
            depth+=1
        elif c==')':
            depth-=1
            if depth==1: yield text[start:i+1]
    if depth or quoted: raise ValueError('unbalanced KiCad expression')


class Drawing:
    def __init__(self,name,title):
        self.p=k.Project();self.s=k.Sheet(self.p,name,title)
        for kind in ('R','C'):
            self.p.definition(kind,[('1','1','passive',-5.08,0,0),('2','2','passive',5.08,0,180)],half=0,passive=True)
        # IEC-ish diode and inductor graphics are replaced after definitions.
        for kind in ('D','F','L','SW'):
            self.p.definition(kind,[('1','K' if kind=='D' else '1','passive',-5.08,0,0),('2','A' if kind=='D' else '2','passive',5.08,0,180)],half=0,passive=True)
        self.p.definition('PWR_FLAG',[('1','PWR','power_out',5.08,0,180)],half=0,passive=True)
        self.p.definition('TESTPOINT',[('1','TP','passive',5.08,0,180)],half=0,passive=True)
    def ic(self,name,left,right):
        pins=[]
        rows=max(len(left),len(right))
        for sign,group in ((-1,left),(1,right)):
            for i,(number,label,typ) in enumerate(group):
                pins.append((str(number),label,typ,sign*20.32,(rows-1)*2.54-i*5.08,0 if sign<0 else 180))
        self.p.definition(name,pins,half=(rows+1)*2.54)
    def add(self,symbol,ref,value,x,y,mapping,fp='',source='',dnp=False):
        start=len(self.s.items)
        self.s.instance(symbol,ref,value,x,y,{str(a):b for a,b in mapping.items()},dnp)
        item=self.s.items[start]
        item=item.replace('(property "Footprint" ""', '(property "Footprint" '+k.q(fp))
        item=item.replace('(property "Datasheet" ""', '(property "Datasheet" '+k.q(source))
        if symbol=='PWR_FLAG':
            item=item.replace('(in_bom yes)','(in_bom no)').replace('(on_board yes)','(on_board no)')
        self.s.items[start]=item
    def r(self,ref,val,x,y,a,b): self.add('R',ref,val,x,y,{1:a,2:b},'Resistor_SMD:R_0603_1608Metric')
    def c(self,ref,val,x,y,a,b): self.add('C',ref,val,x,y,{1:a,2:b},'Capacitor_SMD:C_0805_2012Metric')
    def tp(self,ref,x,y,net): self.add('TESTPOINT',ref,net,x,y,{1:net},'TestPoint:TestPoint_Pad_D1.0mm')
    def flag(self,ref,x,y,net): self.add('PWR_FLAG',ref,'PWR_FLAG',x,y,{1:net})


def input_sheet():
    d=Drawing('10_input_protection','INPUT: 9-15 V regulated bench supply; eFuse circuit breaker + protected AON')
    d.ic('DC_INPUT',[],[(1,'VIN','power_out'),(2,'GND','power_out')])
    d.add('DC_INPUT','J101','12V INPUT / 9-15V',35.56,50.8,{1:'VIN_RAW',2:'GND'})
    d.add('F','F101','2A backup fuse / 0451002.MRL',96.52,48.26,{1:'VIN_RAW',2:'VIN_FUSED'},source='https://www.littelfuse.com/products/fuses-overcurrent-protection/fuses/surface-mount-fuses/nano2-fuses/451-453')
    d.add('D','D101','SS34 reverse-polarity diode',96.52,68.58,{1:'VIN_EFUSE',2:'VIN_FUSED'},'Diode_SMD:D_SMA',source='https://www.diodes.com/assets/Datasheets/ds23001.pdf')
    d.add('D','D102','SMBJ16A / 16V standoff TVS',35.56,99.06,{1:'VIN_EFUSE',2:'GND'},'Diode_SMD:D_SMB')
    d.c('C101','10uF / 50V X7R',35.56,124.46,'VIN_EFUSE','GND')
    d.c('C102','100nF / 50V X7R',96.52,124.46,'VIN_EFUSE','GND')
    d.flag('PF101',35.56,144.78,'VIN_EFUSE')
    d.ic('TPS259474L',[(5,'IN','power_in'),(1,'EN_UVLO','input'),(2,'OVLO','input'),(4,'PGTH','input'),(8,'GND','power_in')],[(6,'OUT','power_out'),(3,'PG','open_collector'),(7,'DVDT','passive'),(9,'ILM','passive'),(10,'ITIMER','passive')])
    d.add('TPS259474L','U101','TPS259474LRPWR / latched circuit breaker',195.58,91.44,{5:'VIN_EFUSE',1:'UVLO_IN',2:'OVLO_IN',4:'PGTH_IN',8:'GND',6:'VIN_PROT',3:'INPUT_OK',7:'DVDT_IN',9:'ILIM_IN',10:'ITIMER_IN'},source='https://www.ti.com/lit/ds/symlink/tps25947.pdf')
    for ref,val,x,y,a,b in [('R101','680k 0.1%',152.4,144.78,'VIN_EFUSE','UVLO_IN'),('R102','60.4k 0.1%',213.36,144.78,'UVLO_IN','OVLO_IN'),('R103','60.4k 0.1%',274.32,144.78,'OVLO_IN','GND'),('R104','56.2k 0.1%',152.4,170.18,'VIN_PROT','PGTH_IN'),('R105','10k 0.1%',213.36,170.18,'PGTH_IN','GND'),('R106','2.21k 1% / 1.51A nominal',274.32,170.18,'ILIM_IN','GND'),('R107','10k',335.28,170.18,'3V3_AON','INPUT_OK')]: d.r(ref,val,x,y,a,b)
    d.c('C103','3.3nF / 50V C0G',274.32,66.04,'DVDT_IN','GND')
    d.c('C104','1nF / 16V C0G',335.28,66.04,'ITIMER_IN','GND')
    d.c('C105','47uF / 35V effective >=22uF',274.32,91.44,'VIN_PROT','GND')
    d.c('C106','100nF / 50V',335.28,91.44,'VIN_PROT','GND')
    d.add('SW','SW101','POWER RESET (normally open)',96.52,195.58,{1:'UVLO_IN',2:'GND'})
    d.ic('TPS70933_DBV',[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input')],[(5,'OUT','power_out'),(4,'NC','no_connect')])
    d.add('TPS70933_DBV','U102','TPS70933DBVR / AON only',195.58,220.98,{1:'VIN_PROT',2:'GND',3:None,5:'3V3_AON',4:None},'Package_TO_SOT_SMD:SOT-23-5','https://www.ti.com/lit/ds/symlink/tps709.pdf')
    d.c('C107','1uF / 35V X7R',35.56,220.98,'VIN_PROT','GND')
    d.c('C108','4.7uF / 16V effective >=2.2uF',274.32,220.98,'3V3_AON','GND')
    d.c('C109','100nF / 16V',335.28,220.98,'3V3_AON','GND')
    d.s.text('TPS709 EN is intentionally OPEN (internal pull-up). NEVER tie its 7V-abs-max EN directly to 12V.',25.4,251.46)
    d.s.text('UVLO ~7.95V, OVLO ~15.91V at VIN_EFUSE; PGTH ~7.94V. 474L is a CIRCUIT BREAKER, not continuous 1.5A regulation.',25.4,259.08)
    d.s.text('TVS/fuse surge coordination is NOT qualified. Use current-limited SELV 9-15V supply; no motor DC bus connection.',25.4,266.7)
    return d


STAGES={'input':input_sheet}


def root_sheet(dst):
    names=[p.stem for p in dst.glob('*.kicad_sch') if p.name!='servohil_io_revB.kicad_sch']
    priority=['01_carrier_interface','10_input_protection','20_positive_rails','30_negative_reference','40_power_supervision','03_peripheral_boundaries','04_dac_0_3','05_dac_4_7','06_analog_outputs']
    names.sort(key=lambda x:priority.index(x) if x in priority else 100)
    children=[]
    for i,name in enumerate(names):
        x=25.4+(i%2)*177.8;y=50.8+(i//2)*50.8
        children.append(f'''(sheet (at {k.n(x)} {k.n(y)}) (size 139.7 30.48) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid "{k.uid(name)}")
(property "Sheetname" {k.q(name)} (at {k.n(x)} {k.n(y-2.54)} 0) {k.fx()})
(property "Sheetfile" {k.q(name+'.kicad_sch')} (at {k.n(x)} {k.n(y+33.02)} 0) {k.fx()})
(instances (project "servohil_io_revB" (path "/{k.uid('root')}" (page "{i+2}")))))''')
    text=f'''(kicad_sch (version 20231120) (generator eeschema) (uuid "{k.uid('root')}") (paper "A2")
(title_block (title "ServoHIL Rev.B - native editable single-SoC expansion") (rev "B-power-development"))
(lib_symbols) (text "NATIVE SOURCE. Power development; safety/PHY/PCB/bench qualification remain OPEN." (at 25.4 25.4 0) (effects (font (size 1.524 1.524)) (justify left bottom)) (uuid "{k.uid('native-title')}"))
{' '.join(children)} (sheet_instances (path "/" (page "1"))))\n'''
    (dst/'servohil_io_revB.kicad_sch').write_text(text)


def migrate(stage):
    if stage not in STAGES: raise ValueError('unknown stage')
    drawing=STAGES[stage]()
    if (DST/(drawing.s.name+'.kicad_sch')).exists():
        raise ValueError('REFUSED: editable child sheet already exists; edit it in KiCad, do not regenerate')
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp)
        if not DST.exists():
            revb.generate(ROOT,'axu2cgb',temp/'base')
            shutil.copytree(temp/'base',DST)
            (DST/'02_power_safety_boundary.kicad_sch').unlink()
            expected=json.loads((DST/'expected_connections.json').read_text())
            expected={pin:net for pin,net in expected.items() if pin.split('.')[0] not in {'J1','J2','R1'}}
            (DST/'expected_connections.json').write_text(json.dumps(expected,indent=2,sort_keys=True)+'\n')
        (temp/'new').mkdir();drawing.p.save(temp/'new')
        shutil.copyfile(temp/'new'/(drawing.s.name+'.kicad_sch'),DST/(drawing.s.name+'.kicad_sch'))
        libpath=DST/'revb.kicad_sym';old=libpath.read_text();new=[]
        existing={re.match(r'\(symbol "([^"]+)"',e).group(1):e for e in expressions(old) if e.startswith('(symbol "')}
        for e in expressions((temp/'new/revb.kicad_sym').read_text()):
            m=re.match(r'\(symbol "([^"]+)"',e)
            if m and m.group(1) not in existing: new.append(e)
        libpath.write_text(old.rstrip()[:-1]+'\n'+'\n'.join(new)+'\n)\n')
        expected=json.loads((DST/'expected_connections.json').read_text())
        if set(expected)&set(drawing.p.expected): raise ValueError('duplicate reference/pin across native sheets')
        expected.update(drawing.p.expected)
        (DST/'expected_connections.json').write_text(json.dumps(expected,sort_keys=True,indent=2)+'\n')
        root_sheet(DST)
        (DST/'README.md').write_text('''# Native editable AXU2CGB expansion

Open `servohil_io_revB.kicad_pro`. These checked-in `.kicad_sch` files are the
hardware source of truth. Edit them in KiCad. Do not run the Rev.B review
builder into this directory. `tools/migrations/pr17_native.py` is a one-shot
migration and refuses to replace an existing child sheet.

This is ongoing board development, not a manufacturing release. No second
FPGA; SoM remains a separate unbound carrier contract. ADC/PHY and complete
DUT safety are not yet populated. `hardware/revB/gates.json` remains blocked.

`expected_connections.json` is a migration checkpoint, NOT an independent
hardware oracle. Native checks must also inspect actual IC pin identities,
source paths, resistor values and the current netlist. Tests cannot substitute
for power/thermal/transient bench qualification.
''')
        log=DST/'MIGRATION_LOG.md'
        with log.open('a') as f:f.write(f'- {stage}: added {drawing.s.name}.kicad_sch; existing child sheets preserved.\n')
    print('Native sheet created:',drawing.s.name)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',choices=STAGES,required=True)
    migrate(parser.parse_args().stage)
