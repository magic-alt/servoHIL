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
AD3542_GEOMETRY = ROOT / "hardware/revB/evidence/ad3542r/u1_geometry_review.json"
AD3542_FOOTPRINT = (
    NATIVE
    / "footprints/Package_DFN_QFN.pretty/AnalogDevices_CP-28-15_AD3542R.kicad_mod"
)

REF_RE = re.compile(r'\(property "Reference" "([^"]+)"')
FP_RE = re.compile(r'\(property "Footprint" "([^"]*)"')
DS_RE = re.compile(r'\(property "Datasheet" "([^"]*)"')
VAL_RE = re.compile(r'\(property "Value" "([^"]*)"')

AD3542_REFS = ("U20", "U21", "U22", "U23")
MECHANICAL_REFS = ("J101", "SW101", "J5", "J501", "J701")
AD3542_FOOTPRINT_ID = "Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R"
AD3542_DATASHEET = "https://www.analog.com/media/en/technical-documentation/data-sheets/ad3542r.pdf"
AD3542_GEOMETRY_REL = "hardware/revB/evidence/ad3542r/u1_geometry_review.json"
AD3542_EVIDENCE_REL = "hardware/revB/ad3542r_footprint_evidence.json"
AD3542_FOOTPRINT_REL = "hardware/kicad/revB/axu2cgb_expansion/footprints/Package_DFN_QFN.pretty/AnalogDevices_CP-28-15_AD3542R.kicad_mod"

SOURCE_HASHES = {
    "datasheet_rev_c_sha256": "a9536b981e1dc140082ddff947487faaaa47874cd8b648966ee9c6b92fa292fa",
    "package_drawing_sha256": "f6aab2aa746e79a01b4d9067bde56c886001a4cb1b7ed83e198d480ab0845b73",
    "evaluation_user_guide_sha256": "ed5afa177bce6c907a3981c71f49cc3964078a6b6ff79ecfd24ae78f6a1093b4",
    "evaluation_gerber_zip_sha256": "87eee7f3ed85e81798918b1977bc0b416d72699a39c771d95e9ea3839ef461e8",
    "evaluation_bom_sha256": "4608d8884754e5768424832af2331fa0490ab90e05a990a1292bf8f7bab0f7df",
}

GERBER_MEMBER_HASHES = {
    "ipc356": "a49a303ec88df607d4ee274ed38fca04365ef6f17ed142f30a5c63ee93fe82ac",
    "top_copper": "0532c246d68346eb38b9458bccc966bb6b14d4fc77575acdb8c55f3a2226a2f5",
    "top_solder_mask": "811a289f8c01471350f20f0fb68e0e4606b5ad2d1d46f3a22249c02867390825",
    "top_paste": "35bc764741a78a7482bd1733ddddb85357533c4ff886179bcb9cccd629d5fc83",
    "fab_drawing": "f064e7f6145e03adcc9a4da9d0993e81214085485563855cdf4ecef82f729fa3",
}

PAD_RE = re.compile(
    r'\(pad\s+(?:"([^"]*)"|([^\s]+))\s+smd\s+oval\s+'
    r'\(at\s+([-+0-9.]+)\s+([-+0-9.]+)\)\s+'
    r'\(size\s+([-+0-9.]+)\s+([-+0-9.]+)\)\s+'
    r'\(layers\s+([^)]+)\)\)'
)


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


