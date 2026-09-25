# Rev.B ADC / PHY / health implementation — PR #22

Engineering continuation from main `37a4463dbf956cdefe1d55922078de9e327a287b`
after merged PR #21. **Non-release native circuit implementation. No fabrication,
board measurement, full DUT inhibition or functional-safety approval.**

## Source and implementation

The native circuit commit is `90247a6df219d9f0e203d16366d70aad0cb9fd55`.
The root project now has 15 sheets. The two reserved module headers J3/J4 are
removed so their external devices cannot contend with the new on-board circuits.
All original carrier signal names, pin allocation and voltage domains remain.
409 physical components = 263 previous - 2 reserved headers + 148 peripheral
parts. Existing safety checks (47 parts/168 pins) remain; the independent
peripheral oracle checks 148 parts/461 pins. Existing power/DAC wiring is frozen.

| Sheet | Circuit | Deliberate limit |
|---|---|---|
| 70_adc_frontend | U801 AD7606C-16BSTZ; eight single-ended inputs; two 100-ohm series legs and a 1nF differential capacitor each; explicit supply/reference/regulator capacitors; eight DOUT lanes and host controls | Low-energy candidate, not field-input surge protection or qualified 16-bit acquisition |
| 80_encoder_phy | Four THVD1450 half-duplex pairs for two clock/data ports; four safety-gated DE controls; pull defaults and selectable termination | SSI/BiSS directional profile, not arbitrary ABZ or SPI compatibility; non-isolated, no encoder supply |
| 03_peripheral_boundaries | Six SN74LVC541A PWM receive paths; gated THVD1450 RS485; six AUX logic pins and I2C | 3.3V laboratory logic, not a 24V PLC/gate-drive input |
| rtl/revb/health_heartbeat.sv | Sequence/deadline/lease-qualified WDI and ARM state | Standalone synchronous core; real Plant/host/CDC/top-level/Vivado integration remains open |

All newly added components have explicit footprint identifiers backed by the
project-local official KiCad library snapshot. That is **not** final land-pattern,
MPN, tolerance, rating or component-lifecycle sign-off. Earlier unbound safety
packages and connector/ESD details are still blockers.

## ADC configuration and electrical interface

AD7606C-16 (not legacy AD7606) allows the allocated 1.8V digital supply. AVCC uses
+5V0_DAC, not +5V2_PVDD. All four AVCC and all grounds are wired. REGCAP_A and REGCAP_D use
separate 1uF capacitors; REFIN/OUT has 100nF; the two REFCAP pins share only their
10uF capacitor. The internal reference is selected. OS[2:0]=111 selects software
mode; SER/PAR is strapped serial, STBY is inactive and WR high. Unused parallel
pins are grounded per serial-interface guidance. RESET and CS have pullups;
CONVST/SCLK/SDI have pulldowns. Controls and return data have series resistors.

An eight-lane connection does not select eight-lane mode by itself. Initialization
must configure and read back CONFIG register 0x02 bits [4:3]=11 before using all
DOUT lanes. Keep range, bandwidth, oversampling and diagnostics under explicit
configuration control. Tie each accepted I/O-completion acknowledgement to actual
valid data, never a requested conversion. Verify channel identity using distinct
bounded DC inputs/diagnostic patterns. No production initialization/acquisition
state machine, sample-rate qualification or ADC-to-Plant integration is claimed.

J801 is paired single-ended input/GND. Nominal intended range is +/-10V only for
a reviewed low-energy source. The IC's clamp and absolute-maximum specifications
do not qualify external fault energy, cable surge, unpowered input or leakage.
100-ohm legs and 1nF are a candidate EMI/source network, not a complete external
anti-alias filter. R/C type, tolerance, temperature coefficient, fault dissipation
and connector constraints must be bound before assembly.

## Differential roles and host binding

For each encoder port, IO0 -> pair0 D, pair0 R -> IO1, IO2 -> pair1 D,
pair1 R -> IO3. DIR0/1 request transmit and are gated with SAFE_ENABLE. Receiver
RE_N pins are tied low (always receive). The generic carrier inout declaration
must not be mistaken for arbitrary reassignment: drive IO0/2 only; receive IO1/3.
Configure tri-state/CDC/top-level directions accordingly before a real bitstream.

