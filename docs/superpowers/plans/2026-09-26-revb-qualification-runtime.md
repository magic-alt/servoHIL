# Rev.B Qualification Closure and Runtime Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** Advance Rev.B from source-level ADC/PHY implementation to strict qualification gating plus ADC/runtime/Vivado integration without prematurely authorizing Layout.

**Architecture:** Keep qualification, DUT evidence, ADC runtime, health integration and Vivado evidence as independent units. Every unit exposes a machine-checkable contract; final aggregation is fail-closed and preserves `layout_allowed=false` until real evidence exists.

**Tech Stack:** Python 3.11+, unittest, SystemVerilog/Icarus, KiCad source contracts, Vivado batch Tcl/XDC/report parser.

**Spec:** `docs/superpowers/specs/2026-09-26-revb-qualification-runtime-design.md`

## Global Constraints

- Never invent DUT thresholds, leakage or shutdown timing.
- Never turn simulation/catalog data into physical PASS.
- Preserve current 64-signal allocation; no CAN/EtherCAT repurposing.
- No PCB/Gerber creation in this plan.
- `layout_allowed=false` throughout.
- New code follows RED -> GREEN tests and commits after each deliverable.

## Review Focus

- Missing or malformed DUT profile must fail closed.
- Stale/wrong-MPN component evidence must not qualify a part.
- ADC must not emit a completed sample sequence before CONFIG readback and BUSY/capture completion.
- Replayed command/lease/sample events must not refresh health deadlines.
- Vivado report parser must reject stale SHA/XDC/top/part and negative/unconstrained timing.

---

### Task 1: Qualification and DUT evidence contract

**Files:**
- Create: `hardware/revB/dut_adapter_profile.json`
- Create: `hardware/revB/qualification_requirements.json`
- Create: `tools/revb_qualification.py`
- Test: `tests/test_revb_qualification_gate.py`

**Interfaces:**
- Produces `load_profile(path)`, `evaluate_dut_profile(profile)`, `build_qualification_report(root)`.
- Final report contains `layout_allowed:false`, `qualification:BLOCKED|READY_FOR_ENGINEERING_REVIEW`, and explicit blocker IDs.

- [ ] Write failing tests for unbound DUT values, contradictory thresholds, missing physical evidence, and invariant layout block.
- [ ] Run targeted unittest and observe RED.
- [ ] Implement strict validator/aggregator.
- [ ] Run targeted unittest and full Python suite.
- [ ] Commit.

### Task 2: Component candidate and new-load qualification

**Files:**
- Modify: `sim/power/capacitor_candidates.json`
- Modify: `sim/power/component_candidates.json`
- Modify: `sim/power/qualification.py`
- Modify: `sim/peripherals/screen.py`
- Test: `tests/test_edv_qualification.py`, `tests/test_edv_capacitors.py`, `tests/test_peripheral_screen.py`

**Interfaces:**
- Qualification report distinguishes lifecycle binding, raw curve evidence, analytical margins and required board measurement.
- Cuk transfer capacitor candidate becomes production `CGA6L2X7R1H105K160AA`; no curve claim without raw evidence.

- [ ] Add failing tests for NRND rejection, exact-MPN evidence binding, and new-load thermal/partial-power blockers.
- [ ] Observe RED.
- [ ] Update candidate metadata and qualification logic.
- [ ] Run EDV/peripheral tests and strict-design screens.
- [ ] Commit.

### Task 3: AD7606C-16 initialization and acquisition RTL

**Files:**
- Create: `rtl/revb/ad7606c16_controller.sv`
- Create: `tests/rtl/tb_ad7606c16_controller.sv`
- Create/modify: `tests/test_adc_runtime_rtl.py`
- Modify: `rtl/revb/README.md`

**Interfaces:**
- Inputs include reset/start, BUSY, eight DOUT lanes and SPI register-read response.
- Outputs include RESET/CONVST/CS/SCLK/SDI, `configured`, `sample_valid`, eight samples and monotonic `sample_seq`.
- Acquisition cannot enable until CONFIG 0x02 eight-lane write/readback succeeds.

- [ ] Write Icarus benches for config success, config mismatch, BUSY timeout, sample sequencing and reset recovery.
- [ ] Observe RED because controller is absent.
- [ ] Implement synthesizable controller.
- [ ] Run targeted Icarus/unittest suite.
- [ ] Commit.

### Task 4: Runtime completion integration

**Files:**
- Create: `rtl/revb/runtime_health_integration.sv`
- Create: `tests/rtl/tb_runtime_health_integration.sv`
- Modify: `tests/test_health_rtl.py`
- Modify: `rtl/revb/README.md`

**Interfaces:**
- Consumes completed ADC `sample_seq/sample_valid`, completed Plant sequence, renewed lease sequence and ARM/session controls.
- Produces existing HIL_WDI/HIL_ARM/fault code via `health_heartbeat`.
- Command/request pulses are deliberately absent from the completion interface.

- [ ] Add failing integration simulations for completion-only semantics, replay rejection and explicit recovery.
- [ ] Observe RED.
- [ ] Implement wrapper and CDC-boundary assertions/documentation.
- [ ] Run all RTL tests.
- [ ] Commit.

### Task 5: Vivado batch verification and evidence parser

**Files:**
- Create: `vivado/revb/run_verify.tcl`
- Create: `vivado/revb/revb_constraints.xdc`
- Create: `tools/check_vivado_evidence.py`
- Create: `tests/test_vivado_evidence.py`
- Modify: `hardware/revB/qualification_requirements.json`

**Interfaces:**
- Parser consumes JSON metadata plus timing/DRC summaries generated by the Tcl flow.
- PASS requires exact source SHA/top/part/XDC digest, no fatal IO DRC, no unconstrained reviewed clocks, WNS>=0 and WHS>=0.
- Missing Vivado execution remains NOT_RUN rather than simulated PASS.

- [ ] Add failing parser tests for stale SHA, negative slack and unconstrained paths.
- [ ] Observe RED.
- [ ] Implement parser and reproducible Tcl/XDC flow.
- [ ] Run parser tests; if Vivado binary is absent, record actual tool execution as NOT_RUN.
- [ ] Commit.

### Task 6: Final qualification handoff and README

**Files:**
- Create: `docs/review/revb-qualification/README.md`
- Modify: `README.md`
- Modify: `hardware/revB/gates.json` only to attach truthful evidence/status; do not set PASS for physical gates and do not set `layout_allowed=true`.

- [ ] Run complete available CI/test suite on branch HEAD.
- [ ] Record exact PASS/NOT_RUN/BLOCKED states and source hashes.
- [ ] Verify no PCB/Gerber and no invented physical evidence.
- [ ] Commit documentation.
