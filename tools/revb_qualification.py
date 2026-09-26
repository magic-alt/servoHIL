#!/usr/bin/env python3
"""Fail-closed Rev.B qualification aggregation.

This module validates evidence contracts. It never converts simulation, catalog
ratings, ERC, or a component datasheet into physical hardware qualification.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_profile(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("DUT profile must be a JSON object")
    if data.get("schema_version") != 1:
        raise ValueError("unsupported DUT profile schema")
    return data


def _finite(value: Any, name: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and result < 0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _nested(profile: dict[str, Any], section: str, fields: tuple[str, ...]) -> dict[str, Any]:
    value = profile.get(section)
    if not isinstance(value, dict):
        raise ValueError(f"missing {section} section")
    for field in fields:
        if field not in value:
            raise ValueError(f"missing {section}.{field}")
    return value


def _profile_is_unbound(profile: dict[str, Any]) -> bool:
    if not profile.get("adapter_id"):
        return True
    required = (
        ("ao_neutral", ("target_v", "min_v", "max_v", "source_impedance_ohm", "max_residual_current_a")),
        ("permit_input", ("asserted_min_v", "inhibited_max_v", "max_input_leakage_a")),
        ("cable_faults", ("open_response", "short_response")),
        ("measured_at", ("hw_revision", "dut_revision", "instrument_set")),
        ("evidence", ("ao_disconnect", "permit", "cable_open", "cable_short", "shutdown_time")),
    )
    if profile.get("max_end_to_end_disable_us") is None:
        return True
    for section, fields in required:
        value = profile.get(section)
        if not isinstance(value, dict):
            return True
        if any(value.get(field) in (None, "") for field in fields):
            return True
    return False


def _evidence_files(profile: dict[str, Any], root: Path) -> list[Path]:
    evidence = _nested(
        profile,
        "evidence",
        ("ao_disconnect", "permit", "cable_open", "cable_short", "shutdown_time"),
    )
    root = root.resolve()
    result: list[Path] = []
    for name, raw in evidence.items():
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"evidence.{name} must be a nonempty relative path")
        rel = Path(raw)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"evidence.{name} escapes repository")
        path = (root / rel).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"evidence.{name} escapes repository")
        result.append(path)
    return result


def evaluate_dut_profile(profile: dict[str, Any], root: str | Path | None = None) -> dict[str, Any]:
    if profile.get("schema_version") != 1:
        raise ValueError("unsupported DUT profile schema")

    if _profile_is_unbound(profile):
        return {
            "status": "BLOCKED",
            "adapter_id": profile.get("adapter_id"),
            "blockers": ["DUT_PROFILE_UNBOUND"],
            "physical_evidence": "NOT_BOUND",
        }

    adapter_id = profile.get("adapter_id")
    if not isinstance(adapter_id, str) or not adapter_id.strip():
        raise ValueError("adapter_id must be nonempty")

    neutral = _nested(
        profile,
        "ao_neutral",
        ("target_v", "min_v", "max_v", "source_impedance_ohm", "max_residual_current_a"),
    )
    target = _finite(neutral["target_v"], "neutral target")
    minimum = _finite(neutral["min_v"], "neutral minimum")
    maximum = _finite(neutral["max_v"], "neutral maximum")
    if minimum > maximum or not minimum <= target <= maximum:
        raise ValueError("neutral target must lie inside neutral min/max window")
    _finite(neutral["source_impedance_ohm"], "neutral source impedance", positive=True)
    _finite(neutral["max_residual_current_a"], "neutral residual current", nonnegative=True)

    permit = _nested(
        profile,
        "permit_input",
        ("asserted_min_v", "inhibited_max_v", "max_input_leakage_a"),
    )
    asserted_min = _finite(permit["asserted_min_v"], "permit asserted minimum")
    inhibited_max = _finite(permit["inhibited_max_v"], "permit inhibited maximum")
    if asserted_min <= inhibited_max:
        raise ValueError("permit asserted threshold must exceed inhibited threshold")
    _finite(permit["max_input_leakage_a"], "permit input leakage", nonnegative=True)

    disable_us = _finite(
        profile["max_end_to_end_disable_us"],
        "max end-to-end disable time",
        positive=True,
    )

    measured = _nested(profile, "measured_at", ("hw_revision", "dut_revision", "instrument_set"))
    for field, value in measured.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"measured_at.{field} must be bound")

    faults = _nested(profile, "cable_faults", ("open_response", "short_response"))
    blockers: list[str] = []
    if faults["open_response"] != "INHIBIT":
        blockers.append("DUT_CABLE_OPEN_NOT_FAIL_SAFE")
    if faults["short_response"] != "INHIBIT":
        blockers.append("DUT_CABLE_SHORT_NOT_FAIL_SAFE")

    evidence_state = "DECLARED_NOT_CHECKED"
    if root is not None:
        paths = _evidence_files(profile, Path(root))
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            blockers.append("DUT_PHYSICAL_EVIDENCE_MISSING")
            evidence_state = "MISSING"
        else:
            evidence_state = "FILES_PRESENT_NOT_CONTENT_QUALIFIED"

    return {
        "status": "BLOCKED" if blockers else "READY_FOR_ENGINEERING_REVIEW",
        "adapter_id": adapter_id,
        "max_end_to_end_disable_us": disable_us,
        "blockers": sorted(set(blockers)),
        "physical_evidence": evidence_state,
    }


def build_qualification_report(root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    gates = json.loads((root / "hardware/revB/gates.json").read_text(encoding="utf-8"))
    requirements = json.loads(
        (root / "hardware/revB/qualification_requirements.json").read_text(encoding="utf-8")
    )
    dut = evaluate_dut_profile(
        load_profile(root / requirements["dut_profile"]["path"]),
        root=root,
    )

    if gates.get("layout_allowed") is not False:
        raise ValueError("qualification branch must preserve layout_allowed=false")

    blockers = list(dut["blockers"])
    active_gates = gates.get("gates", {})
    for name, entry in sorted(active_gates.items()):
        if not isinstance(entry, dict) or entry.get("status") != "PASS":
            blockers.append(f"GATE_{name.upper()}_NOT_PASS")

    # These categories require real evidence outside this aggregator. Their
    # presence in the requirements file keeps them visible even if another
    # report accidentally omits a blocker.
    for name in requirements.get("physical_required", []):
        blockers.append(f"PHYSICAL_{name}_REQUIRED")
    for name in requirements.get("vivado_required", []):
        blockers.append(f"TOOL_{name}_REQUIRED")

    return {
        "schema_version": 1,
        "revision": gates.get("revision", "Rev.B"),
        "qualification": "BLOCKED" if blockers else "READY_FOR_ENGINEERING_REVIEW",
        "layout_allowed": False,
        "dut_adapter": dut,
        "blockers": sorted(set(blockers)),
        "note": "Evidence aggregation only; never a fabrication or functional-safety approval.",
    }


if __name__ == "__main__":
    print(json.dumps(build_qualification_report(), indent=2, allow_nan=False))
