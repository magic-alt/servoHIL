# Rev.B Electrical Design Verification — implementation ledger

**Goal:** execute the user-approved calculation → simulation → component-selection verification stage against native Rev.B, without changing board topology or starting layout.
**Base:** main bc08c999843a1eacb0794f673f65e532ac1148c1 (PR19 merged).
**Architecture:** read native KiCad component values; keep assumptions/provenance separate; run portable, explicitly non-vendor SPICE power-stage/envelope cases in ngspice; prepare LTspice vendor workflows without redistributing vendor models. No simulator result alone may release hardware.
**Execution:** inline, section-by-section commits and remote GitHub Actions because the current local runtime cannot start. No claims of local simulation execution.

## Constraints
- Single SoC, SoM UNBOUND, archive unchanged, no ADC/PHY expansion or PCB layout.
- Do not regenerate native schematics, alter feedback values to make checks green, or rewrite release gates.
- Analytical screening, behavioral/power-stage SPICE, vendor-macro simulation and bench evidence are distinct.
- Missing model/license/curve means BLOCKED, not assumed PASS. Exact source/deck/model hashes accompany results.
- Preserve original GitHub↔Notion tests; read-only CI.

## Tasks / commit checkpoints
- [ ] A: RED tests, then native-value-bound worst-case / thermal / MLCC / magnetic screening.
- [ ] B: runnable ngspice startup, load-step and shutdown benches; strict measure parser; raw logs, waveform data, hash manifest.
- [ ] C: LTspice vendor acquisition/bench instructions, exact inductor candidates and capacitor derating evidence requirements.
- [ ] D: run existing + new tests, inspect actual simulation outputs, publish reviewed results and PR; keep layout blocked.

## Acceptance
Changing a used native resistor/inductor must change the derived calculations, not silently leave stale constants. Reject invalid/nonfinite inputs, missing measures, missing ngspice and absent DC-bias evidence. Test the known +/-5.2V full-temperature tolerance issue without changing the schematic. A passing automation job means the analysis ran, not that the electrical design passed. '--strict-design' must fail while blockers exist.

## Review focus
Thermal Rtheta/efficiency assumptions are not package guarantees. AP63201 has only typical oscillator frequency: 450kHz sensitivity is not a guaranteed minimum. Cuk switch carries the sum of two currents and its 1A rating is not output capability. Initial SET accuracy is not full-temperature accuracy. Power-stage open-loop results do not validate chip control/stability/current limiting. Vendor IP is not committed or uploaded as an artifact.
