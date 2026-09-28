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
- exact AD3542RBCPZ16 CP-28-15 bindings on U20..U23 using a locally vendored
  footprint reconstructed and independently checked against the official
  EVAL-AD3542RFMCZ IPC-356/top-copper/solder-mask/paste evidence;
- a fail-closed package/BOM audit in `tools/check_revb_schematic_closure.py`;
- connector-side clamps for low-energy AI/AO, 3.3 V logic, SSI/BiSS, RS-485 and the
  dry-contact interlock;
- independent oracle assertions for the added protection-device pins and packages.

## Deliberate remaining physical bindings

The only blank physical footprints allowed are defined in
`hardware/revB/schematic_open_items.json`. At this checkpoint there are **5**,
all requiring the real mechanical/enclosure/cable/DUT contract:

- J101 — 12 V field connector;
- SW101 — power-reset switch;
- J5 — AO connector;
- J501 — 3.3 V dry-contact service connector;
- J701 — floating DUT-permit connector.

U20..U23 are no longer blank-footprint blockers. The AD3542R package review is
source-bound through:

- `hardware/revB/ad3542r_footprint_evidence.json`;
- `hardware/revB/evidence/ad3542r/u1_geometry_review.json`;
- `Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R`.

The official EVAL BOM binds U1 to AD3542RBCPZ16. The official IPC-356 contains
exactly pins 1..28, and the EVAL top copper/paste/mask data defines a 28-pad
perimeter land pattern at 0.40 mm pitch with **no center exposed pad**. The local
footprint reproduces those copper/paste dimensions and explicit mask apertures.
A generic nominal 4 mm QFN is still not an acceptable substitute.

U101 and L201/L202/L301/L302 are likewise no longer blank-footprint blockers.
Their package/land-pattern bindings are source-closed, but that **does not**
qualify the components electrically, thermally or mechanically for production.

L203 uses the exact official `Inductor_SMD:L_Coilcraft_XAL5030` footprint.
None of these footprint assignments establish L(I,T), AC/core loss, startup
saturation, board temperature rise, placement clearance or manufacturability.

## AD3542R package evidence boundary

The AD3542R package blocker is now closed at source level, not by package-name
guessing. The review pins the exact manufacturer artifact SHA-256 values and retains
the U1 IPC-356/Gerber geometry needed to reproduce the footprint.

This closure proves the checked-in U20..U23 land-pattern binding. It does **not**
qualify DAC accuracy, dynamic settling, output stability, thermal behavior, EMC,
fabrication process or the finished PCB.

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
