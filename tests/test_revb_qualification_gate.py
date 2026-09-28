import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from revb import source_digest
from revb_qualification import (
    _qualification_evidence_state,
    _verified_gate_evidence,
    build_qualification_report,
    evaluate_dut_profile,
    load_profile,
)


class DutProfileQualificationTests(unittest.TestCase):
    def valid_profile(self):
        return {
            "schema_version": 1,
            "adapter_id": "fixture-reviewed-revX",
            "ao_neutral": {
                "target_v": 0.0,
                "min_v": -0.05,
                "max_v": 0.05,
                "source_impedance_ohm": 10000.0,
                "max_residual_current_a": 0.0001,
            },
            "permit_input": {
                "asserted_min_v": 10.0,
                "inhibited_max_v": 2.0,
                "max_input_leakage_a": 0.00001,
            },
            "cable_faults": {
                "open_response": "INHIBIT",
                "short_response": "INHIBIT",
            },
            "max_end_to_end_disable_us": 5000.0,
            "measured_at": {
                "hw_revision": "fixture-revX",
                "dut_revision": "dut-revX",
                "instrument_set": "bound",
            },
            "evidence": {
                "ao_disconnect": "evidence/ao.csv",
                "permit": "evidence/permit.csv",
                "cable_open": "evidence/open.csv",
                "cable_short": "evidence/short.csv",
                "shutdown_time": "evidence/shutdown.csv",
            },
        }

    def test_checked_in_profile_is_deliberately_unbound(self):
        profile = load_profile(ROOT / "hardware/revB/dut_adapter_profile.json")
        result = evaluate_dut_profile(profile)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("DUT_PROFILE_UNBOUND", result["blockers"])

    def test_contradictory_neutral_window_is_rejected(self):
        p = self.valid_profile()
        p["ao_neutral"]["target_v"] = 0.2
        with self.assertRaisesRegex(ValueError, "neutral"):
            evaluate_dut_profile(p)

    def test_permit_threshold_order_is_rejected(self):
        p = self.valid_profile()
        p["permit_input"]["asserted_min_v"] = 1.0
        p["permit_input"]["inhibited_max_v"] = 2.0
        with self.assertRaisesRegex(ValueError, "permit"):
            evaluate_dut_profile(p)

    def test_non_inhibiting_cable_short_remains_a_blocker(self):
        p = self.valid_profile()
        p["cable_faults"]["short_response"] = "UNDETECTED_BLOCKER"
        result = evaluate_dut_profile(p)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("DUT_CABLE_SHORT_NOT_FAIL_SAFE", result["blockers"])

    def test_bound_values_without_real_files_do_not_qualify(self):
        result = evaluate_dut_profile(self.valid_profile(), root=ROOT)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("DUT_PHYSICAL_EVIDENCE_MISSING", result["blockers"])

    def test_board_report_never_authorizes_layout_from_analytical_inputs(self):
        report = build_qualification_report(ROOT)
        self.assertFalse(report["layout_allowed"])
        self.assertEqual(report["qualification"], "BLOCKED")
        self.assertIn("DUT_PROFILE_UNBOUND", report["blockers"])

    def test_component_and_fixture_requirements_cannot_disappear_from_aggregate(self):
        report = build_qualification_report(ROOT)
        self.assertEqual(report["schema_version"], 3)
        self.assertFalse(report["layout_allowed"])
        self.assertEqual(set(report["mechanical_required"]), {"J101", "SW101", "J5", "J501", "J701"})
        self.assertIn("MECHANICAL_J701_REQUIRED", report["blockers"])
        self.assertEqual(report["prelayout_contract"]["status"], "PASS_CONTRACT_BLOCKED_EVIDENCE")
        self.assertEqual(report["prelayout_evidence_status"]["mechanical"]["J701"], "NOT_RUN")
        self.assertEqual(report["verified_requirement_evidence"], {})
        self.assertIn("MAGNETICS_L_I_T_CURVES", report["component_evidence_required"])
        self.assertIn("MAGNETICS_AC_CORE_AND_WINDING_LOSS", report["component_evidence_required"])
        self.assertIn("MLCC_EXACT_MPN_DC_BIAS_CURVES", report["component_evidence_required"])
        self.assertIn("MLCC_EXACT_LAND_PATTERN_HEIGHT_PLACEMENT", report["component_evidence_required"])
        self.assertIn("MOUNTED_BOARD_TEMPERATURE_RISE", report["component_evidence_required"])
        self.assertIn("LOW_ENERGY_FIXTURE_ACCEPTANCE", report["physical_required"])
        self.assertIn("VIVADO_IO_DRC", report["vivado_required"])
        self.assertIn("VIVADO_TIMING", report["vivado_required"])
        self.assertIn("EMC", report["post_layout_release_required"])
        self.assertIn("FOC_CLOSED_LOOP", report["post_layout_release_required"])
        self.assertIn(
            "COMPONENT_MAGNETICS_L_I_T_CURVES_REQUIRED",
            report["blockers"],
        )
        self.assertIn(
            "COMPONENT_MLCC_EXACT_MPN_DC_BIAS_CURVES_REQUIRED",
            report["blockers"],
        )
        self.assertIn(
            "PHYSICAL_LOW_ENERGY_FIXTURE_ACCEPTANCE_REQUIRED",
            report["blockers"],
        )

    def test_prelayout_evidence_registry_has_exact_required_coverage(self):
        status = json.loads((ROOT / "hardware/revB/prelayout_evidence_status.json").read_text())
        requirements = json.loads((ROOT / "hardware/revB/qualification_requirements.json").read_text())
        result = _qualification_evidence_state(
            status,
            ROOT,
            requirements["mechanical_bindings"]["required_refs"],
            requirements["component_evidence_required"],
            requirements["physical_required"],
            requirements["vivado_required"],
        )
        self.assertEqual(result["carrier"], "axu2cgb")
        self.assertEqual(result["verified"], {})
        self.assertTrue(all(v == "NOT_RUN" for section in result["states"].values() for v in section.values()))

    def test_missing_requirement_state_is_rejected(self):
        status = json.loads((ROOT / "hardware/revB/prelayout_evidence_status.json").read_text())
        requirements = json.loads((ROOT / "hardware/revB/qualification_requirements.json").read_text())
        del status["physical"]["BOARD_THERMAL"]
        with self.assertRaisesRegex(ValueError, "physical coverage drift"):
            _qualification_evidence_state(
                status,
                ROOT,
                requirements["mechanical_bindings"]["required_refs"],
                requirements["component_evidence_required"],
                requirements["physical_required"],
                requirements["vivado_required"],
            )

    def test_nonfinite_or_nonpositive_shutdown_budget_rejected(self):
        for value in (0, -1, float("inf"), float("nan")):
            with self.subTest(value=value):
                p = self.valid_profile()
                p["max_end_to_end_disable_us"] = value
                with self.assertRaises(ValueError):
                    evaluate_dut_profile(p)


