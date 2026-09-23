#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ICD = ROOT / "docs" / "icd" / "j12-hil-link.csv"
SCH = ROOT / "hardware" / "kicad" / "revA" / "04_axu_hil_link.kicad_sch"
PLAN = ROOT / "hardware" / "fpga" / "revA" / "pin_plan.csv"
XDC = ROOT / "hardware" / "fpga" / "revA" / "hil_link_ports.xdc.tmpl"

errors: list[str] = []

with ICD.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

if len(rows) != 40:
    errors.append(f"J12 ICD must contain exactly 40 pins, got {len(rows)}")

pins = [int(r["J12 Pin"]) for r in rows]
if pins != list(range(1, 41)):
    errors.append("J12 ICD pin numbers are not exactly 1..40")

active_rows = [r for r in rows if r["ServoHIL Rev.A Net"] not in {"GND", "NC"}]
active = {r["ServoHIL Rev.A Net"] for r in active_rows}

if len(active) != 34:
    errors.append(f"expected 34 active PL I/O nets, got {len(active)}")

sch = SCH.read_text(encoding="utf-8")
if 'reference "J10"' not in sch:
    errors.append("J10 connector instance missing from schematic")

instance_pos = sch.find('(property "Reference" "J10"')
instance_end = sch.find("(instances", instance_pos)
j10_chunk = sch[instance_pos:instance_end] if instance_pos >= 0 and instance_end >= 0 else ""
j10_pins = {int(x) for x in re.findall(r'\(pin "(\d+)"', j10_chunk)}
if j10_pins != set(range(1, 41)):
    errors.append(f"J10 schematic instance does not expose exactly pins 1..40: {sorted(j10_pins)}")

for net in sorted(active):
    if f'(global_label "{net}"' not in sch:
        errors.append(f"active ICD net missing from 04 schematic: {net}")

for forbidden in ("VCC5V", "VCC_3V3_BUCK4"):
    if f'(global_label "{forbidden}"' in sch:
        errors.append(f"AXU supply must remain NC, but schematic labels {forbidden}")

if sch.count("(no_connect ") != 3:
    errors.append(f"expected exactly 3 no-connect markers for J12 pins 2/39/40, got {sch.count('(no_connect ')}")

with PLAN.open(newline="", encoding="utf-8-sig") as f:
    plan_rows = list(csv.DictReader(f))

plan = {r["logical_net"]: r for r in plan_rows}
plan_set = set(plan)
if plan_set != active:
    missing = sorted(active - plan_set)
    extra = sorted(plan_set - active)
    if missing:
        errors.append(f"pin plan missing ICD nets: {missing}")
    if extra:
        errors.append(f"pin plan has nets not in ICD: {extra}")

for net, row in plan.items():
    if row["iostandard"] != "LVCMOS18":
        errors.append(f"{net}: IOSTANDARD must be LVCMOS18, got {row['iostandard']}")
    if row["required_bank_vcco"] != "1.8V":
        errors.append(f"{net}: required bank VCCO must be 1.8V, got {row['required_bank_vcco']}")
    if row["package_pin"].strip():
        errors.append(f"{net}: PACKAGE_PIN must remain blank until Vivado I/O Planner freeze")
    if row["status"] != "UNASSIGNED":
        errors.append(f"{net}: status must remain UNASSIGNED before pin-plan freeze")

expected_direction = {
    "HL_TX_CLK": "input",
    "HL_RX_CLK": "output",
    "HL_SYNC": "input",
    "HL_IRQ": "output",
    "HL_SAFE_N": "input",
    "HL_RESET_N": "input",
    "HL_HEARTBEAT": "input",
    "TRIG0": "input",
    "TRIG1": "input",
}
expected_direction.update({f"HL_TX{i}": "input" for i in range(8)})
expected_direction.update({f"HL_RX{i}": "output" for i in range(8)})

for net, direction in expected_direction.items():
    if net in plan and plan[net]["direction_at_local_fpga"] != direction:
        errors.append(
            f"{net}: local-FPGA direction must be {direction}, got {plan[net]['direction_at_local_fpga']}"
        )

xdc = XDC.read_text(encoding="utf-8")
required_xdc_tokens = [
    "LVCMOS18",
    "hl_tx_clk",
    "hl_rx_clk",
    "hl_tx_data[*]",
    "hl_rx_data[*]",
    "hl_sync",
    "hl_irq",
    "hl_safe_n",
    "hl_reset_n",
    "hl_heartbeat",
    "trig[*]",
    "dbg[*]",
    "spare[*]",
    "spare_gc[*]",
    "create_clock -name HIL_TX_CLK -period 10.000",
]
for token in required_xdc_tokens:
    if token not in xdc:
        errors.append(f"XDC template missing required token: {token}")

if "set_property PACKAGE_PIN " in "\n".join(
    line for line in xdc.splitlines() if not line.lstrip().startswith("#")
):
    errors.append("XDC template must not contain active PACKAGE_PIN assignments before Vivado pin-plan freeze")

if errors:
    print("Rev.A HIL-Link contract FAIL")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)

print("Rev.A HIL-Link contract PASS")
print(f" - J12 pins: {len(rows)}")
print(f" - active PL I/O nets: {len(active)}")
print(f" - pin-plan rows: {len(plan_rows)}")
print(" - PACKAGE_PIN assignments: intentionally UNASSIGNED")
