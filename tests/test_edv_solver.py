"""Solver and model preparation regression, no manufacturer simulation claim."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from test_edv_spice import engine, ROOT
from test_edv_qualification import module

class SolverEvidence(unittest.TestCase):
    def test_switching_clock_has_explicit_breakpoints(self):
        for c in engine().make_cases(ROOT):
            if c['kind']=='ldo':continue
            self.assertIn('Vpwm pwm 0 PULSE',c['deck'])
            self.assertNotIn('v(saw)<v(duty)',c['deck'])
            self.assertIn('gate_duty',c['measures'])
    def test_vendor_preparation_preserves_pin_order_and_does_not_copy_model(self):
        names=['IN','EN/UV','PG','GND','OUT','OUTS','SET','PGFB','ILIM']
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t);symbol=folder/'model.asy';model=folder/'model.lib';out=folder/'out'
            symbol.write_text('SYMATTR Prefix X\nSYMATTR Value LT3045\n'+''.join(
                f'PIN 0 0 NONE 0\nPINATTR PinName {name}\nPINATTR SpiceOrder {i+1}\n' for i,name in enumerate(names)))
            model.write_text('* SYNTHETIC PARSER FIXTURE ONLY - NOT A VENDOR MODEL\n.subckt LT3045 '+ ' '.join('p'+str(i) for i in range(9))+'\n.ends LT3045\n')
            report=module('vendor_ltspice').prepare(ROOT,'LT3045',symbol,model,out)
            self.assertEqual(report['status'],'PREPARED_NOT_RUN')
            self.assertFalse(report['vendor_model_executed'])
            self.assertEqual(report['ordered_nodes'],['vin','enable','pg','0','out','out','set','pgfb','ilim'])
            self.assertEqual({p.name for p in out.iterdir()},{'bench.cir','manifest.json'})
            self.assertIn('Rset set 0 52000', (out/'bench.cir').read_text())
            self.assertAlmostEqual(float(re.search(r'Cset set 0 (\S+)',(out/'bench.cir').read_text())[1]),470e-9)

if __name__=='__main__':unittest.main()
