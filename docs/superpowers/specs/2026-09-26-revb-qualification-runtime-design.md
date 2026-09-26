# Rev.B Qualification Closure and Runtime Integration Design

**Date:** 2026-09-26
**Base:** main `d3a99ba505ff94d59d5f5ea56f08b64839893fe6`
**Status:** engineering continuation; no layout or production release

## Intent

Continue Rev.B in the order requested by the project owner:

1. close as much of the power / thermal / MLCC / magnetics / new-load qualification as can be proven from source-bound analysis;
2. bind an actual DUT adapter profile for neutral bias, permit threshold/leakage, cable-failure behavior and maximum shutdown budget;
3. complete ADC initialization/acquisition plumbing and connect real Plant/I/O completion plus host lease semantics to the health producer;
4. provide Vivado synthesis/IO/timing scripts and an evidence-import gate for real implementation reports;
5. only after final schematic/BOM/package/connector, partial-power and DUT-inhibit evidence are complete may Layout be considered.

## Non-negotiable release rules

- `hardware/revB/gates.json:layout_allowed` stays `false` in this work.
- Missing physical evidence is a blocker, never silently converted to PASS.
- AO disconnect means high impedance, not zero volts.
- A single AQY212GS permit contact is not redundant STO and is not SIL/PL certification.
- Catalog ratings, simulation, ERC and timing models are not board-level qualification.
- No DUT profile field is populated with an invented value. Unknown real-DUT values remain null and strict qualification must fail.
- No CAN/EtherCAT PHY is added because the current 64-signal contract has no dedicated allocation for it.

## Architecture

### A. Qualification manifest

Add a source-bound qualification aggregator that separates:
- analytical evidence;
- manufacturer-candidate evidence;
- physical-evidence-required blockers;
- Vivado-evidence-required blockers;
- DUT-profile-required blockers.

The aggregator may report `ANALYTICAL_PASS` for a subcheck, but the board result remains `BLOCKED` until all mandatory physical and tool-generated evidence is bound.

### B. DUT adapter profile

Add a machine-readable DUT adapter profile with explicit fields:
- AO neutral target/min/max voltage;
- AO source/bias impedance;
- permit asserted and inhibited thresholds;
- maximum permit input leakage;
- cable-open interpretation;
- cable-short interpretation;
- maximum end-to-end disable time;
- maximum allowed AO residual current/voltage after disconnect;
- evidence references and measured-at metadata.

The checked-in default profile is intentionally unbound. A validator rejects absent/nonfinite/physically inconsistent values and will not authorize layout.

### C. Component qualification

Retain current TDK/Coilcraft candidates but strengthen lifecycle and evidence metadata.

Current manufacturer facts checked on 2026-09-26:
- TDK `C3225X7R1C226M250AC`: Production, 22 uF +/-20%, 16 V, X7R, 1210.
- TDK `C3225X7R1E106K250AC`: Production, 10 uF +/-10%, 25 V, X7R, 1210.
- TDK commercial `C3225X7R1H105K160AA` is NRND; replace the candidate with production automotive-grade `CGA6L2X7R1H105K160AA`, 1 uF +/-10%, 50 V, X7R, 1210, AEC-Q200.
- Coilcraft XAL candidates remain catalog-screening candidates only. AC/core loss and L(I,T) must remain physical/vendor-curve blockers until raw evidence is imported.

Do not copy graph pixels as numerical truth. A future curve importer must require exact MPN plus source hash and measured/reference status.

### D. ADC runtime

Implement a synthesizable AD7606C-16 serial-control/acquisition core with:
- reset and software-mode entry;
- CONFIG 0x02 write for eight-lane output;
- register readback verification before acquisition enable;
- explicit conversion request/BUSY completion;
- eight 16-bit lane capture with channel identity ordering;
- completed-sample sequence output only after valid capture.

The core remains separate from analog calibration and alias-filter qualification.

### E. Health integration

Add a wrapper that consumes completed ADC sample sequence / completed Plant sequence / renewed host lease sequence and drives the existing `health_heartbeat` core. Command submission must never count as completion.

### F. Vivado evidence

Add Tcl/XDC checks and an importer for real Vivado reports:
- synthesis success;
- IO DRC;
- unconstrained path count = 0 for the reviewed clock domain;
- WNS >= 0 ns;
- WHS >= 0 ns;
- exact top, part, source SHA and XDC digest.

No fake report is checked in as PASS. In CI without Vivado, parser tests may pass while the `vivado_timing` and `vivado_io_drc` gates remain NOT_RUN.

## Completion boundary for this branch

This branch may:
- close code/analysis defects;
- bind improved component candidates;
- create strict evidence schemas and validators;
- implement and simulate ADC/runtime integration;
- prepare reproducible Vivado batch scripts.

This branch may **not** claim:
- actual DUT adapter qualification unless real values/evidence already exist;
- measured shutdown timing;
- EMC/thermal/partial-power board PASS;
- production BOM approval;
- PCB layout permission.
