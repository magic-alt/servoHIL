#!/usr/bin/env python3
"""One-shot PR18 hierarchy edit; never invoked by normal read-only CI.

No physical pin, value, footprint or package mapping is changed. Native pin
partition must match the independently exported original main after each stage.
"""
from __future__ import annotations
import copy
from pathlib import Path
import sys
from collections import Counter
from test_digital_drawing import NATIVE
from test_interface_wiring import POWER_NETS
from kicad_sexpr import parse, items, one, expr, Atom
from _apply_digital_drawing import pretty, uid, mm, put, props

ROOT_FILE = 'servohil_io_revA.kicad_sch'
HL = ['HL_TX_CLK'] + [f'HL_TX{i}' for i in range(8)] + ['HL_SYNC','HL_SAFE_N','HL_RESET_N','HL_HEARTBEAT','TRIG0','TRIG1','HL_RX_CLK'] + [f'HL_RX{i}' for i in range(8)] + ['HL_IRQ']
COMMON = ['DAC_SCLK','DAC_LDAC_N','DAC_RESET_N']
SUPPLIES = ['1V8_D','+5V0_DAC','+5V2_PVDD','-5V2_PVSS','VREF_2V5']
AO = ['AO0_IA','AO1_IB','AO2_IC','AO3_VBUS']

def dac_signals(start):
    return [f'DAC_CS{i}_N' for i in range(start,start+2)] + [f'DAC_SDIO{i}' for i in range(start*2,start*2+4)] + [f'DAC_ALERT{i}_N' for i in range(start,start+2)]

def shape(page, name):
    if name == 'GND': raise ValueError('Use a standard ground symbol, not a hierarchy pin')
    if page == '01': return 'input' if name == '3V3_AON' else 'output'
    if page == '02': return 'input' if name in ('12V_PROT','6V0_PRE','ANALOG_EN') else 'output'
    if page == '03': return 'input' if name in ('12V_PROT','EFUSE_PG') else 'output'
    if page == '04': return 'input' if name.startswith('HL_RX') or name == 'HL_IRQ' else 'output'
    if page == '05':
        if name.startswith('DAC_SDIO'): return 'bidirectional'
        return 'output' if name.startswith('HL_RX') or name == 'HL_IRQ' or (name.startswith('DAC_') and not name.startswith('DAC_ALERT')) else 'input'
    if page in ('06','07'):
        if name.startswith('DAC_SDIO'): return 'bidirectional'
        return 'output' if name.startswith('DAC_ALERT') or name in AO else 'input'
    raise ValueError((page,name))

def spans(text):
    """Top-level child spans, preserving all untouched schematic bytes."""
    depth = 0; quote = False; escaped = False; start = 0
    for i,c in enumerate(text):
        if quote:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': quote = False
            continue
        if c == '"': quote = True
        elif c == '(':
            depth += 1
            if depth == 2: start = i
        elif c == ')':
            if depth == 2: yield start, i+1
            depth -= 1
    assert depth == 0 and not quote

