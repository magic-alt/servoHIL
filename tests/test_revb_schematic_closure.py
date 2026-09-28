import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_revb_schematic_closure", ROOT / "tools/check_revb_schematic_closure.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
MANIFEST = ROOT / "hardware/revB/schematic_open_items.json"
EVIDENCE = ROOT / "hardware/revB/ad3542r_footprint_evidence.json"


class RevBSchematicClosureTests(unittest.TestCase):
    def manifest(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def check_with_manifest(self, data):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "schematic_open_items.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with mock.patch.object(MOD, "MANIFEST", path):
                return MOD.check()

    def check_with_evidence(self, data):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ad3542r_footprint_evidence.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with mock.patch.object(MOD, "AD3542_EVIDENCE", path):
                return MOD.check()

    def test_checked_in_native_source_matches_explicit_open_contract(self):
        report = MOD.check()
        self.assertEqual(report["status"], "PASS_SOURCE_CLOSURE_CONTRACT")
        self.assertFalse(report["layout_allowed"])
        manifest = self.manifest()
        self.assertEqual(set(report["blank_footprints"]), set(manifest["open_footprints"]))
        self.assertEqual(report["blank_footprint_count"], 9)
        self.assertEqual(report["binding_requirement_count"], 9)
        self.assertEqual(report["land_pattern_blockers"], ["U20", "U21", "U22", "U23"])
        self.assertEqual(
            report["mechanical_blockers"], ["J101", "J5", "J501", "J701", "SW101"]
        )
        self.assertEqual(
            report["ad3542r_footprint_evidence_status"],
            "OFFICIAL_SOURCES_LOCATED_GERBER_AND_CAD_BYTES_NOT_ARCHIVED",
        )
        self.assertEqual(
            report["ad3542r_exposed_pad_status"],
            "UNRESOLVED_REQUIRES_CURRENT_CAD_OR_GERBER",
        )
        self.assertGreater(report["physical_components"], 350)

    def test_manifest_contract_keys_exactly_match_open_footprints(self):
        manifest = self.manifest()
        self.assertEqual(
            set(manifest["binding_requirements"]), set(manifest["open_footprints"])
        )
        self.assertEqual(
            manifest["status"],
            "SCHEMATIC_FUNCTION_COMPLETE_9_PHYSICAL_BINDINGS_OPEN",
        )
        self.assertFalse(manifest["layout_allowed"])

    def test_ad3542r_blocker_identity_is_exact_and_not_generic_qfn(self):
        manifest = self.manifest()
        base = manifest["binding_requirements"]["U20"]
        self.assertEqual(base["manufacturer"], "Analog Devices")
        self.assertEqual(base["mpn"], "AD3542RBCPZ16")
        self.assertEqual(base["package_option"], "CP-28-15")
        self.assertIn("cp-28-15", base["package_drawing_url"].lower())
        self.assertIn("4 mm x 4 mm", base["package_description"])
        for ref in ("U21", "U22", "U23"):
            self.assertEqual(manifest["binding_requirements"][ref]["same_as"], "U20")

    def test_ad3542r_evidence_binds_official_eval_sources(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["part"]["mpn"], "AD3542RBCPZ16")
        self.assertEqual(evidence["part"]["package_option"], "CP-28-15")
        self.assertEqual(evidence["part"]["pin_count"], 28)
        self.assertEqual(evidence["part"]["lead_pitch_mm"], 0.4)
        self.assertTrue(
            evidence["official_sources"]["evaluation_gerber_zip"].endswith(
                "/09-050892-01c.zip"
            )
        )
        self.assertEqual(
            evidence["official_sources"]["adi_documentation_source"]["repository"],
            "analogdevicesinc/system-level",
        )
        self.assertEqual(
            evidence["exposed_pad_review"]["status"],
            "UNRESOLVED_REQUIRES_CURRENT_CAD_OR_GERBER",
        )
        self.assertIsNone(evidence["geometry_review"]["center_pad_present"])

    def test_ad3542r_cannot_guess_center_pad_without_current_cad_or_gerber(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        evidence["geometry_review"]["center_pad_present"] = True
        with self.assertRaisesRegex(ValueError, "center-pad geometry must not be guessed"):
            self.check_with_evidence(evidence)

    def test_ad3542r_cannot_claim_geometry_review_before_archive(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        evidence["geometry_review"]["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "geometry review must remain NOT_RUN"):
            self.check_with_evidence(evidence)

    def test_ad3542r_official_gerber_source_cannot_drift(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        evidence["official_sources"]["evaluation_gerber_zip"] = "https://example.invalid/fake.zip"
        with self.assertRaisesRegex(ValueError, "official EVAL Gerber source drift"):
            self.check_with_evidence(evidence)

    def test_stale_open_count_is_rejected(self):
        manifest = self.manifest()
        manifest["status"] = "SCHEMATIC_FUNCTION_COMPLETE_14_PHYSICAL_BINDINGS_OPEN"
        with self.assertRaisesRegex(ValueError, "status/count drift"):
            self.check_with_manifest(manifest)

    def test_missing_binding_requirement_is_rejected(self):
        manifest = self.manifest()
        del manifest["binding_requirements"]["J5"]
        with self.assertRaisesRegex(ValueError, "binding requirement set changed"):
            self.check_with_manifest(manifest)

    def test_ad3542r_false_pass_is_rejected(self):
        manifest = self.manifest()
        manifest["binding_requirements"]["U20"]["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "U20.status drift"):
            self.check_with_manifest(manifest)

    def test_dut_permit_contract_cannot_drop_leakage_or_isolation(self):
        manifest = self.manifest()
        fields = manifest["binding_requirements"]["J701"]["required_contract_fields"]
        manifest["binding_requirements"]["J701"]["required_contract_fields"] = [
            x for x in fields if "leakage" not in x.lower() and "isolation" not in x.lower()
        ]
        with self.assertRaisesRegex(ValueError, "J701 physical contract"):
            self.check_with_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
