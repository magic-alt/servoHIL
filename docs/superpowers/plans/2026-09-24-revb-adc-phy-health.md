# Rev.B ADC/PHY and health implementation plan

> Inline execution; preserve separate commits for independently testable work.

**Goal:** implement the remaining allocated interfaces and useful-system heartbeat
without granting layout or production qualification.
**Architecture:** one ZU2CG, native ADC/PHY sheets, independent pin oracles,
synchronous lease/deadline watchdog producer, source-bound electrical screening.
**Tech stack:** KiCad, Python unittest/ngspice, synthesizable SystemVerilog/Icarus.
**Spec:** ../specs/2026-09-24-revb-adc-phy-health.md

## Global constraints

- Base main 37a4463; no changes to Rev.A, second FPGA, PCB or release-gate PASS.
- Native KiCad is source of truth; normal CI is read-only.
- No fabricated DUT, board, EMC, thermal, timing or functional-safety evidence.
- Existing 64-signal pin allocation unchanged; CAN/EtherCAT not silently added.
- Preserve healthy disarmed heartbeat; recovery alone never re-arms.

## Review focus

Duplicate lease/progress must not keep a failed system alive; held-high ARM and
reset recovery must not enable; partial power and bidirectional contention must
remain explicit; ADC clamp/RC claims must not substitute for field protection;
all qualification results must distinguish simulation from physical evidence.

## Stage 1 — baseline and runtime heartbeat

Files: rtl/revb/health_heartbeat.sv, tests/rtl/tb_health_heartbeat.sv,
tests/test_health_rtl.py, .github/workflows/revb-runtime-verification.yml.
Interface: one synchronous clk/reset, session-start event, sequence-bearing Plant/
I/O/lease transactions, ARM request and runtime fault; outputs WDI, ARM, ready and
latched reason bits. Port-level assumptions are documented with the module.

- [ ] Record exact baseline source and test environment.
- [ ] Write missing-core and behavioural tests; observe failure.
- [ ] Implement bounded deadline/sequence state; test startup, 5ms falling cadence,
      duplicated activity, missing progress, lease expiry, sequence wrap,
      fault priority, held-high ARM and explicit session recovery.
- [ ] Commit tested RTL and contract. No board/top-level integration claim.

## Stage 2 — native ADC and PHY

Files: native ADC/AFE/PWM/encoder/RS485 sheets and library; explicit interface
header replacement; tools/check_native_peripherals.py and mutation regressions.

- [ ] Transcribe vendor pin/mode/supply tables independently of drawing helper.
- [ ] Write source/netlist tests that reject the old reserved-only interface.
- [ ] Populate actual parts, passives, connectors and defaults with continuous
      local wiring. Freeze power/safety/DAC pins outside the declared delta.
- [ ] Run actual KiCad export/ERC, independent oracles, mutations and PDF review.
- [ ] Commit native source; remove any temporary source writer from active tree.

## Stage 3 — electrical and qualification handoff

Files: peripheral electrical screening, its tests, review/acceptance document,
README status update. Gates JSON remains unchanged.

- [ ] Bind calculations to actual native values; report ADC rail/current headroom,
      RC loading/bandwidth, PHY loaded-driver current and total new rail budget.
- [ ] Reject invalid/nonfinite inputs and show missing evidence as BLOCKED.
- [ ] Run full local/CI regression plus source-bound EDV. Record exact SHA/tool
      versions and identify every test not executed on real hardware.
- [ ] Publish source/native evidence and current status in a new Draft PR.

## Execution ledger

2026-09-24: PR21 is already merged. A new branch is based on main; no reopened or
rewritten PR21. Clarify the existing reserved interface contract before drawing.
Ruling: implement ADC/PHY engineering design under the user's renewed request;
keep power/safety qualification open and continue blocking physical layout.
