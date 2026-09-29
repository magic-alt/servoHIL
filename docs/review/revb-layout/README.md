# Rev.B PCB Layout — Phase 1

## Scope

PR #30 closed the **schematic/Layout-entry gate**. This phase therefore does not reopen the 15-page schematic architecture. The active sequence is:

1. carrier mechanical reference, board outline, mounting holes, connector placement and keepouts;
2. six-layer stackup and design rules;
3. power and precision-analog placement;
4. grounding and return-path control;
5. routing;
6. KiCad PCB DRC and layout review.

The source-of-truth contracts are:

- `hardware/revB/pcb_layout_contract.json`
- `hardware/revB/pcb_design_rules.json`
- `hardware/revB/layout_entry_contract.json`

`layout_allowed=true` remains independent from `fabrication_allowed=false` and
`release_allowed=false`.

## Mechanical baseline

The original AXU2CGB exposes J12 and J15 as two 40-pin, 0.1-inch / 2.54 mm
expansion ports. The repository already binds the logical pinout in
`hardware/carriers/axu2cgb/physical_pinout.csv` and the 64 used signals in
`assignments.csv`.

The schematic intentionally represents J12/J15 as **purchased-host logical
boundaries** with `on_board=no`. That was correct for schematic closure, but a
directly mated PCB requires a physical expansion-board mating connector and exact
mechanical registration.

The pinned manufacturer DXF now binds the 100 x 85 mm host outline, four primary
mounting holes, both 2x20 pin grids, J12/J15 geometric centers, and pin-1
orientation. Pin 1 is the non-circular square `PIN_TOP` pad: J12 is at
`(6.5278, 18.3769)` and J15 at `(93.4720, 66.6369)` in ALINX DXF native mm.

The remaining mechanical inputs that must be bound before a real mating
connector footprint / stack is released are:

- exact host connector manufacturer/MPN and expansion-board mating MPN;
- mated stack height;
- tall-component / heatsink / connector keepouts.

**Do not scale a product photograph into manufacturing coordinates.**

These remaining items are PCB mechanical inputs, not a reason to return to broad
schematic redesign. Until connector MPN/stack height is bound, PR #31 keeps the
native `.kicad_pcb` intentionally absent rather than committing a guessed generic
2x20 footprint. If direct mezzanine mating is selected, the only schematic
adjustment should be the minimum reviewed representation needed to give the
physical mating connectors real nets/ratsnest connectivity.

## Stackup target

Use a six-layer role stack while the manufacturer-specific dielectric geometry is
still unbound:

| Layer | Role |
|---|---|
| L1 / F.Cu | components + signals |
| L2 / In1.Cu | continuous GND reference |
| L3 / In2.Cu | power distribution + slow signals |
| L4 / In3.Cu | signals |
| L5 / In4.Cu | continuous GND reference |
| L6 / B.Cu | components + signals |

Nominal total thickness is 1.6 mm only as a mechanical target. Copper thickness,
dielectric thickness, finished impedance geometry and via capability must be
rebound to the chosen PCB fabricator before fabrication release.

## Grounding / return path

The board uses **continuous reference planes with functional zoning**, not hard
AGND/DGND islands.

- Keep L2 and L5 continuous GND.
- Separate switchers, digital PHY, ADC and DAC by placement and current-loop
  geometry.
- Never route a fast or precision signal across a reference-plane void.
- Put a nearby GND stitching via next to each high-speed layer transition.
- Keep switching current return loops local.
- Put connector ESD return vias immediately beside the protection device.
- J5 pins 9/10 are signal GND, not chassis/PE.

## Placement order

### 1. Input power

Place in physical current-flow order:

`J101 -> F101 -> D101/D102 -> U101 -> C105`

Keep TVS/eFuse/bulk paths compact and reserve an edge-access zone for J101 and
SW101.

### 2. Switching power

Treat each converter as a compact island:

- U201/L201 — 6V2_PRE
- U202/L202 — 3V3_D
- U203/L203 — 1V8_D
- U301/L301/L302/D301/C410/C411 — negative preregulator

The SW-node copper is intentionally small. Do not route it under or adjacent to
ADC, DAC, reference or low-noise LDO networks.

### 3. Low-noise rails and precision analog

Place U211/U212/U302 downstream of the switching stages and close to their
precision loads. Cluster U20-U23 with local decoupling/output networks. Orient
the DAC region so digital traffic enters from the host side and AO paths leave
toward J5.

For U801, keep reference/REGCAP/decoupling and the input RC network compact.
Connector-side protection is physically before the ADC victim.

### 4. External PHY

For encoder/RS-485 paths, use:

`external connector -> protection -> termination/transceiver -> digital logic`

Keep the A/B pair coupled and free of long stubs. A 120-ohm differential target
is a **target**, not a released width/gap, until the board shop stackup is
selected.

## Baseline geometry

The current layout target is intentionally conservative for prototype-capable
fabrication:

- default clearance: 0.20 mm;
- default signal width: 0.20 mm;
- default via: 0.60 / 0.30 mm;
- copper-to-edge: 0.30 mm;
- VIN_RAW/VIN_PROT: polygon or >=1.00 mm trace when not poured;
- medium-current rails: polygon or >=0.50 mm trace when not poured.

These dimensions are Layout defaults, not a manufacturer process approval.

## Routing priority

1. switching hot loops and power current paths;
2. precision reference / DAC / ADC analog;
3. external differential pairs;
4. fast DAC/ADC digital groups;
5. safety handshake/control;
6. remaining low-speed signals.

The fast J12 ADC/DAC buses must remain compact over an uninterrupted GND
reference, with no long stubs and few vias. Numeric skew limits are not invented
here; they are closed later with the functional timing contract.

## PCB DRC close criteria

Layout close requires:

- zero unconnected items;
- zero clearance, width, via and board-edge violations;
- all courtyard overlaps reviewed and no unwaived conflict;
- connector keepouts and access envelopes reviewed;
- a selected-fabricator stackup before controlled-impedance geometry is treated
  as closed.

Passing PCB DRC does **not** authorize Gerber/fabrication.

## Gates that remain outside Layout entry

The following remain fabrication/release gates and continue in parallel without
blocking placement/routing:

- manufacturer MLCC/magnetics curves;
- real DUT adapter thresholds/leakage/shutdown timing;
- partial-power/backfeed;
- assembled-board thermal;
- low-energy fixture/fault injection;
- Vivado raw I/O DRC and functional STA/CDC;
- EMC, power-down, fault injection and FOC closed-loop acceptance.
