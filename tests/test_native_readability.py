"""Read-only native schematic regression; no migration or generator runs here."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from kicad_sexpr import parse,items,one,walk
from check_native_readability import audit,compare,normalize
NATIVE=ROOT/'hardware/kicad/revB/axu2cgb_expansion'
WIRED=('10_input_protection','20_positive_rails','30_negative_reference','40_power_supervision','41_power_status','04_dac_0_3','05_dac_4_7')


def field(symbol,name):return next(p for p in items(symbol,'property') if p[1]==name)
def hidden(prop):
    effects=one(prop,'effects',[])
    return 'hide' in effects or any(x[0]=='hide' and x[1]=='yes' for x in items(effects,'hide'))

class NativeReadabilityTests(unittest.TestCase):
    def test_globals_only_represent_cross_sheet_nets(self):
        result=audit(NATIVE)
        self.assertFalse(result['errors'])
        self.assertLess(result['global_total'],300)

    def test_local_feedback_is_visible_wiring_not_global_labels(self):
        tree=parse((NATIVE/'20_positive_rails.kicad_sch').read_text())
        self.assertGreater(len(items(tree,'wire')),180)
        self.assertIn('FB_201',{str(x[1]) for x in items(tree,'label')})
        self.assertNotIn('FB_201',{str(x[1]) for x in items(tree,'global_label')})

    def test_all_native_references_are_unique_including_power_symbols(self):
        seen=set()
        for path in NATIVE.glob('*.kicad_sch'):
            for symbol in items(parse(path.read_text()),'symbol'):
                ref=str(field(symbol,'Reference')[2])
                self.assertNotIn(ref,seen,ref+' occurs twice')
                seen.add(ref)

    def test_value_fields_remain_live_and_editable_not_static_text_clones(self):
        failures=[]
        for name in WIRED:
            for symbol in items(parse((NATIVE/(name+'.kicad_sch')).read_text()),'symbol'):
                ref=str(field(symbol,'Reference')[2])
                if ref.startswith(('#','PF','TP')):continue
                if hidden(field(symbol,'Value')):failures.append(name+':'+ref)
        self.assertFalse(failures,'Hidden Value with static display text would become stale after native edits: '+str(failures))

    def test_notes_and_component_anchors_stay_inside_paper(self):
        sizes={'A3':(420,297),'A2':(594,420),'A1':(841,594)}
        for name in WIRED:
            tree=parse((NATIVE/(name+'.kicad_sch')).read_text())
            width,height=sizes[str(one(tree,'paper')[1])]
            for item in items(tree,'text')+items(tree,'symbol'):
                at=one(item,'at')
                x,y=float(at[1]),float(at[2])
                self.assertTrue(7<=x<=width-7 and 7<=y<=height-10,(name,x,y))

    def test_source_stage_guard_records_every_completed_wiring_part(self):
        data=json.loads((NATIVE/'READABILITY_PROGRESS.json').read_text())
        self.assertTrue(set(WIRED))
        self.assertTrue({'scope','positive','input','negative','dac','supervision','status'}<=set(data['completed']))

class GraphRegressionTests(unittest.TestCase):
    def fixture(self,path,swap=False):
        root=ET.Element('export');components=ET.SubElement(root,'components')
        for ref in ('R1','R2'):
            c=ET.SubElement(components,'comp',ref=ref);ET.SubElement(c,'value').text='10k';ET.SubElement(c,'footprint').text='R_0603'
        nets=ET.SubElement(root,'nets')
        for name,nodes in [('A',[('R1','1'),('R2','2' if swap else '1')]),('B',[('R1','2'),('R2','1' if swap else '2')])]:
            net=ET.SubElement(nets,'net',name=name)
            for ref,pin in nodes:ET.SubElement(net,'node',ref=ref,pin=pin)
        ET.ElementTree(root).write(path)

    def test_graph_rejects_pin_swap_even_when_net_names_are_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a.xml',Path(t)/'b.xml';self.fixture(a);self.fixture(b,True)
            with self.assertRaisesRegex(ValueError,'partition'):compare(a,b)

    def test_graph_preserves_connectivity_across_local_net_renaming(self):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'a.xml',Path(t)/'b.xml';self.fixture(a);self.fixture(b)
            xml=ET.parse(b)
            for net in xml.findall('./nets/net'):net.set('name','/sheet/'+net.attrib['name'])
            xml.write(b)
            self.assertEqual(compare(a,b)['result'],'ELECTRICALLY_EQUIVALENT')

    def test_normalizer_must_not_merge_same_named_nets_on_two_sheets(self):
        with tempfile.TemporaryDirectory() as t:
            src,dst=Path(t)/'a.xml',Path(t)/'b.xml';self.fixture(src)
            xml=ET.parse(src);nets=xml.findall('./nets/net')
            nets[0].set('name','/one/FB');nets[1].set('name','/two/FB');xml.write(src)
            with self.assertRaisesRegex(ValueError,'two distinct'):normalize(src,dst)

if __name__=='__main__':unittest.main()