def migrate(full=False):
    for path in sorted(NATIVE.glob('*.kicad_sch')):
        if path.name == ROOT_FILE: continue
        text = path.read_text(); replacements = []
        tree = parse(text); ground_def = None
        for a,b in spans(text):
            block = text[a:b]
            if not block.startswith('(global_label'): continue
            n = parse(block); name = n[1]
            if not full and name not in POWER_NETS: continue
            if name == 'GND':
                source = parse((NATIVE/'01_power_entry.kicad_sch').read_text())
                ground_def = copy.deepcopy(next(s for s in items(one(source,'lib_symbols'),'symbol') if s[1]=='power:GND'))
                template = copy.deepcopy(next(s for s in items(source,'symbol') if one(s,'lib_id')[1]=='power:GND'))
                at = one(n,'at'); x,y=at[1:3]; ref='#PWRH'+path.name[:2]
                put(template,'at',expr(f'(at {x} {y} 0)')); put(template,'uuid',expr(f'(uuid "{uid(ref)}")'))
                for prop in items(template,'property'):
                    put(prop,'at',expr(f'(at {x} {y} 0)'))
                    put(prop,'effects',expr('(effects (font (size 1.016 1.016)) hide)'))
                props(template)['Reference'][2]=ref
                for pin in items(template,'pin'): put(pin,'uuid',expr(f'(uuid "{uid(ref+".1")}")'))
                inst=copy.deepcopy(one(items(tree,'symbol')[0],'instances'))
                for project in items(inst,'project'):
                    for p in items(project,'path'): one(p,'reference')[1]=ref
                put(template,'instances',inst)
                replacements.append((a,b,pretty(template)))
            else:
                n[0]=Atom('hierarchical_label')
                put(n,'shape',expr(f'(shape {shape(path.name[:2],name)})'))
                n[:]=[v for v in n if not (isinstance(v,list) and v and v[0]=='property')]
                replacements.append((a,b,pretty(n)))
        if ground_def is not None and not any(d[1]=='power:GND' for d in items(one(tree,'lib_symbols'),'symbol')):
            for a,b in spans(text):
                if text[a:b].startswith('(lib_symbols'):
                    lib=parse(text[a:b]);lib.append(ground_def);replacements.append((a,b,pretty(lib)))
        for a,b,repl in sorted(replacements,reverse=True):text=text[:a]+repl+text[b:]
        if replacements:path.write_text(text)
    draw_root()

