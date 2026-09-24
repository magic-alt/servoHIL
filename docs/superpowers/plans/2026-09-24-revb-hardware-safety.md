# Rev.B hardware safety continuation

> Inline execution of the user's ongoing Rev.B development request. This is a
> laboratory HIL interlock implementation, not functional-safety certification.

**Base:** main c29abb07e9fca5584235860dbe7f2bd1460141ca, after PR #20 and PR #18.
**Spec:** docs/superpowers/specs/2026-09-23-single-soc-design.md, supplemented by
this user's explicit request to populate the missing hardware safety chain.
**Goal:** real native KiCad watchdog, eight-channel disconnect and normally-open
DUT permit circuit, with independent pin assertions and negative regressions.
**Stack:** native KiCad, Python unittest, actual KiCad XML/ERC in read-only CI.

## Constraints and rulings

- One ZU2CG only. Existing power setpoints and Rev.A archive are untouched.
- Electrical verification remains BLOCKED and layout_allowed remains false.
  No ADC/PHY or PCB expansion until the power EDV blockers are resolved.
- Source of truth is the checked-in native schematic. No ordinary CI generator
  may rewrite it. Only real cross-sheet signals use global labels.
- Preserve the existing power supervisors and ARM latch. Add an open-drain
  watchdog qualifier to RAILS_OK rather than rewriting the power sheets.
- Watchdog recovery, restored rails or a closed interlock must not set the ARM
  latch. A fresh low-to-high HIL_ARM transition after qualification is required.
- A Python logic model is not a vendor macromodel or physical safety evidence.
  KiCad ERC and pin contracts are not power-off, latency or analogue qualification.

## Circuit decision

TPS3430DRCR is powered from 3V3_AON, with VDD1/VDD2 externally joined, exposed
pad grounded, SET0/SET1 hard-high, CWD through 10k to AON and CRST open. The
factory falling-edge window has lower boundary 1.48/1.85/2.22 ms and upper
boundary 9.35/11/12.65 ms; requested heartbeat period is 5 ms (4..6 ms contract).
CRST open selects 170/200/230 ms reset delay, excluding evaluation/startup.

Ioff-capable logic buffers HIL_WDI and inverts its falling edge into the clock
for two SN74LVC1G74 stages. Both stages clear asynchronously on watchdog or
AON/interlock reset. Two observed edges are required before HB_VALID. A second
TPS3808G33DBVR qualifies HB_VALID and AON before releasing its open-drain output
onto RAILS_OK. CT open has 12/20/28 ms release delay, not an exact 20 ms timer.
An AON-domain AND generates SAFE_ENABLE = RAILS_OK & ARM_LATCH & HIL_ARM.

Two ADG5412FBRUZ normally-open quad switches are candidates for eight AO
channels. Protected S terminals face the DUT; D terminals face the DAC. All
IN controls follow SAFE_ENABLE with default pulldowns. FF outputs are brought
to local test points only: a guaranteed-margin FF-to-interlock interface is
not claimed. Unpowered high impedance does not define the DUT's safe analogue
bias; the adapter must provide its application-specific neutral state.

A normally-open AQY212GS PhotoMOS, driven by SAFE_ENABLE through a current-
limited LED/NPN path, provides an isolated *permit contact* to a reviewed DUT
adapter. The proposed interface is SELV <=24 V, <=10 mA. It is neither motor
power switching nor a certified STO output. The adapter must interpret an open
contact, cable removal and output leakage as inhibited. This remains an open
system-level acceptance item until tested with the actual DUT.

## Stages and acceptance

1. Add a time-monotonic window-watchdog and latch/qualification reference with
   failing-then-passing tests: valid window corners, absent/fast/late heartbeat,
   two-edge qualification, delayed release, direct disarm and no automatic rearm.
2. Populate native watchdog, AO disconnect and DUT permit circuits. Check actual
   IC pin identities, supply polarity, source/drain orientation, pull defaults,
   contact isolation and absence of a parallel DAC-to-DUT bypass.
3. Retain the historical readability baseline. Replace strict whole-board
   equivalence (incompatible with intentional new hardware) with a frozen-old-
   pin partition check plus an explicit, narrow AO-connector delta and an
   independent safety pin oracle. Mutation tests must reject bypass and pin swaps.
4. Run source regressions, actual KiCad export/ERC, inspect review pages, bind
   evidence to exact source, and rerun EDV. Record any pre-existing main CI
   failure separately. Update status without granting fabrication permission.

## Review focus / still-open physical evidence

Power ramps and partial power; reset/clock slew, propagation and recovery/removal;
DFF hold/clock skew; watchdog timing over voltage/temperature; relay LED current,
AON dissipation, contact leakage and turnoff with actual DUT input; switch RON,
settling, charge injection, off leakage and fault energy at the selected rails;
connector/ESD/cable and package review; existing DAC rail/headroom conflict.

## Primary design references

- TI TPS3430, SBVS366A, sections 5, 6.6, 7.3.3.2, 8.1:
  https://www.ti.com/lit/ds/symlink/tps3430.pdf
- TI TPS3808, SBVS050M, sections 6, 7.5/7.6:
  https://www.ti.com/lit/ds/symlink/tps3808.pdf
- TI SN74LVC1G74 / SN74LVC1G17 / SN74LVC1G14 datasheets:
  https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf
  https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf
  https://www.ti.com/lit/ds/symlink/sn74lvc1g14.pdf
- ADI ADG5412F/ADG5413F Rev.C, TSSOP pin table and power-off protection:
  https://www.analog.com/media/en/technical-documentation/data-sheets/ADG5412F_5413F.pdf
- Panasonic AQY212GS product specifications:
  https://industry.panasonic.com/ap/en/products/control/relay/photomos/number/aqy212gs

No procurement, layout, independent sign-off or measured pass is implied.