def _close(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol


def _expected_pad(pin):
    if 1 <= pin <= 7:
        return (-1.8933, -1.2 + (pin - 1) * 0.4, 0.7366, 0.2286, 0.8382, 0.2794)
    if 8 <= pin <= 14:
        return (-1.2 + (pin - 8) * 0.4, 1.8933, 0.2286, 0.7366, 0.2794, 0.8382)
    if 15 <= pin <= 21:
        return (1.8933, 1.2 - (pin - 15) * 0.4, 0.7366, 0.2286, 0.8382, 0.2794)
    if 22 <= pin <= 28:
        return (1.2 - (pin - 22) * 0.4, -1.8933, 0.2286, 0.7366, 0.2794, 0.8382)
    raise ValueError("unexpected AD3542R pin")


def _check_geometry_evidence():
    data = json.loads(AD3542_GEOMETRY.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported AD3542R geometry evidence schema")
    if data.get("conclusion") != "PASS_EXACT_OFFICIAL_EVAL_LAND_PATTERN":
        raise ValueError("AD3542R geometry evidence must be explicitly reviewed")

    sources = data.get("source_artifacts", {})
    source_map = {
        "datasheet_rev_c_sha256": ("datasheet_rev_c", "sha256"),
        "package_drawing_sha256": ("package_drawing", "sha256"),
        "evaluation_user_guide_sha256": ("evaluation_user_guide", "sha256"),
        "evaluation_gerber_zip_sha256": ("evaluation_gerber_zip", "sha256"),
        "evaluation_bom_sha256": ("evaluation_bom", "sha256"),
    }
    for key, expected in SOURCE_HASHES.items():
        section, field = source_map[key]
        if sources.get(section, {}).get(field) != expected:
            raise ValueError("AD3542R source artifact hash drift: " + key)

    members = data.get("gerber_members", {})
    for key, expected in GERBER_MEMBER_HASHES.items():
        if members.get(key, {}).get("sha256") != expected:
            raise ValueError("AD3542R Gerber member hash drift: " + key)

    bom = data.get("bom_u1", {})
    if (
        bom.get("location") != "U1"
        or bom.get("manufacturer") != "ANALOG DEVICES"
        or bom.get("manufacturer_part_number") != "AD3542RBCPZ16"
        or bom.get("jedec_type") != "QFN28_4X4"
    ):
        raise ValueError("AD3542R official BOM U1 identity drift")

    pkg = data.get("package_cross_check", {})
    expected_pkg = {
        "manufacturer": "Analog Devices",
        "mpn": "AD3542RBCPZ16",
        "package_option": "CP-28-15",
        "pin_count": 28,
        "pitch_mm": 0.4,
        "center_exposed_pad": False,
    }
    for key, expected in expected_pkg.items():
        if pkg.get(key) != expected:
            raise ValueError("AD3542R package cross-check drift: " + key)

    ipc = data.get("eval_u1_ipc356_records", [])
    if len(ipc) != 28 or {x.get("pin") for x in ipc} != set(range(1, 29)):
        raise ValueError("AD3542R IPC-356 must contain exactly pins 1..28")

    apertures = data.get("gerber_apertures", {})
    expected_apertures = {
        "L1_TOP.art": ((0.7366, 0.2286), (0.2286, 0.7366)),
        "PMT.art": ((0.7366, 0.2286), (0.2286, 0.7366)),
        "SMT.art": ((0.8382, 0.2794), (0.2794, 0.8382)),
    }
    for layer, (side, top_bottom) in expected_apertures.items():
        got = apertures.get(layer, {})
        for group, expected in (("side", side), ("top_bottom", top_bottom)):
            entry = got.get(group, {})
            if entry.get("shape") != "obround":
                raise ValueError(f"AD3542R {layer} {group} aperture must remain obround")
            if not _close(entry.get("x_mm", -1), expected[0]) or not _close(
                entry.get("y_mm", -1), expected[1]
            ):
                raise ValueError(f"AD3542R {layer} {group} aperture geometry drift")

    flashes = data.get("gerber_u1_flashes", {})
    for layer in ("L1_TOP.art", "SMT.art", "PMT.art"):
        rows = flashes.get(layer, [])
        if len(rows) != 28 or {x.get("pin") for x in rows} != set(range(1, 29)):
            raise ValueError("AD3542R " + layer + " must retain exactly 28 U1 flashes")

    center = data.get("center_region_review", {})
    if center.get("center_exposed_pad_present") is not False:
        raise ValueError("AD3542R center/exposed pad must remain absent")
    if center.get("top_solder_mask_center_aperture") is not False:
        raise ValueError("AD3542R center solder-mask aperture must remain absent")
    if center.get("top_paste_center_aperture") is not False:
        raise ValueError("AD3542R center paste aperture must remain absent")

    canonical = data.get("canonical_kicad_land_pattern", {})
    if canonical.get("footprint") != AD3542_FOOTPRINT_ID:
        raise ValueError("AD3542R canonical footprint identity drift")
    if canonical.get("center_pad_present") is not False:
        raise ValueError("AD3542R canonical footprint must not add a center pad")
    pads = canonical.get("pads", [])
    if len(pads) != 28 or {x.get("pin") for x in pads} != set(range(1, 29)):
        raise ValueError("AD3542R canonical geometry must contain 28 pads")
    for row in pads:
        pin = row["pin"]
        ex, ey, _, _, _, _ = _expected_pad(pin)
        if not _close(row.get("x_mm"), ex) or not _close(row.get("y_mm"), ey):
            raise ValueError("AD3542R canonical pin coordinate drift: " + str(pin))

    policy = data.get("archive_policy", {})
    if policy.get("raw_binary_files_committed_to_repository") is not False:
        raise ValueError("AD3542R evidence policy unexpectedly claims binary redistribution")
    if "SHA-256" not in str(policy.get("audit_record", "")):
        raise ValueError("AD3542R evidence must retain hash-bound audit record")
    return data


def _check_footprint_geometry():
    text = AD3542_FOOTPRINT.read_text(encoding="utf-8")
    numbered = {}
    mask = []
    for m in PAD_RE.finditer(text):
        number = m.group(1) if m.group(1) is not None else m.group(2)
        row = {
            "x": float(m.group(3)),
            "y": float(m.group(4)),
            "sx": float(m.group(5)),
            "sy": float(m.group(6)),
            "layers": tuple(m.group(7).replace('"', "").split()),
        }
        if number == "":
            mask.append(row)
        else:
            try:
                pin = int(number)
            except ValueError as exc:
                raise ValueError("AD3542R footprint has nonnumeric electrical pad") from exc
            if pin in numbered:
                raise ValueError("AD3542R footprint has duplicate electrical pad " + str(pin))
            numbered[pin] = row

    if set(numbered) != set(range(1, 29)):
        raise ValueError("AD3542R footprint electrical pad set must be exactly 1..28")
    if len(mask) != 28:
        raise ValueError("AD3542R footprint must contain exactly 28 explicit mask apertures")

    for pin, row in numbered.items():
        ex, ey, esx, esy, _, _ = _expected_pad(pin)
        if row["layers"] != ("F.Cu", "F.Paste"):
            raise ValueError("AD3542R electrical pads must use exact copper/paste layers")
        for got, expected, field in (
            (row["x"], ex, "x"),
            (row["y"], ey, "y"),
            (row["sx"], esx, "size-x"),
            (row["sy"], esy, "size-y"),
        ):
            if not _close(got, expected):
                raise ValueError(f"AD3542R footprint pin {pin} {field} drift")

    expected_mask = []
    for pin in range(1, 29):
        ex, ey, _, _, msx, msy = _expected_pad(pin)
        expected_mask.append((ex, ey, msx, msy))
    unmatched = list(mask)
    for expected in expected_mask:
        hit = None
        for i, row in enumerate(unmatched):
            if row["layers"] != ("F.Mask",):
                continue
            if all(
                _close(got, want)
                for got, want in zip(
                    (row["x"], row["y"], row["sx"], row["sy"]), expected
                )
            ):
                hit = i
                break
        if hit is None:
            raise ValueError("AD3542R footprint missing exact official solder-mask aperture")
        unmatched.pop(hit)
    if unmatched:
        raise ValueError("AD3542R footprint contains unexpected solder-mask aperture")
    return {"electrical_pad_count": 28, "mask_aperture_count": 28}


def _check_ad3542_evidence():
    data = json.loads(AD3542_EVIDENCE.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2:
        raise ValueError("unsupported AD3542R footprint evidence schema")
    if data.get("status") != "REVIEWED_OFFICIAL_EVAL_GERBER_FOOTPRINT_VENDORED":
        raise ValueError("AD3542R footprint evidence is not in reviewed state")
    if data.get("release_effect") != "U20_U23_PACKAGE_BLOCKERS_CLOSED_LAYOUT_STILL_BLOCKED":
        raise ValueError("AD3542R evidence must not authorize Layout")

    part = data.get("part", {})
    expected_part = {
        "manufacturer": "Analog Devices",
        "mpn": "AD3542RBCPZ16",
        "package_option": "CP-28-15",
        "pin_count": 28,
        "lead_pitch_mm": 0.4,
    }
    for key, expected in expected_part.items():
        if part.get(key) != expected:
            raise ValueError("AD3542R evidence part identity drift: " + key)

    if data.get("geometry_evidence") != AD3542_GEOMETRY_REL:
        raise ValueError("AD3542R evidence must bind the source geometry transcript")
    source_hashes = data.get("source_artifact_hashes", {})
    for key, expected in SOURCE_HASHES.items():
        if source_hashes.get(key) != expected:
            raise ValueError("AD3542R evidence source hash drift: " + key)

    footprint = data.get("footprint", {})
    if footprint.get("library_id") != AD3542_FOOTPRINT_ID:
        raise ValueError("AD3542R evidence footprint id drift")
    if footprint.get("path") != AD3542_FOOTPRINT_REL:
        raise ValueError("AD3542R evidence footprint path drift")
    if footprint.get("center_exposed_pad") is not False:
        raise ValueError("AD3542R evidence must retain no-center-pad decision")

    exposed = data.get("exposed_pad_review", {})
    if exposed.get("status") != "RESOLVED_NO_CENTER_EXPOSED_PAD_CURRENT_SOURCES":
        raise ValueError("AD3542R exposed-pad decision is not resolved")
    if "Do not add" not in str(exposed.get("decision", "")):
        raise ValueError("AD3542R exposed-pad decision must be explicit")

    geometry = data.get("geometry_review", {})
    if geometry.get("status") != "PASS_OFFICIAL_EVAL_GERBER":
        raise ValueError("AD3542R geometry review is not PASS_OFFICIAL_EVAL_GERBER")
    if geometry.get("pad_count") != 28 or geometry.get("center_pad_present") is not False:
        raise ValueError("AD3542R reviewed geometry identity drift")
    if not _close(geometry.get("pitch_mm", -1), 0.4):
        raise ValueError("AD3542R reviewed pitch drift")

    transcript = _check_geometry_evidence()
    fp = _check_footprint_geometry()
    return data, transcript, fp


LAYOUT_REFS = ("J101", "SW101", "C105", "J5", "J501", "J701")
LAYOUT_FOOTPRINTS = {
    "J101": "Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_2-G-5,08_1x02_P5.08mm_Horizontal",
    "SW101": "Button_Switch_SMD:SW_Push_PTS645SM43SMTR92",
    "C105": "Capacitor_SMD:TDK_C5750X7R1V476M230KC",
    "J5": "Connector_Phoenix_MC:PhoenixContact_MC_1,5_10-G-3.5_1x10_P3.50mm_Horizontal",
    "J501": "Connector_Phoenix_MC:PhoenixContact_MC_1,5_2-G-3.5_1x02_P3.50mm_Horizontal",
    "J701": "Connector_Molex:Molex_Micro-Fit_3.0_43045-0212_2x01_P3.00mm_Vertical",
}


def _check_resolved_ad3542(manifest, by_ref):
    bindings = manifest.get("resolved_bindings")
    if not isinstance(bindings, dict) or not set(AD3542_REFS).issubset(bindings):
        raise ValueError("resolved_bindings must retain U20..U23")
    resolved = {ref: _resolve_requirement(bindings, ref) for ref in AD3542_REFS}

    for ref in AD3542_REFS:
        req = resolved[ref]
        expected = {
            "kind": "exact_land_pattern",
            "status": "RESOLVED_REVIEWED_OFFICIAL_EVAL_LAND_PATTERN",
            "manufacturer": "Analog Devices",
            "mpn": "AD3542RBCPZ16",
            "package_option": "CP-28-15",
            "footprint": AD3542_FOOTPRINT_ID,
            "evidence_manifest": AD3542_EVIDENCE_REL,
            "geometry_evidence": AD3542_GEOMETRY_REL,
        }
        for key, value in expected.items():
            if req.get(key) != value:
                raise ValueError(f"{ref} resolved binding drift: {key}")
        row = by_ref.get(ref)
        if not row:
            raise ValueError("missing resolved AD3542R instance " + ref)
        if row["value"] != "AD3542RBCPZ16":
            raise ValueError(ref + " must use exact AD3542RBCPZ16 value")
        if row["footprint"] != AD3542_FOOTPRINT_ID:
            raise ValueError(ref + " must bind the reviewed CP-28-15 footprint")
        if row["datasheet"] != AD3542_DATASHEET:
            raise ValueError(ref + " datasheet binding drift")
        if manifest.get("bound_packages", {}).get(ref) != AD3542_FOOTPRINT_ID:
            raise ValueError(ref + " bound_packages entry drift")
        if ref in manifest.get("open_footprints", {}):
            raise ValueError(ref + " cannot be both resolved and open")

    evidence, transcript, fp = _check_ad3542_evidence()
    return resolved, evidence, transcript, fp


def _check_layout_bindings(manifest, by_ref):
    bindings = manifest.get("resolved_bindings")
    if not isinstance(bindings, dict):
        raise ValueError("resolved_bindings must be an object")
    if set(manifest.get("layout_entry_resolved_refs", [])) != set(LAYOUT_REFS):
        raise ValueError("layout-entry resolved reference set drift")
    if manifest.get("open_footprints") != {} or manifest.get("binding_requirements") != {}:
        raise ValueError("layout entry requires zero open footprint/binding contracts")

    resolved = {}
    for ref in LAYOUT_REFS:
        req = bindings.get(ref)
        if not isinstance(req, dict):
            raise ValueError(ref + ": missing resolved layout binding")
        row = by_ref.get(ref)
        if not row:
            raise ValueError(ref + ": missing native schematic instance")
        expected_fp = LAYOUT_FOOTPRINTS[ref]
        if row["footprint"] != expected_fp:
            raise ValueError(f"{ref}: native footprint drift: {row['footprint']} != {expected_fp}")
        if manifest.get("bound_packages", {}).get(ref) != expected_fp:
            raise ValueError(ref + ": bound_packages drift")
        if req.get("footprint") != expected_fp:
            raise ValueError(ref + ": resolved binding footprint drift")
        if not str(req.get("status", "")).startswith("RESOLVED_"):
            raise ValueError(ref + ": resolved binding status drift")
        evidence = req.get("evidence_manifest")
        if not isinstance(evidence, str) or not (ROOT / evidence).is_file():
            raise ValueError(ref + ": source-bound layout evidence missing")
        resolved[ref] = req

    if resolved["C105"].get("mpn") != "C5750X7R1V476M230KC":
        raise ValueError("C105 exact MPN drift")
    if resolved["J101"].get("order_number") != "1757242":
        raise ValueError("J101 exact order-number drift")
    if resolved["J5"].get("order_number") != "1844294":
        raise ValueError("J5 exact order-number drift")
    if resolved["J501"].get("order_number") != "1844210":
        raise ValueError("J501 exact order-number drift")
    if resolved["J701"].get("order_number") != "430450212":
        raise ValueError("J701 exact order-number drift")
    return resolved


def check():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 4:
        raise ValueError("unsupported schematic-open-items schema")
    if manifest.get("layout_allowed") is not True:
        raise ValueError("schematic closure manifest must authorize source-bound PCB Layout entry")
    if manifest.get("status") != "SCHEMATIC_LAYOUT_ENTRY_READY_NO_OPEN_FOOTPRINTS":
        raise ValueError("schematic layout-entry status drift")

    rows = placed_symbols()
    by_ref = {r["reference"]: r for r in rows}
    if len(by_ref) != len(rows):
        dup = sorted(r for r in by_ref if sum(x["reference"] == r for x in rows) > 1)
        raise ValueError("duplicate physical references: " + str(dup))

    physical = [
        r for r in rows
        if r["in_bom"] and r["on_board"] and not r["reference"].startswith("#")
    ]
    missing = {r["reference"] for r in physical if not r["footprint"]}
    if missing:
        raise ValueError("layout entry requires zero blank physical footprints: " + str(sorted(missing)))

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

    layout_bindings = _check_layout_bindings(manifest, by_ref)
    ad_bindings, ad_evidence, transcript, fp = _check_resolved_ad3542(manifest, by_ref)

    return {
        "status": "PASS_LAYOUT_ENTRY_SOURCE_CLOSURE",
        "physical_components": len(physical),
        "blank_footprints": [],
        "blank_footprint_count": 0,
        "binding_requirement_count": 0,
        "land_pattern_blockers": [],
        "resolved_land_patterns": sorted(ad_bindings),
        "resolved_layout_refs": sorted(layout_bindings),
        "mechanical_blockers": [],
        "ad3542r_footprint_evidence_status": ad_evidence["status"],
        "ad3542r_geometry_conclusion": transcript["conclusion"],
        "ad3542r_electrical_pad_count": fp["electrical_pad_count"],
        "ad3542r_mask_aperture_count": fp["mask_aperture_count"],
        "layout_allowed": True,
        "fabrication_allowed": False,
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, sort_keys=True))
