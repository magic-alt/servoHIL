# Rev.B Hardware Design Guide

> **Revision:** Rev.B  
> **Design snapshot:** 2026-09-29 / source baseline `193d8bc61edc690c2f8518b8da784f56a821d872`  
> **Purpose:** single engineering entry point for schematic intent, power calculations, I/O definition, PCB constraints, procurement and first-board bring-up.  
> **Release boundary:** `layout_allowed=true`, `fabrication_allowed=false`, `release_allowed=false`.

This document consolidates the Rev.B design rationale. It does **not** replace the
native KiCad source or machine-readable contracts. If prose conflicts with an
active contract, use the native schematic plus the contract as the source of truth
and fix this guide in the same change.

## 1. Source-of-truth hierarchy

1. Native schematic:
   `hardware/kicad/revB/axu2cgb_expansion/servohil_io_revB.kicad_pro`
2. Carrier physical pin facts:
   `hardware/carriers/axu2cgb/physical_pinout.csv`
3. Rev.B signal assignment:
   `hardware/carriers/axu2cgb/assignments.csv`
4. Electrical I/O contract:
   `hardware/revB/io_contract.json`
5. Layout / release contracts:
   `hardware/revB/gates.json`,
   `hardware/revB/layout_entry_contract.json`,
   `hardware/revB/pcb_layout_contract.json`,
   `hardware/revB/pcb_design_rules.json`
6. Component/evidence contracts:
   `hardware/revB/component_evidence_sources.json`,
   `hardware/revB/qualification_requirements.json`,
   `hardware/revB/verification_plans/`
7. Complete grouped costed BOM:
   `bom/revb-costed.csv` and `bom/revb-cost-summary.json`

Historical review checkpoints under `docs/review/` are evidence of the state at
their recorded commit/date. They must not override current machine-readable gates.

## 2. Architecture

Rev.B is a **single-ZU2CG HIL expansion board** for the original ALINX AXU2CGB.
The ZU2CG performs Plant and real-time I/O. There is no second FPGA on this board.

Functional paths:

- **8 AO:** 4 × AD3542RBCPZ16 (2 channels each) -> source/isolation network ->
  2 × ADG5412F protected analog switches -> J5.
- **8 AI:** J801 -> connector protection -> per-channel RC frontend ->
  AD7606C-16BSTZ -> eight serial DOUT lanes to ZU2CG.
- **PWM:** six 3.3 V laboratory PWM inputs -> protection/buffer -> ZU2CG.
- **Encoders:** two SSI/BiSS ports, each with clock and data differential pairs
  using THVD1450.
- **RS-485 / AUX / management:** one gated RS-485 path, 3.3 V AUX logic and I2C.
- **Independent hardware supervision:** input qualification, rail monitoring,
  explicit arm/re-arm state, window watchdog, physical AO disconnect and floating
  DUT-permit contact.

The board accepts **regulated 9–15 V SELV**. It is not a 48/67 V motor-bus input.

## 3. Schematic page map and design intent

The root plus 14 child sheets form the current 15-page design.

| Sheet | Purpose | Layout-critical intent |
|---|---|---|
| root | hierarchy and cross-sheet power/control | do not create new global nets for page-local wiring |
| 01_carrier_interface | AXU2CGB J12/J15 logical boundary | preserve 1.8 V J12 vs 3.3 V J15 domains |
| 03_peripheral_boundaries | PWM/AUX/I2C/RS-485 | connector protection before victim; 3.3 V lab logic only |
| 04_dac_0_3 | U20/U21, AO0..3 | keep DAC/reference/feedback compact |
| 05_dac_4_7 | U22/U23, AO4..7 | same geometry and return strategy as first DAC bank |
| 06_analog_outputs | AO connector and protection | short analog paths; J5 pins 9/10 are signal GND |
| 10_input_protection | fuse/reverse diode/TVS/eFuse/AON | physical current flow J101 -> F101 -> D101/D102 -> U101 -> C105 |
| 20_positive_rails | three bucks + LT3045 rails | minimize switch nodes; separate switchers from precision analog |
| 30_negative_reference | LT8330, LT3094, ADR4525 | compact Cuk loop; isolate negative switch node from ADC/DAC |
| 40_power_supervision | rail-valid detection / arm latch | power-qualified defaults must fail closed |
| 41_power_status | diagnostic status output | avoid powered-off backfeed into host |
| 50_watchdog_interlock | independent watchdog/interlock | watchdog must not depend on software continuing to execute |
| 60_dut_permit | floating PhotoMOS permit | floating contact; do not clamp to board GND |
| 70_adc_frontend | AD7606C-16 + 8 AI RC channels | protect at connector; compact REF/REGCAP and input RC |
| 80_encoder_phy | dual SSI/BiSS transceivers | coupled pairs, short stubs, optional 120-ohm termination |

