#!/usr/bin/env python3
"""Fail-closed audit for Rev.B native schematic package/BOM closure."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "hardware/kicad/revB/axu2cgb_expansion"
MANIFEST = ROOT / "hardware/revB/schematic_open_items.json"
AD3542_EVIDENCE = ROOT / "hardware/revB/ad3542r_footprint_evidence.json"

REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
FP_RE = re.compile(r'\(property "Footprint" "([^"]*)"')
DS_RE = re.compile(r'\(property "Datasheet" "([^"]*)"')
VAL_RE = re.compile(r'\(property "Value" "([^"]*)"')

AD3542_REFS = ("U20", "U21", "U22", "U23")
MECHANICAL_REFS = ("J101", "SW101", "J5", "J501", "J701")


def _field(rx, line, default=""):
    m = rx.search(line)
    return m.group(1) if m else default


def placed_symbols():
    rows = []
    for path in sorted(NATIVE.glob("*.kicad_sch")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.lstrip().startswith("(symbol (lib_id "):
                continue
            ref = _field(REF_RE, line)
            if not ref:
                continue
            rows.append(
                {
                    "sheet": path.name,
                    "reference": ref,
                    "value": _field(VAL_RE, line),
                    "footprint": _field(FP_RE, line),
                    "datasheet": _field(DS_RE, line),
                    "in_bom": "(in_bom yes)" in line,
                    "on_board": "(on_board yes)" in line,
                    "dnp": "(dnp yes)" in line,
                }
            )
    return rows


def _nonempty_string_list(value, name, minimum=1):
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{name} must contain at least {minimum} entries")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{name} entries must be nonempty strings")
    return value


def _resolve_requirement(requirements, ref, stack=()):
    if ref in stack:
        raise ValueError("binding requirement inheritance cycle: " + " -> ".join(stack + (ref,)))
    raw = requirements.get(ref)
    if not isinstance(raw, dict):
        raise ValueError("missing binding requirement for " + ref)
    parent = raw.get("same_as")
    if parent is None:
        return dict(raw)
    if not isinstance(parent, str) or not parent:
        raise ValueError(ref + ".same_as must be a nonempty reference")
    merged = _resolve_requirement(requirements, parent, stack + (ref,))
    merged.update({k: v for k, v in raw.items() if k != "same_as"})
    return merged



def _optional_sha256(value, name):
    if value is None:
        return
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(name + " must be null or lowercase SHA-256")


def _check_ad3542_evidence(req):
    expected_rel = "hardware/revB/ad3542r_footprint_evidence.json"
    if req.get("evidence_manifest") != expected_rel:
        raise ValueError("AD3542R binding must point to official footprint evidence manifest")
    data = json.loads(AD3542_EVIDENCE.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported AD3542R footprint evidence schema")
    if data.get("release_effect") != "BLOCKER_REMAINS_OPEN":
        raise ValueError("AD3542R evidence must not silently close the blocker")
    if data.get("status") != "OFFICIAL_SOURCES_LOCATED_GERBER_AND_CAD_BYTES_NOT_ARCHIVED":
        raise ValueError("AD3542R evidence status drift")

    part = data.get("part", {})
    expected = {
        "manufacturer": "Analog Devices",
        "mpn": "AD3542RBCPZ16",
        "package_option": "CP-28-15",
        "pin_count": 28,
        "lead_pitch_mm": 0.4,
    }
    for key, value in expected.items():
        if part.get(key) != value:
            raise ValueError(f"AD3542R evidence part.{key} drift")
    if "4 mm x 4 mm" not in str(part.get("package_description", "")):
        raise ValueError("AD3542R evidence must retain 4 mm x 4 mm package identity")

    sources = data.get("official_sources", {})
    gerber = sources.get("evaluation_gerber_zip", "")
    schematic = sources.get("evaluation_schematic", "")
    bom = sources.get("evaluation_bom", "")
    if not isinstance(gerber, str) or not gerber.endswith("/09-050892-01c.zip"):
        raise ValueError("AD3542R official EVAL Gerber source drift")
    if not isinstance(schematic, str) or not schematic.endswith("/02_050892d_top.pdf"):
        raise ValueError("AD3542R official EVAL schematic source drift")
    if not isinstance(bom, str) or not bom.endswith("/05-050892-01-d.xlsx"):
        raise ValueError("AD3542R official EVAL BOM source drift")
    doc = sources.get("adi_documentation_source", {})
    if doc.get("repository") != "analogdevicesinc/system-level":
        raise ValueError("AD3542R ADI documentation repository drift")
    if doc.get("commit") != "76eb29d83e6eaca9ce4470921d315938b2b1aa17":
        raise ValueError("AD3542R ADI documentation commit drift")
    if doc.get("path") != "docs/solutions/reference-designs/eval-ad35xxr/user-guide.rst":
        raise ValueError("AD3542R ADI documentation path drift")
    if doc.get("blob_sha") != "6327c05006caf900728a31445a3c4fdf3d31253a":
        raise ValueError("AD3542R ADI documentation blob drift")

    exposed = data.get("exposed_pad_review", {})
    if exposed.get("status") != "UNRESOLVED_REQUIRES_CURRENT_CAD_OR_GERBER":
        raise ValueError("AD3542R exposed/center-pad decision must remain unresolved")
    resolution = _nonempty_string_list(
        exposed.get("required_resolution"),
        "AD3542R exposed_pad_review.required_resolution",
        minimum=4,
    )
    joined = " ".join(resolution).lower()
    for term in ("cad", "gerber", "center pad", "electrical"):
        if term not in joined:
            raise ValueError("AD3542R exposed-pad resolution lost required term: " + term)

    artifacts = data.get("retrieved_artifacts", {})
    for key, value in artifacts.items():
        _optional_sha256(value, "AD3542R retrieved_artifacts." + key)
    if artifacts.get("evaluation_gerber_zip_sha256") is not None:
        raise ValueError("AD3542R status says Gerber bytes are not archived")
    if artifacts.get("ultra_librarian_archive_sha256") is not None:
        raise ValueError("AD3542R status says exact CAD bytes are not archived")
    if artifacts.get("samacsys_archive_sha256") is not None:
        raise ValueError("AD3542R status says exact CAD bytes are not archived")

    geometry = data.get("geometry_review", {})
    if geometry.get("status") != "NOT_RUN_BYTES_NOT_ARCHIVED":
        raise ValueError("AD3542R geometry review must remain NOT_RUN until bytes are archived")
    if geometry.get("center_pad_present") is not None:
        raise ValueError("AD3542R center-pad geometry must not be guessed")

    criteria = _nonempty_string_list(data.get("close_criteria"), "AD3542R close_criteria", minimum=8)
    criteria_text = " ".join(criteria).lower()
    for term in ("gerber", "pin-1", "0.40", "center-pad", "kicad", "erc"):
        if term not in criteria_text:
            raise ValueError("AD3542R close criteria lost required term: " + term)

    return data


def _check_binding_requirements(manifest, by_ref, allowed):
    requirements = manifest.get("binding_requirements")
    if not isinstance(requirements, dict):
        raise ValueError("binding_requirements must be an object")
    if set(requirements) != allowed:
        raise ValueError(
            "binding requirement set changed: missing=%s unexpected=%s"
            % (sorted(allowed - set(requirements)), sorted(set(requirements) - allowed))
        )

    resolved = {ref: _resolve_requirement(requirements, ref) for ref in sorted(allowed)}
    ad3542_evidence = _check_ad3542_evidence(resolved["U20"])

    for ref in AD3542_REFS:
        req = resolved[ref]
        row = by_ref.get(ref)
        if not row:
            raise ValueError("missing AD3542R instance " + ref)
        expected = {
            "kind": "exact_land_pattern",
            "status": "OPEN_VENDOR_LAND_PATTERN_NOT_VENDORED",
            "manufacturer": "Analog Devices",
            "mpn": "AD3542RBCPZ16",
            "package_option": "CP-28-15",
        }
        for key, value in expected.items():
            if req.get(key) != value:
                raise ValueError(f"{ref}.{key} drift: {req.get(key)!r} != {value!r}")
        if row["footprint"]:
            raise ValueError(ref + " must remain blank until exact reviewed land pattern is vendored")
        if req.get("datasheet_url") != row["datasheet"]:
            raise ValueError(ref + " binding datasheet must exactly match native schematic")
        package_url = req.get("package_drawing_url", "")
        if not isinstance(package_url, str) or "cp-28-15" not in package_url.lower():
            raise ValueError(ref + " must bind the CP-28-15 package drawing source")
        if "4 mm x 4 mm" not in str(req.get("package_description", "")):
            raise ValueError(ref + " must retain the reviewed 4 mm x 4 mm package identity")
        _nonempty_string_list(req.get("cad_sources"), ref + ".cad_sources", minimum=1)
        evidence = _nonempty_string_list(
            req.get("required_evidence"), ref + ".required_evidence", minimum=4
        )
        if not any("independent" in x.lower() for x in evidence):
            raise ValueError(ref + " requires an independent land-pattern check")
        reason = manifest["open_footprints"].get(ref, "")
        if "CP-28-15" not in reason or "land pattern" not in reason.lower():
            raise ValueError(ref + " must retain the exact CP-28-15 land-pattern blocker")

    for ref in MECHANICAL_REFS:
        req = resolved[ref]
        row = by_ref.get(ref)
        if not row:
            raise ValueError("missing mechanical instance " + ref)
        if req.get("kind") != "mechanical_selection":
            raise ValueError(ref + " must remain a mechanical_selection blocker")
        if req.get("status") != "OPEN_REAL_MECHANICAL_CONTRACT_REQUIRED":
            raise ValueError(ref + " must remain explicitly OPEN")
        if row["footprint"]:
            raise ValueError(ref + " must remain blank until real mechanical contract is bound")
        if not isinstance(req.get("interface"), str) or not req["interface"].strip():
            raise ValueError(ref + " must identify its physical interface")
        _nonempty_string_list(
            req.get("required_contract_fields"), ref + ".required_contract_fields", minimum=5
        )
        _nonempty_string_list(req.get("required_evidence"), ref + ".required_evidence", minimum=2)

    j701 = resolved["J701"]
    required_terms = " ".join(j701["required_contract_fields"]).lower()
    for term in ("dut", "leakage", "isolation", "cable"):
        if term not in required_terms:
            raise ValueError("J701 physical contract must retain " + term + " requirement")

    return resolved, ad3542_evidence


def check():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 2:
        raise ValueError("unsupported schematic-open-items schema")
    if manifest.get("layout_allowed") is not False:
        raise ValueError("schematic closure manifest must not authorize Layout")
    if not isinstance(manifest.get("close_policy"), str) or "insufficient" not in manifest["close_policy"]:
        raise ValueError("close_policy must explicitly prevent evidence-free blocker closure")

    rows = placed_symbols()
    by_ref = {r["reference"]: r for r in rows}
    if len(by_ref) != len(rows):
        dup = sorted(r for r in by_ref if sum(x["reference"] == r for x in rows) > 1)
        raise ValueError("duplicate physical references: " + str(dup))

    physical = [
        r
        for r in rows
        if r["in_bom"] and r["on_board"] and not r["reference"].startswith("#")
    ]
    missing = {r["reference"] for r in physical if not r["footprint"]}
    allowed = set(manifest.get("open_footprints", {}))
    if missing != allowed:
        raise ValueError(
            "blank footprint set changed: unexpected=%s resolved_not_removed=%s"
            % (sorted(missing - allowed), sorted(allowed - missing))
        )

    expected_status = f"SCHEMATIC_FUNCTION_COMPLETE_{len(allowed)}_PHYSICAL_BINDINGS_OPEN"
    if manifest.get("status") != expected_status:
        raise ValueError(
            "manifest status/count drift: %r != %r" % (manifest.get("status"), expected_status)
        )

    for ref in manifest.get("excluded_host_boundaries", []):
        row = by_ref.get(ref)
        if not row:
            raise ValueError("missing host boundary " + ref)
        if row["in_bom"] or row["on_board"]:
            raise ValueError(ref + " must remain excluded from expansion-board BOM/placement")

    for ref, expected in manifest.get("bound_packages", {}).items():
        row = by_ref.get(ref)
        if not row:
            raise ValueError("missing bound component " + ref)
        if row["footprint"] != expected:
            raise ValueError("%s footprint drift: %s != %s" % (ref, row["footprint"], expected))
        lib, name = expected.split(":", 1)
        local = NATIVE / "footprints" / (lib + ".pretty") / (name + ".kicad_mod")
        if not local.is_file():
            raise ValueError("missing locally vendored footprint for %s: %s" % (ref, local))

    resolved, ad3542_evidence = _check_binding_requirements(manifest, by_ref, allowed)

    return {
        "status": "PASS_SOURCE_CLOSURE_CONTRACT",
        "physical_components": len(physical),
        "blank_footprints": sorted(missing),
        "blank_footprint_count": len(missing),
        "binding_requirement_count": len(resolved),
        "land_pattern_blockers": sorted(
            ref for ref, req in resolved.items() if req["kind"] == "exact_land_pattern"
        ),
        "mechanical_blockers": sorted(
            ref for ref, req in resolved.items() if req["kind"] == "mechanical_selection"
        ),
        "ad3542r_footprint_evidence_status": ad3542_evidence["status"],
        "ad3542r_exposed_pad_status": ad3542_evidence["exposed_pad_review"]["status"],
        "layout_allowed": False,
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, sort_keys=True))