class GateEvidenceTests(unittest.TestCase):
    def make_evidence(self, root: Path, gate="permit_reaction", *, raw=b"measured,data\n"):
        evidence_dir = root / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        raw_path = evidence_dir / "raw.csv"
        raw_path.write_bytes(raw)
        report = {
            "source_digest": source_digest(root),
            "carrier": "axu2cgb",
            "gate": gate,
            "result": "PASS",
            "raw_report": "evidence/raw.csv",
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
        }
        report_path = evidence_dir / "gate.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return {"status": "PASS", "evidence": "evidence/gate.json"}, report_path, raw_path

    def test_non_pass_gate_does_not_need_evidence(self):
        self.assertEqual(
            _verified_gate_evidence({"status": "NOT_RUN", "evidence": None}, ROOT, "test"),
            [],
        )

    def test_pass_without_release_evidence_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "release evidence JSON path"):
            _verified_gate_evidence({"status": "PASS", "evidence": None}, ROOT, "test")

    def test_missing_release_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(ValueError, "evidence file missing"):
                _verified_gate_evidence(
                    {"status": "PASS", "evidence": "evidence/missing.json"},
                    root,
                    "test",
                )

    def test_pass_accepts_release_envelope_and_byte_matched_raw_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entry, _, _ = self.make_evidence(root)
            self.assertEqual(
                _verified_gate_evidence(entry, root, "permit_reaction", expected_carrier="axu2cgb"),
                ["evidence/gate.json", "evidence/raw.csv"],
            )

    def test_carrier_mismatch_is_rejected_for_bound_requirement_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entry, _, _ = self.make_evidence(root)
            with self.assertRaisesRegex(ValueError, "carrier mismatch"):
                _verified_gate_evidence(entry, root, "permit_reaction", expected_carrier="other")

    def test_raw_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entry, _, raw_path = self.make_evidence(root)
            raw_path.write_bytes(b"changed\n")
            with self.assertRaisesRegex(ValueError, "raw report hash mismatch"):
                _verified_gate_evidence(entry, root, "permit_reaction")

    def test_raw_artifact_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entry, report_path, _ = self.make_evidence(root)
            artifact = root / "evidence" / "io_runtime.csv"
            artifact.write_bytes(b"port,pin\n")
            report = json.loads(report_path.read_text())
            report["raw_artifacts"] = [{
                "path": "evidence/io_runtime.csv",
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }]
            report_path.write_text(json.dumps(report))
            self.assertIn(
                "evidence/io_runtime.csv",
                _verified_gate_evidence(entry, root, "permit_reaction", expected_carrier="axu2cgb"),
            )
            artifact.write_bytes(b"changed\n")
            with self.assertRaisesRegex(ValueError, "raw artifact hash mismatch"):
                _verified_gate_evidence(entry, root, "permit_reaction", expected_carrier="axu2cgb")

    def test_stale_source_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entry, report_path, _ = self.make_evidence(root)
            report = json.loads(report_path.read_text())
            report["source_digest"] = "0" * 64
            report_path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "stale evidence source digest"):
                _verified_gate_evidence(entry, root, "permit_reaction")

    def test_pass_evidence_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entry = {"status": "PASS", "evidence": "../outside.json"}
            with self.assertRaisesRegex(ValueError, "escapes repository"):
                _verified_gate_evidence(entry, root, "test")


if __name__ == "__main__":
    unittest.main()