## 4. Power tree and calculations

### 4.1 Input protection

Nominal input range: **9–15 V regulated SELV**.

`J101 -> F101 -> D101 -> D102 -> TPS259474L -> VIN_PROT`

- F101: 2 A Littelfuse 0451002.MRL backup fuse.
- D101: SS34 series reverse-polarity diode.
- D102: 16 V standoff TVS candidate.
- U101: TPS259474L latched circuit breaker/eFuse.
- RILM = 2.21 kOhm gives nominal trip:
  `I_trip ~= 3334 / 2210 ~= 1.51 A`.
- UV/OV divider 680 k / 60.4 k / 60.4 k gives approximately
  **7.95 V UV** and **15.91 V OV** at the eFuse input.
- PG threshold is approximately **7.94 V**.
- U102 TPS70933 supplies the always-on 3.3 V domain. Its EN is intentionally
  left open per the device's internal pull-up behavior; do not tie EN to the raw
  12 V input.

These are design calculations, not surge, startup, current-limit or thermal
qualification.

### 4.2 Positive switchers

Three AP63201WU-7 forced-PWM stages use
`Vout = 0.8 * (1 + Rupper/Rlower)`.

| Rail | Rupper/Rlower | Calculated nominal | L nominal |
|---|---:|---:|---:|
| 6V2_PRE | 67.3k / 10k | 6.184 V | 10 uH |
| 3V3_D | 31.2k / 10k | 3.296 V | 6.8 uH |
| 1V8_D | 12.4k / 10k | 1.792 V | 4.7 uH |

The original worst-case screen at VIN=15 V, f=450 kHz and L=80% nominal gave
approximate inductor ripple of **1.01 A / 1.05 A / 0.93 A** respectively.
Current system-level screening budgets have subsequently increased to
6V2_PRE=0.55 A, 3V3_D=0.70 A and 1V8_D=0.32 A; therefore the original peak-current
numbers must not be reused as a final release proof.

Each switching island should have a very small SW copper region and local return.
Do not route SW copper under ADC, DAC, VREF or low-noise LDO circuitry.

### 4.3 Positive low-noise rails

Two LT3045 stages produce the precision positive analog rails.

- 49.9 k SET -> about **4.990 V**.
- 52.0 k SET -> about **5.200 V**.
- 499 Ohm ILIM -> about **300 mA** nominal current limit.
- OUTS is Kelvin-connected to the output capacitor.
- Existing analytical dissipation checkpoints are about **0.239 W** and
  **0.118 W** for the reviewed loads; mounted-board temperature remains open.

### 4.4 Negative rail

U301 LT8330 uses the reviewed two-inductor inverting/Cuk path:

`VIN -> L301 -> SW_NEG -> C410 -> NEG_X -> L302 -> negative output`.

A 1 M / 147 k FBX network gives approximately **-6.242 V**. U302 LT3094 then
creates the low-noise **-5.2 V PVSS** rail; its exposed pad is negative IN,
**not GND**. The transfer capacitor C410 must tolerate VIN + |Vout| and ripple.

### 4.5 Reference and DAC rail-margin caveat

ADR4525 generates **VREF_2V5** for the four AD3542R devices. Do not assume
multiple internal DAC references may be paralleled.

The EDV checkpoint intentionally retains a supply/headroom conflict rather than
hiding it:

- calculated DAC rail span: about **10.622608 V** against the 10.6 V screen;
- minimum +/-5 V output headroom in the reviewed corner: about **0.088904 V**
  against a 0.2 V recommended target;
