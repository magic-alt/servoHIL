# ServoHIL-I/O Rev.A KiCad project

This directory is the native KiCad hierarchy for the first ServoHIL-I/O board.

## Current state

- all seven child schematic sheets are populated;
- historical pre-repair baseline: KiCad 10.0.6 parsed the full hierarchy;
- historical pre-repair ERC baseline: **0 errors / 0 warnings**; rerun ERC after the archive readability repair before relying on that result;
- CI exports the complete schematic PDF review artifact;
- POWER topology is implemented but switching-stage values are still PRELIM;
- AXU2CGB J12 HIL-Link mapping is implemented from the ICD;
- XC7A35T is intentionally represented as a functional pre-layout symbol;
- FGG484 PACKAGE_PIN / footprint assignment remains deferred to Vivado I/O Planner;
- four AD3542R devices implement the 8-channel AO path;
- PCB placement/routing has **not** started.

`layout_gate.yaml` remains the authority:

- `schematic_erc: true`
- `power_tree_frozen: false`
- `fpga_pinplan_frozen: false`
- `j12_xdc_crosscheck: false`
- `dac_network_review: false`
- `layout_allowed: false`

## 2026-09-23 archive readability repair

The Rev.A circuit/net intent is unchanged, but the native schematic presentation
has been repaired so the pages are usable in the editor:

- every former pin-mounted global label now terminates a 2.54 mm explicit wire
  stub, making connectivity visible without renaming or merging nets;
- visible Reference/Value fields are restored to the placement defined by each
  embedded symbol instead of the scattered generated coordinates;
- the two analog-power flags and the crowded/off-page digital-power passives are
  repositioned inside the A3 sheet; the four digital-power output rows are
  separated from the ADP5054 body;
- all global-label names/multiplicities, reference designators, component values
  and explicit no-connect markers are preserved.

This is an archive-only editability/readability repair, not a Rev.A redesign.
A fresh KiCad ERC should be run on a workstation before merging or using the
archived schematic for any engineering decision.

## Hierarchy

- `01_power_entry.kicad_sch`
- `02_analog_power.kicad_sch`
- `03_digital_power.kicad_sch`
- `04_axu_hil_link.kicad_sch`
- `05_io_fpga.kicad_sch`
- `06_dac_0_3.kicad_sch`
- `07_dac_4_7.kicad_sch`

Open `servohil_io_revA.kicad_pro` / `servohil_io_revA.kicad_sch` in KiCad 8+.

## No-layout rule

A zero-warning ERC result does **not** authorize placement/routing. Before layout:

1. freeze ADP5054/LTC7149 power-stage values and thermal budget;
2. replace functional pre-layout power/FPGA symbols with verified complete package symbols where required;
3. complete Vivado FGG484 I/O planning and reviewed PACKAGE_PIN XDC;
4. close the J12↔schematic↔XDC cross-check gate;
5. close the AD3542R package/output-stability/layout review gate;
6. set `layout_allowed: true` only in a dedicated reviewed commit.
