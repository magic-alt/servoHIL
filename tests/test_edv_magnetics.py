"""Hash-bound Coilcraft L-vs-current reference evidence, never hardware PASS."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_edv_qualification import module, ROOT

MPN = "XAL5050-103MEC"


def synthetic_pack(root: Path, *, source_url=None):
    raw = b"SYNTHETIC TEST ONLY; not Coilcraft measured data\n"
    csv = b"current_a,inductance_uh\n0,10\n5,7\n10,4\n"
    (root / "synthetic-original.txt").write_bytes(raw)
    (root / "synthetic.csv").write_bytes(csv)
    if source_url is None:
        registry = json.loads((ROOT / "hardware/revB/component_evidence_sources.json").read_text())
        source_url = registry["magnetics"]["datasheet_url"]
    data = {
        "schema": 1,
        "manufacturer": "Coilcraft",
        "part_number": MPN,
        "characteristic": "L_VS_CURRENT_REFERENCE",
        "source_url": source_url,
        "retrieved_on": "2026-09-28",
        "reviewer": "SYNTHETIC TEST",
        "normalization_note": "Synthetic fixture; not engineering evidence.",
        "conditions": {"temperature_c": 25, "curve_basis": "SYNTHETIC_TEST_ONLY"},
        "original": {
            "file": "synthetic-original.txt",
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "normalized_csv": {
            "file": "synthetic.csv",
            "sha256": hashlib.sha256(csv).hexdigest(),
        },
    }
    path = root / (MPN + ".json")
    path.write_text(json.dumps(data))
    return path, data


class MagneticEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.m = module("magnetics")

    def test_no_curve_remains_blocked_not_qualified(self):
        result = self.m.report(ROOT)
        self.assertEqual(result["status"], "NOT_QUALIFIED")
        self.assertFalse(result["layout_allowed"])
        self.assertEqual(result["imported_curve_count"], 0)
        self.assertEqual(len(result["rows"]), 5)
        self.assertTrue(all(row["curve_status"] == "BLOCKED_MISSING_CURVE" for row in result["rows"]))
        self.assertTrue(all(row["qualification"] == "NOT_QUALIFIED" for row in result["rows"]))

    def test_hashed_curve_values_come_from_csv_not_manifest_points(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, data = synthetic_pack(root)
            data["points"] = [[0, 10], [10, 10]]
            path.write_text(json.dumps(data))
            curve = self.m.load_curve(path, MPN)
            self.assertEqual(curve["points"], [[0.0, 10.0], [5.0, 7.0], [10.0, 4.0]])
            self.assertEqual(
                curve["provenance"]["manifest_sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_interpolation_and_no_extrapolation(self):
        curve = {"part_number": MPN, "points": [[0, 10], [5, 7], [10, 4]]}
        self.assertAlmostEqual(self.m.inductance_at(curve, 2.5, MPN), 8.5)
        with self.assertRaisesRegex(ValueError, "extrapolation"):
            self.m.inductance_at(curve, 11, MPN)

    def test_corrupted_original_or_csv_is_rejected(self):
        for filename in ("synthetic-original.txt", "synthetic.csv"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                path, _ = synthetic_pack(root)
                (root / filename).write_text("CHANGED")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    self.m.load_curve(path, MPN)

    def test_paths_cannot_escape_pack(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pack = root / "pack"
            pack.mkdir()
            path, data = synthetic_pack(pack)
            outside = root / "outside.csv"
            outside.write_bytes((pack / "synthetic.csv").read_bytes())
            data["normalized_csv"]["file"] = "../outside.csv"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "escapes"):
                self.m.load_curve(path, MPN)

    def test_source_url_must_match_reviewed_coilcraft_source_for_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            synthetic_pack(root, source_url="https://example.invalid/not-reviewed")
            with self.assertRaisesRegex(ValueError, "source URL differs"):
                self.m.report(ROOT, root)

    def test_reference_curve_can_screen_but_never_qualifies(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            synthetic_pack(root)
            result = self.m.report(ROOT, root)
            rows = [row for row in result["rows"] if row["part_number"] == MPN]
            self.assertTrue(rows)
            self.assertTrue(any(row["curve_status"] == "SCREEN_ONLY_REFERENCE_CURVE" for row in rows))
            self.assertTrue(all(row["qualification"] == "NOT_QUALIFIED" for row in rows))
            self.assertFalse(result["layout_allowed"])


if __name__ == "__main__":
    unittest.main()
