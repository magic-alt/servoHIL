#!/usr/bin/env python3
import argparse
from verify_native import verify
from native_supervision_rules import check
p=argparse.ArgumentParser();p.add_argument('netlist');p.add_argument('--stage',choices=['input','positive','negative','supervision'],required=True)
a=p.parse_args();nets,values=verify(a.netlist,a.stage)
if a.stage=='supervision':check(nets,values)
