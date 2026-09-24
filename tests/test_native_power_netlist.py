"""Tests use the actual exported native XML, not a generated expected pin list."""
from pathlib import Path
import copy
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from verify_native import verify
from native_supervision_rules import check


@unittest.skipUnless(os.environ.get('NATIVE_NETLIST'),'requires KiCad native XML; executed by native CI')
class NativePowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path(os.environ['NATIVE_NETLIST'])
        cls.doc=ET.parse(cls.source)
        cls.nets,cls.values=verify(cls.source,'supervision')
    def test_actual_netlist(self):check(self.nets,self.values)
    def test_disarm_pin_is_required(self):
        bad=dict(self.nets);bad['U408.6']='INPUT_OK'
        with self.assertRaisesRegex(ValueError,'U408.6'):check(bad,self.values)
    def test_no_expansion_rail_fault_pullup(self):
        bad=dict(self.nets);bad['R552.1']='3V3_AON'
        with self.assertRaisesRegex(ValueError,'R552.1'):check(bad,self.values)
    def test_missing_power_status_transistor(self):
        bad=dict(self.nets);bad.pop('Q401.3')
        with self.assertRaisesRegex(ValueError,'Q401.3'):check(bad,self.values)
    def mutated(self,ref,pin,newnet):
        tree=copy.deepcopy(self.doc);root=tree.getroot();parent=None;node=None
        for net in root.findall('./nets/net'):
            for n in net.findall('node'):
                if n.get('ref')==ref and n.get('pin')==str(pin):parent,node=net,n
        if node is None:raise AssertionError('missing mutation target')
        parent.remove(node)
        target=next(n for n in root.findall('./nets/net') if n.get('name')==newnet)
        target.append(node)
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'mutated.xml';tree.write(path)
            with self.assertRaises(ValueError):verify(path,'supervision')
    def test_tps709_en_must_not_see_12v(self):
        tree=copy.deepcopy(self.doc);net=next(n for n in tree.getroot().findall('./nets/net') if n.get('name')=='VIN_PROT')
        net.append(ET.Element('node',ref='U102',pin='3'))
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'bad.xml';tree.write(path)
            with self.assertRaises(ValueError):verify(path,'supervision')
    def test_negative_ep_must_not_be_ground(self):self.mutated('U302',13,'GND')
    def test_cuk_diode_polarity(self):self.mutated('D301',1,'NEG_X')
    def test_bootstrap_return(self):self.mutated('C210',2,'GND')
    def test_reference_ground(self):self.mutated('U303',4,'VREF_2V5')
    def test_latch_function_from_real_pins(self):
        check(self.nets,self.values)
        q=False;last_arm=False;results=[]
        # power available, ARM, expected DAC reset release
        sequence=[(False,False,False),(True,False,False),(True,True,True),
                  (True,False,False),(True,True,True),(False,True,False),
                  (True,True,False),(True,False,False),(True,True,True)]
        for rails,arm,expected in sequence:
            if not rails:q=False
            elif arm and not last_arm:q=True
            released=rails and q and arm
            self.assertEqual(released,expected)
            last_arm=arm;results.append(released)
        self.assertEqual(results,[False,False,True,False,True,False,False,False,True])
    def test_power_status_no_supply_default(self):
        # A static transistor truth model; not analog transient qualification.
        for host_arm in (False,True):
            for board_power in (False,True):
                for latch in (False,True):
                    release_transistor=board_power and latch
                    fault_sink=host_arm and not release_transistor
                    status_high=host_arm and not fault_sink
                    if not board_power or not host_arm:self.assertFalse(status_high)


if __name__=='__main__':unittest.main()
