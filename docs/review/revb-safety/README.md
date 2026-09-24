# Rev.B hardware safety continuation — 2026-09-24

**Native circuit implementation checkpoint. Electrical design BLOCKED; no PCB,
fabrication, complete-DUT-inhibit or functional-safety sign-off.**

[PR #21](https://github.com/magic-alt/servoHIL/pull/21) continues from main
`c29abb07e9fca5584235860dbe7f2bd1460141ca`, after merged PR #20/#18.
The native circuit commit is `3af3ab79177c31b2c46e7233b07dbd12985c1451`.
There is still one ZU2CG. No ADC/PHY expansion, Rev.A file change or release-gate
promotion is part of this continuation.

## What is now a real native circuit

| Sheet | Added implementation | Remaining qualification |
|---|---|---|
| 50_watchdog_interlock | U501 TPS3430; U504/U505 input buffer/inverter; U502/U509 dry-contact/AON reset; U510 reset buffer; U506/U507 two-edge qualification; U503 delayed release into RAILS_OK; U508 three-input SAFE_ENABLE | Partial power, timing/clock skew, startup/reset propagation, host/PL heartbeat semantics, package review and physical fault injection |
| 06_analog_outputs | U601/U602 ADG5412F: eight normally-open switches; protected S faces DUT, D faces DAC; two independently pulled-down IN groups; bypass capacitors and FF test points | RON, settling, charge injection, voltage headroom, off leakage, fault energy and actual DUT neutral state |
| 60_dut_permit | U701 AQY212GS; Q701 MMBT3904; LED/base current limiting and base pulldown; J701 floating normally-open contact | Final package, LED-current/thermal corners, actual DUT threshold/leakage/cable-loss response and measured shutdown time |

The project is 13 pages, 263 physical components (216 retained + 47 added).
Existing physical pin relationships are frozen except the eight explicitly
rerouted J5 output contacts. `40_power_supervision` only promotes RAILS_OK to a
cross-sheet label; no old physical circuit was silently replaced.

## Interface contract — implementation is not system qualification

`HIL_WDI` is J15.33 and `HIL_ARM` is J15.32 in the existing AXU2CGB binding.
WDI is buffered with an Ioff-capable part. TPS3430 uses **falling-to-falling**
intervals: nominal 5 ms, requested contract 4..6 ms. A square-wave implementation
therefore toggles every 2.5 ms at nominal timing, not once every 5 ms. SET0/SET1
are hard-high; CWD is through 10k to AON. There is no firmware-controlled watchdog
bypass. Factory lower-window corners are 1.48/1.85/2.22 ms; upper corners are
9.35/11/12.65 ms. CRST open selects 170/200/230 ms reset hold; initial evaluation
and startup are additional and not simulated by the discrete reference.

WDI must attest completed real-time Plant/I/O deadlines and a valid host/session
lease. An unconditional free-running PL timer can keep the watchdog healthy
while the useful system has failed. **This PR does not implement or verify that
firmware/RTL health producer.** Deliberate recovery must first hold ARM low,
restore qualified rails/interlock/heartbeat, then issue a fresh ARM rising edge.

U502 supervises AON and the local 3.3 V dry-contact interlock. U510 buffers the
open-drain clear into the two DFFs. Two observed heartbeat edges set HB_VALID;
U503 adds its open-drain inhibit to existing RAILS_OK. CT open has a 12..28 ms
release range, not an exact 20 ms delay. RAILS_OK clears the existing ARM latch.
It does not feed back into the heartbeat clear path. A recovered watchdog,
restored rail or closed interlock cannot re-arm the board while ARM stays high.
SAFE_ENABLE = RAILS_OK AND ARM_LATCH AND HIL_ARM, with a default pulldown. The
existing 1.8 V DAC reset gate remains separate from the new AON-domain enable.

AO OFF means **high impedance, not zero voltage or a safe neutral**. The reviewed
DUT adapter must establish its own neutral bias and respect the separate permit.
FF outputs currently terminate only at local test points; their guaranteed
logic-level margin to an aggregate interlock is unresolved. A channel's internal
fault protection is not a verified global DUT inhibit.

J701 is a proposed SELV <=24 V / <=10 mA permit interface, not a board-qualified
rating. Its two contact nets have no copper connection to board GND or a supply.
R701=220 ohm, R702=680 ohm and R703=10k are candidate drive values. AQY212GS
component specifications include <=1 uA off leakage and recommended 5..30 mA LED
drive; these do not prove the actual DUT's inhibited state. The new AON load and
all-temperature LED/transistor/logic margins need qualification. It is not motor
power switching, not redundant, and not a certified STO output. A shorted relay,
shorted AO switch or stuck-high enable is not covered by a single-fault safety
claim. Motor-powered testing needs an independently reviewed energy-removal and
emergency-stop arrangement.

## Evidence checkpoint (downloaded native artifact, not inferred from green CI)

- PR head: `3af3ab79177c31b2c46e7233b07dbd12985c1451`.
- GitHub PR merge-test/source commit: `3117c13c24374dd03cdf32a1596ac2ab7e9e1f49`.
- [Native read-only CI run](https://github.com/magic-alt/servoHIL/actions/runs/36010821083): PASS;
  artifact `10812267969`, `native-schematic-readability`.
- Artifact SHA256: `29998d925aba9bdb6a6bc8bc47bfc261139732f4941a4352715f2b3c03353927`.
- 42 archived native source files compared byte-for-byte with the inspected
  source; actual KiCad **10.0.6**, 13 sheets, **0 ERC violations**, no suppressed
  rules/exclusions added. PDF pages for AO/watchdog/permit visually inspected.
- Frozen 216 old components; 47 new components, 168 new physical-pin assertions,
  explicit J5.1..8 delta, AO bypass and contact-isolation assertions: PASS.
- Local full repository suite with the actual native XML and real ngspice:
  **144 tests, 144 passed, 0 skipped**. Includes 12 watchdog/qualification/rearm
  tests and 11 native miswire mutation subcases. Source/model regressions were
  observed RED before their corresponding implementation and GREEN afterward.
- [Hardware structure CI](https://github.com/magic-alt/servoHIL/actions/runs/36010821133): PASS.
  Its prior main failure was the stale pre-PR18 archive hash. The guard now freezes
  the already merged snapshot `052a06c6e6e5b0ce23e94f75774a9f1cc7f3f167`; unknown
  trees and rollback to the old snapshot are rejected by new regression tests.
- [EDV CI](https://github.com/magic-alt/servoHIL/actions/runs/36010821141): PASS for
  execution/integrity, **not electrical qualification**. The existing workflow
  requires strict-design exit 2 and verifies the full source-bound simulation
  pack in CI. Raw EDV waveforms were not independently downloaded/re-audited in
  this continuation; this is distinct from the downloaded native evidence above.

The earlier bootstrap runs were pre-commit scratch evidence, not evidence of a
committed native HEAD. Their temporary writer workflow and both authoring helpers
were removed in `3af3ab7`. Ordinary validation only reads/exports native files.
For later revisions, use the latest PR run's native artifact: it contains the
PDF, source ZIP, XML, ERC and source-commit identity. GitHub may test a merge
commit rather than the branch HEAD; compare the recorded native bytes as well.
The older PDF in `docs/review/revb-readability/` is the historical 11-page version.

Review was performed inline; the separately coded pin oracle is not a claim of
independent human or separate-agent design approval. No board measurement occurred.

## Planned physical acceptance — all NOT RUN

Run only after power EDV and the test fixture are reviewed. Start with a
current-limited, low-energy fixture and representative DUT input loads, not an
energized motor system. Capture AON, RAILS_OK, HB_VALID, ARM_LATCH, SAFE_ENABLE,
DAC_RESET_N, actual AO voltage/current and the J701/DUT input response on a common
timebase. Retain exact HW revision, part lots, firmware/bitstream SHA, supply/load,
temperature, instruments and raw traces. No stimulus API or Python truth model
can substitute for these observations.

| Test | Stimulus / required observation |
|---|---|
| SAFE-01 cold boot | WDI absent or static; ARM held high. No DUT permit, no AO connection or automatic startup, including watchdog retry grace periods. |
| SAFE-02 intentional ARM | 4/5/6 ms falling-edge intervals, healthy rails/contact; only a fresh ARM edge after qualification permits output. Check every AO channel with a reviewed neutral-bias/load fixture. |
| SAFE-03 stopped heartbeat | Stuck-high and stuck-low during enable. Capture detection and actual output/contact release. A DUT-specific maximum shutdown budget must be approved before assigning PASS. |
| SAFE-04 invalid window | 1 ms and 13 ms falling intervals plus burst/glitch sequences. Verify inhibition and no transient re-enable; test voltage/temperature corners. |
| SAFE-05 faults and recovery | Open dry contact; inject each reviewed rail fault; interrupt AON. Recover while ARM stays high. Require inhibited state until explicit disarm/re-arm. |
| SAFE-06 direct disarm | Drop HIL_ARM during valid heartbeat. Measure actual AO and DUT input reaction, not just the logic signal. |
| SAFE-07 partial power / cabling | Reviewed host-only, DUT-only and expansion-only supply combinations; remove cables. Measure Ioff/backfeed, neutral state, contact leakage and adapter response. |
| SAFE-08 analog / aggregate faults | RON/error/settling/charge injection/off leakage at selected rails and loads; bounded source-side faults with a reviewed energy-limited fixture; verify whether the application needs an aggregate FF inhibit. |

Before any release, close the existing DAC rail/headroom conflict, real regulator
startup/transient models, MLCC bias curves, magnetic/thermal qualification, new
AON current budget, device-package/connector/ESD review and all tests above.
ADC/PHY, layout and complete FOC HIL acceptance are separate unfinished stages.
`hardware/revB/gates.json` is unchanged; `layout_allowed=false`.

## Primary component references

- [TI TPS3430, SBVS366A](https://www.ti.com/lit/ds/symlink/tps3430.pdf): pins, fixed watchdog windows and reset timing.
- [TI TPS3808, SBVS050M](https://www.ti.com/lit/ds/symlink/tps3808.pdf): DBV pins, MR and CT timing.
- [TI SN74LVC1G74](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf), [G17](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf), [G14](https://www.ti.com/lit/ds/symlink/sn74lvc1g14.pdf), [G11](https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf): pin functions, timing and logic limits.
- [ADI ADG5412F/ADG5413F Rev.C](https://www.analog.com/media/en/technical-documentation/data-sheets/ADG5412F_5413F.pdf): TSSOP pin table, protected S terminal and power-off behaviour.
- [Panasonic AQY212GS](https://na.industrial.panasonic.com/products/relays-contactors/semiconductor-relays/lineup/photomos-relays/series/12653/model/12659): LED/current/leakage/contact timing; not a board rating.
- [Nexperia MMBT3904](https://assets.nexperia.com/documents/data-sheet/MMBT3904.pdf): B1/E2/C3 and specified test-condition limits.

These component facts do not establish all-temperature, assembled-board or
system-level safety compliance. Final land patterns and DUT limits remain open.
