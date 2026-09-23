# ServoHIL-I/O V1 Rev.A — detailed block and schematic review

This document complements the native KiCad hierarchy under `hardware/kicad/revA/`.

Scope remains frozen to:

```text
POWER -> HIL-Link -> Local FPGA -> 8ch fast DAC -> DUT Adapter
```

## 1. System partition

- AXU2CGB / ZU2CG owns inverter, PMSM, mechanics, gearbox and sensor plant models.
- Local I/O FPGA owns deterministic transport, edge timestamping, DAC serialization, trace FIFO and autonomous safe-state behavior.
- DUT Adapter owns controller-specific range scaling, clamp/protection and later physical fault insertion.
- Rev.A does not implement ADC, general DIO, encoder PHY, CAN/RS485 or FIU hardware.

## 2. POWER

Selected topology:

```text
9–15 V IN
  -> TVS
  -> TPS25947-class eFuse
  -> 12V_PROT
       -> ADP5054
            -> 1V0_FPGA
            -> 1V8_D
            -> 3V3_D
            -> 6V0_PRE
                 -> LT3045 -> +5V0_DAC
                 -> LT3045 -> +5V2_PVDD
       -> LTC7149 -> -6V0_PRE -> LT3094 -> -5V2_PVSS

+5V0_DAC -> ADR4525 -> VREF_2V5
```

A small 3V3_AON rail supplies the sequencer/supervisor path before the main FPGA rails are released.

Target power order:

1. 1V0
2. 1V8
3. 3V3
4. analog preregulator
5. positive/negative DAC rails

Final ADP5054 inductors, switching frequencies, compensation and capacitance are not frozen until Vivado/XPE current estimates and transient/thermal calculations are available.

## 3. HIL-Link

Boundary: AXU2CGB J12 / ZU2CG Bank66 / 1.8 V.

Electrical contract:

- LVCMOS18
- 100 MHz source-synchronous clock
- DDR data
- 8 bits each direction
- per-frame sequence and CRC
- dedicated safe/reset/heartbeat sideband
- source damping footprint on FPGA-driven groups

The raw link rate is 1.6 Gbit/s per direction.

Fast Plant-to-I/O frame:

```text
SEQ       16 bit
AO0..7   128 bit
FAST_DO   32 bit
CONTROL   16 bit
CRC16     16 bit
----------------
TOTAL    208 bit
```

At 1.6 Gbit/s this is about 130 ns serialization time.

The authoritative J12 pin assignment is `docs/icd/j12-hil-link.csv`. The schematic and Local-FPGA XDC must be cross-checked against that file.

## 4. Local I/O FPGA

Candidate device: `XC7A35T-1FGG484I`.

The device does **not** run the PMSM plant.

Initial bank intent:

- configuration/QSPI/debug: 3.3 V
- HIL-Link: 1.8 V
- AD3542R digital interface: 1.8 V
- future I/O banks remain reserved

Concrete FGG484 PACKAGE_PIN values remain unassigned until Vivado I/O Planner and DRC pass.

## 5. 8-channel fast DAC

Four identical AD3542R-16 devices:

| Device | Channel A | Channel B |
| --- | --- | --- |
| U20 | AO0 / Ia | AO1 / Ib |
| U21 | AO2 / Ic | AO3 / Vbus |
| U22 | AO4 / Torque | AO5 / Temperature |
| U23 | AO6 / AUX0 | AO7 / AUX1 |

Shared:

- DAC_SCLK
- DAC_LDAC_N
- DAC_RESET_N
- VREF_2V5

Per device:

- one CS_N
- two SDIO lanes for dual-SPI operation

Power intent:

- DVDD = 1.8 V
- VLOGIC = 1.8 V
- AVDD = +5.0 V
- PVDD = +5.2 V
- PVSS/AVSS = -5.2 V

Rev.A output target is fixed ±5 V capability.

For the fixed -5 V to +5 V output range, use the device feedback selection required by the current AD3542R datasheet and keep the CAPx-to-VOUTx NP0/C0G compensation footprint tunable.

The AO series resistor is also tunable. 33 / 49.9 / 52.3 ohm are bring-up candidates; the final value is selected from measured step response with the real DUT-adapter cable and ADC input network.

## 6. Hardware safety

The analog-output path must default SAFE without FPGA firmware.

Conceptually:

```text
DAC_RESET_N =
    FPGA_CONFIG_OK
  AND MANDATORY_POWER_GOOD
  AND HIL_LINK_WATCHDOG_OK
```

DAC_RESET_N is physically biased to the asserted state.

Any of the following must force the safe state:

- FPGA unconfigured/reset,
- mandatory rail fault,
- HIL-Link clock loss,
- HIL-Link heartbeat timeout,
- repeated frame/CRC fault condition.

## 7. Layout gate

Do not begin Rev.A PCB layout until:

1. power-tree values and thermal/current budget are frozen;
2. XC7A35T bank/ball planning passes Vivado I/O review;
3. J12 ICD, schematic and XDC cross-check passes;
4. AD3542R output/reference/compensation network is reviewed;
5. KiCad ERC passes;
6. hardware fail-safe path is reviewed;
7. HIL-Link timing constraints are drafted;
8. bring-up plan is accepted.

`hardware/kicad/revA/layout_gate.yaml` is the machine-readable authority.

## 8. Bring-up order

```text
rails
 -> FPGA configuration
 -> HIL-Link PRBS
 -> static DAC output
 -> 8-channel LDAC synchronization
 -> PWM -> Plant -> DAC latency
 -> 20 kHz Controller-HIL closed loop
```

Primary Rev.A targets:

- event timestamp granularity <= 5 ns
- deterministic PWM-to-DAC latency < 1 us
- 20 kHz physical Controller-HIL FOC closed-loop PASS
