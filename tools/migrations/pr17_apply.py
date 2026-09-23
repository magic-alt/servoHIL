#!/usr/bin/env python3
"""Named one-shot entry points; editable sheets are never overwritten."""
import argparse
import pr17_native as native
from pr17_positive import positive_sheet
native.STAGES['positive']=positive_sheet
p=argparse.ArgumentParser();p.add_argument('--stage',choices=native.STAGES,required=True)
native.migrate(p.parse_args().stage)