def draw_root():
    path=NATIVE/ROOT_FILE; old=parse(path.read_text())
    tree=[old[0]]+[copy.deepcopy(n) for n in old[1:] if isinstance(n,list) and n[0] in ('version','generator','generator_version','uuid','paper','title_block','lib_symbols')]
    boxes={'01':(14,18,58,32),'03':(104,18,76,35),'02':(228,18,76,35),'04':(14,88,57,100),'05':(124,70,75,128),'06':(253,73,43,57),'07':(253,143,43,57)}
    locations={}; ports={}; routes=[]; named=[]
    def assign(page,names,side,x,ys):
        for name,y in zip(names,ys):locations[(page,name)]=(x,y,side)
    assign('01',['12V_PROT','EFUSE_PG','3V3_AON'],'right',72,[25,31,41])
    assign('03',['12V_PROT','EFUSE_PG'],'left',104,[25,31])
    assign('03',['1V0_FPGA','1V8_D','3V3_D','6V0_PRE','3V3_AON','ANALOG_EN','SEQ_DONE'],'right',180,[25,29,33,37,41,45,49])
    assign('02',['12V_PROT','6V0_PRE','ANALOG_EN'],'left',228,[25,37,45])
    assign('02',['+5V0_DAC','+5V2_PVDD','-5V2_PVSS','VREF_2V5'],'right',304,[25,31,37,43])
    assign('04',HL,'right',71,range(94,169,3));assign('05',HL,'left',124,range(94,169,3))
    assign('05',['1V0_FPGA','1V8_D','3V3_D','3V3_AON','SEQ_DONE'],'left',124,[75,79,83,87,180])
    assign('05',COMMON,'right',199,[79,83,87])
    for p,start,offset in [('06',0,0),('07',2,70)]:
        assign('05',dac_signals(start),'right',199,range(94+offset,126+offset,4))
        assign(p,COMMON,'left',253,[79+offset,83+offset,87+offset])
        assign(p,dac_signals(start),'left',253,range(94+offset,126+offset,4))
        assign(p,SUPPLIES,'right',296,[78+offset,82+offset,86+offset,90+offset,94+offset])
        assign(p,AO,'right',296,[106+offset,111+offset,116+offset,121+offset])
    for sheet in items(old,'sheet'):
        s=copy.deepcopy(sheet);ps=props(s);filename=ps['Sheetfile'][2];p=filename[:2]
        x,y,w,h=boxes[p];put(s,'at',expr(f'(at {mm(x)} {mm(y)})'));put(s,'size',expr(f'(size {mm(w)} {mm(h)})'))
        for key,yy in [('Sheetname',y-2),('Sheetfile',y+h+2)]:
            put(ps[key],'at',expr(f'(at {mm(x)} {mm(yy)} 0)'))
            put(ps[key],'effects',expr('(effects (font (size 1.016 1.016)) (justify left bottom))'))
        s[:]=[n for n in s if not (isinstance(n,list) and n and n[0]=='pin')]
        child=parse((NATIVE/filename).read_text())
        for n in items(child,'hierarchical_label'):
            name=n[1];xx,yy,side=locations[(p,name)];angle=0 if side=='right' else 180
            s.append(expr(f'(pin "{name}" {shape(p,name)} (at {mm(xx)} {mm(yy)} {angle}) (effects (font (size 1.016 1.016))) (uuid "{uid("root/"+p+"/"+name)}"))'))
            ports[(p,name)]=(xx,yy)
        tree.append(s)
    linked=set()
    def connect(a,b,via=()):
        if a not in ports or b not in ports:return
        seq=[ports[a],*via,ports[b]]
        routes.extend(zip(seq,seq[1:]));linked.update((a,b))
    for n in ('12V_PROT','EFUSE_PG'):connect(('01',n),('03',n))
    for n in ('6V0_PRE','ANALOG_EN'):connect(('03',n),('02',n))
    for n in HL:connect(('04',n),('05',n))
    for p,start in [('06',0),('07',2)]:
        for n in dac_signals(start):connect(('05',n),(p,n))
    for i,n in enumerate(COMMON):
        if ('05',n) not in ports:continue
        trunk=218+7*i;ya=ports[('05',n)][1]
        connect(('05',n),('06',n),[(trunk,ya)])
        if ('07',n) in ports:connect(('05',n),('07',n),[(trunk,ya),(trunk,ports[('07',n)][1])])
    for key,(x,y) in ports.items():
        if key in linked and key[1] not in POWER_NETS:continue
        side=locations[key][2]
        if key in linked:
            if key[0]=='01' and key[1]=='12V_PROT': named.append((key[1],80,y))
            continue
        xx=x+(5 if side=='right' else -12);routes.append(((x,y),(xx,y)))
        named.append((key[1],xx if side=='left' else x+1,y))
    ends={p for a,b in routes for p in (a,b)};segments=set()
    def on(p,a,b):return (p[0]==a[0]==b[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1])) or (p[1]==a[1]==b[1] and min(a[0],b[0])<=p[0]<=max(a[0],b[0]))
    for a,b in routes:
        assert a[0]==b[0] or a[1]==b[1],(a,b)
        points=sorted(p for p in ends if on(p,a,b))
        segments.update(tuple(sorted((p,q))) for p,q in zip(points,points[1:]) if p!=q)
    degree=Counter(p for pair in segments for p in pair)
    for a,b in sorted(segments):tree.append(expr(f'(wire (pts (xy {mm(a[0])} {mm(a[1])}) (xy {mm(b[0])} {mm(b[1])})) (stroke (width 0.1524) (type solid)) (uuid "{uid("rootwire"+str((a,b)))}"))'))
    for (x,y),d in degree.items():
        if d>2:tree.append(expr(f'(junction (at {mm(x)} {mm(y)}) (diameter 0) (color 0 0 0 0) (uuid "{uid("rootjunction"+str((x,y)))}"))'))
    for n,x,y in named:tree.append(expr(f'(label "{n}" (at {mm(x)} {mm(y)} 0) (effects (font (size 1.016 1.016)) (justify left bottom)) (uuid "{uid("rootlabel"+str((n,x,y)))}"))'))
    for text,x,y in [('POWER: source -> sequenced digital rails -> analog rails',14,10),('HIL-LINK: direction is relative to this I/O board',14,78),('FPGA -> DAC: shared clock / latch / reset, independent chip select / data / alerts',124,61),('Power fanout uses named local taps; HIL-Link and DAC control/data paths are wired above.',14,207),('AO0..3 remain shared between the two legacy DAC sheets exactly as archived; NOT a new output-isolation approval.',14,213),('FUNCTIONAL PRELAYOUT only. Pin plan, component qualification, safety validation and PCB release remain BLOCKED.',14,219)]:
        tree.append(expr(f'(text "{text}" (at {mm(x)} {mm(y)} 0) (effects (font (size 1.016 1.016)) (justify left)) (uuid "{uid("rootnote"+text)}"))'))
    path.write_text(pretty(tree)+'\n')

if __name__=='__main__':migrate('--full' in sys.argv)
