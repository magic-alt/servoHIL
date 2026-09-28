#!/usr/bin/env python3
"""Validate and package Rev.B Vivado I/O-DRC raw evidence.

The script never runs Vivado. It independently checks retained raw outputs against
the checked-in 64-port contract before creating a PASS evidence envelope.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import json
import re
from pathlib import Path
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE = "prelayout_tool_vivado_io_drc"
CARRIER = "axu2cgb"
REQUIRED_RAW = (
    "report_drc.rpt",
    "report_io.rpt",
    "drc_summary.json",
    "io_runtime.csv",
    "run_identity.txt",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        if "=" not in raw:
            raise ValueError(f"run_identity line {number}: expected key=value")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key or key in result:
            raise ValueError(f"run_identity line {number}: duplicate/empty key")
        result[key] = value.strip()
    return result


def runtime_io(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or set(rows[0]) != {"port", "package_pin", "iostandard"}:
        raise ValueError("io_runtime.csv must use port,package_pin,iostandard columns")
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        port = row["port"]
        if not port or port in result:
            raise ValueError("io_runtime.csv contains empty/duplicate port")
        result[port] = {
            "PACKAGE_PIN": row["package_pin"],
            "IOSTANDARD": row["iostandard"],
        }
    return result


def validate_run(run_dir: str | Path, root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    run_dir = Path(run_dir)
    missing = [name for name in REQUIRED_RAW if not (run_dir / name).is_file()]
    if missing:
        raise ValueError("missing Vivado raw outputs: " + ", ".join(missing))
    for name in ("report_drc.rpt", "report_io.rpt"):
        if (run_dir / name).stat().st_size == 0:
            raise ValueError(name + " is empty")

    from check_revb_vivado_io_drc import PART, TOP, expected_io, check as check_static

    static = check_static(root)
    ident = identity(run_dir / "run_identity.txt")
    required_identity = {
        "purpose": "REV_B_IO_DRC_HARNESS_ONLY",
        "target_part": PART,
        "top_module": TOP,
        "timing_claim": "NOT_RUN",
    }
    for key, value in required_identity.items():
        if ident.get(key) != value:
            raise ValueError(f"run_identity {key} mismatch")
    if not ident.get("vivado_version"):
        raise ValueError("run_identity vivado_version missing")
    if not ident.get("source_commit") or ident["source_commit"] == "UNBOUND":
        raise ValueError("run_identity source_commit must be bound")
    digest = ident.get("source_digest")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("run_identity source_digest must be a bound lowercase SHA-256")

    from revb import source_digest
    current_digest = source_digest(root)
    if digest != current_digest:
        raise ValueError("Vivado raw run source_digest is stale for current source")

    summary = json.loads((run_dir / "drc_summary.json").read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or summary.get("schema_version") != 1:
        raise ValueError("unsupported drc_summary schema")
    for key, value in {
        "purpose": "REV_B_IO_DRC_HARNESS_ONLY",
        "target_part": PART,
        "top_module": TOP,
        "port_count": 64,
        "timing_claim": "NOT_RUN",
    }.items():
        if summary.get(key) != value:
            raise ValueError(f"drc_summary {key} mismatch")
    for key in ("error_count", "critical_warning_count", "warning_count", "total_violation_count"):
        if type(summary.get(key)) is not int or summary[key] < 0:
            raise ValueError(f"drc_summary {key} must be nonnegative integer")
    if summary["error_count"] != 0 or summary["critical_warning_count"] != 0:
        raise ValueError("Vivado I/O DRC contains Error/Critical Warning violations")

    expected = expected_io(root)
    observed = runtime_io(run_dir / "io_runtime.csv")
    if set(observed) != set(expected):
        raise ValueError(
            f"runtime I/O coverage drift: missing={sorted(set(expected)-set(observed))} "
            f"unexpected={sorted(set(observed)-set(expected))}"
        )
    for port, row in expected.items():
        if observed[port]["PACKAGE_PIN"] != row["PACKAGE_PIN"]:
            raise ValueError(f"{port}: runtime PACKAGE_PIN drift")
        if observed[port]["IOSTANDARD"] != row["IOSTANDARD"]:
            raise ValueError(f"{port}: runtime IOSTANDARD drift")

    return {
        "status": "PASS_RAW_IO_DRC_VALIDATED",
        "layout_allowed": False,
        "gate": GATE,
        "carrier": CARRIER,
        "source_commit": ident["source_commit"],
        "source_digest": digest,
        "vivado_version": ident["vivado_version"],
        "target_part": PART,
        "top_module": TOP,
        "port_count": 64,
        "warning_count": summary["warning_count"],
        "total_violation_count": summary["total_violation_count"],
        "static_contract": static["status"],
        "timing_claim": "NOT_RUN",
        "raw_files": {name: sha256(run_dir / name) for name in REQUIRED_RAW},
    }


def _repo_relative(root: Path, path: Path, name: str) -> str:
    root = root.resolve()
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError(name + " must be inside the repository")
    return path.relative_to(root).as_posix()


def prepare(
    run_dir: str | Path,
    output_dir: str | Path,
    *,
    source_commit: str,
    reviewer: str,
    reviewed_on: str,
    root: str | Path = ROOT,
) -> dict[str, Any]:
    root = Path(root).resolve()
    run_dir = Path(run_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if not output_dir.is_relative_to(root):
        raise ValueError("evidence output directory must be inside repository")
    rel_output = output_dir.relative_to(root)
    if not rel_output.parts or rel_output.parts[0] != "evidence":
        raise ValueError("Vivado evidence must live under top-level evidence/")
    if output_dir.exists():
        raise ValueError("evidence output directory already exists; never overwrite raw evidence")
    date.fromisoformat(reviewed_on)
    if not reviewer.strip():
        raise ValueError("reviewer must be nonempty")

    validated = validate_run(run_dir, root)
    if validated["source_commit"] != source_commit:
        raise ValueError("requested source_commit differs from Vivado run identity")

    output_dir.mkdir(parents=True)
    copied: list[dict[str, str]] = []
    for name in REQUIRED_RAW:
        dst = output_dir / name
        shutil.copyfile(run_dir / name, dst)
        copied.append({
            "path": _repo_relative(root, dst, name),
            "sha256": sha256(dst),
        })

    raw_manifest = {
        "schema_version": 1,
        "record_type": "REV_B_VIVADO_IO_DRC_RAW_MANIFEST",
        "purpose": "REV_B_IO_DRC_HARNESS_ONLY",
        "source_commit": source_commit,
        "vivado_version": validated["vivado_version"],
        "target_part": validated["target_part"],
        "top_module": validated["top_module"],
        "port_count": validated["port_count"],
        "warning_count": validated["warning_count"],
        "total_violation_count": validated["total_violation_count"],
        "timing_claim": "NOT_RUN",
        "artifacts": copied,
    }
    manifest_path = output_dir / "raw_manifest.json"
    manifest_path.write_text(json.dumps(raw_manifest, indent=2) + "\n", encoding="utf-8")

    source_files = [
        "hardware/revB/io_contract.json",
        "hardware/carriers/axu2cgb/profile.json",
        "hardware/carriers/axu2cgb/assignments.csv",
        "hardware/carriers/axu2cgb/physical_pinout.csv",
        "hardware/revB/vivado_input_contract.json",
        "fpga/revb/io_drc/servohil_io_drc_top.sv",
        "fpga/revb/io_drc/axu2cgb_io_drc.xdc",
        "fpga/revb/io_drc/run_io_drc.tcl",
    ]
    source_artifacts = [
        {"path": path, "sha256": sha256(root / path)}
        for path in source_files
    ]
    evidence = {
        "schema_version": 2,
        "record_type": "REV_B_VIVADO_IO_DRC_EVIDENCE",
        "carrier": CARRIER,
        "gate": GATE,
        "result": "PASS",
        "scope": "PACKAGE_PIN_AND_IOSTANDARD_ONLY",
        "timing_result": "NOT_RUN",
        "vivado_version": validated["vivado_version"],
        "target_part": validated["target_part"],
        "top_module": validated["top_module"],
        "source_commit": source_commit,
        "source_digest": validated["source_digest"],
        "source_artifacts": source_artifacts,
        "raw_report": _repo_relative(root, manifest_path, "raw manifest"),
        "raw_sha256": sha256(manifest_path),
        "raw_artifacts": copied,
        "reviewed_on": reviewed_on,
        "reviewer": reviewer,
        "note": "PASS is limited to the dedicated 64-port package-pin/IOSTANDARD harness. Functional STA remains NOT_RUN.",
    }
    evidence_path = output_dir / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "PREPARED_PASS_EVIDENCE_NOT_YET_REGISTERED",
        "evidence": _repo_relative(root, evidence_path, "evidence"),
        "raw_manifest": evidence["raw_report"],
        "source_digest": evidence["source_digest"],
        "timing_result": "NOT_RUN",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("source-digest")
    validate = sub.add_parser("validate-run")
    validate.add_argument("run_dir", type=Path)

    prep = sub.add_parser("prepare")
    prep.add_argument("run_dir", type=Path)
    prep.add_argument("output_dir", type=Path)
    prep.add_argument("--source-commit", required=True)
    prep.add_argument("--reviewer", required=True)
    prep.add_argument("--reviewed-on", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "source-digest":
            from revb import source_digest
            print(source_digest(ROOT))
            return 0
        if args.command == "validate-run":
            result = validate_run(args.run_dir)
        else:
            result = prepare(
                args.run_dir,
                args.output_dir,
                source_commit=args.source_commit,
                reviewer=args.reviewer,
                reviewed_on=args.reviewed_on,
            )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("VIVADO IO DRC EVIDENCE ERROR:", exc, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
