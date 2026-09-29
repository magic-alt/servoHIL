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
GEOMETRY = ROOT / "hardware/revB/evidence/ad3542r/u1_geometry_review.json"
FOOTPRINT = (
    ROOT
    / "hardware/kicad/revB/axu2cgb_expansion/footprints/"
    "Package_DFN_QFN.pretty/AnalogDevices_CP-28-15_AD3542R.kicad_mod"
)


class RevBSchematicClosureTests(unittest.TestCase):
    def manifest(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def evidence(self):
        return json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def geometry(self):
        return json.loads(GEOMETRY.read_text(encoding="utf-8"))

    def check_with_manifest(self, data):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "schematic_open_items.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with mock.patch.object(MOD, "MANIFEST", path):
                return MOD.check()

    def check_with_geometry(self, data):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "u1_geometry_review.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with mock.patch.object(MOD, "AD3542_GEOMETRY", path):
                return MOD.check()

    def check_with_footprint_text(self, text):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "AD3542R.kicad_mod"
            path.write_text(text, encoding="utf-8")
            with mock.patch.object(MOD, "AD3542_FOOTPRINT", path):
                return MOD.check()

    def test_checked_in_native_source_is_ready_for_layout_entry(self):
        report = MOD.check()
        self.assertEqual(report["status"], "PASS_LAYOUT_ENTRY_SOURCE_CLOSURE")
        self.assertTrue(report["layout_allowed"])
        self.assertFalse(report["fabrication_allowed"])
        self.assertEqual(report["blank_footprint_count"], 0)
        self.assertEqual(report["binding_requirement_count"], 0)
        self.assertEqual(report["land_pattern_blockers"], [])
        self.assertEqual(
            report["resolved_land_patterns"], ["U20", "U21", "U22", "U23"]
        )
        self.assertEqual(
            set(report["resolved_layout_refs"]),
            {"J101", "SW101", "C105", "J5", "J501", "J701"},
        )
        self.assertEqual(report["mechanical_blockers"], [])
        self.assertEqual(
            report["ad3542r_footprint_evidence_status"],
            "REVIEWED_OFFICIAL_EVAL_GERBER_FOOTPRINT_VENDORED",
        )
        self.assertEqual(
            report["ad3542r_geometry_conclusion"],
            "PASS_EXACT_OFFICIAL_EVAL_LAND_PATTERN",
        )
        self.assertEqual(report["ad3542r_electrical_pad_count"], 28)
        self.assertEqual(report["ad3542r_mask_aperture_count"], 28)
        self.assertGreater(report["physical_components"], 350)

    def test_manifest_has_zero_open_layout_bindings(self):
        manifest = self.manifest()
        self.assertEqual(manifest["schema_version"], 4)
        self.assertEqual(manifest["open_footprints"], {})
        self.assertEqual(manifest["binding_requirements"], {})
        self.assertEqual(
            manifest["status"], "SCHEMATIC_LAYOUT_ENTRY_READY_NO_OPEN_FOOTPRINTS"
        )
        self.assertTrue(manifest["layout_allowed"])
        self.assertEqual(
            set(manifest["layout_entry_resolved_refs"]),
            {"J101", "SW101", "C105", "J5", "J501", "J701"},
        )

    def test_ad3542r_resolved_binding_is_exact_and_source_bound(self):
        manifest = self.manifest()
        bindings = manifest["resolved_bindings"]
        self.assertTrue({"U20", "U21", "U22", "U23"}.issubset(bindings))
        base = bindings["U20"]
        self.assertEqual(base["manufacturer"], "Analog Devices")
        self.assertEqual(base["mpn"], "AD3542RBCPZ16")
        self.assertEqual(base["package_option"], "CP-28-15")
        self.assertEqual(
            base["footprint"], "Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R"
        )
        self.assertEqual(
            base["geometry_evidence"],
            "hardware/revB/evidence/ad3542r/u1_geometry_review.json",
        )
        for ref in ("U21", "U22", "U23"):
            self.assertEqual(bindings[ref]["same_as"], "U20")
            self.assertEqual(
                manifest["bound_packages"][ref],
                "Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R",
            )

    def test_ad3542r_official_artifact_hashes_and_bom_are_pinned(self):
        evidence = self.evidence()
        hashes = evidence["source_artifact_hashes"]
        self.assertEqual(
            hashes["evaluation_gerber_zip_sha256"],
            "87eee7f3ed85e81798918b1977bc0b416d72699a39c771d95e9ea3839ef461e8",
        )
        self.assertEqual(
            hashes["evaluation_bom_sha256"],
            "4608d8884754e5768424832af2331fa0490ab90e05a990a1292bf8f7bab0f7df",
        )
        geometry = self.geometry()
        self.assertEqual(geometry["bom_u1"]["location"], "U1")
        self.assertEqual(
            geometry["bom_u1"]["manufacturer_part_number"], "AD3542RBCPZ16"
        )
        self.assertEqual(geometry["bom_u1"]["jedec_type"], "QFN28_4X4")

    def test_ad3542r_current_sources_resolve_no_center_exposed_pad(self):
        evidence = self.evidence()
        self.assertEqual(
            evidence["exposed_pad_review"]["status"],
            "RESOLVED_NO_CENTER_EXPOSED_PAD_CURRENT_SOURCES",
        )
        self.assertFalse(evidence["geometry_review"]["center_pad_present"])
        geometry = self.geometry()
        self.assertFalse(geometry["package_cross_check"]["center_exposed_pad"])
        self.assertFalse(
            geometry["center_region_review"]["center_exposed_pad_present"]
        )
        self.assertFalse(
            geometry["center_region_review"]["top_solder_mask_center_aperture"]
        )
        self.assertFalse(geometry["center_region_review"]["top_paste_center_aperture"])

    def test_ad3542r_geometry_must_keep_exact_28_ipc_pins(self):
        geometry = self.geometry()
        geometry["eval_u1_ipc356_records"].pop()
        with self.assertRaisesRegex(ValueError, "IPC-356 must contain exactly pins 1..28"):
            self.check_with_geometry(geometry)

    def test_ad3542r_geometry_cannot_reintroduce_center_pad(self):
        geometry = self.geometry()
        geometry["center_region_review"]["center_exposed_pad_present"] = True
        with self.assertRaisesRegex(ValueError, "center/exposed pad must remain absent"):
            self.check_with_geometry(geometry)

    def test_ad3542r_official_source_hash_drift_is_rejected(self):
        geometry = self.geometry()
        geometry["source_artifacts"]["evaluation_gerber_zip"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source artifact hash drift"):
            self.check_with_geometry(geometry)

    def test_ad3542r_footprint_copper_geometry_drift_is_rejected(self):
        text = FOOTPRINT.read_text(encoding="utf-8")
        text = text.replace(
            "(pad 1 smd oval (at -1.8933 -1.2000) (size 0.7366 0.2286)",
            "(pad 1 smd oval (at -1.8933 -1.2000) (size 0.7000 0.2286)",
            1,
        )
        with self.assertRaisesRegex(ValueError, "pin 1 size-x drift"):
            self.check_with_footprint_text(text)

    def test_ad3542r_footprint_mask_aperture_drift_is_rejected(self):
        text = FOOTPRINT.read_text(encoding="utf-8")
        text = text.replace(
            '(pad "" smd oval (at -1.8933 -1.2000) (size 0.8382 0.2794)',
            '(pad "" smd oval (at -1.8933 -1.2000) (size 0.8000 0.2794)',
            1,
        )
        with self.assertRaisesRegex(ValueError, "missing exact official solder-mask aperture"):
            self.check_with_footprint_text(text)

    def test_stale_open_status_is_rejected(self):
        manifest = self.manifest()
        manifest["status"] = "SCHEMATIC_FUNCTION_COMPLETE_5_PHYSICAL_BINDINGS_OPEN"
        with self.assertRaisesRegex(ValueError, "layout-entry status drift"):
            self.check_with_manifest(manifest)

    def test_reopened_footprint_contract_is_rejected(self):
        manifest = self.manifest()
        manifest["open_footprints"]["J5"] = "stale blocker"
        with self.assertRaisesRegex(ValueError, "zero open footprint"):
            self.check_with_manifest(manifest)

    def test_missing_layout_resolved_binding_is_rejected(self):
        manifest = self.manifest()
        del manifest["resolved_bindings"]["J5"]
        with self.assertRaisesRegex(ValueError, "J5: missing resolved layout binding"):
            self.check_with_manifest(manifest)

    def test_layout_footprint_drift_is_rejected(self):
        manifest = self.manifest()
        manifest["resolved_bindings"]["J701"]["footprint"] = "Connector_Generic:Fake"
        with self.assertRaisesRegex(ValueError, "J701: resolved binding footprint drift"):
            self.check_with_manifest(manifest)

    def test_ad3542r_resolved_binding_cannot_be_weakened_to_generic_pass(self):
        manifest = self.manifest()
        manifest["resolved_bindings"]["U20"]["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "U20 resolved binding drift"):
            self.check_with_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
