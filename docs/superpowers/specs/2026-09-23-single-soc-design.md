# Rev.B single-SoC migration

Approved scope: the user requested replacement of the dual-FPGA Rev.A with one
ZU2CG host, shared HIL I/O, and two carrier forms. This change implements that
migration, not a fabrication release or a measured FOC result.

## Decisions

- Preserve the exact Rev.A source tree under `archive/revA`, with its commit ID.
- Active designs contain no XC7A35T, secondary FPGA configuration flash, local
  FPGA JTAG/clock, 1V0_FPGA rail, or FPGA-to-FPGA HIL-Link.
- Original AXU2CGB (not AXU2CGB-I/-E) is the initial physical carrier: J12=1.8 V,
  J15=3.3 V; power contacts are NC. Physical pinout is separate from assignments.
- A purchased ZU2CG SoM is a second carrier, not a second compute device. Until
  the exact module/revision is selected, its connector, balls, supplies and
  voltage translation are unbound; generating a physical XDC must fail closed.
- Both forms consume the same logical peripheral contract: 8 AO, an 8-AI
  interface reservation, six PWM inputs, two profile-selected encoder ports,
  six auxiliary lines, RS485, I2C and three safety handshake lines.
- Native KiCad review output is reproducibly generated from checked-in design
  sources. It contains direct host interfaces and 8-channel DAC circuitry;
  explicit connectors represent the unfinished ADC/PHY, external safety and
  regulated-I/O-supply boundaries. They are not fictitious completed ICs.
- Existing power/AFE/DAC resources remain reference candidates. No DDR or SoC
  core supply is placed on the new expansion board. A SoM supply is specified
  only by its future vendor-qualified carrier profile.
- Layout gates are new and all start NOT_RUN/BLOCKED; legacy gates are
  SUPERSEDED, never PASS. An ERC-clean interface model does not prove analog
  behavior, safety, timing, package correctness or manufacturability.
- `hil_lab` AN9767/AN706 and Raspberry Pi IgH paths are unchanged.

## Acceptance

Archive bytes match the recorded baseline; active hardware has zero additional
FPGA/config-flash/core-rail components; 64 assigned I/O fit 68 physical I/O;
connector, logical signal, voltage, direction and generated constraints agree;
duplicate pins, wrong voltages, missing critical signals and unbound SoM release
attempts fail; CI exports native KiCad, XML netlist and fresh ERC reports.