SSI/BiSS master role: DIR0=1 (clock transmit), DIR1=0 (data receive). Emulated
slave role: DIR0=0, DIR1=1. Select roles only while disarmed and validate bus-idle
and contention response. Four-wire SPI and three differential ABZ pairs are not
supported by this physical profile. No encoder power is sourced on J901/J902.

J1004 is RS485 A/B/GND; transmit request similarly requires SAFE_ENABLE.
All 120-ohm termination jumpers ship unshunted in this design. Install only for
the reviewed role/cable ends; receiver always-on may see local transmit echo.
Non-isolated buses, host-off backfeed through receiver/AUX/I2C paths, DE ramps,
ESD/surge, common mode, line length and turn-around delays still require review.
SAFE_ENABLE gating alone is not a partial-power or single-fault safety proof.

The fixed 64-signal carrier contract contains no independent CAN controller or
EtherCAT slave interface. Those were an overbroad earlier README description.
Adding them requires an explicit controller/PHY/clock/power/pin allocation and
review; no spare AUX signal was silently repurposed. An external Raspberry Pi
EtherCAT host is not a populated PHY on this expansion board.

## Native-value load and RC screening

`sim/peripherals/screen.py` reads the actual component values and combines them
with the existing regulator limits. The output always has qualification=BLOCKED,
layout_allowed=false and physical_tests=NOT_RUN. `--strict-design` returns 2.
The 9 regression tests include changed RC/termination/MPN and invalid parameters.

Current analytical results (not measurements):

| Quantity | Screen | Interpretation |
|---|---:|---|
| ADC AVCC static limits | 4.883310..5.096890V | Within IC static operating window; startup/transient still unqualified |
| ADC VDRIVE static limits | 1.772118..1.811926V | Within C-16 static window; not proof of 40MHz board timing |
| External 100+100ohm / 1nF pole | 795.775kHz | External-only first-order network; excludes the internal ADC filter |
| External attenuation at 500kHz | -1.445dB | Cannot serve as the sole anti-alias qualification |
| External full step to 0.5LSB | 2.357us | Simplified linear RC calculation, not IC acquisition/settling specification |
| Positive-leg simplified DC gain loss | 99.990ppm; 3.276LSB at +10V | Assumes 1Mohm input load, excludes other ADC errors; calibration/error budget remains |
| Five enabled PHY resistive-load stress | 323.704mA | VCCmax/54ohm + 3mA no-load each, not dynamic or short-circuit qualification |
| Local 120ohm termination dissipation | 93.566mW | Worst VCC across -1% nominal resistor, not all-temperature component rating |
| 3.3V additive allocation need | 648.704mA | Retains all old 300mA plus load stress and assumed 20mA dynamic/5mA logic reserve |

The earlier full budgets are conservatively retained, even if they included
unused headroom. Updated EDV loads are 3V3_D=0.70A, 1V8_D=0.32A,
6V2_PRE=0.55A and +5V0_DAC=0.25A. This is allocation, not measured consumption or
a supply capability guarantee. Firmware normally transmits only two encoder
pairs plus optional RS485; five transmitters is an allocation stress case, not
an approved bus role. The 250mA component short-circuit magnitude and all-five
short scenario show why loaded/fault thermal and upstream limits remain open.

These new loads feed the existing 25-case ngspice and analytical reports.
The unchanged rail-setpoint/headroom conflict, vendor closed-loop model gap,
MLCC curves, magnetic/thermal qualification, input energy and AON/partial-power
blockers are not cleared by this extension. No regulator set resistor was changed
merely to hide the earlier failing margins.

## Verified pre-commit native checkpoint

The source was authored in a branch-scoped disposable checkout, checked by real
KiCad, then its immutable blobs were inspected and committed. Temporary writers
and their write-enabled workflow were removed in the native commit. Normal CI
never redraws or overwrites the source.

- Workbench run 36026084609, input HEAD d1a2ecbe0fc6151a8730f20c68af2aa615284222.
- Artifact 10819538628, `revb-peripheral-precommit-review`.
- ZIP SHA256 c51a666311c14577a89300f967e87d62e93c2c9e94f02386cf8378beb9fe27c6.
- Scope is explicitly PRECOMMIT_SCRATCH_NOT_HEAD_EVIDENCE. It is **not** proof that
  the unmodified input HEAD already contained the new native circuit files.
