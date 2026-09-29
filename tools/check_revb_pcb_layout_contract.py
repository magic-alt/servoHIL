#!/usr/bin/env python3
"""Validate Rev.B PCB Layout phase contracts without promoting fabrication gates."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SEQUENCE = [
    "mechanical_reference_and_board_outline",
    "stackup_and_design_rules",
    "power_and_precision_analog_placement",
    "grounding_and_return_path",
    "routing",
    "pcb_drc",
]

EXPECTED_LAYER_ROLES = [
    ("F.Cu", "components_and_signal"),
    ("In1.Cu", "continuous_ground_reference"),
    ("In2.Cu", "power_distribution_and_slow_signal"),
    ("In3.Cu", "signal"),
    ("In4.Cu", "continuous_ground_reference"),
    ("B.Cu", "components_and_signal"),
]


def _load(path: Path, name: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name}: unreadable JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name}: expected object")
    return value


def _repo_path(root: Path, raw: Any, name: str, *, require_file: bool = True) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{name}: missing repository path")
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"{name}: path escapes repository")
    path = (root / rel).resolve()
    base = root.resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"{name}: path escapes repository")
    if require_file and not path.is_file():
        raise ValueError(f"{name}: file missing")
    return path


def _validate_layout_contract(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != 1:
        raise ValueError("PCB layout contract schema drift")
    if data.get("status") != "PHASE1_LAYOUT_ACTIVE_EXACT_CARRIER_MECHANICS_OPEN":
        raise ValueError("PCB layout phase status drift")
    if data.get("layout_allowed") is not True:
        raise ValueError("PCB layout contract must authorize Layout")
    if data.get("fabrication_allowed") is not False or data.get("release_allowed") is not False:
        raise ValueError("PCB layout contract must not authorize fabrication/release")
    if data.get("layout_sequence") != EXPECTED_SEQUENCE:
        raise ValueError("PCB layout execution sequence drift")

    _repo_path(root, data.get("source_schematic"), "source schematic")
    pcb = data.get("pcb_source")
    if not isinstance(pcb, dict):
        raise ValueError("pcb_source contract missing")
    pcb_path = _repo_path(root, pcb.get("path"), "PCB source", require_file=False)
    if pcb.get("status") == "NOT_CREATED_UNTIL_EXACT_CARRIER_MECHANICAL_REFERENCE_IS_BOUND" and pcb_path.exists():
        raise ValueError("PCB source exists while contract still says NOT_CREATED")

    mech = data.get("carrier_mechanical_reference")
    if not isinstance(mech, dict) or mech.get("carrier_id") != "axu2cgb":
        raise ValueError("carrier mechanical reference drift")
    facts = mech.get("documented_facts")
    if not isinstance(facts, dict) or not {"J12", "J15"}.issubset(facts):
        raise ValueError("carrier J12/J15 mechanical facts missing")
    if facts.get("host_form_factor_mm") != [100, 85]:
        raise ValueError("AXU2CGB documented host form factor drift")
    source_manifest = _load(
        _repo_path(root, mech.get("mechanical_source_manifest"), "carrier mechanical source"),
        "carrier mechanical source",
    )
    if source_manifest.get("source_commit") != "43effb3dacf1f9c7e76ac801d21f14a66f14d24e":
        raise ValueError("carrier mechanical source commit drift")
    if source_manifest.get("cad_sources", {}).get("dxf", {}).get("github_blob_sha") != "3d3e2af818db5514c503d16d592db3629b0ff00f":
        raise ValueError("carrier mechanical DXF blob drift")
    for ref, voltage in (("J12", 1.8), ("J15", 3.3)):
        row = facts[ref]
        if row.get("pins") != 40 or row.get("rows") != 2 or row.get("columns") != 20:
            raise ValueError(f"{ref}: expected 2x20 / 40-pin expansion port")
        if row.get("pitch_mm") != 2.54 or row.get("io_voltage_v") != voltage:
            raise ValueError(f"{ref}: pitch/voltage contract drift")
        _repo_path(root, row.get("logical_boundary"), f"{ref} logical boundary")

    required = mech.get("exact_mechanical_inputs_required_before_edge_cuts_freeze")
    if not isinstance(required, dict):
        raise ValueError("exact carrier mechanical input set missing")
    expected_keys = {
        "J12_center_xy_mm",
        "J15_center_xy_mm",
        "J12_pin1_orientation",
        "J15_pin1_orientation",
        "host_connector_manufacturer_and_mpn",
        "mating_connector_manufacturer_and_mpn",
        "mated_stack_height_mm",
        "carrier_mounting_hole_xy_and_drill_mm",
        "carrier_component_height_keepouts",
    }
    if set(required) != expected_keys:
        raise ValueError("exact carrier mechanical input key set drift")

    expected_pin1 = {
        "J12": {
            "pin1_center_xy_mm": [6.5278, 18.3769],
            "grid_position": "right_column_low_y",
        },
        "J15": {
            "pin1_center_xy_mm": [93.472, 66.6369],
            "grid_position": "left_column_high_y",
        },
    }
    source_grids = source_manifest.get("extracted_geometry", {}).get("expansion_header_pin_grids", {})
    for ref in ("J12", "J15"):
        orientation = required.get(f"{ref}_pin1_orientation")
        if not isinstance(orientation, dict):
            raise ValueError(f"{ref}: pin-1 orientation must be bound from official DXF")
        for key, value in expected_pin1[ref].items():
            if orientation.get(key) != value:
                raise ValueError(f"{ref}: pin-1 orientation drift")
        source_row = source_grids.get(ref, {})
        if source_row.get("pin1_orientation_status") != "BOUND_FROM_DXF_SQUARE_PAD":
            raise ValueError(f"{ref}: mechanical source pin-1 evidence is not bound")
        if source_row.get("pin1_center_xy_mm") != expected_pin1[ref]["pin1_center_xy_mm"]:
            raise ValueError(f"{ref}: mechanical source pin-1 coordinate drift")
        if source_row.get("pin1_grid_position") != expected_pin1[ref]["grid_position"]:
            raise ValueError(f"{ref}: mechanical source pin-1 grid position drift")

    open_fields = sorted(key for key, value in required.items() if value is None)
    return {
        "pcb_path": str(pcb_path.relative_to(root.resolve())),
        "pcb_exists": pcb_path.is_file(),
        "mechanical_open_fields": open_fields,
    }


def _validate_rules(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != 1:
        raise ValueError("PCB design-rule schema drift")
    if data.get("layout_allowed") is not True:
        raise ValueError("PCB design rules must remain active for Layout")
    if data.get("fabrication_allowed") is not False or data.get("release_allowed") is not False:
        raise ValueError("PCB design rules must not authorize fabrication/release")

    stack = data.get("stackup")
    if not isinstance(stack, dict) or stack.get("layer_count") != 6:
        raise ValueError("Rev.B target must remain six-layer")
    if stack.get("manufacturer_stackup_bound") is not False:
        raise ValueError("fabricator stackup cannot be pre-qualified")
    actual = [(row.get("name"), row.get("role")) for row in stack.get("layers", [])]
    if actual != EXPECTED_LAYER_ROLES:
        raise ValueError("six-layer role assignment drift")

    baseline = data.get("baseline_geometry_mm")
    if baseline != {
        "minimum_clearance": 0.20,
        "default_signal_width": 0.20,
        "default_via_diameter": 0.60,
        "default_via_drill": 0.30,
        "copper_to_board_edge": 0.30,
        "silkscreen_to_pad": 0.15,
    }:
        raise ValueError("baseline prototype geometry drift")

    classes = data.get("net_classes")
    if not isinstance(classes, dict):
        raise ValueError("net-class contract missing")
    required_classes = {"DEFAULT", "POWER_INPUT", "POWER_MEDIUM", "PRECISION_ANALOG", "FAST_SINGLE_ENDED", "EXTERNAL_DIFFERENTIAL"}
    if set(classes) != required_classes:
        raise ValueError("net-class set drift")
    ext = classes["EXTERNAL_DIFFERENTIAL"]
    if ext.get("impedance_target_ohm") != 120 or ext.get("geometry_status") != "TARGET_ONLY_PENDING_FABRICATOR_STACKUP":
        raise ValueError("external differential impedance target drift")
    if classes["FAST_SINGLE_ENDED"].get("hard_length_match_required") is not False:
        raise ValueError("numeric timing constraints must not be invented in PCB contract")

    grounding = data.get("grounding_and_return_path")
    if not isinstance(grounding, dict):
        raise ValueError("grounding contract missing")
    if grounding.get("primary_policy") != "continuous_ground_planes_with_functional_zoning":
        raise ValueError("grounding policy drift")
    if grounding.get("split_ground_planes") is not False:
        raise ValueError("hard split GND planes are not the Rev.B Layout policy")

    domains = {row.get("domain") for row in data.get("critical_placement", []) if isinstance(row, dict)}
    required_domains = {
        "input_power", "positive_switchers", "negative_switcher", "low_noise_rails",
        "dac", "adc", "encoder_phy", "permit_and_interlock",
    }
    if domains != required_domains:
        raise ValueError("critical placement domain set drift")

    drc = data.get("drc_acceptance")
    if not isinstance(drc, dict):
        raise ValueError("PCB DRC acceptance contract missing")
    for key in (
        "unconnected_items_allowed",
        "clearance_violations_allowed",
        "track_width_violations_allowed",
        "via_violations_allowed",
        "edge_clearance_violations_allowed",
    ):
        if drc.get(key) != 0:
            raise ValueError(f"{key}: Layout close must remain zero")
    if drc.get("fabrication_output_allowed") is not False:
        raise ValueError("PCB DRC cannot authorize fabrication")
    if drc.get("impedance_geometry_can_close_before_fab_stack") is not False:
        raise ValueError("impedance geometry must remain open until fabricator stackup")
    return {"layer_count": 6, "net_classes": sorted(classes)}


def check(root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    layout = _load(root / "hardware/revB/pcb_layout_contract.json", "PCB layout contract")
    rules = _load(root / "hardware/revB/pcb_design_rules.json", "PCB design rules")
    gates = _load(root / "hardware/revB/gates.json", "Rev.B gates")
    entry = _load(root / "hardware/revB/layout_entry_contract.json", "Layout-entry contract")

    if gates.get("layout_allowed") is not True or entry.get("layout_allowed") is not True:
        raise ValueError("source Layout entry is no longer authorized")
    if gates.get("fabrication_allowed") is not False or entry.get("fabrication_allowed") is not False:
        raise ValueError("fabrication gate was accidentally promoted")
    if gates.get("release_allowed") is not False or entry.get("release_allowed") is not False:
        raise ValueError("release gate was accidentally promoted")

    phase = _validate_layout_contract(root, layout)
    rule_state = _validate_rules(rules)
    return {
        "schema_version": 1,
        "status": "PASS_PCB_LAYOUT_PHASE1_CONTRACT",
        "layout_allowed": True,
        "fabrication_allowed": False,
        "release_allowed": False,
        "pcb_exists": phase["pcb_exists"],
        "pcb_path": phase["pcb_path"],
        "mechanical_open_fields": phase["mechanical_open_fields"],
        "layer_count": rule_state["layer_count"],
        "net_classes": rule_state["net_classes"],
        "note": "Layout work is active. Official DXF binds outline, mounting holes, J12/J15 grids and pin-1 orientation; exact connector MPNs, mated stack height and component-height keepouts remain open. Fabrication/release remain blocked.",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, sort_keys=True))
