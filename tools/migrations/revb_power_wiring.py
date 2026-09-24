"""Explicit page-local layouts for existing native components; no electrical value changes."""
from revb_wiring import Editor


def input_power(directory):
    d=Editor(directory,'10_input_protection','INPUT PROTECTION - fuse / reverse diode / eFuse / always-on regulator')
    for ref,x,y,a in [('J101',10,25,0),('F101',30,24,0),('D101',42,24,180),
                      ('D102',50,32,270),('C101',56,32,270),('C102',62,32,270),
                      ('U101',82,28,0),('R101',46,43,270),('R102',46,53,270),('R103',46,63,270),
                      ('R104',105,56,270),('R105',105,66,270),('R106',101,47,270),('R107',138,19,270),
                      ('C103',93,47,270),('C104',117,47,270),('C105',122,32,270),('C106',131,32,270),
                      ('SW101',32,53,0),('U102',111,85,0),('C107',94,89,270),('C108',131,89,270),('C109',140,89,270)]:d.place(ref,x,y,a)
    d.anchor('PF101',1,52,19)
    d.wire('VIN_RAW','J101.1','F101.1');d.label('VIN_RAW',(22,24))
    d.wire('VIN_FUSED','F101.2','D101.2');d.label('VIN_FUSED',(34,24))
    d.bus('VIN_EFUSE',24,['D101.1','D102.1','C101.1','C102.1','U101.5','R101.1'],44,74)
    d.wire('VIN_EFUSE','PF101.1',(52,24))
    d.gnd('J101',2,4)
    for ref in ('D102','C101','C102','C103','C104','C105','C106','R103','R105','R106','C107','C108','C109'):d.gnd(ref,2)
    d.wire('UVLO_IN','R101.2',(46,48),'R102.1')
    d.wire('UVLO_IN','U101.1',(70,26),(70,48),(46,48))
    d.wire('UVLO_IN','SW101.1',(30,48),(46,48));d.label('UVLO_IN',(49,48));d.gnd('SW101',2,4)
    d.wire('OVLO_IN','R102.2',(46,58),'R103.1')
    d.wire('OVLO_IN','U101.2',(67,28),(67,58),(46,58));d.label('OVLO_IN',(49,58))
    d.bus('VIN_PROT',24,['U101.6','C105.1','C106.1'],90,146)
    d.terminal('R104',1,-4)
    d.wire('PGTH_IN','R104.2',(105,61),'R105.1')
    d.wire('PGTH_IN','U101.4',(72,30),(72,76),(99,76),(99,61),(105,61));d.label('PGTH_IN',(99,73))
    d.wire('DVDT_IN','U101.7',(93,28),'C103.1');d.label('DVDT_IN',(93,40))
    d.wire('ILIM_IN','U101.9',(101,30),'R106.1');d.label('ILIM_IN',(101,40))
    d.wire('ITIMER_IN','U101.10',(117,32),'C104.1');d.label('ITIMER_IN',(117,40))
    d.wire('INPUT_OK','U101.3',(138,26),'R107.2');d.label('INPUT_OK',(135,26))
    d.terminal('R107',1,-3);d.gnd('U101',8,4)
    d.bus('VIN_PROT',79,['C107.1'],90,103)
    d.wire('VIN_PROT',(103,79),'U102.1')
    d.bus('3V3_AON',83,['U102.5','C108.1','C109.1'],119,147)
    d.gnd('U102',2,4)
    d.note('TPS70933 EN is intentionally open: internal pull-up. Never connect EN directly to 12 V.',8,105,1.0)
    d.note('TVS/fuse surge coordination remains unqualified. Use a current-limited SELV 9-15 V supply, not the motor DC bus.',8,109,1.0)
    d.note('UV/OV divider and PGTH paths are local wires. 474L is a latched circuit breaker, not a continuous current regulator.',8,113,1.0)
    d.finish()


