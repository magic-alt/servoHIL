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
        self.assertEqual(report["dut_adapter_status"], "UNBOUND")
        self.assertEqual(report["vivado_status"], "TARGET_PART_BOUND_PREVIEW_ONLY_TOP_XDC_CLOCKS_UNBOUND")
        self.assertEqual(report["vivado_input_contract"]["target_part"], "xczu2cg-sfvc784-1-e")
        self.assertEqual(report["vivado_input_contract"]["marketing_part"], "XCZU2CG-1SFVC784E")
        self.assertEqual(report["active_vivado_inputs"], {"xdc": [], "project": []})
        self.assertGreaterEqual(report["template_count"], 4)
        self.assertEqual(report["verification_plan_count"], 5)

    def test_mechanical_interface_cannot_disappear_without_close_workflow(self):
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        manifest = self.load("hardware/revB/schematic_open_items.json")
        plan = self.load("hardware/revB/mechanical_binding_plan.json")
        del plan["interfaces"]["J701"]
        with self.assertRaisesRegex(ValueError, "exactly five interfaces"):
            _validate_mechanical(contract, manifest, plan)

    def test_mechanical_plan_cannot_pretend_a_part_is_selected(self):
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        manifest = self.load("hardware/revB/schematic_open_items.json")
        plan = self.load("hardware/revB/mechanical_binding_plan.json")
        plan["interfaces"]["J5"]["selected_part"] = "UNREVIEWED-PART"
        with self.assertRaisesRegex(ValueError, "selected_part"):
            _validate_mechanical(contract, manifest, plan)

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

    def test_mlcc_input_bank_remains_blocked_on_exact_mpn(self):
        report = check(ROOT)
        self.assertEqual(
            report["component_source_state"]["unresolved_mlcc_banks"],
            ["input_protected"],
        )

    def test_checked_in_verification_plan_cannot_claim_pass_without_raw_evidence(self):
        plan = self.load("hardware/revB/verification_plans/partial_power_backfeed.json")
        plan["status"] = "PASS"
        plan["result"] = "PASS"
        with self.assertRaisesRegex(ValueError, "result must remain NOT_RUN"):
            _validate_verification_plan(plan, "partial-power")

    def test_vivado_preview_cannot_be_promoted_to_active_constraint(self):
        from check_revb_prelayout_contract import _validate_vivado_contract
        contract = self.load("hardware/revB/prelayout_qualification_contract.json")
        work = copy.deepcopy(contract["workstreams"]["VIVADO_IO_DRC_TIMING"])
        original = self.load("hardware/revB/vivado_input_contract.json")
        original["io_constraint_preview"]["can_close_gate"] = True
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Build only the paths needed by the validator under a temp repo root.
            for rel in [
                "hardware/carriers/axu2cgb/profile.json",
                "hardware/kicad/revB/axu2cgb_expansion/carrier.xdc.preview",
            ]:
                src = ROOT / rel
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
            vpath = root / "hardware/revB/vivado_input_contract.json"
            vpath.parent.mkdir(parents=True, exist_ok=True)
            vpath.write_text(json.dumps(original), encoding="utf-8")
            work["input_contract"] = "hardware/revB/vivado_input_contract.json"
            with self.assertRaisesRegex(ValueError, "cannot close"):
                _validate_vivado_contract(root, work)


    def test_source_location_does_not_equal_qualification_pass(self):
        report = check(ROOT)
        self.assertIn("NOT_HASH", report["component_source_state"]["magnetics_source_status"])
        self.assertIn("NOT_HASH", report["component_source_state"]["mlcc_source_status"])


if __name__ == "__main__":
    unittest.main()