- one reviewed RSET feasibility screen had no overlap after dynamic reserve.

Therefore the power tree is adequate to continue Layout, but rail tolerance,
actual output span, settling/stability and temperature corners remain
fabrication/release blockers.

## 5. Power supervision and safe default behavior

Power qualification uses TPS3808 supervisors, LT3045/LT3094 PG signals and an
AON-powered TLV1701 negative-rail detector.

Nominal reviewed positive thresholds:

- 1V8 sense: about **1.7334 V**;
- 3V3 sense: about **3.13065 V**;
- 2.5 V reference sense: about **2.42595 V**;
- negative rail detector: approximately **-5.0 V**.

RAILS_OK falling clears the arm latch asynchronously. Restoring rails does not
automatically re-arm a previously asserted HIL_ARM; a new arm transition is
required. DAC reset has a hardware default asserted state.

The RTL heartbeat is progress-qualified rather than a free-running toggler:
completed Plant/I/O progress and a valid host lease are required. Default RTL
parameters currently target a WDI falling-edge interval of 5 ms, Plant/I/O
deadlines of 100 us and a 10 ms host lease. These are engineering defaults, not
a physical watchdog timing qualification.

**Procurement alert:** U501 is currently written in the schematic as
`TPS3430DRCR`, while TI currently exposes `TPS3430WDRCR` as the active
orderable 10-pin DRC device. The costed BOM marks this
`ORDERABLE_MPN_MISMATCH`; do not silently purchase/substitute until the exact
variant/timing/package equivalence is reviewed and the schematic/BOM are made
consistent.

## 6. AXU2CGB interface definition

### 6.1 J12 — 1.8 V Bank 66

J12 pins 3..34 are allocated as:

| Pins | Signals |
|---|---|
| 3..4 | DAC_SCLK, DAC_LDAC_N |
| 5..8 | DAC_CS0_N..DAC_CS3_N |
| 9..16 | DAC_SDIO0..DAC_SDIO7 |
| 17..20 | DAC_ALERT0_N..DAC_ALERT3_N |
| 21..28 | ADC_DOUT0..ADC_DOUT7 |
| 29..34 | ADC_SCLK, ADC_CS_N, ADC_SDI, ADC_CONVST, ADC_BUSY, ADC_RESET |

J12 physical pins 1/37/38 are GND, pin 2 is VCC5V, and pins 39/40 are carrier 3.3 V.
Those power pins are carrier facts, not permission to mix the 1.8 V GPIO bank with
3.3 V logic.

### 6.2 J15 — 3.3 V Bank 25/26

| Pins | Signals |
|---|---|
| 3..8 | PWM_UH, PWM_UL, PWM_VH, PWM_VL, PWM_WH, PWM_WL |
| 9..14 | ENC0_IO0..3, ENC0_DIR0..1 |
| 15..20 | ENC1_IO0..3, ENC1_DIR0..1 |
| 21..26 | AUX_IO0..AUX_IO5 |
| 27..29 | RS485_TX, RS485_RX, RS485_DE |
| 30..31 | MGMT_SCL, MGMT_SDA |
| 32..34 | HIL_ARM, HIL_WDI, HIL_FAULT_N |

The exact per-pin SoC-ball mapping is normative in
`hardware/carriers/axu2cgb/physical_pinout.csv`; the exact logical assignment
is normative in `assignments.csv`.

### 6.3 Mechanical registration

The pinned official ALINX DXF currently binds:

- host outline: **100 x 85 mm**;
- four mounting holes: 3.175 mm drill at
  (4.445,4.445), (95.5548,4.445), (4.445,80.5688), (95.5548,80.5688);
- J12 center: **(5.2578, 42.5069) mm**;
- J15 center: **(94.742, 42.5069) mm**;
- J12 pin 1: **(6.5278, 18.3769) mm**, right-column / low-y;
- J15 pin 1: **(93.4720, 66.6369) mm**, left-column / high-y.

Still open before a real mating footprint/stack can be released:

- exact AXU2CGB host connector MPN;
- exact mating connector MPN;
- mated stack height;
- carrier component/heatsink height keepouts.

Do not use a generic 2x20 footprint to create a manufacturable-looking board.

## 7. Analog outputs

