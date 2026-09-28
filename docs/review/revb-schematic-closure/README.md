# Rev.B schematic closure

**Date:** 2026-09-28  
**Scope:** native KiCad source closure only; no PCB/Layout authorization.

## What is closed in source

The Rev.B root project now contains 16 sheets and 439 physical
`in_bom=yes && on_board=yes` instances by the source audit. Purchased AXU2CGB
J12/J15 interfaces are schematic boundaries, not expansion-board placements.

This closure adds:

- exact local package bindings where the manufacturer package has a reviewed matching
  KiCad land pattern: LT3045/LT3094 MSOP-12+EP, TPS3430 DRC VSON, LVC1G74 DCT,
  AQY212GS SOP-4, Littelfuse 451 fuse and XAL5030;
- deterministic R/C footprints on all four AD3542R pages while keeping the converter
  CP-28-15 land pattern explicitly open;
- a fail-closed package/BOM audit in `tools/check_revb_schematic_closure.py`;
- `90_connector_protection.kicad_sch` with connector-side clamps for low-energy AI/AO,
  3.3 V logic, SSI/BiSS, RS-485 and the dry-contact interlock;
- independent oracle assertions for every added protection-device pin and package.

## Deliberate remaining physical bindings

The only blank physical footprints allowed are defined in
`hardware/revB/schematic_open_items.json`. At this checkpoint there are 14:

- exact/special land patterns: U101 TPS259474 RPW, U20..U23 AD3542R CP-28-15;
- XAL5050 footprint/thermal binding: L201, L202, L301, L302;
- mechanical/connector choices that need the real enclosure/cable/DUT contract:
  J101, SW101, J5, J501, J701.

L203 is no longer in this list: its XAL5030 candidate now uses the exact official
`Inductor_SMD:L_Coilcraft_XAL5030` footprint. This does **not** qualify its
L(I,T), AC/core loss, startup saturation or board temperature rise.

## Protection boundary

The connector-protection page intentionally does not clamp the floating
`DUT_PERMIT_A/B` contact to board ground. Its cross-line protection must be selected
only after the actual DUT voltage, leakage, cable and isolation requirements are bound.

All protection parts are source-level topology decisions. Physical qualification still
requires connector-entry placement review, short return paths, partial-power/backfeed
tests, cable/common-mode conditions, IEC ESD/surge testing and raw evidence.

## Release boundary

`hardware/revB/gates.json:layout_allowed` remains `false`.
The following cannot be inferred from passing ERC, source audits or RTL simulation:

- real DUT neutral/permit thresholds, leakage, cable-fault response or shutdown time;
- board thermal, MLCC bias/aging, XAL5050 magnetic loss/saturation;
- DAC stability/accuracy and ADC analog precision/sample-rate qualification;
- powered-off backfeed and cable transient behavior;
- Vivado STA/IO DRC until a report bound to the exact source/top/part/XDC is imported;
- EMC, fault injection or FOC closed-loop acceptance on physical hardware.

The next engineering step is therefore evidence/physical binding, not adding more
functional schematic pages.
