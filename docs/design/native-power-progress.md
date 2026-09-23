# PR17 native power implementation ledger

Scope: the user's approved single-SoC AXU2CGB expansion, native editable KiCad,
and real input -> regulated rails -> DAC supply/reference wiring. No PCB layout.
Branch: feat/revb-native-power-safety-dac.

## Recovery checkpoint
At 1baf66cf the remote PR had only devtool preparation, not the native schematic.
Earlier local screenshots are not a committed deliverable. This work adds and
commits each physical circuit section independently. Runtime execution is in
GitHub Actions, and outputs become native source, not just CI-only artifacts.

## Stage plan
1. Input: fuse/series reverse diode/TVS, TPS259474L latched circuit breaker,
   UVLO/OVLO/PGTH/ILM/dVdt/ITIMER, TPS70933 AON supply.
2. Positive rails: 6.2V preregulator, 3.3V and 1.8V bucks, +5.0/+5.2V low-noise LDOs.
3. Negative/reference: LT8330 dual-inductor inverting stage, LT3094 -5.2V,
   ADR4525 and explicit DAC decoupling/power paths.
4. Rail supervision: regulator PG and digital supervisors, power-good reset
   interlock and native full-hierarchy ERC. Full DUT safety remains separately qualified.

Each stage is a one-shot, refuses to overwrite existing child sheets, and is
committed after KiCad parses its actual netlist and pin-level checks pass.
A partial-stage parse is not full-board ERC or electrical qualification.

## Input design facts
TPS259474L is the adjustable-OVLO CIRCUIT-BREAKER/latch variant, not the active
current-limit TPS259470L. RILM=2.21k -> nominal 3334/2210=1.51 A trip setting.
Input pin divider 680k/60.4k/60.4k: UV~7.95 V, OV~15.91 V at VIN_EFUSE.
PGTH 56.2k/10k: ~7.94 V. Input rating remains regulated 9-15 V SELV, NOT a motor bus.
TPS70933 DBV pin 3 EN is OPEN per datasheet internal current pull-up: NEVER tie
it directly to 12 V (7 V absolute maximum). Output capacitance 4.7uF rated16V
requires >=2.2uF effective capacitance. AON budget <=15mA.

## Primary sources checked
- TI TPS25947 SLVSFC9C (May 2026), variant table p4, pin table pp5-6, design equations pp43-46: https://www.ti.com/lit/ds/symlink/tps25947.pdf
- TI TPS709 SBVS186H, DBV pins p3, output capacitance, EN open guidance p13: https://www.ti.com/lit/ds/symlink/tps709.pdf
- Diodes AP63200/1/3/5 DS41326 Rev3-2 (Nov2024): https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf
- ADI LT3045 RevD, LT3094 RevB, LT8330 and AD3542R RevC.

All thermal, surge, effective-capacitance, loop stability and board-revision
measurements remain OPEN. Do not relabel candidate calculations as bench PASS.
