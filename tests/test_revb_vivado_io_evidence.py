import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_revb_vivado_io_drc import expected_io
from revb import source_digest
from revb_vivado_io_evidence import validate_run


class RevBVivadoIoDrcEvidenceTests(unittest.TestCase):
    def make_run(self, root: Path):
        (root / "report_drc.rpt").write_text("synthetic DRC report for parser contract\n")
        (root / "report_io.rpt").write_text("synthetic IO report for parser contract\n")
        (root / "run_identity.txt").write_text(
            "\n".join([
                "purpose=REV_B_IO_DRC_HARNESS_ONLY",
                "vivado_version=2025.2",
                "target_part=xczu2cg-sfvc784-1-e",
                "top_module=servohil_io_drc_top",
                "rtl=/repo/fpga/revb/io_drc/servohil_io_drc_top.sv",
                "xdc=/repo/fpga/revb/io_drc/axu2cgb_io_drc.xdc",
                "source_commit=0123456789abcdef",
                f"source_digest={source_digest(ROOT)}",
                "timing_claim=NOT_RUN",
                "",
            ])
        )
        (root / "drc_summary.json").write_text(json.dumps({
            "schema_version": 1,
            "purpose": "REV_B_IO_DRC_HARNESS_ONLY",
            "target_part": "xczu2cg-sfvc784-1-e",
            "top_module": "servohil_io_drc_top",
            "port_count": 64,
            "error_count": 0,
            "critical_warning_count": 0,
            "warning_count": 0,
            "total_violation_count": 0,
            "timing_claim": "NOT_RUN",
        }))
        with (root / "io_runtime.csv").open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["port", "package_pin", "iostandard"])
            for port, row in sorted(expected_io(ROOT).items()):
                writer.writerow([port, row["PACKAGE_PIN"], row["IOSTANDARD"]])

    def test_synthetic_complete_raw_pack_validates_contract_only(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            self.make_run(run)
            result = validate_run(run, ROOT)
            self.assertEqual(result["status"], "PASS_RAW_IO_DRC_VALIDATED")
            self.assertEqual(result["vivado_version"], "2025.2")
            self.assertEqual(result["port_count"], 64)
            self.assertEqual(result["timing_claim"], "NOT_RUN")

    def test_runtime_pin_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            self.make_run(run)
            rows = (run / "io_runtime.csv").read_text().splitlines()
            rows[1] = rows[1].replace(rows[1].split(",")[1], "ZZ99")
            (run / "io_runtime.csv").write_text("\n".join(rows) + "\n")
            with self.assertRaisesRegex(ValueError, "runtime PACKAGE_PIN drift"):
                validate_run(run, ROOT)

    def test_error_or_critical_warning_is_rejected(self):
        for field in ("error_count", "critical_warning_count"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as td:
                run = Path(td)
                self.make_run(run)
                summary = json.loads((run / "drc_summary.json").read_text())
                summary[field] = 1
                summary["total_violation_count"] = 1
                (run / "drc_summary.json").write_text(json.dumps(summary))
                with self.assertRaisesRegex(ValueError, "Error/Critical Warning"):
                    validate_run(run, ROOT)

    def test_stale_source_digest_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            self.make_run(run)
            current = source_digest(ROOT)
            text = (run / "run_identity.txt").read_text().replace(
                f"source_digest={current}", "source_digest=" + "0" * 64
            )
            (run / "run_identity.txt").write_text(text)
            with self.assertRaisesRegex(ValueError, "source_digest is stale"):
                validate_run(run, ROOT)

    def test_unbound_source_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            self.make_run(run)
            text = (run / "run_identity.txt").read_text().replace(
                "source_commit=0123456789abcdef", "source_commit=UNBOUND"
            )
            (run / "run_identity.txt").write_text(text)
            with self.assertRaisesRegex(ValueError, "source_commit"):
                validate_run(run, ROOT)


if __name__ == "__main__":
    unittest.main()
