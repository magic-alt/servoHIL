# Rev.B hardware contract and release boundary

Rev.B is a **single-ZU2CG** HIL architecture. The active editable native KiCad source is:

```text
hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_pro
```

The current functional schematic topology is closed at **15 pages**. It includes the
AXU2CGB carrier boundary, power/protection, DAC and physical AO disconnect, hardware
watchdog/interlock, floating DUT permit, ADC frontend, PWM/AUX/RS-485 boundaries and
SSI/BiSS PHY. This is not equivalent to a production-qualified PCB.

## Source and generated review kits

The checked-in native KiCad files under
`hardware/kicad/revB/axu2cgb_expansion/` are the active schematic design source.
`tools/revb.py generate` remains useful for carrier-contract review fixtures and
compatibility regressions; generated build directories are not the manufacturing
source of truth.

Example non-release review generation:

```sh
python tools/revb.py validate --carrier axu2cgb
python tools/revb.py generate --carrier axu2cgb --output build/revB
```

The alternative ZU2CG SoM profile remains vendor/model **UNBOUND**. Synthetic SoM
fixtures only test tooling compatibility and do not establish product compatibility.

## Physical binding state

`hardware/revB/schematic_open_items.json` is the fail-closed source for unresolved
blank footprints. It currently contains **5** blockers, all mechanical/interface
contracts:

- J101: 12 V field connector mechanical/cable contract;
- SW101: reset switch actuator/mechanical contract;
- J5: AO connector and DUT cable contract;
- J501: dry-contact service/interlock connector contract;
- J701: floating DUT-permit connector, actual DUT voltage/current/leakage/isolation and cable contract.

U20..U23 are source-bound to the reviewed
`Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R` footprint. That footprint is
traceable to the official EVAL-AD3542RFMCZ BOM, IPC-356 and top copper/mask/paste
Gerber geometry through `hardware/revB/ad3542r_footprint_evidence.json` and
`hardware/revB/evidence/ad3542r/u1_geometry_review.json`. The reviewed land pattern
has 28 perimeter pads at 0.40 mm pitch and no center/exposed pad.

U101 and L201/L202/L301/L302/L203 also have source-level package/footprint
bindings. None of these bindings constitutes electrical, thermal, magnetic,
mechanical or production qualification.

Run:

```sh
python tools/check_revb_schematic_closure.py
```

A passing source-closure report only proves that the checked-in schematic matches the
explicit binding contract. It does not authorize Layout.

## Pre-layout qualification workstreams

The remaining pre-layout work is coordinated by
`hardware/revB/prelayout_qualification_contract.json`. Its checked-in state is
deliberately **BLOCKED_PRE_LAYOUT_EVIDENCE_REQUIRED** and cannot authorize Layout.

Run both source/evidence contract audits:

```sh
python tools/check_revb_schematic_closure.py
python tools/check_revb_prelayout_contract.py
python tools/revb_qualification.py
```

The five mechanical interfaces have a machine-readable selection plan in
`hardware/revB/mechanical_binding_plan.json`. No connector or switch is currently
claimed as selected: each exact part and evidence pack remains null until the real
enclosure, mating cable and DUT contract are known.

Manufacturer-source discovery is tracked separately in
`hardware/revB/component_evidence_sources.json`:

- Coilcraft XAL5050-103MEC / XAL5050-682MEC / XAL5030-472MEC source pages and the
  current XAL50xx datasheet are located, but the characteristic bytes/curves are
  not yet hash-archived and independently digitized;
- TDK exact characterization sheets are located for the assigned 22 uF / 16 V,
  10 uF / 25 V and automotive 1 uF / 50 V candidates, but no reviewed,
  hash-bound DC-bias curve pack has yet been imported;
- the protected-input MLCC bank still has no exact production MPN.

Located source URLs are provenance discovery, not qualification evidence.

The executable bench/tool plans live under
`hardware/revB/verification_plans/`:

- `dut_adapter_acceptance.json`;
- `partial_power_backfeed.json`;
- `board_thermal.json`;
- `low_energy_fixture.json`;
- `vivado_io_timing.json`.

All checked-in results remain `NOT_RUN`. The Vivado plan is additionally blocked
because this repository currently has no active non-archive `.xdc` or `.xpr`
binding for the Rev.B RTL. Target part, top module, clocks and XDC must be bound
before any IO-DRC/STA result can be accepted.

## Qualification state

`hardware/revB/qualification_requirements.json`,
`hardware/revB/dut_adapter_profile.json` and `hardware/revB/gates.json` are
fail-closed. At this checkpoint `layout_allowed=false`.

Before Layout, the project still requires:

1. exact physical closure of the 5 remaining mechanical/interface items;
2. power margin, thermal, MLCC and magnetic evidence, including XAL5050 L(I,T),
   AC/core/winding losses, startup/short-circuit saturation and mounted-board
   temperature rise;
3. exact-MPN MLCC DC-bias curves plus temperature/aging and applicable ESR/RMS-current
   evidence;
4. a real DUT adapter profile binding AO neutral behavior, permit thresholds/leakage,
   cable open/short response and maximum end-to-end disable time to raw measurements;
5. partial-power/backfeed testing with relevant interfaces energized while other
   domains are unpowered;
6. Vivado IO DRC and STA reports bound to the exact part/top/XDC/source revision;
7. low-energy fixture acceptance and engineering review.

Post-layout/sample qualification still requires real EMC, board thermal,
power-down, fault injection and FOC closed-loop evidence.

## Safety semantics

- AO disconnect is **high impedance**, not a guaranteed safe zero-voltage output.
- The single floating DUT permit contact is **not redundant STO** and must not be
  represented as certified functional safety.
- Catalog ratings, exact footprints, ERC, SPICE and RTL simulation are design
  evidence; none is a board-level safety or production certificate.
- A gate must not be changed to PASS without raw evidence tied to the exact hardware,
  DUT, tool inputs and revision that were actually tested.
