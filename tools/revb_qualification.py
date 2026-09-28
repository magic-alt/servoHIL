#!/usr/bin/env python3
"""Fail-closed Rev.B qualification aggregation.

This module validates evidence contracts. It never converts simulation, catalog
ratings, ERC, or a component datasheet into physical hardware qualification.
"""
from __future__ import annotations

import hashlib
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


def _string_list(data: dict[str, Any], name: str, *, minimum: int = 1) -> list[str]:
    value = data.get(name)
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{name} must contain at least {minimum} entries")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{name} entries must be nonempty strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} must not contain duplicates")
    return value


def _verified_gate_evidence(
    entry: dict[str, Any],
    root: Path,
    gate_name: str,
    expected_carrier: str | None = None,
) -> list[str]:
    """Validate the same source-bound evidence envelope used by tools/revb.py release."""
    if entry.get("status") != "PASS":
        return []

    evidence = entry.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError(f"{gate_name}: PASS requires a release evidence JSON path")

    root = root.resolve()
    rel = Path(evidence)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"{gate_name}: evidence path escapes repository")
    report_path = (root / rel).resolve()
    if not report_path.is_relative_to(root):
        raise ValueError(f"{gate_name}: evidence path escapes repository")
    if not report_path.is_file():
        raise ValueError(f"{gate_name}: evidence file missing: {evidence}")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{gate_name}: invalid evidence JSON") from exc
    if not isinstance(report, dict):
        raise ValueError(f"{gate_name}: evidence report must be an object")
    if report.get("gate") != gate_name or report.get("result") != "PASS":
        raise ValueError(f"{gate_name}: evidence gate/result mismatch")
    if expected_carrier is not None and report.get("carrier") != expected_carrier:
        raise ValueError(f"{gate_name}: evidence carrier mismatch")

    # Keep the qualification aggregator and the actual release path on one source
    # identity algorithm rather than inventing a parallel digest.
    from revb import source_digest

    expected_digest = source_digest(root)
    if report.get("source_digest") != expected_digest:
        raise ValueError(f"{gate_name}: stale evidence source digest")

    raw_name = report.get("raw_report")
    raw_sha = report.get("raw_sha256")
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise ValueError(f"{gate_name}: evidence report must name raw_report")
    raw_rel = Path(raw_name)
    if raw_rel.is_absolute() or ".." in raw_rel.parts:
        raise ValueError(f"{gate_name}: raw report path escapes repository")
    raw_path = (root / raw_rel).resolve()
    if not raw_path.is_relative_to(root) or not raw_path.is_file():
        raise ValueError(f"{gate_name}: raw report missing")
    if not isinstance(raw_sha, str) or len(raw_sha) != 64:
        raise ValueError(f"{gate_name}: raw_sha256 missing/invalid")
    actual = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    if actual != raw_sha:
        raise ValueError(f"{gate_name}: raw report hash mismatch")

    verified = [evidence, raw_name]
    artifacts = report.get("raw_artifacts", [])
    if artifacts:
        if not isinstance(artifacts, list):
            raise ValueError(f"{gate_name}: raw_artifacts must be a list")
        seen: set[str] = set()
        for artifact in artifacts:
            if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
                raise ValueError(f"{gate_name}: invalid raw_artifacts record")
            raw_artifact = artifact["path"]
            raw_artifact_sha = artifact["sha256"]
            if not isinstance(raw_artifact, str) or not raw_artifact.strip() or raw_artifact in seen:
                raise ValueError(f"{gate_name}: invalid/duplicate raw artifact path")
            artifact_rel = Path(raw_artifact)
            if artifact_rel.is_absolute() or ".." in artifact_rel.parts:
                raise ValueError(f"{gate_name}: raw artifact path escapes repository")
            artifact_path = (root / artifact_rel).resolve()
            if not artifact_path.is_relative_to(root) or not artifact_path.is_file():
                raise ValueError(f"{gate_name}: raw artifact missing")
            if not isinstance(raw_artifact_sha, str) or len(raw_artifact_sha) != 64:
                raise ValueError(f"{gate_name}: raw artifact SHA-256 missing/invalid")
            if hashlib.sha256(artifact_path.read_bytes()).hexdigest() != raw_artifact_sha:
                raise ValueError(f"{gate_name}: raw artifact hash mismatch")
            seen.add(raw_artifact)
            verified.append(raw_artifact)

    return verified


