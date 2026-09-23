"""Deterministic native KiCad review project; unfinished circuits are explicit interfaces.

Supply and safety connectors are EXTERNAL boundary contracts, not pretend PMICs
or safety-certified logic. This project is not authorized for fabrication.
"""
from pathlib import Path
import json
import uuid

NS = uuid.UUID('7bd56f8d-8dbc-460c-a25a-9f28b02707fd')
def uid(value): return str(uuid.uuid5(NS,str(value)))
def q(value): return json.dumps(str(value),ensure_ascii=True)
def n(value): return f'{value:.2f}'.rstrip('0').rstrip('.')
def fx(size=1.27): return f'(effects (font (size {n(size)} {n(size)})))'

class Project:
    def __init__(self):
        self.defs={};self.pages=[];self.root=uid('root');self.expected={}
    def definition(self,name,pins,half=25.4,width=15.24,passive=False):
        """pins: (number, displayed name, electrical type, x, y, orientation)."""
        pintext=[]
        for number,label,typ,x,y,angle in pins:
            length=3.81 if passive and name=='C' else 2.54 if passive else 5.08
            pintext.append(f'(pin {typ} line (at {n(x)} {n(y)} {angle}) (length {n(length)}) (name {q(label)} {fx()}) (number {q(number)} {fx()}))')
        if passive and name=='C':
            shape='(polyline (pts (xy -1.27 2.54) (xy -1.27 -2.54)) (stroke (width 0.254) (type default)) (fill (type none))) (polyline (pts (xy 1.27 2.54) (xy 1.27 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))'
        elif passive:
            shape='(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width 0.254) (type default)) (fill (type none)))'
        else:
            shape=f'(rectangle (start {-width} {n(half)}) (end {width} {n(-half)}) (stroke (width 0.254) (type default)) (fill (type background)))'
        text=f'''(symbol {q(name)} (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
(property "Reference" "U" (at 0 {n(half+3.81)} 0) {fx()})
(property "Value" {q(name)} (at 0 {n(-half-3.81)} 0) {fx()})
(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
(symbol {q(name+'_0_1')} {shape})
(symbol {q(name+'_1_1')} {' '.join(pintext)}))'''
        self.defs[name]=(text,pins,half)
        return name
    def connector_def(self,name,entries):
        # entries = (pin number, label, electrical type)
        count=len(entries);rows=(count+1)//2;half=(rows+1)*2.54
        pins=[]
        for i,(number,label,typ) in enumerate(entries):
            right=i%2==1
            y=(rows-1)*2.54-(i//2)*5.08
            pins.append((str(number),label,typ,20.32 if right else -20.32,y,180 if right else 0))
        return self.definition(name,pins,half)
    def save(self,out):
        libs='\n'.join(v[0] for v in self.defs.values())
        (out/'revb.kicad_sym').write_text(f'(kicad_symbol_lib (version 20231120) (generator kicad_symbol_editor)\n{libs}\n)\n')
        (out/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "RevB") (type "KiCad") (uri "${KIPRJMOD}/revb.kicad_sym") (options "") (descr "Generated single-SoC interface review")))\n')
        (out/'servohil_io_revB.kicad_pro').write_text('{}\n')
        children=[]
        for i,page in enumerate(self.pages):
            page.save(out)
            x=25.4+(i%2)*177.8;y=50.8+(i//2)*60.96
            children.append(f'''(sheet (at {n(x)} {n(y)}) (size 139.7 35.56)
(stroke (width 0.254) (type default)) (fill (color 0 0 0 0))
(uuid "{page.sheet_id}") (property "Sheetname" "{page.name}" (at {n(x)} {n(y-2.54)} 0) {fx()})
(property "Sheetfile" "{page.name}.kicad_sch" (at {n(x)} {n(y+38.1)} 0) {fx()})
(instances (project "servohil_io_revB" (path "/{self.root}" (page "{i+2}")))))''')
        note='REVIEW ONLY: direct single-SoC host + 8 AO. Supply, safety and ADC/PHY interfaces are NOT completed onboard circuits. NO PCB LAYOUT.'
        top=f'''(kicad_sch (version 20231120) (generator eeschema) (uuid "{self.root}") (paper "A3")
(title_block (title "ServoHIL Rev.B - single SoC / direct carrier") (rev "B-review") (company "magic-alt/servoHIL"))
(lib_symbols)
(text {q(note)} (at 25.4 25.4 0) (effects (font (size 1.524 1.524)) (justify left bottom)) (uuid "{uid('top-note')}"))
{' '.join(children)} (sheet_instances (path "/" (page "1"))))\n'''
        (out/'servohil_io_revB.kicad_sch').write_text(top)
        (out/'expected_connections.json').write_text(json.dumps(self.expected,sort_keys=True,indent=2)+'\n')

class Sheet:
    def __init__(self,project,name,title):
        self.p=project;self.name=name;self.title=name.replace('_',' ');self.sheet_id=uid(name);self.items=[];self.used=set();self.seq=0
        project.pages.append(self)
        self.text(title,25.4,25.4)
    def newid(self):
        self.seq+=1;return uid(self.name+str(self.seq))
    def text(self,text,x,y):
        self.items.append(f'(text {q(text)} (at {n(x)} {n(y)} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{self.newid()}"))')
    def label(self,net,x,y,angle=0):
        justify='right' if angle==180 else 'left'
        self.items.append(f'''(global_label {q(net)} (shape bidirectional) (at {n(x)} {n(y)} {angle})
(effects (font (size 1.27 1.27)) (justify {justify})) (uuid "{self.newid()}")
(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {n(x)} {n(y)} 0) (effects (font (size 1.27 1.27)) hide)))''')
    def instance(self,definition,ref,value,x,y,mapping,dnp=False):
        self.used.add(definition)
        _,pins,half=self.p.defs[definition]
        ref_y=y-half-5.08;val_y=y+half+5.08
        inst=f'''(symbol (lib_id "RevB:{definition}") (at {n(x)} {n(y)} 0) (unit 1)
(in_bom yes) (on_board yes) (dnp {'yes' if dnp else 'no'}) (uuid "{self.newid()}")
(property "Reference" {q(ref)} (at {n(x)} {n(ref_y)} 0) {fx()})
(property "Value" {q(value)} (at {n(x)} {n(val_y)} 0) {fx()})
(property "Footprint" "" (at {n(x)} {n(y)} 0) (effects (font (size 1.27 1.27)) hide))
(property "Datasheet" "" (at {n(x)} {n(y)} 0) (effects (font (size 1.27 1.27)) hide))
{' '.join(f'(pin {q(z[0])} (uuid "{self.newid()}"))' for z in pins)}
(instances (project "servohil_io_revB" (path "/{self.p.root}/{self.sheet_id}" (reference {q(ref)}) (unit 1)))))'''
        self.items.append(inst)
        for number,_,_,px,py,_ in pins:
            ax,ay=x+px,y-py;net=mapping.get(str(number))
            if net is None:
                self.items.append(f'(no_connect (at {n(ax)} {n(ay)}) (uuid "{self.newid()}"))')
            else:
                # Move the label outward instead of drawing its text over the pin/body.
                lx=ax+(-5.08 if px<0 else 5.08)
                self.items.append(f'(wire (pts (xy {n(ax)} {n(ay)}) (xy {n(lx)} {n(ay)})) (stroke (width 0) (type default)) (uuid "{self.newid()}"))')
                self.label(net,lx,ay,180 if px<0 else 0)
                self.p.expected[f'{ref}.{number}']=net
    def passive(self,kind,ref,value,x,y,a,b,dnp=False):
        self.instance(kind,ref,value,x,y,{'1':a,'2':b},dnp)
    def save(self,out):
        defs=[]
        for name in sorted(self.used):
            text=self.p.defs[name][0].replace(f'(symbol {q(name)}',f'(symbol "RevB:{name}"',1)
            defs.append(text)
        s=f'''(kicad_sch (version 20231120) (generator eeschema) (uuid "{uid(self.name+'-file')}") (paper "A3")
(title_block (title {q(self.title)}) (rev "B-review") (company "magic-alt/servoHIL")
(comment 1 "NON-RELEASE: physical power, safety, timing and package reviews remain open"))
(lib_symbols {' '.join(defs)})
{' '.join(self.items)}
)\n'''
        (out/(self.name+'.kicad_sch')).write_text(s)

def build(d,profile,physical,assignments,out: Path):
    p=Project()
    for kind in ['R','C']:
        p.definition(kind,[('1','1','passive',-5.08,0,0),('2','2','passive',5.08,0,180)],half=0,passive=True)
    sig={s['net']:s for s in d['signals']}
    pinmap={(r['connector'],int(r['pin'])):r['net'] for r in assignments}
    # Carrier interface. Source/sink pin types model the purchased HOST at its connector.
    host=Sheet(p,'01_carrier_interface','01 - Purchased carrier connectors: direct peripheral I/O')
    for i,conn in enumerate(sorted({r['connector'] for r in physical})):
        rows=[r for r in physical if r['connector']==conn]
        entries=[];mapping={}
        for row in rows:
            number=str(row['pin']);net=pinmap.get((conn,int(number)))
            typ='passive'
            if net: typ={'input':'input','output':'output','inout':'bidirectional'}[sig[net]['direction']]
            display_name='AXU_3V3' if row['board_signal']=='VCC_3V3_BUCK4' else row['board_signal']
            entries.append((number,display_name,typ))
            mapping[number]=net if net else 'GND' if row['kind']=='ground' else None
        name=p.connector_def('HOST_'+conn,entries)
        host.instance(name,conn,conn+' / PURCHASED HOST boundary',88.9+i*215.9,111.76,mapping)
    host.text('Connector power contacts remain NC. 64 assigned GPIO; unused GPIO also NC. No secondary compute chip.',25.4,190.5)
    host.text('J12 and J15 are ORIGINAL AXU2CGB interfaces, not AXU2CGB-I or -E. No board-power backfeed through contacts.',25.4,200.66)
    host.text('Signal-pin backfeed, output enable and bank power sequencing STILL REQUIRE electrical review.',25.4,210.82)
    # External bench rails and independent safety integration boundary; no fake PMIC.
    power=Sheet(p,'02_power_safety_boundary','02 - External regulated I/O rails and independent safety boundary')
    rails=['+5V0_DAC','+5V2_PVDD','-5V2_PVSS','1V8_D','3V3_D','VREF_2V5','GND']
    name=p.connector_def('SUPPLY_INTERFACE',[(str(i+1),v,'power_out') for i,v in enumerate(rails)])
    power.instance(name,'J1','EXTERNAL BENCH RAILS ONLY',88.9,76.2,{str(i+1):v for i,v in enumerate(rails)})
    safe=[('1','ARM_IN','input'),('2','WDI_IN','input'),('3','FAULT_N','output'),('4','DAC_RESET_N','output'),('5','V3V3','power_in'),('6','V1V8','power_in'),('7','GND','power_in')]
    name=p.connector_def('SAFETY_INTERFACE',safe)
    power.instance(name,'J2','EXTERNAL INDEPENDENT SAFETY - NOT IMPLEMENTED HERE',292.1,76.2,dict(zip([str(i+1) for i in range(7)],['HIL_ARM','HIL_WDI','HIL_FAULT_N','DAC_RESET_N','3V3_D','1V8_D','GND'])))
    power.passive('R','R1','10k default RESET asserted',292.1,127,'DAC_RESET_N','GND')
    power.text('These connectors are explicit unfinished integration boundaries, NOT completed onboard power/safety ICs.',25.4,170.18)
    power.text('Do not power DAC outputs before power sequencing, CFB stability and independent DUT inhibit are reviewed.',25.4,180.34)
    power.text('A DAC RESET is NOT proof of safe current. DUT midpoint voltage and physical power-stage inhibit are profile-specific.',25.4,190.5)
    power.text('The expansion board has no SoC core rail, DDR, configuration flash or extra FPGA clock/JTAG.',25.4,200.66)
    # Reserved peripheral interfaces: proper drivers/sinks, but no false ADC/PHY implementation.
    peripherals=Sheet(p,'03_peripheral_boundaries','03 - ADC and digital PHY integration interfaces (reserved)')
    for ref,groups,x,y in [('J3',{'adc'},88.9,111.76),('J4',{'pwm','encoder0','encoder1','aux','rs485','management'},292.1,111.76)]:
        signals=[s for s in d['signals'] if s['group'] in groups]
        entries=[];mapping={}
        for i,s in enumerate(signals):
            typ={'input':'output','output':'input','inout':'bidirectional'}[s['direction']]
            entries.append((str(i+1),s['net'],typ));mapping[str(i+1)]=s['net']
        entries.append((str(len(entries)+1),'GND','passive'));mapping[str(len(entries))]='GND'
        name=p.connector_def(ref+'_INTERFACE',entries)
        peripherals.instance(name,ref,'RESERVED MODULE INTERFACE - PHY/ADC NOT POPULATED',x,y,mapping)
    peripherals.text('Eight AI channels are an interface reservation. No 1 MSPS verification is implied; 1.8V serial timing must be closed.',25.4,218.44)
    peripherals.text('Each encoder uses one selected profile; ABZ/SSI/BiSS/SPI are NOT simultaneously independent ports.',25.4,228.6)
    # Accurate electrical pin names/numbers from AD3542R Rev.C pp11-12; package still not bound.
    left=[('1','DVDD','power_in'),('2','VLOGIC','power_in'),('3','CS_N','input'),('4','SCLK','input'),('5','SDIO0','bidirectional'),('6','SDIO1','bidirectional'),('7','LDAC_N','input'),('8','RESET_N','input'),('9','ALERT_N','output'),('10','AGND','power_in'),('16','PVDD','power_in'),('17','AVDD','power_in'),('18','VREF','input'),('19','CVREF','passive')]
    right=[('11','CAP1','passive'),('12','VOUT1','output'),('13','RFB1_1','passive'),('14','RFB2_1','passive'),('15','RFB4_1','passive'),('20','VOUT0','output'),('21','RFB4_0','passive'),('22','RFB2_0','passive'),('23','RFB1_0','passive'),('24','CAP0','passive'),('25','PVSS','power_in'),('26','AGND','power_in'),('27','DGND','power_in'),('28','DNC','passive')]
    pins=[]
    for side,entries in [(-1,left),(1,right)]:
        for i,(number,name,typ) in enumerate(entries):
            pins.append((number,name,typ,side*20.32,33.02-i*5.08,0 if side<0 else 180))
    p.definition('AD3542R',pins,38.1)
    for page_no,first in [(4,0),(5,2)]:
        sh=Sheet(p,f'0{page_no}_dac_{first*2}_{first*2+3}',f'0{page_no} - AD3542R eight-AO candidate: channels {first*2}-{first*2+3}')
        for col,index in enumerate(range(first,first+2)):
            x=76.2+col*203.2;y=88.9
            v0=f'DAC{index}_VOUT0';v1=f'DAC{index}_VOUT1';cap0=f'DAC{index}_CAP0';cap1=f'DAC{index}_CAP1';cv=f'DAC{index}_CVREF'
            mapping={'1':'1V8_D','2':'1V8_D','3':f'DAC_CS{index}_N','4':'DAC_SCLK','5':f'DAC_SDIO{index*2}','6':f'DAC_SDIO{index*2+1}','7':'DAC_LDAC_N','8':'DAC_RESET_N','9':f'DAC_ALERT{index}_N','10':'GND','11':cap1,'12':v1,'14':v1,'16':'+5V2_PVDD','17':'+5V0_DAC','18':'VREF_2V5','19':cv,'20':v0,'22':v0,'24':cap0,'25':'-5V2_PVSS','26':'GND','27':'GND'}
            sh.instance('AD3542R','U'+str(20+index),'AD3542RBCPZ16 / package review OPEN',x,y,mapping)
            base=300+index*20
            sh.passive('C','C'+str(base),'DNP C0G CFB0 REVIEW',x+66.04,60.96,cap0,v0,True)
            sh.passive('C','C'+str(base+1),'DNP C0G CFB1 REVIEW',x+66.04,81.28,cap1,v1,True)
            sh.passive('R','R'+str(base),'52.3R START',x+66.04,101.6,v0,'AO'+str(index*2))
            sh.passive('R','R'+str(base+1),'52.3R START',x+66.04,121.92,v1,'AO'+str(index*2+1))
            for j,(rail,val) in enumerate([(cv,'1uF'),('1V8_D','4.7uF'),('+5V0_DAC','1uF'),('+5V2_PVDD','4.7uF'),('-5V2_PVSS','4.7uF'),('VREF_2V5','100nF')]):
                sh.passive('C','C'+str(base+2+j),val,x-25.4+(j%2)*88.9,157.48+(j//2)*20.32,rail,'GND')
        sh.text('RFB2 selects +/-5V capability; RFB1/RFB4/DNC are not connected. CFB and load stability are NOT approved.',25.4,233.68)
        sh.text('External reference configuration and power-up register settings must be verified before enabling outputs.',25.4,243.84)
    outpage=Sheet(p,'06_analog_outputs','06 - Eight analog outputs to reviewed DUT adapter')
    name=p.connector_def('AO_INTERFACE',[(str(i+1),'AO'+str(i),'passive') for i in range(8)]+[('9','GND','passive'),('10','GND','passive')])
    outpage.instance(name,'J5','AO0..AO7 - NOT MCU-safe without adapter',127,101.6,{**{str(i+1):'AO'+str(i) for i in range(8)},'9':'GND','10':'GND'})
    outpage.text('Default metadata: Ia, Ib, Ic, Vbus, torque, temperature, AUX0, AUX1. Electrical channels are equivalent.',25.4,160.02)
    outpage.text('DUT adapter supplies scaling/clamping and hardware inhibition. No direct +/-5V connection to MCU ADC.',25.4,170.18)
    p.save(out)
