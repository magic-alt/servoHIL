import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from revb_qualification import (
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
        self.assertEqual(report["schema_version"], 2)
        self.assertFalse(report["layout_allowed"])
        self.assertIn("MAGNETICS_L_I_T_CURVES", report["component_evidence_required"])
        self.assertIn("MAGNETICS_AC_CORE_AND_WINDING_LOSS", report["component_evidence_required"])
        self.assertIn("MLCC_EXACT_MPN_DC_BIAS_CURVES", report["component_evidence_required"])
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

    def test_nonfinite_or_nonpositive_shutdown_budget_rejected(self):
        for value in (0, -1, float("inf"), float("nan")):
            with self.subTest(value=value):
                p = self.valid_profile()
                p["max_end_to_end_disable_us"] = value
                with self.assertRaises(ValueError):
                    evaluate_dut_profile(p)


class GateEvidenceTests(unittest.TestCase):
    def test_non_pass_gate_does_not_need_evidence(self):
        self.assertEqual(
            _verified_gate_evidence({"status": "NOT_RUN", "evidence": None}, ROOT, "test"),
            [],
        )

    def test_pass_without_hashed_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "PASS requires hashed evidence"):
            _verified_gate_evidence({"status": "PASS", "evidence": None}, ROOT, "test")

    def test_missing_or_hash_mismatched_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing = {
                "status": "PASS",
                "evidence": [{"path": "evidence/raw.csv", "sha256": "0" * 64}],
            }
            with self.assertRaisesRegex(ValueError, "evidence file missing"):
                _verified_gate_evidence(missing, root, "test")

            path = root / "raw.csv"
            path.write_bytes(b"measured,data\n")
            mismatch = {
                "status": "PASS",
                "evidence": [{"path": "raw.csv", "sha256": "0" * 64}],
            }
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                _verified_gate_evidence(mismatch, root, "test")

    def test_pass_accepts_only_existing_byte_matched_repository_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "evidence" / "raw.csv"
            path.parent.mkdir()
            raw = b"scope_time_s,permit_v\n0.000000,0.0\n"
            path.write_bytes(raw)
            entry = {
                "status": "PASS",
                "evidence": [
                    {
                        "path": "evidence/raw.csv",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ],
            }
            self.assertEqual(
                _verified_gate_evidence(entry, root, "permit_reaction"),
                ["evidence/raw.csv"],
            )

    def test_pass_evidence_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            entry = {
                "status": "PASS",
                "evidence": [{"path": "../outside.csv", "sha256": "0" * 64}],
            }
            with self.assertRaisesRegex(ValueError, "escapes repository"):
                _verified_gate_evidence(entry, root, "test")


if __name__ == "__main__":
    unittest.main()