- Actual KiCad 10.0.6, 15 pages, 0 ERC violations, no exclusions added.
- 20 native/checker/library objects checked against both Git blob SHA and SHA256;
  downloaded native bytes match the locally inspected files.
- 166 regression tests passed, 0 skipped, including actual Icarus and ngspice.
  Peripheral mutations include 15 deliberate ADC/PHY/wiring errors; earlier
  safety mutations remain. New source tests were observed failing before circuit
  implementation; screen tests likewise failed before the analysis/budget change.
- The three changed/new PDF pages were visually reviewed; the title-block and
  label collisions found in the first run were corrected before native commit.

For committed-HEAD acceptance, use the latest PR native and EDV artifacts instead
of reusing this scratch checkpoint. They record the actual source/merge-test SHA;
PR branch SHA and GitHub synthetic merge SHA may differ. The native CI stores
full test log, XML, ERC, PDF and source ZIP. The compact EDV artifact is only a
report/source index; full raw SPICE files remain in the full EDV artifact.
Review was inline, not an independent human/agent hardware approval.

## Actual DUT safety: mandatory unresolved binding

Do not choose a generic zero voltage, pull resistor or shutdown deadline for an
unknown DUT. Before low-energy acceptance, record the actual DUT/adapter model
and schematic revision; AO input transfer/neutral window/source impedance; the
permit input threshold/current/leakage; cable connections, grounds and supply
sequences; and the maximum allowed hazard-reaction time. Review the independent
energy-removal arrangement before any motor-powered testing.

| Acceptance item | Required raw observation / acceptance basis |
|---|---|
| Cold boot and ARM held high | No permit or unintended AO connection while WDI missing/static or while hardware qualification is pending |
| Health faults | Stop Plant completion, I/O completion or host lease separately; replay a duplicate sequence; capture WDI, ARM, SAFE_ENABLE, AO, permit contact and real DUT input on one timebase |
| Fault recovery | Restore supplies/progress/contact while ARM remains high; require continued inhibition until explicit recovery and new ARM transition |
| AO neutral state | Measure every DUT input when switch off, cable removed and supplies sequenced; compare against the DUT-specific neutral window, not nominal 0V |
| Permit leakage/cable loss | Worst component leakage, open cable, brownout and unpowered adapter must yield the DUT-specific inhibited state |
| End-to-end reaction | Add detection, logic, switch/PhotoMOS, cable/DUT filter and DUT reaction; compare the measured total with the reviewed DUT hazard budget |
| ADC/PHY electrical | Distinct bounded input patterns, calibrated DC/AC/error/noise, serial timing, termination/roles, contention, PWM glitches and powered/unpowered cable cases |
| Production evidence | Exact PCB/HW revision, BOM lots, FW/bitstream SHA, equipment/calibration, conditions, raw thermal/EMC/transient/fault/FOC traces and engineering sign-off |

All physical cases above are NOT_RUN. A resistor calculation, a component rating,
a synthetic fixture or passing ERC cannot be filed as a physical PASS. The
existing release-gate file remains unchanged. No PCB/Gerber or production release
is included in this PR.

## Primary component references

- [ADI AD7606C-16 Rev.A](https://www.analog.com/media/en/technical-documentation/data-sheets/ad7606c-16.pdf): pins pp15-17, supply/current/input tables, serial software configuration and decoupling guidance.
- [TI THVD1450 Rev.E](https://www.ti.com/lit/ds/symlink/thvd1450.pdf): pin table, loaded/no-load conditions, DE/RE and power-off limitations.
- [TI SN74LVC541A Rev.O](https://www.ti.com/lit/ds/symlink/sn74lvc541a.pdf): PW20 pin mapping and Ioff/logic limits.
- [TI SN74LVC1G08 Rev.Z](https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf): DBV pin mapping and logic limits.
- [TI TPS3430](https://www.ti.com/lit/ds/symlink/tps3430.pdf): external watchdog timing; standalone RTL simulation does not verify the complete hardware timing chain.