Four AD3542RBCPZ16 provide eight 16-bit DAC channels. The exact CP-28-15
land pattern is source-bound to the official ADI evaluation-board evidence and
must not be replaced by a generic 4x4 QFN footprint.

The current analog output chain uses 52.3 Ohm starting-value source resistors and
ADG5412F protected switches. AO disconnect means **high impedance**, not a
guaranteed zero-voltage safe state. Cable load, DAC stability, settling,
calibration and actual DUT neutral behavior remain to be measured.

J5 is Phoenix 1844294, 10 positions: AO0..AO7 plus two signal grounds.
Those grounds are not chassis/PE.

## 8. Analog inputs

U801 is AD7606C-16BSTZ:

- AVCC = +5V0_DAC;
- VDRIVE = 1V8_D;
- internal reference selected;
- serial/software mode;
- CONFIG register 0x02 is written/read back before eight-DOUT operation;
- J801 provides eight low-energy single-ended channels;
- each input pair uses two 100 Ohm series legs and 1 nF differential capacitance.

This frontend is a **laboratory low-energy +/-10 V candidate**, not a 24 V PLC
input or qualified field-surge interface. The simplified 100 Ohm / 1 MOhm path
can contribute roughly 100 ppm uncalibrated gain error; source impedance,
anti-alias behavior, calibration, 16-bit accuracy and physical 1 MSPS operation
remain qualification items.

## 9. PWM, encoders, RS-485 and auxiliary I/O

Six PWM channels use a SN74LVC541A input buffer and hardware default pull-downs.

Each encoder port has clock and data differential pairs through THVD1450.
The intended SSI/BiSS roles are directional; generic `inout` at the carrier
contract does not mean arbitrary pin swapping. These ports do not supply encoder
power and are not a general ABZ / arbitrary 3-wire or 4-wire SPI interface.

RS-485 also uses THVD1450 and is safety-permit gated. 120 Ohm termination is
jumper-selectable and defaults open. AUX and I2C are 3.3 V logic. None of these
interfaces is isolated or suitable for direct motor-phase, gate-drive or 24 V PLC
connection.

## 10. Interlock and DUT permit limitations

J501 is a two-wire 3.3 V dry-contact service/interlock interface.
J701 uses AQY212GS as a floating normally-open DUT-permit contact.

For both two-wire contact semantics, a cross-line cable short can look like a
closed contact. Rev.B explicitly accepts this as a **non-safety residual risk**
for laboratory HIL use. These interfaces are not STO, redundant safety outputs
or cable-short fail-safe channels.

## 11. PCB Layout rules

Target layer roles:

| Layer | Role |
|---|---|
| L1 | components + signals |
| L2 | continuous GND reference |
| L3 | power distribution + slow signals |
| L4 | signals |
| L5 | continuous GND reference |
| L6 | components + signals |

Use continuous reference planes with functional zoning; do not hard-split
AGND/DGND. Fast or precision signals must never cross a reference-plane void.

Baseline non-fabricator-specific geometry:

- default clearance: 0.20 mm;
- default signal width: 0.20 mm;
- default via: 0.60 / 0.30 mm;
- copper-to-edge: 0.30 mm;
- VIN_RAW/VIN_PROT: pour or >=1.00 mm trace;
- medium-current rails: pour or >=0.50 mm trace.

Routing priority:

1. switcher hot loops and power current paths;
2. precision reference / DAC / ADC analog;
3. external differential pairs;
4. fast DAC/ADC digital groups;
5. safety handshake/control;
6. remaining low-speed signals.

Controlled-impedance width/gap is **not frozen** until a PCB fabricator stackup is
selected. Add a nearby GND stitching via at high-speed layer transitions and
place ESD return vias immediately beside the connector-side protection device.

## 12. Procurement and substitution policy

The complete grouped procurement snapshot is `bom/revb-costed.csv`.
It covers all 439 on-board physical refs: **431 populated + 8 DNP = 139 grouped
BOM lines**.

Pricing states mean:

- `EXACT_QUOTE`: source-bound MPN with a dated authorized-distributor/manufacturer
  small-quantity price.
- `CANDIDATE_QUOTE`: exact engineering candidate already present in qualification
  documents, but electrical/thermal qualification remains open.
