#!/usr/bin/env python3
"""Static audit for the Rev.B AXU2CGB Vivado I/O-DRC harness.

This checker proves source-contract consistency only. It does not run Vivado and
cannot turn VIVADO_IO_DRC or VIVADO_TIMING into PASS.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PART = "xczu2cg-sfvc784-1-e"
TOP = "servohil_io_drc_top"
HARNESS_RTL = "fpga/revb/io_drc/servohil_io_drc_top.sv"
HARNESS_XDC = "fpga/revb/io_drc/axu2cgb_io_drc.xdc"
HARNESS_TCL = "fpga/revb/io_drc/run_io_drc.tcl"
PREVIEW_XDC = "hardware/kicad/revB/axu2cgb_expansion/carrier.xdc.preview"


def _json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def parse_xdc(text: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(
            r"set_property\s+(PACKAGE_PIN|IOSTANDARD)\s+(\S+)\s+\[get_ports\s+\{([A-Za-z_][A-Za-z0-9_]*)\}\]",
            line,
        )
        if match is None:
            raise ValueError(f"XDC line {number}: only PACKAGE_PIN/IOSTANDARD is allowed in IO-DRC harness")
        prop, value, port = match.groups()
        row = result.setdefault(port, {})
        if prop in row:
            raise ValueError(f"{port}: duplicate {prop}")
        row[prop] = value
    for port, row in result.items():
        if set(row) != {"PACKAGE_PIN", "IOSTANDARD"}:
            raise ValueError(f"{port}: incomplete XDC properties")
    return result


def parse_rtl_ports(text: str) -> dict[str, str]:
    ports: dict[str, str] = {}
    for direction, port in re.findall(
        r"^\s*(input|output|inout)\s+wire\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:,)?\s*$",
        text,
        flags=re.MULTILINE,
    ):
        if port in ports:
            raise ValueError(f"{port}: duplicate RTL top port")
        ports[port] = direction
    return ports


def expected_io(root: Path) -> dict[str, dict[str, str]]:
    io = _json(root / "hardware/revB/io_contract.json")
    if io.get("schema_version") != 1 or len(io.get("signals", [])) != 64:
        raise ValueError("Rev.B io_contract must contain exactly 64 signals")
    assignments = {row["net"]: row for row in _csv(root / "hardware/carriers/axu2cgb/assignments.csv")}
    physical = {
        (row["connector"], row["pin"]): row
        for row in _csv(root / "hardware/carriers/axu2cgb/physical_pinout.csv")
    }
    expected: dict[str, dict[str, str]] = {}
    for signal in io["signals"]:
        net = signal["net"]
        port = signal["port"]
        direction = signal["direction"]
        voltage = float(signal["voltage"])
        if net not in assignments:
            raise ValueError(f"{net}: missing carrier assignment")
        assignment = assignments[net]
        key = (assignment["connector"], assignment["pin"])
        if key not in physical:
            raise ValueError(f"{net}: missing physical pinout row")
        pin = physical[key]
        if not pin["soc_ball"]:
            raise ValueError(f"{net}: assigned contact has no SoC ball")
        pin_voltage = float(pin["voltage"])
        if not math.isclose(pin_voltage, voltage, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"{net}: io_contract voltage disagrees with carrier pinout")
        if math.isclose(voltage, 1.8, abs_tol=1e-9):
            standard = "LVCMOS18"
        elif math.isclose(voltage, 3.3, abs_tol=1e-9):
            standard = "LVCMOS33"
        else:
            raise ValueError(f"{net}: unsupported harness I/O voltage {voltage}")
        if direction not in {"input", "output", "inout"}:
            raise ValueError(f"{net}: unsupported direction {direction}")
        if port in expected:
            raise ValueError(f"{port}: duplicate io_contract port")
        expected[port] = {
            "direction": direction,
            "PACKAGE_PIN": pin["soc_ball"],
            "IOSTANDARD": standard,
            "net": net,
        }
    return expected


def check(root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    contract = _json(root / "hardware/revB/vivado_input_contract.json")
    if contract.get("schema_version") != 2:
        raise ValueError("Vivado input contract must use schema 2")
    if contract.get("layout_allowed") is not False:
        raise ValueError("Vivado input contract cannot authorize Layout")
    if contract.get("status") != "IO_DRC_HARNESS_BOUND_TIMING_UNBOUND":
        raise ValueError("Vivado input contract status drift")
    carrier = _json(root / contract["carrier_profile"])
    if carrier.get("device") != PART:
        raise ValueError("carrier profile target part drift")
    if contract.get("target_part", {}).get("vivado_part") != PART:
        raise ValueError("Vivado target part drift")

    harness = contract.get("io_drc_harness")
    if not isinstance(harness, dict):
        raise ValueError("missing io_drc_harness contract")
    if harness.get("status") != "BOUND_NOT_RUN":
        raise ValueError("I/O DRC harness must remain BOUND_NOT_RUN before raw Vivado evidence")
    if harness.get("top_module") != TOP:
        raise ValueError("I/O DRC harness top drift")
    if harness.get("rtl_sources") != [HARNESS_RTL] or harness.get("xdc_files") != [HARNESS_XDC]:
        raise ValueError("I/O DRC harness source/XDC drift")
    if harness.get("runner") != HARNESS_TCL:
        raise ValueError("I/O DRC runner drift")
    if harness.get("expected_port_count") != 64:
        raise ValueError("I/O DRC expected port count drift")
    if harness.get("can_close_timing") is not False:
        raise ValueError("I/O DRC harness must never close timing")

    expected = expected_io(root)
    rtl_ports = parse_rtl_ports((root / HARNESS_RTL).read_text(encoding="utf-8"))
    if set(rtl_ports) != set(expected):
        raise ValueError(
            f"RTL port coverage drift: missing={sorted(set(expected)-set(rtl_ports))} "
            f"unexpected={sorted(set(rtl_ports)-set(expected))}"
        )
    for port, row in expected.items():
        if rtl_ports[port] != row["direction"]:
            raise ValueError(f"{port}: RTL direction drift")

    harness_xdc = parse_xdc((root / HARNESS_XDC).read_text(encoding="utf-8"))
    preview_xdc = parse_xdc((root / PREVIEW_XDC).read_text(encoding="utf-8"))
    if harness_xdc != preview_xdc:
        raise ValueError("I/O DRC XDC is not semantically identical to carrier.xdc.preview")
    if set(harness_xdc) != set(expected):
        raise ValueError("I/O DRC XDC port coverage drift")
    for port, row in expected.items():
        actual = harness_xdc[port]
        if actual["PACKAGE_PIN"] != row["PACKAGE_PIN"]:
            raise ValueError(f"{port}: PACKAGE_PIN drift")
        if actual["IOSTANDARD"] != row["IOSTANDARD"]:
            raise ValueError(f"{port}: IOSTANDARD drift")

    tcl = (root / HARNESS_TCL).read_text(encoding="utf-8")
    required_fragments = [
        f'set part "{PART}"',
        f'set top "{TOP}"',
        "synth_design -top $top -part $part",
        "report_drc -file",
        "report_io -file",
        'puts $fh "source_digest=$source_digest"',
        'puts $fh "timing_claim=NOT_RUN"',
    ]
    for fragment in required_fragments:
        if fragment not in tcl:
            raise ValueError(f"runner lost required fragment: {fragment}")
    forbidden = ["report_timing_summary", "create_clock", "set_input_delay", "set_output_delay"]
    if any(item in tcl for item in forbidden):
        raise ValueError("I/O DRC runner must not acquire functional timing claims")

    timing = contract.get("functional_timing")
    if not isinstance(timing, dict):
        raise ValueError("missing functional_timing contract")
    if timing.get("top_module") is not None or timing.get("active_xdc_files") != []:
        raise ValueError("functional timing top/XDC must remain unbound")
    if timing.get("clock_definitions") != [] or timing.get("timing_constraints") != []:
        raise ValueError("functional timing clocks/constraints must remain unbound")

    return {
        "schema_version": 1,
        "status": "PASS_STATIC_CONTRACT_IO_DRC_NOT_RUN",
        "layout_allowed": False,
        "target_part": PART,
        "top_module": TOP,
        "port_count": len(expected),
        "direction_counts": {
            direction: sum(1 for row in expected.values() if row["direction"] == direction)
            for direction in ("input", "output", "inout")
        },
        "iostandard_counts": {
            standard: sum(1 for row in expected.values() if row["IOSTANDARD"] == standard)
            for standard in ("LVCMOS18", "LVCMOS33")
        },
        "harness_xdc": HARNESS_XDC,
        "constraint_preview": PREVIEW_XDC,
        "timing_status": timing.get("status"),
        "note": "Static source consistency only; Vivado I/O DRC and functional STA remain NOT_RUN.",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, sort_keys=True))