def negative(directory):
    d=Editor(directory,'30_negative_reference','NEGATIVE RAIL / REFERENCE - wired Cuk converter, LT3094 and ADR4525')
    for ref,x,y,a in [('U301',42,42,0),('L301',30,25,0),('C410',53,25,0),('L302',75,25,0),
                      ('D301',64,34,90),('C411',12,34,270),('C412',21,34,270),('C413',57,49,270),
                      ('C414',90,34,270),('C415',100,34,270),('R410',82,52,270),('R411',82,64,270),
                      ('C416',94,52,270),('R412',107,45,270),('U302',150,42,0),
                      ('R420',168,54,270),('C420',178,54,270),('R421',125,60,270),
                      ('R422',201,49,270),('R423',201,61,270),('R424',218,60,270),
                      ('C421',122,40,270),('C422',129,40,270),('C423',173,40,270),('C424',184,40,270),
                      ('U303',50,100,0),('C430',25,105,270),('C431',34,105,270),('C432',78,106,270),('C433',90,106,270)]:d.place(ref,x,y,a)
    d.anchor('PF301',1,101,20);d.anchor('TP301',1,110,25);d.anchor('TP302',1,218,36);d.anchor('TP303',1,103,101)
    d.bus('VIN_PROT',25,['C411.1','C412.1','L301.1'],8,28)
    d.wire('VIN_PROT','U301.6',(26,40),(26,25))
    d.wire('SW_NEG','L301.2','C410.1')
    d.wire('SW_NEG',(44,25),(44,33),(53,33),(53,40),'U301.1');d.label('SW_NEG',(36,25))
    d.wire('NEG_X','C410.2','L302.1');d.wire('NEG_X',(64,25),'D301.2');d.label('NEG_X',(61,25))
    d.bus('-6V2_PRE',25,['L302.2','C414.1','C415.1','R410.1','C416.1','R412.1','TP301.1'],77,110)
    d.wire('-6V2_PRE','PF301.1',(101,25))
    d.terminal('U301',4,-3);d.gnd('U301',2)
    d.wire('INTVCC_NEG','U301.5',(57,44),'C413.1');d.label('INTVCC_NEG',(57,44))
    for ref in ('C411','C412','C413','C414','C415','R411','R412'):d.gnd(ref,2)
    d.gnd('D301',1)
    d.wire('FB_NEG','R410.2',(82,58),'R411.1')
    d.wire('FB_NEG','C416.2',(94,58),(82,58))
    d.wire('FB_NEG','U301.3',(60,42),(60,58),(82,58));d.label('FB_NEG',(66,58))
    # LT3094 input/EP connect to the negative preregulator, not to ground.
    d.bus('-6V2_PRE',30,['C421.1','C422.1'],118,134)
    d.wire('-6V2_PRE',(134,30),(134,52))
    for pin,y in [(1,36),(2,38),(3,40)]:d.wire('-6V2_PRE','U302.'+str(pin),(134,y))
    d.wire('-6V2_PRE','U302.13',(142,52),(134,52))
    d.wire('GND','U302.9',(138,46),(138,49));d.ground_at((138,49))
    d.wire('-5V2_PVSS','U302.11',(164,36),(164,40),'U302.10')
    d.wire('-5V2_PVSS','U302.12',(164,38))
    d.bus('-5V2_PVSS',36,['C423.1','C424.1','R422.1','TP302.1'],164,218)
    d.wire('SET_PVSS','U302.8',(168,42),'R420.1')
    d.wire('SET_PVSS',(168,48),(178,48),'C420.1');d.label('SET_PVSS',(169,48))
    d.wire('ILIM_PVSS','U302.6',(140,44),(140,56),(125,56),'R421.1');d.label('ILIM_PVSS',(125,56))
    d.wire('PGFB_PVSS','R422.2',(201,55),'R423.1')
    d.wire('PGFB_PVSS','U302.5',(136,42),(136,66),(198,66),(198,55),(201,55));d.label('PGFB_PVSS',(172,66))
    d.terminal('U302',4,3);d.terminal('R424',1,-3);d.terminal('R424',2,3)
    for ref in ('R420','C420','R421','R423','C421','C422','C423','C424'):d.gnd(ref,2)
    # Precision reference input/output capacitors physically surround the IC.
    d.bus('+5V0_DAC',93,['C430.1','C431.1'],20,40)
    d.wire('+5V0_DAC',(40,93),(40,99),'U303.2')
    d.bus('VREF_2V5',101,['U303.6','C432.1','C433.1','TP303.1'],58,103)
    for ref in ('C430','C431','C432','C433'):d.gnd(ref,2)
    d.gnd('U303',4,3)
    d.note('Cuk current path: VIN -> L301 -> C410 -> L302 -> negative output. D301 cathode is grounded.',8,77,1.1)
    d.note('Independent inductors; transfer capacitor sees VIN + |VOUT|. Existing component values are preserved.',8,82,1.1)
    d.note('LT3094 EP13 / EN3 connect to negative IN. OUTS/SET require Kelvin layout. No startup/ripple/thermal PASS is implied.',8,130,1.1)
    d.note('ADR4525: unused NIC/DNC pads remain NC. DAC external-reference configuration and actual fanout/load require validation.',8,135,1.1)
    d.finish()


