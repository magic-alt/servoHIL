# Rev.B hardware contract and release boundary

Rev.B is a **single-ZU2CG** HIL architecture. The active editable native KiCad source is:

```text
hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_pro
```

For the consolidated design rationale, calculations, pin definitions, Layout
rules, procurement policy and first-board bring-up procedure, use:

- `docs/design/revb-hardware-design-guide.md`
- `docs/design/revb-procurement-and-cost.md`
- `bom/revb-costed.csv`

## Current gate state

The 15-page source-level schematic and Layout-entry contract are closed sufficiently
to start PCB placement/routing:

- `layout_allowed=true`
- `fabrication_allowed=false`
- `release_allowed=false`
- layout-entry status: `READY_FOR_PCB_LAYOUT`

This means **Layout may proceed, but Gerber/fabrication/production release may not**.

The five previously open board-side mechanical parts are now source-bound for
Layout: J101=Phoenix 1757242, SW101=PTS645SM43SMTR92 LFS,
J5=Phoenix 1844294, J501=Phoenix 1844210 and J701=Molex 43045-0212.
C105 is bound to TDK C5750X7R1V476M230KC and U20..U23 retain the reviewed exact
AD3542R CP-28-15 land pattern. The current native source audit has **zero on-board
blank footprints**.

AXU2CGB official CAD now binds the 100 x 85 mm host outline, four mounting holes,
J12/J15 pin grids/centers and pin-1 orientation. Exact host/mating connector MPN,
mated stack height and carrier component-height keepouts remain open, so a guessed
generic 2x20 mating footprint must not be released.

## Qualification boundary

The following remain fabrication/release gates:

- exact J12/J15 host/mating connector stack definition;
- manufacturer MLCC and magnetic characterization;
- power margin and DAC analog stability;
- real DUT adapter neutral/permit thresholds, leakage, cable-fault behavior and
  maximum shutdown time;
- partial-power/backfeed and powered-off interface behavior;
- assembled-board thermal;
- low-energy fault-injection fixture;
- Vivado raw I/O DRC and functional STA/CDC bound to the exact part/top/XDC/source;
- EMC, power-down, physical fault injection and FOC closed-loop acceptance.

J501/J701 remain laboratory non-safety dry-contact/permit interfaces. A cross-line
cable short can mimic a closed contact; neither interface is STO or redundant
functional safety.

## Costed BOM contract

`bom/revb-costed.csv` covers all **439** on-board physical refs:
**431 populated + 8 DNP**, grouped into **139 purchasing lines**.
`tools/check_revb_costed_bom.py` fails if coverage drifts.

The 2026-09-29 planning snapshot is approximately **CNY 4,085.41** components for
one fully stuffed board and **CNY 17,153.21** components for five fully stuffed
boards after applicable small-quantity breaks. These figures exclude PCB,
assembly, freight/tax, AXU2CGB and the still-unbound J12/J15 mating connector stack.

The BOM also records U501 as an explicit `ORDERABLE_MPN_MISMATCH`: schematic
`TPS3430DRCR` versus TI's current active orderable `TPS3430WDRCR`. It must be
resolved by design review before fabrication, not silently substituted.

## Checks

```sh
python tools/check_revb_schematic_closure.py
python tools/check_revb_prelayout_contract.py
python tools/check_revb_pcb_layout_contract.py
python tools/check_revb_costed_bom.py
python tools/revb_qualification.py
```

Passing these source/contract checks is not a physical qualification or production
certificate.
