# Rev.B Electrical Design Verification — implementation ledger

**Goal:** execute the user-approved calculation → simulation → component-selection verification stage against native Rev.B, without changing board topology or starting layout.
**Base:** main bc08c999843a1eacb0794f673f65e532ac1148c1 (PR19 merged).
**Architecture:** read native KiCad component values; keep assumptions/provenance separate; run portable, explicitly non-vendor SPICE power-stage/envelope cases in ngspice; prepare LTspice vendor workflows without redistributing vendor models. No simulator result alone may release hardware.
**Execution:** inline, section-by-section remote commits. The continuation recovered an isolated local checkout and a hash-identified ngspice-42 executable from CI, then ran local numerical/TDD regressions. Full matrices also run in read-only GitHub Actions. Native KiCad export/ERC evidence comes from CI; local checks consume byte-matched native source/netlists.

## Constraints
- Single SoC, SoM UNBOUND, archive unchanged, no ADC/PHY expansion or PCB layout.
- Do not regenerate native schematics, alter feedback values to make checks green, or rewrite release gates.
- Analytical screening, behavioral/power-stage SPICE, vendor-macro simulation and bench evidence are distinct.
- Missing model/license/curve means BLOCKED, not assumed PASS. Exact source/deck/model hashes accompany results.
- Preserve original GitHub↔Notion tests; read-only CI.

## Tasks / commit checkpoints
- [x] A: RED tests, then native-value-bound worst-case / thermal / MLCC / magnetic screening.
- [x] B: runnable ngspice startup, load-step and shutdown benches; strict measure parser; raw logs, waveform data, hash manifest.
- [x] C: LTspice vendor acquisition/bench instructions, exact inductor candidates and capacitor derating evidence requirements.
- [x] D: run existing + new tests, inspect actual simulation outputs, publish reviewed results and PR; keep layout blocked.

## Acceptance
Changing a used native resistor/inductor must change the derived calculations, not silently leave stale constants. Reject invalid/nonfinite inputs, missing measures, missing ngspice and absent DC-bias evidence. Test the known +/-5.2V full-temperature tolerance issue without changing the schematic. A passing automation job means the analysis ran, not that the electrical design passed. '--strict-design' must fail while blockers exist.

## Review focus
Thermal Rtheta/efficiency assumptions are not package guarantees. AP63201 has only typical oscillator frequency: 450kHz sensitivity is not a guaranteed minimum. Cuk switch carries the sum of two currents and its 1A rating is not output capability. Initial SET accuracy is not full-temperature accuracy. Power-stage open-loop results do not validate chip control/stability/current limiting. Vendor IP is not committed or uploaded as an artifact.

## Continuation rulings and evidence
- A-D above mean screening infrastructure, source-backed candidates, preparation workflows and reviewed automation, NOT completed physical qualification.
- Preserve RSET and native topology. Full-condition DAC limits are a real unresolved design issue; do not tune values merely to pass a check.
- Fix numerical clock edges rather than relaxing the 0.001 duty gate; verify against real ngspice and a half-timestep case.
- Individual Cuk inductor current reversal is not alone the DCM criterion. Check diode-current sum, flag invalid CCM points and retain open-loop output failures.
- Candidate-specific +/-20% capacitor tolerance must not inherit the generic +/-10% scenario. Exact part curves and original-file/CSV hashes are separate evidence.
- A killed/partial/stale simulator run cannot qualify as complete; all 25 native-bound cases and their log/artifact integrity must be checked.
- The local git history is an isolated test snapshot. Upstream commit identities are recorded in the review checkpoint, not substituted by local SHAs.
- Full repository 123/123 tests and synchronization 15/15 tests passed. Native XML came from a separately hashed CI artifact after 37 source files matched exactly.

Detailed commands, model limitations and curve/vendor workflow:
`sim/power/README.md`. Immutable reviewed run identities and open findings:
`docs/review/revb-edv/README.md`.

### Remaining qualification gates (not completed)
- [ ] Resolve DAC full-condition supply/headroom conflict.
- [ ] Execute exact manufacturer closed-loop models, including light-load/short-circuit mode and stability review.
- [ ] Obtain actual MLCC DC-bias/lifetime evidence, close C105 MPN, C410 lifecycle and Cuk effective-C targets.
- [ ] Close magnetic AC/core loss, temperature/current derating and footprint/height verification.
- [ ] Close input protection energy, partial-power backfeed and shutdown/discharge behavior.
- [ ] Independent board thermal/transient measurements; separate layout authorization.
