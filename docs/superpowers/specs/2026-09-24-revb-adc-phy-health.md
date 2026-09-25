# Rev.B ADC, digital PHY and health continuation

Base: main `37a4463dbf956cdefe1d55922078de9e327a287b` after PR21.
The user explicitly requests continued implementation of the unfinished ADC,
digital PHY and prerequisites for layout/production. Work remains engineering
implementation, not permission to manufacture or energize a motor system.

## Scope and stage distinction

Populate the already allocated AD7606C-16, PWM, dual encoder and RS485 interfaces
and implement a deadline/lease-qualified PL heartbeat. The current 64-signal
contract has NO dedicated CAN or EtherCAT interface. Do not silently repurpose
AUX signals, allocate extra carrier pins or introduce a second programmable chip.
EtherCAT host operation remains on the existing external host/carrier path;
a CAN controller/transceiver allocation requires a separately reviewed profile.
Correct the README's broader claim to match the actual contract.

The renewed request advances ADC/PHY *design and simulation* while electrical
qualification is still open. This does not waive prior power-EDV or safety
blockers. Do not create PCB copper, Gerbers or a production PASS. The existing
release gates remain unchanged. Physical tests cannot be replaced by synthetic
fixtures, a logic model, ERC, a vendor component rating or passing CI.

## Health producer

One-clock-domain synthesizable RTL emits HIL_WDI only while all required Plant
and I/O completion sequences advance within explicit deadlines and a monotonic
host lease is fresh. Duplicate/stale acknowledgements do not extend deadlines.
A discontinuity or expiry latches a fault; later activity alone cannot restart.
A deliberate new session with ARM low is required. ARM held high through startup
or recovery cannot arm until first observed low in a healthy session, then high.
WDI edge generation is independent of ARM so hardware watchdog qualification can
complete while disarmed. Do not qualify heartbeat with HIL_FAULT_N, because the
existing hardware asserts fault while unarmed: doing so creates a boot deadlock.
Inputs are synchronous accepted transactions; CDC/AXI integration and bitstream
acceptance must be identified separately, not implied by a standalone core.

## ADC

Use the existing AD7606C-16 allocation: 8 DOUT lanes, SDI, SCLK, CS, CONVST, BUSY
and RESET at 1.8 V. Use the correct C-16 part/pin table, not AD7606 (which has a
different VDRIVE floor). The 5 V analog source must be +5V0_DAC, not the ±5.2 V
TIA supply. All AVCC/AGND/regulator/reference pins, mode straps and decoupling
must be explicit. Provide 8 input channels with bounded RC source networks and
an explicit differential/single-ended input/reference contract. Board fault
energy, cable protection, 16-bit accuracy and alias rejection remain qualification
items. Do not call component clamp voltage a field-input rating.

## Digital PHY

Six PWM inputs get actual input buffering and defined defaults. Dual encoder
ports use two directional differential pairs per port, with a profile that
separates TX data, RX data and direction, rather than claiming arbitrary SPI
three-wire/four-wire compatibility. RS485 gets a real half-duplex transceiver,
direction defaults and optional termination. Use actual semiconductor power-off
and logic limits when screening, but do not claim all partial-power scenarios
are solved. Do not expose raw FPGA pins as an industrial 24 V input.

## Evidence and acceptance

Native KiCad is authoritative. Preserve original power/safety/DAC connectivity;
intentional removal/replacement of reserved interface headers must have a narrow,
explicit independent pin-delta check, never a silently regenerated baseline.
Use actual KiCad XML/ERC and inspect new pages. Test negative cases: ADC pin swaps,
wrong VDRIVE/reference supplies, missing decoupling, differential polarity/DE
errors, PWM bypass and parallel external-header drivers.

Add source-bound electrical screening for the new loads and interface networks.
A nominal calculation is not a closed-loop vendor simulation or measured PASS.
Production qualification stays NOT_RUN until physical evidence exists for the
exact assembled HW, DUT adapter, firmware, supplies, loads and instruments.

Primary references (review actual revision/pin tables before implementation):
- https://www.analog.com/media/en/technical-documentation/data-sheets/ad7606c-16.pdf
- https://www.ti.com/lit/ds/symlink/thvd1450.pdf
- https://www.ti.com/lit/ds/symlink/sn74lvc541a.pdf
- https://www.ti.com/lit/ds/symlink/tps3430.pdf
