import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("check_revb_schematic_closure",ROOT/"tools/check_revb_schematic_closure.py")
MOD=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MOD)

class RevBSchematicClosureTests(unittest.TestCase):
    def test_checked_in_native_source_matches_explicit_open_contract(self):
        report=MOD.check()
        self.assertEqual(report["status"],"PASS_SOURCE_CLOSURE_CONTRACT")
        self.assertFalse(report["layout_allowed"])
        manifest=json.loads((ROOT/"hardware/revB/schematic_open_items.json").read_text())
        self.assertEqual(set(report["blank_footprints"]),set(manifest["open_footprints"]))
        self.assertGreater(report["physical_components"],350)

if __name__=="__main__":
    unittest.main()
