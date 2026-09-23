#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICD = ROOT / "docs" / "icd" / "j12-hil-link.csv"
SCH04 = ROOT / "hardware" / "kicad" / "revA" / "04_axu_hil_link.kicad_sch"
SCH05 = ROOT / "hardware" / "kicad" / "revA" / "05_io_fpga.kicad_sch"
PLAN = ROOT / "hardware" / "fpga" / "revA" / "pin_plan.csv"
XDC = ROOT / "hardware" / "fpga" / "revA" / "hil_link_ports.xdc.tmpl"

errors: list[str] = []

def balanced_block(text: str, start: int) -> str:
    depth = 0
    quoted = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced KiCad S-expression")

def blocks(text: str, marker: str):
    pos = 0
    while True:
        pos = text.find(marker, pos)
        if pos < 0:
            return
        block = balanced_block(text, pos)
        yield block
        pos += len(block)

def at_xy(block: str) -> tuple[float, float] | None:
    m = re.search(r'\(at\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)', block)
    return (float(m.group(1)), float(m.group(2))) if m else None

def key(x: float, y: float) -> tuple[float, float]:
    return (round(x, 2), round(y, 2))

with ICD.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

if len(rows) != 40:
    errors.append(f"J12 ICD must contain 40 rows, got {len(rows)}")

pins = [int(r["J12 Pin"]) for r in rows]
if pins != list(range(1, 41)):
    errors.append("J12 ICD pin numbers must be exactly 1..40")

active_rows = [r for r in rows if r["ServoHIL Rev.A Net"] not in {"GND", "NC"}]
active = {r["ServoHIL Rev.A Net"] for r in active_rows}
if len(active) != 34:
    errors.append(f"J12 must expose 34 PL I/O nets, got {len(active)}")

sch04 = SCH04.read_text(encoding="utf-8")
sch05 = SCH05.read_text(encoding="utf-8")

# Parse J12 embedded symbol pin geometry.
defs: dict[str, dict[int, tuple[float, float]]] = {}
for block in blocks(sch04, '(symbol "ServoHILCore:'):
    m = re.match(r'\(symbol "([^"]+)"', block)
    if not m:
        continue
    pinmap: dict[int, tuple[float, float]] = {}
    pin_re = re.compile(
        r'\(pin\s+\S+\s+line\s+\(at\s+(-?\d+(?:\.\d+)?)\s+'
        r'(-?\d+(?:\.\d+)?)\s+[-\d.]+\)[\s\S]*?'
        r'\(number\s+"(\d+)"'
    )
    for pm in pin_re.finditer(block):
        pinmap[int(pm.group(3))] = (float(pm.group(1)), float(pm.group(2)))
    defs[m.group(1)] = pinmap

j10_block = None
for block in blocks(sch04, '(symbol\n'):
    if '(property "Reference" "J10"' in block:
        j10_block = block
        break
if j10_block is None:
    # KiCad formatting may use "(symbol" followed by whitespace other than newline.
    for m in re.finditer(r'\(symbol\s+\(lib_id', sch04):
        block = balanced_block(sch04, m.start())
        if '(property "Reference" "J10"' in block:
            j10_block = block
            break

if j10_block is None:
    errors.append("J10 instance missing")
    endpoints = {}
else:
    lib = re.search(r'\(lib_id "([^"]+)"', j10_block)
    origin = at_xy(j10_block)
    if not lib or not origin:
        errors.append("cannot parse J10 lib/origin")
        endpoints = {}
    else:
        pinmap = defs.get(lib.group(1), {})
        ox, oy = origin
        endpoints = {n: key(ox + px, oy - py) for n, (px, py) in pinmap.items()}
        if set(endpoints) != set(range(1, 41)):
            errors.append(f"J10 must expose pins 1..40, got {sorted(endpoints)}")

labels_at: dict[tuple[float, float], set[str]] = {}
for block in blocks(sch04, '(global_label "'):
    nm = re.match(r'\(global_label "([^"]+)"', block)
    xy = at_xy(block)
    if nm and xy:
        labels_at.setdefault(key(*xy), set()).add(nm.group(1))

nc_at: set[tuple[float, float]] = set()
for m in re.finditer(r'\(no_connect\s+\(at\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\)', sch04):
    nc_at.add(key(float(m.group(1)), float(m.group(2))))

local_outputs = {"HL_RX_CLK", "HL_IRQ"} | {f"HL_RX{i}" for i in range(8)}