def dac(directory):
    for name,first in [('04_dac_0_3',0),('05_dac_4_7',2)]:
        d=Editor(directory,name,'DAC - direct RFB2 feedback / CFB / output resistors; independent channels preserved')
        for col,i in enumerate(range(first,first+2)):
            off=col*75;base=300+i*20;u=f'U{20+i}'
            def p(x,y):return (x+off,y)
            def put(ref,x,y,a=0):return d.place(ref,x+off,y,a)
            put(u,40,40)
            put(f'C{base+1}',60,21);put(f'C{base}',60,43)
            put(f'R{base+1}',66,29);put(f'R{base}',66,37)
            put(f'C{base+2}',27,63,270)
            for j in range(5):put(f'C{base+3+j}',12+j*12,80,270)
            # Control signals really cross pages; retain one global per net per page.
            for pin in (3,4,5,6,7,8,9,16,17,18):d.terminal(u,pin,-3)
            d.wire('1V8_D',u+'.1',p(28,27),p(28,29),u+'.2');d.label('1V8_D',p(28,27),'right')
            d.wire('GND',u+'.10',p(22,45),p(22,47));d.ground_at(p(22,47))
            d.wire('GND',u+'.26',p(50,49),p(50,54));d.wire('GND',u+'.27',p(50,51));d.ground_at(p(50,54))
            d.terminal(u,25,6)
            v1=f'DAC{i}_VOUT1';v0=f'DAC{i}_VOUT0';cap1=f'DAC{i}_CAP1';cap0=f'DAC{i}_CAP0';cv=f'DAC{i}_CVREF'
            d.wire(v1,u+'.12',f'R{base+1}.1')
            d.wire(v1,u+'.14',p(55,33),p(55,29));d.label(v1,p(57,29))
            d.wire(cap1,u+'.11',p(51,27),p(51,21),f'C{base+1}.1');d.label(cap1,p(51,21))
            d.wire(v1,f'C{base+1}.2',p(62,29))
            d.wire(v0,u+'.20',f'R{base}.1')
            d.wire(v0,u+'.22',p(55,41),p(55,37));d.label(v0,p(57,37))
            d.wire(cap0,u+'.24',p(51,45),p(51,43),f'C{base}.1');d.label(cap0,p(51,43))
            d.wire(v0,f'C{base}.2',p(62,37))
            d.terminal(f'R{base}',2,3);d.terminal(f'R{base+1}',2,3)
            d.wire(cv,u+'.19',p(27,53),f'C{base+2}.1');d.label(cv,p(27,56));d.gnd(f'C{base+2}',2)
            for j in range(5):d.terminal(f'C{base+3+j}',1,-2)
            d.bus('GND',85,[f'C{base+3+j}.2' for j in range(5)],off+12,off+60,label=False);d.ground_at(p(36,85))
            d.note(f'U{20+i}: AO{i*2} / AO{i*2+1}. CFB remains DNP pending analog stability review.',off+8,94,1.0)
        d.note('Only inter-sheet signals use global labels. Feedback and output networks are drawn as visible closed local connections.',8,105,1.0)
        d.note('No electrical component/value change. CFB, output loading, package land pattern and hardware-safe AO behavior remain OPEN.',8,110,1.0)
        d.finish()
