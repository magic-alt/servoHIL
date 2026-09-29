#!/usr/bin/env python3
"""Fail-closed Rev.B pre-layout qualification contract audit."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MECHANICAL = {"J101", "SW101", "J5", "J501", "J701"}
EXPECTED_MAGNETICS = {"XAL5050-103MEC", "XAL5050-682MEC", "XAL5030-472MEC"}
EXPECTED_MLCC = {"C3225X7R1C226M250AC", "C3225X7R1E106K250AC", "CGA6L2X7R1H105K160AA", "C5750X7R1V476M230KC"}


def _load(path: Path, name: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name}: unreadable JSON") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{name}: expected object")
    return data


def _repo_file(root: Path, raw: Any, name: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{name}: missing repository path")
    rel = Path(raw)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"{name}: path escapes repository")
    root = root.resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"{name}: file missing")
    return path


def _validate_template(data: dict[str, Any], name: str) -> None:
    if data.get("status") != "TEMPLATE_ONLY_NOT_EVIDENCE":
        raise ValueError(f"{name}: template must remain TEMPLATE_ONLY_NOT_EVIDENCE")
    if data.get("result") not in (None, "NOT_RUN"):
        raise ValueError(f"{name}: template cannot contain a test result")
    if data.get("raw_report") not in (None, ""):
        raise ValueError(f"{name}: template cannot point at raw evidence")
    if str(data.get("record_type", "")).endswith("TEMPLATE_ONLY") is False:
        raise ValueError(f"{name}: record_type must remain template-only")


def _validate_mechanical(root: Path, contract: dict[str, Any], manifest: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    mechanical = contract.get("mechanical_bindings")
    if not isinstance(mechanical, dict):
        raise ValueError("prelayout mechanical_bindings missing")
    if mechanical.get("required_open_refs") != []:
        raise ValueError("layout entry must have zero required-open mechanical refs")
    refs = mechanical.get("resolved_refs")
    if not isinstance(refs, list) or set(refs) != EXPECTED_MECHANICAL or len(refs) != 5:
        raise ValueError("prelayout resolved mechanical reference set drift")
    if manifest.get("schema_version") != 4 or manifest.get("layout_allowed") is not True:
        raise ValueError("schematic manifest must be layout-entry ready")
    if manifest.get("open_footprints") != {} or manifest.get("binding_requirements") != {}:
        raise ValueError("schematic manifest must contain zero open mechanical bindings")
    if plan.get("schema_version") != 3 or plan.get("layout_allowed") is not True:
        raise ValueError("mechanical plan schema/layout policy drift")
    if plan.get("fabrication_allowed") is not False:
        raise ValueError("mechanical plan must not authorize fabrication")

    source_rel = mechanical.get("layout_sources")
    source_path = _repo_file(root, source_rel, "layout source bindings")
    sources = _load(source_path, "layout source bindings")
    if sources.get("status") != "SOURCE_BOUND_LAYOUT_PARTS":
        raise ValueError("layout source bindings status drift")

    interfaces = plan.get("interfaces")
    if not isinstance(interfaces, dict) or set(interfaces) != EXPECTED_MECHANICAL:
        raise ValueError("mechanical plan must contain exactly five interfaces")
    for ref, item in interfaces.items():
        if not isinstance(item, dict):
            raise ValueError(ref + ": mechanical plan entry must be an object")
        if item.get("selection_status") != "RESOLVED_FOR_LAYOUT":
            raise ValueError(ref + ": selection must remain resolved for Layout")
        if not isinstance(item.get("selected_part"), dict) or not item["selected_part"].get("mpn"):
            raise ValueError(ref + ": selected_part must bind an exact MPN")
        if item.get("evidence_pack") != source_rel:
            raise ValueError(ref + ": layout source evidence binding drift")
        source_item = sources.get("interfaces", {}).get(ref)
        if not isinstance(source_item, dict) or source_item.get("footprint") is None:
            raise ValueError(ref + ": layout source footprint missing")

    expected_connections = _load(
        _repo_file(root, plan.get("native_sources", {}).get("expected_connections"), "native expected connections"),
        "native expected connections",
    )
    expected_pinouts = {
        "J101": {"1": "VIN_RAW", "2": "GND"},
        "SW101": {"1": "UVLO_IN", "2": "GND"},
        "J5": {
            "1": "DUT_AO0", "2": "DUT_AO1", "3": "DUT_AO2", "4": "DUT_AO3",
            "5": "DUT_AO4", "6": "DUT_AO5", "7": "DUT_AO6", "8": "DUT_AO7",
            "9": "GND", "10": "GND",
        },
    }
    for ref, pinout in expected_pinouts.items():
        actual = {pin: expected_connections.get(f"{ref}.{pin}") for pin in pinout}
        if actual != pinout:
            raise ValueError(ref + ": mechanical pinout no longer matches native expected connections")
        if plan["interfaces"][ref].get("pinout") != pinout:
            raise ValueError(ref + ": mechanical plan pinout drift")
        if plan["interfaces"][ref].get("pin_count") != len(pinout):
            raise ValueError(ref + ": mechanical plan pin count drift")

    from check_native_safety import PINS
    for ref, pinout in {
        "J501": {"1": "INTERLOCK_FEED", "2": "INTERLOCK_RAW"},
        "J701": {"1": "DUT_PERMIT_A", "2": "DUT_PERMIT_B"},
    }.items():
        actual = {pin: PINS.get(f"{ref}.{pin}") for pin in pinout}
        if actual != pinout or plan["interfaces"][ref].get("pinout") != pinout:
            raise ValueError(ref + ": mechanical plan no longer matches native safety pin oracle")
        if plan["interfaces"][ref].get("pin_count") != 2:
            raise ValueError(ref + ": mechanical plan pin count drift")

    if plan["interfaces"]["J101"].get("input_operating_range_v") != [9, 15]:
        raise ValueError("J101 input range must remain bound to native 9-15 V contract")
    if plan["interfaces"]["J101"].get("upstream_fuse_nominal_a") != 2:
        raise ValueError("J101 current-rating basis must retain the native 2 A fuse")
    if plan["interfaces"]["SW101"].get("switch_function") != "MOMENTARY_NORMALLY_OPEN_RESET_CONTACT":
        raise ValueError("SW101 must remain a normally-open reset/control contact")
    j5 = plan["interfaces"]["J5"]
    if j5.get("pin_count") != 10 or j5.get("signal_pin_count") != 8 or j5.get("ground_pins") != [9, 10]:
        raise ValueError("J5 must retain 8 AO signals plus two ground contacts")
    if j5.get("disconnect_state") != "HIGH_IMPEDANCE_NOT_GUARANTEED_ZERO":
        raise ValueError("J5 disconnect semantics must remain high-impedance, not safe zero")
    j501 = plan["interfaces"]["J501"]
    if "NON_SAFETY_RESIDUAL_RISK" not in str(j501.get("cable_short_behavior", "")):
        raise ValueError("J501 cable-short semantics must retain explicit non-safety residual risk")
    j701 = plan["interfaces"]["J701"]
    if "NON_SAFETY_RESIDUAL_RISK" not in str(j701.get("cable_short_behavior", "")):
        raise ValueError("J701 cable-short semantics must retain explicit non-safety residual risk")
    if j701.get("lab_interface_envelope") != {"max_voltage_v": 24, "max_current_a": 0.01}:
        raise ValueError("J701 lab envelope drift")
    if j701.get("optorelay_off_state_leakage_component_limit_a") != 0.000001:
        raise ValueError("J701 component leakage limit drift")
    return sorted(EXPECTED_MECHANICAL)

def _validate_cable_fault_architecture(root: Path, mechanical: dict[str, Any]) -> dict[str, Any]:
    path = mechanical.get("cable_fault_architecture")
    data = _load(_repo_file(root, path, "cable-fault architecture"), "cable-fault architecture")
    if data.get("schema_version") != 1 or data.get("layout_allowed") is not True:
        raise ValueError("cable-fault architecture schema/layout policy drift")
    if data.get("fabrication_allowed") is not False:
        raise ValueError("cable-fault architecture must not authorize fabrication")
    if data.get("status") != "NON_SAFETY_RESIDUAL_RISK_PATH_SELECTED_FOR_LAYOUT":
        raise ValueError("cable-fault architecture resolution status drift")
    interfaces = data.get("interfaces")
    if not isinstance(interfaces, dict) or set(interfaces) != {"J501", "J701"}:
        raise ValueError("cable-fault architecture must cover exactly J501/J701")
    expected_options = {
        "J501": {"EOL_SUPERVISED_INPUT", "DUAL_CHANNEL_MONITORED", "ACCEPT_NON_SAFETY_RESIDUAL_RISK"},
        "J701": {"DUT_SIDE_LINE_MONITORING", "DUAL_MONITORED_PERMIT", "ACCEPT_NON_SAFETY_RESIDUAL_RISK"},
    }
    for ref, options in expected_options.items():
        item = interfaces[ref]
        if item.get("selected_resolution") != "ACCEPT_NON_SAFETY_RESIDUAL_RISK":
            raise ValueError(ref + ": non-safety residual-risk layout resolution drift")
        if set(item.get("allowed_resolutions", {})) != options:
            raise ValueError(ref + ": cable-short resolution option drift")
        if "NOT_DETECTABLE" not in str(item.get("cable_short_detectability", "")):
            raise ValueError(ref + ": current two-wire cable-short limitation must remain explicit")
        if "short" not in str(item.get("short_failure_semantics", "")).lower():
            raise ValueError(ref + ": short-failure semantics missing")
    forbidden = set(interfaces["J701"].get("forbidden_claims", []))
    if "STO" not in forbidden or "redundant safety output" not in forbidden:
        raise ValueError("J701 forbidden safety claims drift")
    return {
        "status": data["status"],
        "J501": interfaces["J501"]["cable_short_detectability"],
        "J701": interfaces["J701"]["cable_short_detectability"],
        "selected_resolutions": {
            "J501": interfaces["J501"]["selected_resolution"],
            "J701": interfaces["J701"]["selected_resolution"],
        },
    }

def _https(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.startswith("https://"):
        raise ValueError(name + ": HTTPS manufacturer source required")
    return value


def _validate_sources(
    contract: dict[str, Any],
    registry: dict[str, Any],
    component_candidates: dict[str, Any],
    capacitor_candidates: dict[str, Any],
) -> dict[str, Any]:
    if registry.get("schema_version") != 1 or registry.get("layout_allowed") is not False:
        raise ValueError("component source registry must remain non-authorizing for Layout")
    if registry.get("fabrication_allowed") is not False:
        raise ValueError("component source registry must not authorize fabrication")
    if registry.get("status") == "PASS":
        raise ValueError("manufacturer source discovery cannot be a qualification PASS")

    magnetics = registry.get("magnetics")
    if not isinstance(magnetics, dict):
        raise ValueError("magnetics registry missing")
    if set(magnetics.get("exact_parts", {})) != EXPECTED_MAGNETICS:
        raise ValueError("exact magnetic source set drift")
    _https(magnetics.get("datasheet_url"), "magnetics datasheet")
    if "NOT_HASH" not in str(magnetics.get("source_status", "")):
        raise ValueError("magnetics source status must remain unqualified until bytes are hash-bound")
    assigned_magnetics = set(component_candidates.get("assignments", {}).values())
    if assigned_magnetics != EXPECTED_MAGNETICS:
        raise ValueError("magnetic candidate assignments no longer match source registry")
    for mpn, row in magnetics["exact_parts"].items():
        _https(row.get("web_page"), mpn)
        candidate = component_candidates.get("parts", {}).get(mpn)
        if not isinstance(candidate, dict):
            raise ValueError(mpn + ": missing candidate record")
        if candidate.get("datasheet_url") != magnetics.get("datasheet_url"):
            raise ValueError(mpn + ": candidate datasheet source drift")

    mlcc = registry.get("mlcc")
    if not isinstance(mlcc, dict):
        raise ValueError("MLCC registry missing")
    if set(mlcc.get("exact_parts", {})) != EXPECTED_MLCC:
        raise ValueError("exact MLCC source set drift")
    assigned_mlcc = {x for x in capacitor_candidates.get("bank_candidates", {}).values() if x}
    if assigned_mlcc != EXPECTED_MLCC:
        raise ValueError("assigned MLCC set no longer matches source registry")
    for mpn, row in mlcc["exact_parts"].items():
        _https(row.get("product_url"), mpn + " product")
        _https(row.get("characterization_sheet_url"), mpn + " characterization")
        candidate = capacitor_candidates.get("parts", {}).get(mpn)
        if not isinstance(candidate, dict):
            raise ValueError(mpn + ": missing MLCC candidate record")
        if candidate.get("characterization_sheet_url") != row.get("characterization_sheet_url"):
            raise ValueError(mpn + ": characterization source drift")
        if "NOT_HASH" not in str(candidate.get("curve_source_status", "")):
            raise ValueError(mpn + ": curve source must remain unqualified until hash-bound")
    unresolved = mlcc.get("unresolved", {})
    if unresolved != {}:
        raise ValueError("all currently declared MLCC banks must have an exact screening MPN")
    if capacitor_candidates.get("bank_candidates", {}).get("input_protected") != "C5750X7R1V476M230KC":
        raise ValueError("input_protected exact MPN drift")
    input_row = mlcc["exact_parts"].get("C5750X7R1V476M230KC", {})
    if input_row.get("assigned_banks") != ["input_protected"]:
        raise ValueError("input_protected source registry assignment drift")
    if input_row.get("land_pattern_status") != "RESOLVED_TDK_RECOMMENDED_RANGE_PROJECT_FOOTPRINT_BOUND":
        raise ValueError("input_protected exact land-pattern status drift")
    if input_row.get("local_footprint") != "Capacitor_SMD:TDK_C5750X7R1V476M230KC":
        raise ValueError("input_protected local footprint binding drift")
    requirement = input_row.get("screening_requirement", {})
    if requirement.get("bias_screen_v") != 15.05 or requirement.get("minimum_effective_capacitance_uf") != 22:
        raise ValueError("input_protected MLCC screening requirement drift")
    retention = requirement.get("minimum_dc_bias_retention_after_tolerance_temperature_aging")
    expected_retention = 22 / (47 * 0.8 * 0.85 * 0.97)
    if not isinstance(retention, (int, float)) or abs(retention - expected_retention) > 1e-12:
        raise ValueError("input_protected MLCC retention requirement drift")
    return {
        "registry_status": registry.get("status"),
        "magnetics_source_status": magnetics.get("source_status"),
        "mlcc_source_status": mlcc.get("source_status"),
        "magnetic_mpns": sorted(EXPECTED_MAGNETICS),
        "mlcc_mpns": sorted(EXPECTED_MLCC),
        "unresolved_mlcc_banks": [],
        "input_protected_exact_mpn": "C5750X7R1V476M230KC",
        "input_protected_curve_status": capacitor_candidates["parts"]["C5750X7R1V476M230KC"]["curve_source_status"],
    }



def _validate_verification_plan(data: dict[str, Any], name: str) -> None:
    schema = data.get("schema_version")
    if schema not in {1, 2}:
        raise ValueError(f"{name}: unsupported verification plan schema")
    if data.get("layout_allowed") is not False:
        raise ValueError(f"{name}: verification plan must not authorize Layout")
    if data.get("result") != "NOT_RUN":
        raise ValueError(f"{name}: checked-in plan result must remain NOT_RUN until raw evidence exists")
    status = str(data.get("status", ""))
    if not status or status == "PASS":
        raise ValueError(f"{name}: verification plan must remain explicitly blocked/not-run")
    if schema == 2:
        subresults = data.get("subresults")
        if not isinstance(subresults, dict) or subresults != {"io_drc": "NOT_RUN", "timing": "NOT_RUN"}:
            raise ValueError(f"{name}: schema-2 Vivado subresults must remain NOT_RUN")



def _validate_vivado_contract(root: Path, work: dict[str, Any]) -> dict[str, Any]:
    raw = work.get("input_contract")
    contract = _load(_repo_file(root, raw, "Vivado input contract"), "Vivado input contract")
    if contract.get("schema_version") != 2 or contract.get("layout_allowed") is not False:
        raise ValueError("Vivado input contract schema/layout policy drift")
    if contract.get("status") != "IO_DRC_HARNESS_BOUND_TIMING_UNBOUND":
        raise ValueError("Vivado input contract status drift")
    carrier = _load(_repo_file(root, contract.get("carrier_profile"), "carrier profile"), "carrier profile")
    if carrier.get("id") != "axu2cgb" or carrier.get("board_variant") != "AXU2CGB-original":
        raise ValueError("Vivado carrier identity drift")
    if carrier.get("device") != contract.get("target_part", {}).get("vivado_part"):
        raise ValueError("Vivado target part no longer matches carrier profile")
    if contract.get("target_part", {}).get("marketing_part") != "XCZU2CG-1SFVC784E":
        raise ValueError("Vivado marketing part identity drift")
    preview = _repo_file(root, contract.get("io_constraint_preview", {}).get("path"), "XDC preview")
    if preview.suffix != ".preview" or contract.get("io_constraint_preview", {}).get("status") != "REVIEW_PREVIEW_ONLY_NOT_ACTIVE_XDC":
        raise ValueError("carrier constraint preview must not masquerade as functional XDC")
    if contract.get("io_constraint_preview", {}).get("can_close_gate") is not False:
        raise ValueError("constraint preview cannot close a Vivado gate")

    harness = contract.get("io_drc_harness")
    if not isinstance(harness, dict) or harness.get("status") != "BOUND_NOT_RUN":
        raise ValueError("Vivado I/O DRC harness must remain bound/not-run until raw evidence exists")
    if harness.get("top_module") != "servohil_io_drc_top":
        raise ValueError("Vivado I/O DRC harness top drift")
    if harness.get("xdc_files") != ["fpga/revb/io_drc/axu2cgb_io_drc.xdc"]:
        raise ValueError("Vivado I/O DRC harness XDC drift")
    if harness.get("rtl_sources") != ["fpga/revb/io_drc/servohil_io_drc_top.sv"]:
        raise ValueError("Vivado I/O DRC harness RTL drift")
    for path in harness["xdc_files"] + harness["rtl_sources"] + [harness.get("runner")]:
        _repo_file(root, path, "Vivado I/O DRC harness input")
    if harness.get("can_close_timing") is not False:
        raise ValueError("Vivado I/O DRC harness cannot close timing")

    timing = contract.get("functional_timing")
    if not isinstance(timing, dict):
        raise ValueError("Vivado functional timing contract missing")
    if timing.get("top_module") is not None or timing.get("active_xdc_files") != []:
        raise ValueError("functional timing top/XDC must remain unbound")
    if timing.get("clock_definitions") != [] or timing.get("timing_constraints") != []:
        raise ValueError("functional timing clocks/constraints cannot be predeclared")

    from check_revb_vivado_io_drc import check as check_io_drc_harness
    harness_report = check_io_drc_harness(root)
    return {
        "target_part": contract["target_part"]["vivado_part"],
        "marketing_part": contract["target_part"]["marketing_part"],
        "constraint_preview": contract["io_constraint_preview"]["path"],
        "status": contract["status"],
        "io_drc_harness": harness_report,
        "functional_timing_status": timing.get("status"),
    }


def _active_vivado_inputs(root: Path, harness_xdc: set[str]) -> dict[str, list[str]]:
    root = root.resolve()
    harness: list[str] = []
    functional_xdc: list[str] = []
    project: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in {"archive", "build", ".git"}:
            continue
        rel_text = rel.as_posix()
        suffix = path.suffix.lower()
        if suffix == ".xdc":
            (harness if rel_text in harness_xdc else functional_xdc).append(rel_text)
        elif suffix == ".xpr":
            project.append(rel_text)
    return {
        "harness_xdc": sorted(harness),
        "functional_xdc": sorted(functional_xdc),
        "project": sorted(project),
    }


def check(root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    contract = _load(root / "hardware/revB/prelayout_qualification_contract.json", "prelayout contract")
    if contract.get("schema_version") != 2:
        raise ValueError("unsupported prelayout contract schema")
    if (
        contract.get("layout_allowed") is not True
        or contract.get("fabrication_allowed") is not False
        or contract.get("status") != "LAYOUT_ENTRY_COMPLETE_FABRICATION_QUALIFICATION_OPEN"
    ):
        raise ValueError("prelayout contract layout/fabrication state drift")

    layout_entry = _load(root / "hardware/revB/layout_entry_contract.json", "layout entry contract")
    if (
        layout_entry.get("status") != "READY_FOR_PCB_LAYOUT"
        or layout_entry.get("layout_allowed") is not True
        or layout_entry.get("fabrication_allowed") is not False
    ):
        raise ValueError("layout-entry contract must remain ready-for-layout and fabrication-blocked")

    requirements = _load(root / "hardware/revB/qualification_requirements.json", "qualification requirements")
    if requirements.get("schema_version") != 4:
        raise ValueError("qualification requirements must use schema 4")
    policy = requirements.get("release_policy", {})
    if policy.get("layout_allowed") is not True or policy.get("fabrication_allowed") is not False:
        raise ValueError("qualification release policy layout/fabrication drift")
    if requirements.get("layout_entry_contract", {}).get("path") != "hardware/revB/layout_entry_contract.json":
        raise ValueError("qualification layout-entry path drift")

    prelayout_ref = requirements.get("prelayout_contract", {}).get("path")
    if prelayout_ref != "hardware/revB/prelayout_qualification_contract.json":
        raise ValueError("qualification requirements prelayout path drift")
    mech_req = requirements.get("mechanical_bindings")
    if not isinstance(mech_req, dict) or set(mech_req.get("required_refs", [])) != EXPECTED_MECHANICAL:
        raise ValueError("qualification mechanical requirement set drift")
    if mech_req.get("layout_resolved") is not True:
        raise ValueError("qualification mechanical bindings must be resolved for Layout")
    if (
        mech_req.get("manifest") != contract["mechanical_bindings"]["manifest"]
        or mech_req.get("plan") != contract["mechanical_bindings"]["plan"]
    ):
        raise ValueError("qualification mechanical paths drift")
    registry_path = requirements.get("component_source_registry", {}).get("path")
    if registry_path != contract["component_evidence"]["source_registry"]:
        raise ValueError("qualification component source registry path drift")

    manifest = _load(_repo_file(root, mech_req["manifest"], "mechanical manifest"), "mechanical manifest")
    plan = _load(_repo_file(root, mech_req["plan"], "mechanical plan"), "mechanical plan")
    mechanical_resolved = _validate_mechanical(root, contract, manifest, plan)
    cable_fault_state = _validate_cable_fault_architecture(root, contract["mechanical_bindings"])

    registry = _load(_repo_file(root, registry_path, "component source registry"), "component source registry")
    component_candidates = _load(root / "sim/power/component_candidates.json", "component candidates")
    capacitor_candidates = _load(root / "sim/power/capacitor_candidates.json", "capacitor candidates")
    source_state = _validate_sources(contract, registry, component_candidates, capacitor_candidates)

    template_paths = sorted({
        row.get("evidence_template")
        for row in contract.get("workstreams", {}).values()
        if isinstance(row, dict) and row.get("evidence_template")
    })
    if len(template_paths) < 4:
        raise ValueError("prelayout workstreams must bind all evidence template classes")
    for rel in template_paths:
        data = _load(_repo_file(root, rel, "evidence template"), "evidence template")
        _validate_template(data, rel)

    plan_paths = sorted({
        row.get("verification_plan")
        for row in contract.get("workstreams", {}).values()
        if isinstance(row, dict) and row.get("verification_plan")
    })
    if len(plan_paths) != 5:
        raise ValueError("prelayout contract must bind exactly five physical/tool verification plans")
    for rel in plan_paths:
        data = _load(_repo_file(root, rel, "verification plan"), "verification plan")
        _validate_verification_plan(data, rel)

    dut = _load(root / "hardware/revB/dut_adapter_profile.json", "DUT adapter profile")
    if dut.get("status") != "UNBOUND" or dut.get("adapter_id") is not None:
        raise ValueError("DUT adapter must remain UNBOUND until real measurements are imported")
    if any(value is not None for value in dut.get("evidence", {}).values()):
        raise ValueError("DUT evidence paths cannot be predeclared")

    gates = _load(root / "hardware/revB/gates.json", "Rev.B gates")
    if gates.get("layout_allowed") is not True or gates.get("fabrication_allowed") is not False:
        raise ValueError("Rev.B gates layout/fabrication policy drift")
    if gates.get("layout_entry", {}).get("status") != "READY_FOR_PCB_LAYOUT":
        raise ValueError("Rev.B layout-entry gate status drift")

    work = contract.get("workstreams", {}).get("VIVADO_IO_DRC_TIMING", {})
    vivado_contract = _validate_vivado_contract(root, work)
    harness_paths = {vivado_contract["io_drc_harness"]["harness_xdc"]}
    vivado = _active_vivado_inputs(root, harness_paths)
    if vivado["harness_xdc"] != ["fpga/revb/io_drc/axu2cgb_io_drc.xdc"]:
        raise ValueError("expected exactly the reviewed I/O DRC harness XDC")
    if not vivado["functional_xdc"] and not vivado["project"]:
        expected_work_status = "IO_DRC_HARNESS_BOUND_NOT_RUN_TIMING_BLOCKED_FOR_FABRICATION"
        if work.get("status") != expected_work_status:
            raise ValueError("Vivado workstream must reflect layout-ready/fabrication-blocked state")
        vivado_status = expected_work_status
    else:
        vivado_status = "FUNCTIONAL_INPUTS_PRESENT_REQUIRE_EXACT_BINDING_REVIEW"

    return {
        "schema_version": 2,
        "status": "PASS_LAYOUT_ENTRY_CONTRACT_FABRICATION_BLOCKED",
        "layout_allowed": True,
        "fabrication_allowed": False,
        "mechanical_open_refs": [],
        "mechanical_open_count": 0,
        "mechanical_resolved_refs": mechanical_resolved,
        "mechanical_fault_semantic_blockers": {},
        "mechanical_residual_risks": {
            "J501": plan["interfaces"]["J501"]["cable_short_behavior"],
            "J701": plan["interfaces"]["J701"]["cable_short_behavior"],
        },
        "cable_fault_architecture": cable_fault_state,
        "component_source_state": source_state,
        "template_count": len(template_paths),
        "verification_plan_count": len(plan_paths),
        "verification_plans": plan_paths,
        "dut_adapter_status": dut.get("status"),
        "vivado_status": vivado_status,
        "vivado_input_contract": vivado_contract,
        "active_vivado_inputs": vivado,
        "workstreams": {k: v.get("status") for k, v in sorted(contract.get("workstreams", {}).items())},
        "note": "Source-level PCB Layout entry is closed. Physical/tool/manufacturer evidence remains fail-closed for fabrication/release."
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, sort_keys=True))