def _qualification_evidence_state(
    data: dict[str, Any],
    root: Path,
    mechanical_required: list[str],
    component_required: list[str],
    physical_required: list[str],
    vivado_required: list[str],
) -> dict[str, Any]:
    if data.get("schema_version") != 1:
        raise ValueError("unsupported prelayout evidence status schema")
    if data.get("layout_allowed") is not False:
        raise ValueError("prelayout evidence status must preserve layout_allowed=false")
    carrier = data.get("carrier")
    if not isinstance(carrier, str) or not carrier.strip():
        raise ValueError("prelayout evidence status carrier must be bound")

    expected = {
        "mechanical": set(mechanical_required),
        "component": set(component_required),
        "physical": set(physical_required),
        "vivado": set(vivado_required),
    }
    blockers: list[str] = []
    verified: dict[str, list[str]] = {}
    states: dict[str, dict[str, str]] = {}
    blocker_prefix = {
        "mechanical": lambda name: f"MECHANICAL_{name}_REQUIRED",
        "component": lambda name: f"COMPONENT_{name}_REQUIRED",
        "physical": lambda name: f"PHYSICAL_{name}_REQUIRED",
        "vivado": lambda name: f"TOOL_{name}_REQUIRED",
    }
    for category, required in expected.items():
        section = data.get(category)
        if not isinstance(section, dict) or set(section) != required:
            raise ValueError(
                f"prelayout evidence {category} coverage drift: "
                f"missing={sorted(required-set(section or {}))} "
                f"unexpected={sorted(set(section or {})-required)}"
            )
        states[category] = {}
        for name in sorted(required):
            entry = section[name]
            if not isinstance(entry, dict):
                raise ValueError(f"{category}.{name}: evidence state must be an object")
            status = entry.get("status")
            if status not in {"NOT_RUN", "BLOCKED", "FAIL", "PASS"}:
                raise ValueError(f"{category}.{name}: invalid evidence status")
            gate_name = entry.get("gate")
            if not isinstance(gate_name, str) or not gate_name.startswith("prelayout_"):
                raise ValueError(f"{category}.{name}: invalid evidence gate name")
            states[category][name] = status
            key = f"{category}.{name}"
            if status == "PASS":
                verified[key] = _verified_gate_evidence(
                    entry, root, gate_name, expected_carrier=carrier
                )
            else:
                if entry.get("evidence") not in (None, ""):
                    raise ValueError(f"{category}.{name}: non-PASS state cannot claim evidence")
                blockers.append(blocker_prefix[category](name))
    return {
        "carrier": carrier,
        "status": data.get("status"),
        "states": states,
        "verified": verified,
        "blockers": blockers,
    }

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
    if requirements.get("schema_version") != 3:
        raise ValueError("unsupported qualification requirements schema")
    if requirements.get("release_policy", {}).get("layout_allowed") is not False:
        raise ValueError("qualification requirements must preserve layout_allowed=false")

    component_required = _string_list(requirements, "component_evidence_required", minimum=1)
    physical_required = _string_list(requirements, "physical_required", minimum=1)
    vivado_required = _string_list(requirements, "vivado_required", minimum=1)
    post_layout_required = _string_list(requirements, "release_after_layout_required", minimum=1)
    _string_list(requirements, "analytical_required", minimum=1)

    dut_section = requirements.get("dut_profile")
    if not isinstance(dut_section, dict) or not isinstance(dut_section.get("path"), str):
        raise ValueError("qualification requirements must bind dut_profile.path")
    expected_dut_evidence = _string_list(dut_section, "required_evidence", minimum=5)
    if set(expected_dut_evidence) != {
        "ao_disconnect",
        "permit",
        "cable_open",
        "cable_short",
        "shutdown_time",
    }:
        raise ValueError("DUT evidence contract drift")

    dut = evaluate_dut_profile(load_profile(root / dut_section["path"]), root=root)

    evidence_section = requirements.get("prelayout_evidence_status")
    if not isinstance(evidence_section, dict) or not isinstance(evidence_section.get("path"), str):
        raise ValueError("qualification requirements must bind prelayout_evidence_status.path")

    from check_revb_prelayout_contract import check as check_prelayout_contract
    prelayout = check_prelayout_contract(root)
    mechanical_required = list(prelayout["mechanical_open_refs"])

    if gates.get("layout_allowed") is not False:
        raise ValueError("qualification branch must preserve layout_allowed=false")

    blockers = list(dut["blockers"])
    active_gates = gates.get("gates", {})
    if not isinstance(active_gates, dict):
        raise ValueError("gates.gates must be an object")
    verified_gate_evidence: dict[str, list[str]] = {}
    for name, entry in sorted(active_gates.items()):
        if not isinstance(entry, dict):
            blockers.append(f"GATE_{name.upper()}_NOT_PASS")
            continue
        if entry.get("status") == "PASS":
            verified_gate_evidence[name] = _verified_gate_evidence(entry, root, name)
        else:
            blockers.append(f"GATE_{name.upper()}_NOT_PASS")

    evidence_status = json.loads(
        (root / evidence_section["path"]).read_text(encoding="utf-8")
    )
    requirement_evidence = _qualification_evidence_state(
        evidence_status,
        root,
        mechanical_required,
        component_required,
        physical_required,
        vivado_required,
    )
    blockers.extend(requirement_evidence["blockers"])

    return {
        "schema_version": 3,
        "revision": gates.get("revision", "Rev.B"),
        "qualification": "BLOCKED" if blockers else "READY_FOR_ENGINEERING_REVIEW",
        "layout_allowed": False,
        "dut_adapter": dut,
        "prelayout_contract": prelayout,
        "mechanical_required": mechanical_required,
        "component_evidence_required": component_required,
        "physical_required": physical_required,
        "vivado_required": vivado_required,
        "post_layout_release_required": post_layout_required,
        "verified_gate_evidence": verified_gate_evidence,
        "prelayout_evidence_status": requirement_evidence["states"],
        "verified_requirement_evidence": requirement_evidence["verified"],
        "blockers": sorted(set(blockers)),
        "note": (
            "Evidence aggregation only; analytical screens and catalog ratings cannot "
            "authorize fabrication, safety or production release."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(build_qualification_report(), indent=2, allow_nan=False))
