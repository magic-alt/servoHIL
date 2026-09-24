"""One-shot fixes from actual KiCad 10.0.6 ERC/PDF review; never run in normal CI."""
from pathlib import Path
import sys, shutil, uuid
REPO=Path(__file__).resolve().parents[2]
if __name__!='__main__' or sys.argv[1:]!=['--apply']:
    raise SystemExit('Explicit one-shot --apply required')
sys.path.insert(0,str(REPO/'tools'))
from kicad_sexpr import parse, document, items, one, walk, number, expr
P=REPO/'hardware/kicad/revB/axu2cgb_expansion'
NS=uuid.UUID('b3f4b67e-0703-412e-abee-770acb5129ad')

def fields(s):return {str(p[1]):p for p in items(s,'property')}
def move(s,dx,dy):
    for n in [s]+items(s,'property'):
        a=one(n,'at')
        if a:a[1]=number(float(a[1])+dx);a[2]=number(float(a[2])+dy)
def pin_names(tree):
    # VSS is the negative analogue rail, not a GND alias. Preserve power_in type
    # and pin number 4; an independent oracle asserts its exact negative net.
    for node in walk(tree,'pin'):
        name=one(node,'name');num=one(node,'number')
        if name and num and name[1]=='VSS' and num[1]=='4':name[1]='VSS_NEG'

def relay_graphics(tree):
    # Functional normally-open optical relay drawing, not a discrete MOSFET net.
    for symbol in walk(tree,'symbol'):
        if len(symbol)>1 and symbol[1]=='AQY212GS_0_1':
            for child in list(symbol[2:]):
                if isinstance(child,list) and child[0]=='polyline':symbol.remove(child)
            for points in [
                [(-20.32,10.16),(-10.16,10.16),(-10.16,5.08)],
                [(-13.97,5.08),(-6.35,5.08),(-10.16,-2.54),(-13.97,5.08)],
                [(-13.97,-2.54),(-6.35,-2.54)],
                [(-10.16,-2.54),(-10.16,-10.16),(-20.32,-10.16)],
                [(20.32,10.16),(10.16,10.16),(10.16,5.08)],
                [(20.32,-10.16),(10.16,-10.16),(10.16,-2.54),(5.08,5.08)],
                [(-3.81,3.81),(1.27,1.27),(0,3.81)],
                [(-3.81,0),(1.27,-2.54),(0,0)]]:
                pts=' '.join(f'(xy {x} {y})' for x,y in points)
                symbol.append(expr(f'(polyline (pts {pts}) (stroke (width .254) (type default)) (fill (type none)))'))

for name,title in [('50_watchdog_interlock','Watchdog / re-arm interlock'),
                   ('06_analog_outputs','AO disconnect (unqualified)'),
                   ('60_dut_permit','DUT permit - not STO')]:
    path=P/(name+'.kicad_sch');tree=parse(path.read_text())
    titleblock=one(tree,'title_block');one(titleblock,'title')[1]=title;one(titleblock,'rev')[1]='B-safety-dev'
    pin_names(tree);relay_graphics(tree)
    for symbol in items(tree,'symbol'):
        f=fields(symbol);ref=str(f['Reference'][2]);at=one(symbol,'at')
        if ref.startswith('#') and f['Value'][2]!='GND':
            # Move supply text away from adjacent passive Reference/Value text.
            a=one(f['Value'],'at');a[1]=number(float(a[1])-6.35)
        if name=='50_watchdog_interlock' and float(at[2])>350:
            move(symbol,0,-15.24)
        if name=='50_watchdog_interlock' and ref.startswith('#') and float(at[1])==213.36 and float(at[2])==276.86:
            move(symbol,-20.32,-15.24)
        if name=='06_analog_outputs' and ref=='J5':one(f['Value'],'at')[2]=number(269.24)
    if name=='50_watchdog_interlock':
        for note in items(tree,'text'):
            a=one(note,'at');y=float(a[2])
            if y in (340.36,347.98):a[2]=number(y-10.16)
            if y>350:a[2]=number(372.11)
        found=0
        for wire in list(items(tree,'wire')):
            pts={tuple(float(v) for v in xy[1:]) for xy in items(one(wire,'pts'),'xy')}
            if pts=={(213.36,276.86),(213.36,284.48)}:tree.remove(wire);found+=1
        if found!=1:raise ValueError('unexpected U506 D supply routing')
        for i,(a,b) in enumerate([((213.36,284.48),(193.04,284.48)),((193.04,284.48),(193.04,261.62))]):
            ident=uuid.uuid5(NS,f'U506-D-supply-{i}')
            tree.append(expr(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{ident}"))'))
    path.write_text(document(tree))
lib=P/'safety.kicad_sym';tree=parse(lib.read_text());pin_names(tree);relay_graphics(tree);lib.write_text(document(tree))
# Vendor-installed official KiCad footprints are copied into the already
# project-local library snapshot. Its existing COPYRIGHT covers these files.
for relative in ['Capacitor_SMD.pretty/C_0603_1608Metric.kicad_mod',
                 'Package_SO.pretty/TSSOP-16_4.4x5mm_P0.65mm.kicad_mod']:
    src=Path('/usr/share/kicad/footprints')/relative
    if not src.is_file():raise FileNotFoundError('Install KiCad footprint package: '+str(src))
    dst=P/'footprints'/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
print('Applied reviewed text/negative-pin/package fixes; actual ERC still required.')
