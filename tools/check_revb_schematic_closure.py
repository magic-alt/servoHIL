#!/usr/bin/env python3
"""Fail-closed audit for Rev.B native schematic package/BOM closure."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NATIVE=ROOT/"hardware/kicad/revB/axu2cgb_expansion"
MANIFEST=ROOT/"hardware/revB/schematic_open_items.json"

REF_RE=re.compile(r'\\(property "Reference" "([^"]+)"')
FP_RE=re.compile(r'\\(property "Footprint" "([^"]*)"')
DS_RE=re.compile(r'\\(property "Datasheet" "([^"]*)"')
VAL_RE=re.compile(r'\\(property "Value" "([^"]*)"')

def _field(rx,line,default=""):
    m=rx.search(line)
    return m.group(1) if m else default

def placed_symbols():
    rows=[]
    for path in sorted(NATIVE.glob("*.kicad_sch")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.lstrip().startswith("(symbol (lib_id "):
                continue
            ref=_field(REF_RE,line)
            if not ref:
                continue
            rows.append({
                "sheet":path.name,
                "reference":ref,
                "value":_field(VAL_RE,line),
                "footprint":_field(FP_RE,line),
                "datasheet":_field(DS_RE,line),
                "in_bom":"(in_bom yes)" in line,
                "on_board":"(on_board yes)" in line,
                "dnp":"(dnp yes)" in line,
            })
    return rows

def check():
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("layout_allowed") is not False:
        raise ValueError("schematic closure manifest must not authorize Layout")
    rows=placed_symbols()
    by_ref={r["reference"]:r for r in rows}
    if len(by_ref)!=len(rows):
        dup=sorted(r for r in by_ref if sum(x["reference"]==r for x in rows)>1)
        raise ValueError("duplicate physical references: "+str(dup))
    physical=[r for r in rows if r["in_bom"] and r["on_board"] and not r["reference"].startswith("#")]
    missing={r["reference"] for r in physical if not r["footprint"]}
    allowed=set(manifest["open_footprints"])
    if missing!=allowed:
        raise ValueError("blank footprint set changed: unexpected=%s resolved_not_removed=%s" %
                         (sorted(missing-allowed),sorted(allowed-missing)))
    for ref in manifest.get("excluded_host_boundaries",[]):
        row=by_ref.get(ref)
        if not row:
            raise ValueError("missing host boundary "+ref)
        if row["in_bom"] or row["on_board"]:
            raise ValueError(ref+" must remain excluded from expansion-board BOM/placement")
    for ref,expected in manifest.get("bound_packages",{}).items():
        row=by_ref.get(ref)
        if not row:
            raise ValueError("missing bound component "+ref)
        if row["footprint"]!=expected:
            raise ValueError("%s footprint drift: %s != %s" % (ref,row["footprint"],expected))
        lib,name=expected.split(":",1)
        local=NATIVE/"footprints"/(lib+".pretty")/(name+".kicad_mod")
        if not local.is_file():
            raise ValueError("missing locally vendored footprint for %s: %s" % (ref,local))
    for ref in ("U20","U21","U22","U23"):
        row=by_ref[ref]
        if "ad3542r" not in row["datasheet"].lower():
            raise ValueError(ref+" must bind AD3542R datasheet while land pattern is open")
        if "CP-28-15" not in row["value"] or "OPEN" not in row["value"]:
            raise ValueError(ref+" must visibly identify the open exact land-pattern contract")
    return {
        "status":"PASS_SOURCE_CLOSURE_CONTRACT",
        "physical_components":len(physical),
        "blank_footprints":sorted(missing),
        "blank_footprint_count":len(missing),
        "layout_allowed":False,
    }

if __name__=="__main__":
    print(json.dumps(check(),indent=2,sort_keys=True))
