"""Independent package-pin oracle for the Rev.B populated peripheral delta.

References: AD7606C-16 Rev.A pp15-17/43/58; THVD1450 Rev.E p5;
SN74LVC541A Rev.O p4; SN74LVC1G08 Rev.Z p3. These rules neither draw
schematics nor establish electrical/physical qualification.
"""
PARTS={}
PINS={}
REMOVED_RESERVED={'J3','J4'}
R0603='Resistor_SMD:R_0603_1608Metric'
C0603='Capacitor_SMD:C_0603_1608Metric'
C0805='Capacitor_SMD:C_0805_2012Metric'
SO8='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
SOT5='Package_TO_SOT_SMD:SOT-23-5'
HEADER='Connector_PinHeader_2.54mm:PinHeader_'

def part(ref,value,pins,footprint):
    if ref in PARTS:raise ValueError('duplicate oracle reference: '+ref)
    PARTS[ref]={'value':value,'footprint':footprint}
    PINS.update({f'{ref}.{p}':n for p,n in pins.items()})

def resistor(ref,value,a,b,footprint=R0603):part(ref,value,{1:a,2:b},footprint)
def cap(ref,value,a,b='GND',footprint=C0603):part(ref,value,{1:a,2:b},footprint)
def header(ref,value,pins,shape):part(ref,value,pins,HEADER+shape+'_P2.54mm_Vertical')

adc={1:'+5V0_DAC',37:'+5V0_DAC',38:'+5V0_DAC',48:'+5V0_DAC',
     2:'GND',26:'GND',35:'GND',40:'GND',41:'GND',47:'GND',
     3:'1V8_D',4:'1V8_D',5:'1V8_D',6:'1V8_D',7:'1V8_D',8:'1V8_D',10:'1V8_D',
     9:'ADC_CONVST_IC',11:'ADC_RESET_IC',12:'ADC_SCLK_IC',13:'ADC_CS_N_IC',
     14:'ADC_BUSY_RAW',15:'ADC_FRSTDATA',16:'GND',17:'GND',18:'GND',
     19:'ADC_DOUT4_RAW',20:'ADC_DOUT5_RAW',21:'ADC_DOUT6_RAW',22:'ADC_DOUT7_RAW',
     23:'1V8_D',24:'ADC_DOUT0_RAW',25:'ADC_DOUT1_RAW',27:'ADC_DOUT2_RAW',28:'ADC_DOUT3_RAW',
     29:'ADC_SDI_IC',30:'GND',31:'GND',32:'GND',33:'GND',34:'1V8_D',
     36:'ADC_REGCAP_A',39:'ADC_REGCAP_D',42:'ADC_REFINT',43:'GND',
     44:'ADC_REFBUF',45:'ADC_REFBUF',46:'GND'}
for ch in range(8):adc[49+2*ch]=f'AI{ch}_P';adc[50+2*ch]=f'AI{ch}_N'
part('U801','AD7606C-16BSTZ',adc,'Package_QFP:LQFP-64_10x10mm_P0.5mm')
for n in range(801,805):cap(f'C{n}','100n','+5V0_DAC')
cap('C805','10u','+5V0_DAC',footprint=C0805)
cap('C806','100n','1V8_D')
cap('C807','1u','ADC_REGCAP_A',footprint=C0805)
cap('C808','1u','ADC_REGCAP_D',footprint=C0805)
cap('C809','100n','ADC_REFINT')
cap('C810','10u','ADC_REFBUF',footprint=C0805)
for i,name in enumerate(['SCLK','CS_N','SDI','CONVST','RESET']):
    resistor(f'R{801+i}','33','ADC_'+name,'ADC_'+name+'_IC')
for ch in range(8):resistor(f'R{820+ch}','33',f'ADC_DOUT{ch}_RAW',f'ADC_DOUT{ch}')
resistor('R828','33','ADC_BUSY_RAW','ADC_BUSY')
for i,(name,rail) in enumerate([('CS_N','1V8_D'),('RESET','1V8_D'),('CONVST','GND'),('SCLK','GND'),('SDI','GND')]):
    resistor(f'R{830+i}','10k','ADC_'+name+'_IC',rail)
part('TP801','ADC_FRSTDATA',{1:'ADC_FRSTDATA'},'TestPoint:TestPoint_Pad_D1.0mm')
input_pins={}
for ch in range(8):
    input_pins[2*ch+1]=f'AI{ch}_IN';input_pins[2*ch+2]='GND'
    resistor(f'R{850+2*ch}','100',f'AI{ch}_IN',f'AI{ch}_P')
    resistor(f'R{851+2*ch}','100','GND',f'AI{ch}_N')
    cap(f'C{850+ch}','1n',f'AI{ch}_P',f'AI{ch}_N')
header('J801','AI0..7 / GND - LOW ENERGY +/-10V',input_pins,'2x08')

