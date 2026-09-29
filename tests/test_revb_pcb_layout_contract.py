import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_revb_pcb_layout_contract import _validate_layout_contract, _validate_rules, check


class RevBPcbLayoutContractTests(unittest.TestCase):
    def load(self, rel):
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_checked_in_layout_phase_is_active_but_not_fabrication_ready(self):
        report = check(ROOT)
        self.assertEqual(report["status"], "PASS_PCB_LAYOUT_PHASE1_CONTRACT")
        self.assertTrue(report["layout_allowed"])
        self.assertFalse(report["fabrication_allowed"])
        self.assertFalse(report["release_allowed"])
        self.assertFalse(report["pcb_exists"])
        self.assertEqual(report["layer_count"], 6)
        self.assertIn("J12_center_xy_mm", report["mechanical_open_fields"])
        self.assertIn("carrier_mounting_hole_xy_and_drill_mm", report["mechanical_open_fields"])

    def test_mechanical_photo_estimate_cannot_masquerade_as_bound_geometry(self):
        data = self.load("hardware/revB/pcb_layout_contract.json")
        broken = copy.deepcopy(data)
        broken["carrier_mechanical_reference"]["exact_mechanical_inputs_required_before_edge_cuts_freeze"].pop(
            "J12_center_xy_mm"
        )
        with self.assertRaisesRegex(ValueError, "mechanical input key set drift"):
            _validate_layout_contract(ROOT, broken)

    def test_j12_j15_voltage_domains_are_locked(self):
        data = self.load("hardware/revB/pcb_layout_contract.json")
        broken = copy.deepcopy(data)
        broken["carrier_mechanical_reference"]["documented_facts"]["J12"]["io_voltage_v"] = 3.3
        with self.assertRaisesRegex(ValueError, "J12: pitch/voltage"):
            _validate_layout_contract(ROOT, broken)

    def test_split_ground_policy_is_rejected(self):
        rules = self.load("hardware/revB/pcb_design_rules.json")
        broken = copy.deepcopy(rules)
        broken["grounding_and_return_path"]["split_ground_planes"] = True
        with self.assertRaisesRegex(ValueError, "hard split GND"):
            _validate_rules(broken)

    def test_fabricator_impedance_cannot_be_claimed_before_stackup_binding(self):
        rules = self.load("hardware/revB/pcb_design_rules.json")
        broken = copy.deepcopy(rules)
        broken["drc_acceptance"]["impedance_geometry_can_close_before_fab_stack"] = True
        with self.assertRaisesRegex(ValueError, "fabricator stackup"):
            _validate_rules(broken)

    def test_pcb_drc_zero_violation_policy_is_locked(self):
        rules = self.load("hardware/revB/pcb_design_rules.json")
        broken = copy.deepcopy(rules)
        broken["drc_acceptance"]["clearance_violations_allowed"] = 1
        with self.assertRaisesRegex(ValueError, "must remain zero"):
            _validate_rules(broken)

    def test_design_rules_cannot_promote_fabrication(self):
        rules = self.load("hardware/revB/pcb_design_rules.json")
        broken = copy.deepcopy(rules)
        broken["fabrication_allowed"] = True
        with self.assertRaisesRegex(ValueError, "must not authorize fabrication"):
            _validate_rules(broken)


if __name__ == "__main__":
    unittest.main()
