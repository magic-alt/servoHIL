"""Final read-only drawing regressions; native ERC is still mandatory."""
from __future__ import annotations
import copy
import json
from collections import Counter, defaultdict
import unittest
from test_digital_drawing import NATIVE, CONTRACT, WireGraph
from kicad_sexpr import parse, items, one

class FinishTests(unittest.TestCase):
    def test_root_wires_have_no_unterminated_tails(self):
        t=parse((NATIVE/'servohil_io_revA.kicad_sch').read_text())
        xy=lambda n: tuple(map(float,n[1:3]))
        degree=Counter(xy(p) for w in items(t,'wire') for p in items(one(w,'pts'),'xy'))
        terminals={xy(one(n,'at')) for kind in ('label','junction') for n in items(t,kind)}
        terminals.update(xy(one(p,'at')) for s in items(t,'sheet') for p in items(s,'pin'))
        self.assertEqual([], sorted(p for p,d in degree.items() if d==1 and p not in terminals))

    def test_reviewed_symbol_variants_match_their_external_library(self):
        for sheet,name,library in [('04_axu_hil_link.kicad_sch','ServoHILCore:J12_40','servohil_core.kicad_sym'),
                                   ('06_dac_0_3.kicad_sch','ServoHILCore:AD3542R','servohil_core.kicad_sym'),
                                   ('07_dac_4_7.kicad_sch','ServoHILCore:AD3542R','servohil_core.kicad_sym'),
                                   ('02_analog_power.kicad_sch','ServoHIL:LTC7149','servohil_power.kicad_sym')]:
            d=copy.deepcopy(next(s for s in items(one(parse((NATIVE/sheet).read_text()),'lib_symbols'),'symbol') if s[1]==name))
            d[1]=name.split(':')[-1]
            lib=next(s for s in items(parse((NATIVE/library).read_text()),'symbol') if s[1]==d[1])
            self.assertEqual(d,lib,name)

    def test_review_headers_are_not_in_the_page_border(self):
        for sheet in ('servohil_io_revA.kicad_sch','05_io_fpga.kicad_sch'):
            for n in items(parse((NATIVE/sheet).read_text()),'text'):
                self.assertGreaterEqual(float(one(n,'at')[2]),15.24,(sheet,n[1]))

    def test_fpga_wires_do_not_short_different_contract_nets(self):
        g=WireGraph(parse((NATIVE/'05_io_fpga.kicad_sch').read_text()))
        spec=json.loads(CONTRACT.read_text())['sheets']['05_io_fpga.kicad_sch']
        nets=defaultdict(set)
        for ref,pins in spec.items():
            for pin,net in pins.items():nets[g.find(g.pins[ref+'.'+pin])].add(net)
        self.assertFalse({p:n for p,n in nets.items() if len(n)>1})

    def test_project_does_not_hide_erc_violations(self):
        config=json.loads((NATIVE/'servohil_io_revA.kicad_pro').read_text())
        self.assertNotIn('erc',config,'No exclusions or disabled severities were approved')

if __name__=='__main__':unittest.main(verbosity=2)
