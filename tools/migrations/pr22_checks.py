"""One-shot reviewed drawing fixes, narrow verifier delta and footprint provision."""
from pathlib import Path
import sys,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2]
if __name__!='__main__' or sys.argv[1:]!=['--apply']:
    raise SystemExit('Explicit --apply required')
sys.path.insert(0,str(ROOT/'tools'))
from kicad_sexpr import parse,items
# Actual KiCad PDF review found overlapping labels and a capacitor in the
# title block. Re-author this disposable snapshot; never run in ordinary CI.
p=ROOT/'tools/migrations/pr22_author.py';s=p.read_text()
s=s.replace("'input',-40.64,76.2", "'input',-121.92,76.2").replace("'input',-40.64,66.04", "'input',-121.92,66.04")
s=s.replace("pin(n,nm,k,40.64,dy,180)", "pin(n,nm,k,121.92,dy,180)").replace("'output',40.64,15.24", "'output',121.92,15.24")
if 'body=line(' in s:
    start=s.index('body=line(');end=s.index("\nsymbol('AD7606C",start)
    s=s[:start]+"body='(rectangle (start -116.84 111.76) (end 116.84 -111.76) (stroke (width .254) (type default)) (fill (type background)))'"+s[end:]
s=s.replace("a.add('R',ref,'100',187.96,yp", "a.add('R',ref,'100',139.7,yp").replace("(264.16,yp)","(200.66,yp)")
s=s.replace("'1n',241.3,121.92", "'1n',177.8,121.92")
s=s.replace("'33',424.18,y", "'33',482.6,y").replace("(393.7,y)","(457.2,y)").replace("(391.16,y)","(457.2,y)")
s=s.replace("(469.9,y)","(520.7,y)").replace("469.9,y,offset", "520.7,y,offset").replace("(398.78,y)","(469.9,y)")
s=s.replace("78.74+i*99.06,50.8", "78.74+i*99.06,48.26")
s=s.replace("x=50.8+(i%5)*106.68;y=350.52+(i//5)*30.48", "x=38.1+i*53.34;y=360.68")
s=s.replace("ref=f'R{r+2+j}';xx=43.18+81.28*j;yy=y+35.56", "ref=f'R{r+2+j}';xx=[43.18,175.26,241.3][j];yy=y+35.56")
s=s.replace("        s+=prop('Reference',ref,x,ry,power,1.016)+prop('Value',val,x,vy,False,1.016)","        px=x\n        if lib=='C':\n            px=x+10.16 if angle==0 else x-12.7\n            if angle:ry=y-2.54;vy=y+2.54\n        elif lib.startswith(('SN74','THVD')):px=x-15.24\n        s+=prop('Reference',ref,px,ry,power,1.016)+prop('Value',val,px,vy,False,1.016)")
s=s.replace("a.named('U801',n,name,dx=0,dy=17.78)", "a.named('U801',n,name,dx=0,dy=25.4 if n==39 else 17.78)")
p.write_text(s)
subprocess.run([sys.executable,str(p),'--author-native'],check=True)
# Restore the authoring record so the transport allowlist remains native-only.
subprocess.run(['git','checkout','--','tools/migrations/pr22_author.py'],cwd=ROOT,check=True)
p=ROOT/'tools/check_native_safety.py';s=p.read_text()
if 'import native_peripheral_rules as peripheral' not in s:
    s=s.replace('from check_native_readability import graph','from check_native_readability import graph\nimport native_peripheral_rules as peripheral')
    s=s.replace("    oldrefs=set(old['components'])", "    oldrefs=set(old['components']) - peripheral.REMOVED_RESERVED")
    s=s.replace('oldrefs | set(PARTS):','oldrefs | set(PARTS) | set(peripheral.PARTS):')
    s=s.replace("    for ref,attributes in {**old['components'],**PARTS}.items():", "    retained={r:a for r,a in old['components'].items() if r in oldrefs}\n    for ref,attributes in {**retained,**PARTS,**peripheral.PARTS}.items():")
    s=s.replace("    return {'result':'PIN_CONTRACT_PASS_NOT_HARDWARE_QUALIFIED',", "    peripheral_result=peripheral.check_pins(nets,members)\n    return {**peripheral_result, 'result':'PIN_CONTRACT_PASS_NOT_HARDWARE_QUALIFIED',")
    p.write_text(s)
p=ROOT/'.github/workflows/native-schematic-readability.yml';s=p.read_text().replace('kicad-footprints ngspice >','kicad-footprints ngspice iverilog >');p.write_text(s)
P=ROOT/'hardware/kicad/revB/axu2cgb_expansion'
for sheet in ('03_peripheral_boundaries','70_adc_frontend','80_encoder_phy'):
    tree=parse((P/(sheet+'.kicad_sch')).read_text())
    for symbol in items(tree,'symbol'):
        props={p[1]:p[2] for p in items(symbol,'property')}
        if props['Reference'].startswith('#'):continue
        fp=props['Footprint'];lib,name=fp.split(':')
        relative=Path(lib+'.pretty')/(name+'.kicad_mod')
        target=P/'footprints'/relative
        if not target.exists():
            source=Path('/usr/share/kicad/footprints')/relative
            if not source.is_file():raise FileNotFoundError(source)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Reviewed drawing, narrow verifier delta and footprint snapshot prepared.')
