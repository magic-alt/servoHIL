#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "hardware" / "kicad" / "revA"

FILES = {
    "01_power_entry.kicad_sch": [
        "TPS259474L",
        "VIN_RAW",
        "UVLO_NODE",
        "OVLO_NODE",
        "PGTH_NODE",
        "ILIM_NODE",
        "DVDT_NODE",
        "ITIMER_NODE",
        "EFUSE_PG",
        "12V_PROT",
        "825R 1% (~4A)",
        "3.3nF C0G",
    ],
    "02_analog_power.kicad_sch": [
        "LT3045",
        "LTC7149",
        "LT3094",
        "ADR4525",
        "6V0_PRE",
        "+5V0_DAC",
        "+5V2_PVDD",
        "-6V0_PRE",
        "-5V2_PVSS",
        "VREF_2V5",
        "SET_5V0",
        "SET_5V2",
        "SET_N5V2",
    ],
    "03_digital_power.kicad_sch": [
        "TPS70933",
        "74LVC1G17",
        "ADM1186-1",
        "ADP5054",
        "FUNCTIONAL_PRELAYOUT",
        "SEQ_START",
        "EN1_SEQ",
        "EN2_SEQ",
        "EN3_SEQ",
        "EN4_SEQ",
        "ANALOG_EN",
        "BST1",
        "BST2",
        "BST3",
        "BST4",
        "COMP1",
        "COMP2",
        "COMP3",
        "COMP4",
        "DL1",
        "DL2",
        "32.4k (600kHz)",
        "47k PRELIM ILIM1",
        "47k PRELIM ILIM2",
    ],
}

texts: dict[str, str] = {}
errors: list[str] = []

for name, tokens in FILES.items():
    path = REV / name
    if not path.exists():
        errors.append(f"missing schematic: {path.relative_to(ROOT)}")
        continue
    text = path.read_text(encoding="utf-8")
    texts[name] = text

    if "Hierarchy scaffold" in text:
        errors.append(f"{name}: still contains empty-scaffold marker")

    for token in tokens:
        if token not in text:
            errors.append(f"{name}: missing required token {token!r}")

# Catch the Local-FPGA U10 collision that existed in an early draft.
digital = texts.get("03_digital_power.kicad_sch", "")
if '(reference "U10")' in digital:
    errors.append("03_digital_power.kicad_sch: U10 is reserved for the Local I/O FPGA; power-sheet helper must use another ref")

# Every placed reference in the current Rev.A hierarchy must be unique.
refs: dict[str, str] = {}
for path in REV.glob("*.kicad_sch"):
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r'\(reference "([^"]+)"\)', text):
        if ref in refs:
            errors.append(f"duplicate annotated reference {ref}: {refs[ref]} and {path.name}")
        else:
            refs[ref] = path.name

# Explicitly require the pre-layout ADP5054 symbol to have no footprint.
m = re.search(
    r'\(property "Reference" "U2".*?\(property "Footprint" "([^"]*)"',
    digital,
    re.S,
)
if not m:
    errors.append("03_digital_power.kicad_sch: cannot locate U2 footprint property")
elif m.group(1):
    errors.append("03_digital_power.kicad_sch: functional ADP5054 U2 must not carry a PCB footprint before full 48-pin symbol freeze")

if errors:
    print("Rev.A power schematic contract FAIL")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)

print("Rev.A power schematic contract PASS")
for name in FILES:
    print(f" - {name}: {len(texts[name])} bytes")
print(f" - unique annotated references: {len(refs)}")
