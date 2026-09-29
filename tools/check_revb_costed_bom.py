#!/usr/bin/env python3
import csv,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCH=ROOT/"hardware/kicad/revB/axu2cgb_expansion"
SHEETS=["03_peripheral_boundaries.kicad_sch","04_dac_0_3.kicad_sch","05_dac_4_7.kicad_sch","06_analog_outputs.kicad_sch","10_input_protection.kicad_sch","20_positive_rails.kicad_sch","30_negative_reference.kicad_sch","40_power_supervision.kicad_sch","41_power_status.kicad_sch","50_watchdog_interlock.kicad_sch","60_dut_permit.kicad_sch","70_adc_frontend.kicad_sch","80_encoder_phy.kicad_sch"]
BOM=ROOT/"bom/revb-costed.csv"
def native():
 out={}
 pat=re.compile(r'\(symbol \(lib_id "[^"]+"\)[\s\S]*?\(in_bom (yes|no)\) \(on_board (yes|no)\) \(dnp (yes|no)\)[\s\S]*?\(property "Reference" "([^"]+)"[\s\S]*?\(property "Value" "([^"]*)"[\s\S]*?\(property "Footprint" "([^"]*)"')
 for name in SHEETS:
  for m in pat.finditer((SCH/name).read_text(encoding="utf-8")):
   if m.group(1)=="yes" and m.group(2)=="yes":
    assert m.group(4) not in out
    out[m.group(4)]={"dnp":m.group(3)=="yes","value":m.group(5),"footprint":m.group(6)}
 return out
def main():
 sch=native(); rows=list(csv.DictReader(BOM.open(encoding="utf-8",newline=""))); seen={}; dnp=0; total=0.0
 for row in rows:
  refs=row["refs"].split(); assert int(row["qty_per_board"])==len(refs)
  for ref in refs: assert ref not in seen; seen[ref]=row
  if row["populate"]=="DNP": dnp+=len(refs); assert float(row["extended_cny_one_board"])==0; assert row["pricing_status"]=="DNP"
  else: assert row["pricing_status"] in {"EXACT_QUOTE","CANDIDATE_QUOTE","ORDERABLE_MPN_MISMATCH","BUDGET_GENERIC"}; total+=float(row["extended_cny_one_board"])
 assert set(seen)==set(sch),f"coverage mismatch missing={sorted(set(sch)-set(seen))} extra={sorted(set(seen)-set(sch))}"
 assert len(sch)==439 and len(rows)==139 and dnp==8 and sum(not x["dnp"] for x in sch.values())==431
 assert seen["U501"]["pricing_status"]=="ORDERABLE_MPN_MISMATCH" and seen["U501"]["procurement_mpn"]=="TPS3430WDRCR"
 print(f"Rev.B costed BOM OK: {len(rows)} lines, {len(sch)} physical refs, 431 populated, 8 DNP, one-board component budget CNY {total:.2f}")
if __name__=="__main__": main()
