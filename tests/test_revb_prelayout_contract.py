import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_revb_prelayout_contract import (
    EXPECTED_MECHANICAL,
    _validate_verification_plan,
    _validate_mechanical,
    _validate_sources,
    _validate_template,
    check,
)


class RevBPrelayoutContractTests(unittest.TestCase):
    def load(self, rel):
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_checked_in_contract_is_fail_closed_and_machine_auditable(self):
        report = check(ROOT)
        self.assertEqual(report["status"], "PASS_CONTRACT_BLOCKED_EVIDENCE")
        self.assertFalse(report["layout_allowed"])
        self.assertEqual(set(report["mechanical_open_refs"]), EXPECTED_MECHANICAL)
        self.assertEqual(report["mechanical_open_count"], 5)
        self.assertIn("BLOCKER", report["mechanical_fault_semantic_blockers"]["J501"])
        self.assertIn("BLOCKER", report["mechanical_fault_semantic_blockers"]["J701"])
        self.assertEqual(report["dut_adapter_status"], "UNBOUND")
        self.assertEqual(report["vivado_status"], "IO_DRC_HARNESS_BOUND_NOT_RUN_TIMING_BLOCKED")
        self.assertEqual(report["vivado_input_contract"]["target_part"], "xczu2cg-sfvc784-1-e")
        self.assertEqual(report["vivado_input_contract"]["marketing_part"], "XCZU2CG-1SFVC784E")
        self.assertEqual(
            report["active_vivado_inputs"],
            {
                "harness_xdc": ["fpga/revb/io_drc/axu2cgb_io_drc.xdc"],
                "functional_xdc": [],
                "project": [],
            },
        )
        self.assertGreaterEqual(report["template_count"], 4)
        self.assertEqual(report["verification_plan_count"], 5)

    def test_mechanical_interface_cannot_disappear_without_close_workflow(self):
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        manifest = self.load("hardware/revB/schematic_open_items.json")
        plan = self.load("hardware/revB/mechanical_binding_plan.json")
        del plan["interfaces"]["J701"]
        with self.assertRaisesRegex(ValueError, "exactly five interfaces"):
            _validate_mechanical(ROOT, contract, manifest, plan)

    def test_mechanical_plan_cannot_pretend_a_part_is_selected(self):
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        manifest = self.load("hardware/revB/schematic_open_items.json")
        plan = self.load("hardware/revB/mechanical_binding_plan.json")
        plan["interfaces"]["J5"]["selected_part"] = "UNREVIEWED-PART"
        with self.assertRaisesRegex(ValueError, "selected_part"):
            _validate_mechanical(ROOT, contract, manifest, plan)

    def test_native_mechanical_pinouts_are_bound_without_fake_part_selection(self):
        plan = self.load("hardware/revB/mechanical_binding_plan.json")
        self.assertEqual(plan["interfaces"]["J101"]["pinout"], {"1": "VIN_RAW", "2": "GND"})
        self.assertEqual(plan["interfaces"]["J5"]["pin_count"], 10)
        self.assertEqual(plan["interfaces"]["J5"]["pinout"]["9"], "GND")
        self.assertEqual(plan["interfaces"]["J5"]["pinout"]["10"], "GND")
        self.assertEqual(plan["interfaces"]["J501"]["pinout"], {"1": "INTERLOCK_FEED", "2": "INTERLOCK_RAW"})
        self.assertEqual(plan["interfaces"]["J701"]["pinout"], {"1": "DUT_PERMIT_A", "2": "DUT_PERMIT_B"})
        self.assertTrue(all(plan["interfaces"][ref]["selected_part"] is None for ref in EXPECTED_MECHANICAL))

    def test_j5_stale_eight_pin_metadata_is_rejected(self):
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        manifest = self.load("hardware/revB/schematic_open_items.json")
        plan = self.load("hardware/revB/mechanical_binding_plan.json")
        plan["interfaces"]["J5"]["pin_count"] = 8
        with self.assertRaisesRegex(ValueError, "J5: mechanical plan pin count drift"):
            _validate_mechanical(ROOT, contract, manifest, plan)

    def test_two_wire_short_cannot_be_silently_declared_fail_safe(self):
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        manifest = self.load("hardware/revB/schematic_open_items.json")
        for ref in ("J501", "J701"):
            with self.subTest(ref=ref):
                plan = self.load("hardware/revB/mechanical_binding_plan.json")
                plan["interfaces"][ref]["cable_short_behavior"] = "INHIBIT_REQUIRED"
                with self.assertRaisesRegex(ValueError, ref + " cable-short semantics"):
                    _validate_mechanical(ROOT, contract, manifest, plan)


    def test_two_wire_cable_short_architecture_remains_decision_required(self):
        report = check(ROOT)
        state = report["cable_fault_architecture"]
        self.assertEqual(state["status"], "DECISION_REQUIRED_CABLE_SHORT_SEMANTICS")
        self.assertIn("NOT_DETECTABLE", state["J501"])
        self.assertIn("NOT_DETECTABLE", state["J701"])
        self.assertEqual(state["selected_resolutions"], {"J501": None, "J701": None})

    def test_j701_cable_fault_contract_cannot_claim_sto(self):
        from check_revb_prelayout_contract import _validate_cable_fault_architecture
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        data = self.load("hardware/revB/cable_fault_architecture.json")
        self.assertIn("STO", data["interfaces"]["J701"]["forbidden_claims"])
        self.assertIn("redundant safety output", data["interfaces"]["J701"]["forbidden_claims"])
        self.assertIsNone(data["interfaces"]["J701"]["selected_resolution"])
        self.assertEqual(
            _validate_cable_fault_architecture(ROOT, contract["mechanical_bindings"])["status"],
            "DECISION_REQUIRED_CABLE_SHORT_SEMANTICS",
        )

    def test_template_can_never_be_promoted_to_pass(self):
        template = self.load("hardware/revB/evidence/templates/physical_measurement_record.json")
        template["status"] = "PASS"
        template["result"] = "PASS"
        with self.assertRaisesRegex(ValueError, "TEMPLATE_ONLY_NOT_EVIDENCE"):
            _validate_template(template, "physical")

    def test_magnetic_source_registry_must_match_actual_assignments(self):
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        registry = self.load("hardware/revB/component_evidence_sources.json")
        components = self.load("sim/power/component_candidates.json")
        capacitors = self.load("sim/power/capacitor_candidates.json")
        broken = copy.deepcopy(registry)
        broken["magnetics"]["exact_parts"].pop("XAL5050-682MEC")
        with self.assertRaisesRegex(ValueError, "magnetic source set drift"):
            _validate_sources(contract, broken, components, capacitors)

    def test_mlcc_input_bank_has_exact_mpn_but_curve_remains_blocked(self):
        report = check(ROOT)
        self.assertEqual(report["component_source_state"]["unresolved_mlcc_banks"], [])
        self.assertEqual(
            report["component_source_state"]["input_protected_exact_mpn"],
            "C5750X7R1V476M230KC",
        )
        self.assertIn(
            "NOT_HASH",
            report["component_source_state"]["input_protected_curve_status"],
        )

    def test_checked_in_verification_plan_cannot_claim_pass_without_raw_evidence(self):
        plan = self.load("hardware/revB/verification_plans/partial_power_backfeed.json")
        plan["status"] = "PASS"
        plan["result"] = "PASS"
        with self.assertRaisesRegex(ValueError, "result must remain NOT_RUN"):
            _validate_verification_plan(plan, "partial-power")

    def test_vivado_preview_cannot_be_promoted_to_active_constraint(self):
        original = self.load("hardware/revB/vivado_input_contract.json")
        self.assertFalse(original["io_constraint_preview"]["can_close_gate"])
        self.assertEqual(
            original["io_constraint_preview"]["status"],
            "REVIEW_PREVIEW_ONLY_NOT_ACTIVE_XDC",
        )
        self.assertFalse(original["io_drc_harness"]["can_close_timing"])
        self.assertIsNone(original["functional_timing"]["top_module"])
        self.assertEqual(original["functional_timing"]["active_xdc_files"], [])


    def test_source_location_does_not_equal_qualification_pass(self):
        report = check(ROOT)
        self.assertIn("NOT_HASH", report["component_source_state"]["magnetics_source_status"])
        self.assertIn("NOT_HASH", report["component_source_state"]["mlcc_source_status"])


if __name__ == "__main__":
    unittest.main()
