"""One-shot narrow verifier delta and local footprint provisioning."""
from pathlib import Path
import sys,shutil
ROOT=Path(__file__).resolve().parents[2]
if __name__!='__main__' or sys.argv[1:]!=['--apply']:
    raise SystemExit('Explicit --apply required')
sys.path.insert(0,str(ROOT/'tools'))
from kicad_sexpr import parse,items
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
print('Narrow verifier delta and installed KiCad footprint snapshot prepared.')
