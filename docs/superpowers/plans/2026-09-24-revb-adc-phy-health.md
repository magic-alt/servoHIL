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
I/O/lease transactions, ARM request and runtime fault; outputs WDI, ARM, healthy and
latched reason bits. Port-level assumptions are documented with the module.

- [x] Record exact baseline source and test environment.
- [x] Write missing-core and behavioural tests; observe failure.
- [x] Implement bounded deadline/sequence state; test startup, 5ms falling cadence,
      duplicated activity, missing progress, lease expiry, sequence wrap,
      fault priority, held-high ARM and explicit session recovery.
- [x] Commit tested RTL and contract. No board/top-level integration claim.

## Stage 2 — native ADC and PHY

Files: native ADC/AFE/PWM/encoder/RS485 sheets and library; explicit interface
header replacement; tools/native_peripheral_rules.py and mutation regressions.

- [x] Transcribe vendor pin/mode/supply tables independently of drawing helper.
- [x] Write source/netlist tests that reject the old reserved-only interface.
- [x] Populate actual parts, passives, connectors and defaults with continuous
      local wiring. Freeze power/safety/DAC pins outside the declared delta.
- [x] Run actual KiCad export/ERC, independent oracles, mutations and PDF review.
- [x] Commit native source; remove any temporary source writer from active tree.

## Stage 3 — electrical and qualification handoff

Files: peripheral electrical screening, its tests, review/acceptance document,
README status update. Gates JSON remains unchanged.

- [x] Bind calculations to actual native values; report ADC rail/current headroom,
      RC loading/bandwidth, PHY loaded-driver current and total new rail budget.
- [x] Reject invalid/nonfinite inputs and show missing evidence as BLOCKED.
- [ ] Final committed-HEAD CI/evidence check is recorded in the PR handoff after
      this document commit. Local full regression passed; no physical test ran.
- [ ] Publish final source/native evidence and current status in the Draft PR.

## Execution ledger

2026-09-24: PR21 is already merged. A new branch is based on main; no reopened or
rewritten PR21. Clarify the existing reserved interface contract before drawing.
Ruling: implement ADC/PHY engineering design under the user's renewed request;
keep power/safety qualification open and continue blocking physical layout.

## Execution record

- Stage 1 implemented in 8b2c9bd: real Icarus regression including default 100MHz
  5ms falling-edge cadence; 160 local tests passed with actual native XML/ngspice.
  This is a standalone synchronous core, not integrated Plant/AXI/Vivado evidence.
- Stage 2 implemented in 90247a6: 15 native sheets, 148 new peripheral parts/461
  pin assertions, J3/J4 removed, zero ERC, 166 tests passed in actual KiCad
  precommit workbench. PDF layout findings corrected in d1a2ecb before commit.
- Stage 3 implemented in 638e4ab: native RC/loaded-PHY screening plus 9 regressions
  observed RED then GREEN; conservative additive load budgets feed the EDV matrix.
  Full local suite with the exact reviewed native XML: 175 passed, zero skipped.
- Ruling: a fixed 64-signal allocation does not contain a CAN/EtherCAT expansion
  port. Correct documentation rather than silently allocate or repurpose pins.
- Ruling: DUT neutral state and reaction budget cannot be selected without actual
  DUT electrical requirements. They remain physical acceptance bindings, not
  synthesized values or PASS records.
- Layout, complete DUT inhibit, board integration, physical tests and production
  qualification are NOT complete; gates and Rev.A source were not changed.
