"""One-time entry of internally compensated bucks and low-noise positive DAC rails."""
from pr17_native import Drawing


def positive_sheet():
    d=Drawing('20_positive_rails','POSITIVE POWER: 6.184V preregulator / 3.296V / 1.792V + LT3045 DAC rails')
    d.s.paper='A2'
    d.ic('AP63201_TSOT26',[(3,'VIN','power_in'),(2,'EN','input'),(4,'GND','power_in')],[(6,'BST','passive'),(5,'SW','power_out'),(1,'FB','input')])
    variants=[(201,88.9,'6V2_PRE','67.3k 0.1%','10uH / Isat >=3A / DCR <100mOhm'),(202,266.7,'3V3_D','31.2k 0.1%','6.8uH / Isat >=3A / DCR <100mOhm'),(203,444.5,'1V8_D','12.4k 0.1%','4.7uH / Isat >=3A / DCR <100mOhm')]
    for index,x,rail,rt,ind in variants:
        sw=f'SW_{index}';bst=f'BST_{index}';fb=f'FB_{index}';base=210+(index-201)*10
        d.add('AP63201_TSOT26',f'U{index}','AP63201WU-7 / 500kHz FPWM',x,71.12,{3:'VIN_PROT',2:'INPUT_OK',4:'GND',6:bst,5:sw,1:fb},'Package_TO_SOT_SMD:TSOT-23-6','https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf')
        d.add('L',f'L{index}',ind,x+63.5,71.12,{1:sw,2:rail})
        d.c(f'C{base}','100nF / 16V bootstrap',x+63.5,43.18,bst,sw)
        d.c(f'C{base+1}','10uF / 50V X7R',x-35.56,116.84,'VIN_PROT','GND')
        d.c(f'C{base+2}','100nF / 50V',x+63.5,116.84,'VIN_PROT','GND')
        d.c(f'C{base+3}','22uF / 16V X7R, 1210',x-35.56,139.7,rail,'GND')
        d.c(f'C{base+4}','22uF / 16V X7R, 1210',x+63.5,139.7,rail,'GND')
        d.r(f'R{base}',rt,x-35.56,162.56,rail,fb)
        d.r(f'R{base+1}','10k 0.1%',x+63.5,162.56,fb,'GND')
        d.r(f'R{base+2}','2.2k bleeder',x-35.56,185.42,rail,'GND')
        d.flag(f'PF{index}',x+63.5,185.42,rail)
        d.tp(f'TP{index}',x+63.5,205.74,rail)
    d.r('R201','100k / EN default low',35.56,226.06,'INPUT_OK','GND')
    d.ic('LT3045_MSE',[(1,'IN1','power_in'),(2,'IN2','power_in'),(3,'IN3','power_in'),(4,'EN_UV','input'),(6,'ILIM','passive'),(9,'GND','power_in'),(13,'EP_GND','power_in')],[(12,'OUT2','power_out'),(11,'OUT1','power_out'),(10,'OUTS','input'),(8,'SET','passive'),(5,'PG','open_collector'),(7,'PGFB','input')])
    for index,x,rail,setr,pg,rpg in [(211,139.7,'+5V0_DAC','49.9k 0.1%','PG_5V0','150k 0.1%'),(212,419.1,'+5V2_PVDD','52.0k 0.1%','PG_PVDD','158k 0.1%')]:
        base=240+(index-211)*20;setnet=f'SET_{index}';ilim=f'ILIM_{index}';sense=f'PGFB_{index}'
        d.add('LT3045_MSE',f'U{index}','LT3045EMSE#PBF / complete 12+EP pins',x,289.56,{1:'6V2_PRE',2:'6V2_PRE',3:'6V2_PRE',4:'INPUT_OK',6:ilim,9:'GND',13:'GND',12:rail,11:rail,10:rail,8:setnet,5:pg,7:sense},source='https://www.analog.com/media/en/technical-documentation/data-sheets/lt3045.pdf')
        d.r(f'R{base}',setr,x-88.9,254,setnet,'GND')
        d.c(f'C{base}','470nF / 16V SET',x+88.9,254,setnet,'GND')
        d.r(f'R{base+1}','499R / 300mA nominal limit',x-88.9,276.86,ilim,'GND')
        d.r(f'R{base+2}',rpg,x+88.9,276.86,rail,sense)
        d.r(f'R{base+3}','10k 0.1%',x+88.9,299.72,sense,'GND')
        d.r(f'R{base+4}','10k',x-88.9,299.72,'3V3_AON',pg)
        d.c(f'C{base+1}','10uF / 16V',x-88.9,327.66,'6V2_PRE','GND')
        d.c(f'C{base+2}','100nF / 16V',x+88.9,327.66,'6V2_PRE','GND')
        d.c(f'C{base+3}','22uF / 16V X7R, 1210',x-88.9,350.52,rail,'GND')
        d.c(f'C{base+4}','22uF / 16V X7R, 1210',x+88.9,350.52,rail,'GND')
        d.tp(f'TP{index}',x,350.52,rail)
    d.s.text('Bucks: AP63201 internal compensation; no invented COMP network. Cout requires >=20uF EFFECTIVE per buck after DC-bias/temperature.',25.4,375.92)
    d.s.text('Power budgets: 6V2_PRE 0.50A, 3V3_D 0.30A, 1V8_D 0.30A; +5V0_DAC 0.20A, +5V2_PVDD 0.12A. NOT a 2A-per-rail board rating.',25.4,383.54)
    d.s.text('LT3045 OUTS and SET require Kelvin routing. MSE EP13=GND. +5V0 PG trip ~4.80V; +5V2 PG trip ~5.04V. Layout/thermal/loop response OPEN.',25.4,391.16)
    # Fix capacitor package on high-capacitance parts, using actual instance properties.
    for i,item in enumerate(d.s.items):
        if '(symbol (lib_id ' in item and ('22uF' in item or '10uF / 50V' in item):
            d.s.items[i]=item.replace('Capacitor_SMD:C_0805_2012Metric','Capacitor_SMD:C_1210_3225Metric')
    return d
