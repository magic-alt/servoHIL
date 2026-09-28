# Rev.B schematic closure

**Date:** 2026-09-28  
**Scope:** native KiCad source closure only; no PCB/Layout authorization.

## What is closed in source

The Rev.B root project contains **15 functional sheets** and 439 physical
`in_bom=yes && on_board=yes` instances by the source audit. Purchased AXU2CGB
J12/J15 interfaces are schematic boundaries, not expansion-board placements.

This closure includes:

- connector protection placed in the owning interface sheets (`03/06/50/70/80`) so page-local nets remain local;
- exact local package bindings where the reviewed manufacturer package has a matching
  project-local KiCad land pattern: LT3045/LT3094 MSOP-12+EP, TPS3430 DRC VSON,
  LVC1G74 DCT, AQY212GS SOP-4, Littelfuse 451 fuse, XAL5030 and the reviewed
  TPS259474 RPW/XAL5050 land-pattern bindings;
- deterministic R/C footprints on all four AD3542R pages while keeping the converter
  CP-28-15 land pattern explicitly open;
- a fail-closed package/BOM audit in `tools/check_revb_schematic_closure.py`;
- connector-side clamps for low-energy AI/AO, 3.3 V logic, SSI/BiSS, RS-485 and the
  dry-contact interlock;
- independent oracle assertions for the added protection-device pins and packages.

## Deliberate remaining physical bindings

The only blank physical footprints allowed are defined in
`hardware/revB/schematic_open_items.json`. At this checkpoint there are **9**:

- exact land pattern still open:
  - U20, U21, U22, U23 — AD3542RBCPZ16, Analog Devices CP-28-15;
- mechanical/connector choices that need the real enclosure/cable/DUT contract:
  - J101 — 12 V field connector;
  - SW101 — power-reset switch;
  - J5 — AO connector;
  - J501 — 3.3 V dry-contact service connector;
  - J701 — floating DUT-permit connector.

U101 and L201/L202/L301/L302 are no longer blank-footprint blockers. Their package/
land-pattern bindings are source-closed, but that **does not** qualify the components
electrically, thermally or mechanically for production.

L203 likewise uses the exact official `Inductor_SMD:L_Coilcraft_XAL5030` footprint.
None of these footprint assignments establish L(I,T), AC/core loss, startup saturation,
board temperature rise, placement clearance or manufacturability.

## AD3542R package evidence boundary

The AD3542RBCPZ16 manufacturer ordering guide identifies a 28-lead LFCSP,
4 mm × 4 mm × 0.95 mm package, option **CP-28-15**. The checked-in schematic keeps
U20..U23 blank until a reviewed land pattern is vendored and independently checked
against the package/CAD source. A visually similar generic 4 mm QFN/LFCSP footprint
must not be substituted merely to reduce the blocker count.

## Protection boundary

The DUT-permit protection intentionally does not clamp the floating
`DUT_PERMIT_A/B` contact to board ground. Cross-line protection must be selected only
after the actual DUT voltage, leakage, cable and isolation requirements are bound.

All connector protection parts are source-level topology decisions. Physical
qualification still requires connector-entry placement review, short return paths,
partial-power/backfeed tests, cable/common-mode conditions, IEC ESD/surge testing and
raw evidence.

## Electrical qualification boundary

The XAL5050/XAL5030 candidate MPNs and their catalog Isat/Irms/DCR values are screening
inputs, not board qualification. The remaining magnetic gate requires, at minimum:

- supplier L-versus-DC-bias and temperature evidence;
- AC/core plus winding-loss evaluation at the actual switching waveforms;
- startup/short-circuit/current-limit saturation analysis;
- exact land-pattern/height/clearance verification;
- mounted-board temperature-rise evidence.

MLCC candidates similarly remain blocked on exact-MPN DC-bias evidence, aging,
temperature, RMS-current/ESR where applicable, and real load/startup transients.
Analytical EDV success must not be converted into a production PASS.

## Release boundary

`hardware/revB/gates.json:layout_allowed` remains `false`.
The following cannot be inferred from passing ERC, source audits or RTL simulation:

- real DUT neutral/permit thresholds, leakage, cable-fault response or shutdown time;
- board thermal, MLCC bias/aging and magnetic loss/saturation qualification;
- DAC stability/accuracy and ADC analog precision/sample-rate qualification;
- powered-off backfeed and cable transient behavior;
- Vivado STA/IO DRC until reports bound to the exact source/top/part/XDC are imported;
- EMC, fault injection or FOC closed-loop acceptance on physical hardware.

The next engineering step is therefore evidence/physical binding, not adding more
functional schematic pages.
