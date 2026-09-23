#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "hardware" / "kicad" / "revA"

required = {
    "04_axu_hil_link.kicad_sch": [
        'Reference" "J10"', "AXU2CGB J12", "HL_TX_CLK", "HL_RX_CLK",
        "HL_TX0", "HL_TX7", "HL_RX0", "HL_RX7", "HL_SAFE_N",
        "HL_RESET_N", "HL_HEARTBEAT", "R200", "R209", "33R START",
    ],
    "05_io_fpga.kicad_sch": [
        'Reference" "U10"', "XC7A35T-1FGG484I FUNCTIONAL_PRELAYOUT",
        'Reference" "U11"', "W25Q128JV", 'Reference" "Y1"', "100MHz 1.8V XO",
        'Reference" "J11"', 'Reference" "U13"', 'Reference" "U16"',
        "DAC_SCLK", "DAC_CS0_N", "DAC_CS3_N", "DAC_SDIO0", "DAC_SDIO7",
        "DAC_LDAC_N", "DAC_RESET_N", "FPGA_WDI_3V3",
        "SAFE_RELEASE_3V3", "100k DEFAULT-SAFE PULLDOWN",
    ],
    "06_dac_0_3.kicad_sch": [
        'Reference" "U20"', 'Reference" "U21"', "AD3542RBCPZ16",
        "RFB2_0", "RFB2_1", "RFB1_0", "RFB4_0", "RFB1_1", "RFB4_1",
        "AO0_IA", "AO1_IB", "AO2_IC", "AO3_VBUS", "DNP C0G CFB", "52.3R START",
    ],
    "07_dac_4_7.kicad_sch": [
        'Reference" "U22"', 'Reference" "U23"', "AD3542RBCPZ16",
        "RFB2_0", "RFB2_1", "AO4_TORQUE", "AO5_TEMP", "AO6_AUX0", "AO7_AUX1",
        "DNP C0G CFB", "52.3R START",
    ],
}

errors: list[str] = []
texts: dict[str, str] = {}
for name, tokens in required.items():
    p = REV / name
    if not p.exists():
        errors.append(f"missing {name}")
        continue
    text = p.read_text(encoding="utf-8")
    texts[name] = text
    if "Hierarchy scaffold" in text:
        errors.append(f"{name}: still scaffold")
    for token in tokens:
        if token not in text:
            errors.append(f"{name}: missing {token!r}")

# FPGA is explicitly pre-layout: no footprint allowed yet.
fpga = texts.get("05_io_fpga.kicad_sch", "")
m = re.search(r'\(property "Reference" "U10".*?\(property "Footprint" "([^"]*)"', fpga, re.S)
if not m or m.group(1):
    errors.append("U10 functional XC7A35T must exist with an empty Footprint before Vivado pin freeze")

# All four exact DAC instances must expose the complete 1..28 pin set.
for sheet in ("06_dac_0_3.kicad_sch", "07_dac_4_7.kicad_sch"):
    text = texts.get(sheet, "")
    for ref in re.findall(r'\(property "Reference" "(U2[0-3])"', text):
        start = text.find(f'(property "Reference" "{ref}"')
        end = text.find("(instances", start)
        block = text[start:end]
        pins = {int(x) for x in re.findall(r'\(pin "(\d+)"', block)}
        if pins != set(range(1, 29)):
            errors.append(f"{sheet}:{ref} does not expose exact AD3542R pins 1..28")

# ±5 V hardware feedback contract:
# RFB2 is not represented by a repeated pin-name string per instance; KiCad embeds
# the symbol definition once and connects each instance with net labels. Verify the
# actual per-device VOUT/RFB2 network labels instead. Each DACx_VOUTy label occurs
# at VOUT, RFB2, CFB and the output-series resistor node (>=4 occurrences).
dac_pages = {
    "06_dac_0_3.kicad_sch": (0, 1),
    "07_dac_4_7.kicad_sch": (2, 3),
}
for sheet, devices in dac_pages.items():
    text = texts.get(sheet, "")
    for idx in devices:
        for ch in (0, 1):
            net = f"DAC{idx}_VOUT{ch}"
            if text.count(net) < 4:
                errors.append(f"{sheet}: {net} does not cover VOUT + RFB2 + CFB/output nodes")
    # Per device: DNC + RFB1/RFB4 for both channels = five explicit NC pins.
    expected_nc = 5 * len(devices)
    actual_nc = text.count("(no_connect")
    if actual_nc != expected_nc:
        errors.append(f"{sheet}: expected {expected_nc} explicit DAC NC pins, found {actual_nc}")

# FPGA pin-plan must include every core digital interface and remain unassigned.
plan = ROOT / "hardware" / "fpga" / "revA" / "pin_plan.csv"
rows = list(csv.DictReader(plan.open(encoding="utf-8")))
needed = {
    "HL_TX_CLK","HL_RX_CLK","HL_TX0","HL_TX7","HL_RX0","HL_RX7",
    "DAC_SCLK","DAC_CS0_N","DAC_CS3_N","DAC_SDIO0","DAC_SDIO7",
    "DAC_LDAC_N","DAC_ALERT0_N","DAC_ALERT3_N","FPGA_CLK100","FPGA_WDI_3V3"
}
by_net = {r["logical_net"]: r for r in rows}
for net in sorted(needed):
    if net not in by_net:
        errors.append(f"pin_plan.csv missing {net}")
    elif by_net[net]["package_pin"].strip() or by_net[net]["status"] != "UNASSIGNED":
        errors.append(f"pin_plan.csv {net}: package pin must remain UNASSIGNED before Vivado freeze")

if errors:
    print("Rev.A core schematic contract FAIL")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)

print("Rev.A core schematic contract PASS")
for name, text in texts.items():
    print(f" - {name}: {len(text)} bytes")
print(f" - pin-plan entries: {len(rows)}; PACKAGE_PIN remains deferred")