for row in rows:
    p = int(row["J12 Pin"])
    net = row["ServoHIL Rev.A Net"]
    xy = endpoints.get(p)
    if xy is None:
        continue

    if net == "NC":
        if xy not in nc_at:
            errors.append(f"J12 pin {p}: expected NC marker")
        continue

    if net == "GND":
        expected = "GND"
    elif net in local_outputs:
        expected = f"J12_{net}"
    else:
        expected = net

    if expected not in labels_at.get(xy, set()):
        errors.append(
            f"J12 pin {p}: expected connector-side label {expected!r} at {xy}, "
            f"got {sorted(labels_at.get(xy, set()))}"
        )

if len(nc_at) != 3:
    errors.append(f"only J12 pins 2/39/40 may be NC; schematic has {len(nc_at)} NC markers")

# Local-source series paths must expose both connector-side and FPGA-side nets.
for net in sorted(local_outputs):
    if f'(global_label "J12_{net}"' not in sch04:
        errors.append(f"missing connector-side source-damping net J12_{net}")
    if f'(global_label "{net}"' not in sch04:
        errors.append(f"missing FPGA-side source-damping net {net}")

# All active J12 signals must terminate at Local-FPGA logical ports on sheet 05.
for net in sorted(active):
    if f'(global_label "{net}"' not in sch05:
        errors.append(f"05_IO_FPGA missing HIL-Link net {net}")

# Functional FPGA symbol must expose the 9 reserve/debug pins added after the core 62.
u10 = sch05.find('(property "Reference" "U10"')
u10_end = sch05.find("(instances", u10)
u10_chunk = sch05[u10:u10_end] if u10 >= 0 and u10_end >= 0 else ""
u10_pins = {int(x) for x in re.findall(r'\(pin "(\d+)"', u10_chunk)}
for n in range(63, 72):
    if n not in u10_pins:
        errors.append(f"U10 functional symbol instance missing reserve pin {n}")

with PLAN.open(newline="", encoding="utf-8-sig") as f:
    plan_rows = list(csv.DictReader(f))
plan = {r["logical_net"]: r for r in plan_rows}

missing = sorted(active - set(plan))
if missing:
    errors.append(f"pin_plan.csv missing J12 active nets: {missing}")

direction: dict[str, str] = {
    "HL_TX_CLK": "input", "HL_RX_CLK": "output",
    "HL_SYNC": "input", "HL_IRQ": "output",
    "HL_SAFE_N": "input", "HL_RESET_N": "input", "HL_HEARTBEAT": "input",
    "TRIG0": "input", "TRIG1": "input",
}
direction.update({f"HL_TX{i}": "input" for i in range(8)})
direction.update({f"HL_RX{i}": "output" for i in range(8)})
direction.update({n: "bidirectional" for n in [
    "SPARE_GC0", "SPARE_GC1", "SPARE_GC2",
    "DBG0", "DBG1", "SPARE0", "SPARE1", "SPARE2", "SPARE3",
]})

for net in sorted(active):
    row = plan.get(net)
    if not row:
        continue
    if row["iostandard"] != "LVCMOS18":
        errors.append(f"{net}: IOSTANDARD must be LVCMOS18")
    if row["required_bank_vcco"] != "1.8V":
        errors.append(f"{net}: required_bank_vcco must be 1.8V")
    if row["direction_at_local_fpga"] != direction[net]:
        errors.append(
            f"{net}: direction must be {direction[net]}, got {row['direction_at_local_fpga']}"
        )
    if row["package_pin"].strip():
        errors.append(f"{net}: PACKAGE_PIN must remain blank before Vivado freeze")
    if row["status"] != "UNASSIGNED":
        errors.append(f"{net}: status must remain UNASSIGNED before Vivado freeze")

xdc = XDC.read_text(encoding="utf-8")
required_xdc_tokens = [
    "LVCMOS18",
    "hl_tx_clk", "hl_rx_clk", "hl_tx[*]", "hl_rx[*]",
    "hl_sync", "hl_irq", "hl_safe_n", "hl_reset_n", "hl_heartbeat",
    "trig[*]", "dbg[*]", "spare[*]", "spare_gc[*]",
    "create_clock -name HIL_TX_CLK -period 10.000",
]
for token in required_xdc_tokens:
    if token not in xdc:
        errors.append(f"XDC template missing {token!r}")

active_xdc_lines = [
    line for line in xdc.splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
if any("PACKAGE_PIN" in line for line in active_xdc_lines):
    errors.append("HIL-Link XDC must not activate PACKAGE_PIN before Vivado I/O freeze")

if errors:
    print("Rev.A HIL-Link five-way contract FAIL")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)

print("Rev.A HIL-Link five-way contract PASS")
print(f" - J12 pins: {len(rows)}")
print(f" - active PL I/O: {len(active)}")
print(f" - connector NC pins: {len(nc_at)}")
print(f" - Local FPGA HIL-Link endpoints: {len(active)}")
print(f" - pin-plan total rows: {len(plan_rows)}")
print(" - PACKAGE_PIN: intentionally UNASSIGNED")