- `ORDERABLE_MPN_MISMATCH`: purchasing identity is inconsistent with the schematic;
  release-blocking until resolved.
- `BUDGET_GENERIC`: value/package are fixed but manufacturer MPN is not; price is
  an engineering allowance, not a purchase approval.
- `DNP`: not fitted and zero stuffed cost.

Do not replace the following merely for cost or availability without explicit
design review: AD3542RBCPZ16 speed/grade/package, AD7606C-16 interface variant,
ADG5412F protected switch family, LT3045/LT3094/LT8330 analog power devices,
TPS259474L eFuse variant, ADR4525 grade, C105 exact land-pattern part, the reviewed
connector mechanical parts, or any part that changes a safety/default state.

## 13. First-board bring-up sequence

### 13.1 Before power

- verify PCB revision, assembly option and connector pin-1 orientation;
- inspect CP-28-15 DAC joints, exposed-pad packages, polarity parts and C105;
- measure resistance from input/rails to GND and investigate unexpected shorts;
- confirm J12/J15 mechanical registration before mating to AXU2CGB;
- leave DUT power stage and external AO/permit connections disconnected.

### 13.2 Power-only qualification

- use a current-limited laboratory supply at the low end of the 9–15 V input
  range; increase current limit deliberately while monitoring for abnormal draw;
- verify 3V3 AON and eFuse INPUT_OK behavior;
- verify 6V2_PRE, 3V3_D, 1V8_D, +5V0_DAC, +5V2_PVDD, -6V2_PRE, -5V2_PVSS and
  VREF_2V5 at the dedicated test points;
- check rail startup order, overshoot, ripple and power-down behavior with an
  oscilloscope before enabling analog outputs;
- verify RAILS_OK, arm latch and DAC_RESET_N fail closed.

Do not defeat U101's protection or raise the bench limit above the design intent
merely to make a failing board start.

### 13.3 Digital bring-up

- start DAC/ADC serial interfaces at the reviewed **10 MHz bring-up rate** before
  increasing clock rates;
- verify ADC CONFIG 0x02 write/readback, BUSY/CONVST and eight DOUT lanes;
- verify watchdog timing and explicit re-arm behavior;
- verify HIL_FAULT_N powered/unpowered behavior and absence of host backfeed;
- exercise PWM, encoder and RS-485 pins with low-energy fixtures only.

### 13.4 Analog bring-up

- keep AO physically disconnected from a real DUT;
- command midscale/known codes and measure all eight channels into high impedance;
- validate offset/gain/settling and switch disconnect behavior;
- feed known low-energy AI values and verify all eight ADC channels;
- only after this baseline, run load/cable/stability tests.

### 13.5 DUT connection

Connect a real DUT only after its adapter profile records neutral bias, permit
voltage/current/leakage, cable-open/cable-short behavior and maximum acceptable
disable time. Perform low-energy fault injection before any motor-power
closed-loop test.

## 14. Fabrication/release gates still open

Layout is authorized; fabrication and release are not. The following still need
raw evidence tied to the exact board/source revision:

- exact J12/J15 mating connector MPN, stack height and height keepouts;
- MLCC DC-bias/temperature/aging/RMS/ESR evidence;
- XAL L(I,T), AC/core/winding loss and startup/fault saturation;
- real DUT adapter thresholds, leakage and shutdown timing;
- partial-power/backfeed;
- assembled-board thermal;
- low-energy fault-injection fixture;
- Vivado raw I/O DRC plus functional STA/CDC;
- EMC, power-down, fault injection and FOC physical closed-loop acceptance.

Passing ERC, SPICE, unit tests or PCB DRC is not a manufacturing or functional
safety certificate.

## 15. Related detailed evidence

- Power equations: `docs/design/native-power-stage-calculations.md`
- Power supervision: `docs/design/native-power-supervision.md`
- Electrical verification: `sim/power/README.md`
- ADC/PHY: `docs/review/revb-peripherals/README.md`
- Safety chain: `docs/review/revb-safety/README.md`
- Layout: `docs/review/revb-layout/README.md`
- Procurement/cost methodology: `docs/design/revb-procurement-and-cost.md`
