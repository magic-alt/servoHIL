#!/usr/bin/env python3
"""Named one-shot entry points; editable sheets are never overwritten."""
import argparse
import pr17_native as native
from pr17_positive import positive_sheet
from pr17_negative import negative_sheet
native.STAGES.update(positive=positive_sheet,negative=negative_sheet)
p=argparse.ArgumentParser();p.add_argument('--stage',choices=native.STAGES,required=True)
native.migrate(p.parse_args().stage)