# Each pair is one half-duplex THVD1450 with an always-enabled receiver.
# Board + bus grounds are shared; NOT an isolated industrial port.
for pair in range(4):
    port,lane=divmod(pair,2);prefix=f'ENC{port}_P{lane}'
    part(f'U{901+pair}','THVD1450DR',{1:prefix+'_RX',2:'GND',3:prefix+'_DE',4:prefix+'_TX',
         5:'GND',6:prefix+'_A',7:prefix+'_B',8:'3V3_D'},SO8)
    part(f'U{911+pair}','SN74LVC1G08DBVR',{1:'SAFE_ENABLE',2:f'ENC{port}_DIR{lane}',3:'GND',4:prefix+'_DE',5:'3V3_D'},SOT5)
    resistor(f'R{901+pair*5}','100',f'ENC{port}_IO{lane*2}',prefix+'_TX')
    resistor(f'R{902+pair*5}','100',prefix+'_RX',f'ENC{port}_IO{lane*2+1}')
    resistor(f'R{903+pair*5}','10k',f'ENC{port}_DIR{lane}','GND')
    resistor(f'R{904+pair*5}','10k',prefix+'_TX','GND')
    resistor(f'R{905+pair*5}','10k',prefix+'_DE','GND')
    resistor(f'R{950+pair}','120',prefix+'_A',prefix+'_TERM','Resistor_SMD:R_1206_3216Metric')
    header(f'JP{901+pair}','TERM - SHUNT ABSENT',{1:prefix+'_TERM',2:prefix+'_B'},'1x02')
    cap(f'C{901+pair}','100n','3V3_D');cap(f'C{911+pair}','100n','3V3_D')
for port in range(2):
    header(f'J{901+port}','SSI/BiSS CLK/DATA - NO POWER',
      {1:f'ENC{port}_P0_A',2:f'ENC{port}_P0_B',3:f'ENC{port}_P1_A',4:f'ENC{port}_P1_B',5:'GND',6:'GND'},'2x03')
    cap(f'C{921+port}','1u','3V3_D',footprint=C0805)

part('U1001','THVD1450DR',{1:'RS485_RX_RAW',2:'GND',3:'RS485_DE_SAFE',4:'RS485_TX_IC',
     5:'GND',6:'RS485_A',7:'RS485_B',8:'3V3_D'},SO8)
part('U1002','SN74LVC1G08DBVR',{1:'SAFE_ENABLE',2:'RS485_DE',3:'GND',4:'RS485_DE_SAFE',5:'3V3_D'},SOT5)
resistor('R1001','100','RS485_TX','RS485_TX_IC')
resistor('R1002','100','RS485_RX_RAW','RS485_RX')
resistor('R1003','10k','RS485_DE','GND');resistor('R1004','10k','RS485_TX_IC','GND')
resistor('R1005','10k','RS485_DE_SAFE','GND')
resistor('R1006','120','RS485_A','RS485_TERM','Resistor_SMD:R_1206_3216Metric')
header('JP1001','TERM - SHUNT ABSENT',{1:'RS485_TERM',2:'RS485_B'},'1x02')
header('J1004','RS485 A/B/GND',{1:'RS485_A',2:'RS485_B',3:'GND'},'1x03')
cap('C1001','100n','3V3_D');cap('C1002','100n','3V3_D')
pwm={1:'GND',19:'GND',10:'GND',20:'3V3_D',8:'GND',9:'GND',12:None,11:None}
pwm_pins={}
for ch,name in enumerate(['UH','UL','VH','VL','WH','WL']):
    net='PWM_'+name
    pwm[ch+2]=net+'_IC';pwm[18-ch]=net
    pwm_pins[ch*2+1]=net+'_IN';pwm_pins[ch*2+2]='GND'
    resistor(f'R{1010+ch}','100',net+'_IN',net+'_IC')
    resistor(f'R{1020+ch}','10k',net+'_IC','GND')
part('U1010','SN74LVC541APWR',pwm,'Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm')
header('J1001','SIX PWM / GND - 3.3V LOGIC ONLY',pwm_pins,'2x06')
cap('C1010','100n','3V3_D');cap('C1011','1u','3V3_D',footprint=C0805)
aux={7:'GND',8:'GND'}
for ch in range(6):
    aux[ch+1]=f'AUX{ch}_PORT'
    resistor(f'R{1030+ch}','100',f'AUX_IO{ch}',f'AUX{ch}_PORT')
    resistor(f'R{1040+ch}','100k',f'AUX{ch}_PORT','GND')
header('J1002','AUX 3.3V LOGIC / GND',aux,'2x04')
header('J1003','I2C 3.3V / GND',{1:'MGMT_SCL',2:'MGMT_SDA',3:'GND',4:'GND'},'1x04')
resistor('R1050','4.7k','MGMT_SCL','3V3_D');resistor('R1051','4.7k','MGMT_SDA','3V3_D')


def check_pins(nets,members):
    for key,expected in PINS.items():
        if expected is None:
            if key in nets and members[nets[key]]!={key}:
                raise ValueError('peripheral required NC wired: '+key)
        elif nets.get(key)!=expected:
            raise ValueError(f'peripheral pin {key}: expected {expected}, got {nets.get(key)}')
    extra={k for k in nets if k.rsplit('.',1)[0] in PARTS}-set(PINS)
    if extra:raise ValueError('unexpected peripheral physical pins: '+str(sorted(extra)))
    for n in ('ADC_REGCAP_A','ADC_REGCAP_D'):
        required={'U801.36','C807.1'} if n.endswith('_A') else {'U801.39','C808.1'}
        if members[n]!=required:raise ValueError('regulator capacitor output short/load: '+n)
    if members['ADC_REFBUF']!={'U801.44','U801.45','C810.1'}:
        raise ValueError('reference buffer must only drive its decoupling capacitor')
    return {'peripheral_components':len(PARTS),'peripheral_pin_assertions':len(PINS),
            'removed_reserved_headers':sorted(REMOVED_RESERVED)}
