# ServoHIL-I/O V1 Rev.A — block and schematic review

This file is the diff-friendly source-of-truth companion to the rendered review PDF.

Scope: **POWER → HIL-Link → Local FPGA → 8ch DAC**.

## 01 System block

```text
AXU2CGB / ZU2CG
  Inverter + PMSM + Mechanics Plant
            |
            | J12 / Bank66 / 1.8 V
            | 100 MHz source-synchronous DDR
            v
      Local I/O FPGA
      XC7A35T-1FGG484I
            |
            | DAC serializer + shared LDAC
            v
      4 × AD3542R-16
            |
          AO0..7
            v
        DUT Adapter
            |
            v
        Joint DUT
```

The local FPGA is an I/O engine only. The plant solver stays in ZU2CG.

## 02 POWER

Input chain:

```text
9–15 V IN
  -> TVS
  -> TPS259470L eFuse
  -> 12V_PROT
```

Digital/FPGA rails:

```text
12V_PROT -> ADP5054
              CH1 -> 1V0_FPGA
              CH2 -> 6V0_PRE
              CH3 -> 1V8_D
              CH4 -> 3V3_D
```

Analog rails:

```text
6V0_PRE  -> LT3045 -> +5V0_DAC
6V0_PRE  -> LT3045 -> +5V2_PVDD
12V_PROT -> LTC7149 -> -6V0_PRE -> LT3094 -> -5V2_PVSS
+5V0_DAC -> ADR4525 -> VREF_2V5
```

Sequencing target:

1. 1V0
2. 1V8
3. 3V3
4. 6V0_PRE and analog rails

A separate 3V3_AON rail powers the sequencer/supervisor path.

## 03 HIL-Link

Electrical:

- 1.8 V LVCMOS
- 100 MHz source clock
- DDR
- 8-bit per direction
- 1.6 Gbit/s theoretical per direction
- source damping footprint at each Local-FPGA-driven group

Fast ZU2CG → I/O frame:

```text
SEQ       16
AO0..7   128
FAST_DO   32
CONTROL   16
CRC16     16
-------------
TOTAL    208 bits
```

208-bit serialization at 1.6 Gbit/s is about 130 ns.

Dedicated sideband nets:

- HL_SYNC
- HL_IRQ
- HL_SAFE_N
- HL_RESET_N
- HL_HEARTBEAT
- TRIG0/1
- DBG/SPARE

See `docs/icd/ServoHIL_IO_V1_RevA_J12_HIL_Link_ICD.csv`.

## 04 Local FPGA

Candidate: `XC7A35T-1FGG484I`.

Initial bank intent:

- Bank0 / 3.3 V: configuration, QSPI, JTAG
- Bank14 / 1.8 V: HIL-Link
- Bank15 / 1.8 V: AD3542R digital interface
- additional banks reserved for Rev.B I/O

No PACKAGE_PIN is frozen until Vivado I/O Planner review.

Required hardware safety:

```text
DAC_RESET_N =
    FPGA_CONFIG_OK
  AND POWER_GOOD
  AND HIL_LINK_WATCHDOG_OK
```

DAC_RESET_N has a hardware pull-down so the unpowered/unconfigured state is SAFE.

## 05–06 8-channel DAC

Four identical dual-channel devices:

- U20: AO0 Ia / AO1 Ib
- U21: AO2 Ic / AO3 Vbus
- U22: AO4 Torque / AO5 Temperature
- U23: AO6 AUX0 / AO7 AUX1

Shared:

- DAC_SCLK
- DAC_LDAC_N
- DAC_RESET_N
- VREF_2V5

Per device:

- independent CS_N
- two SDIO lanes for dual-SPI operation

Power:

- DVDD = 1.8 V
- VLOGIC = 1.8 V
- AVDD = +5.0 V
- PVDD = +5.2 V
- PVSS/AVSS = -5.2 V

Rev.A output target: fixed ±5 V capability.

For the fixed -5 V to +5 V range, use RFB2_x and program `CHx_OUTPUT_RANGE_SEL=011`. CAPx-to-VOUTx keeps an NP0/C0G tuning footprint.

Each AO keeps a replaceable source-series resistor footprint. 33 / 49.9 / 52.3 ohm are validation candidates; the final value is selected from the real DUT-adapter cable/input-capacitance step response.

## 07 Schematic freeze gate

Do not start KiCad PCB layout until all are complete:

1. power-tree component values and thermal/current budget frozen,
2. Artix-7 bank/ball assignment passes Vivado I/O review,
3. AXU2CGB J12 mapping matches XDC and schematic,
4. AD3542R RFB/CAP/output network reviewed,
5. ERC passes,
6. power-good and fail-safe paths reviewed,
7. HIL-Link timing constraints drafted,
8. bring-up plan accepted.

Bring-up order:

```text
rails
 -> FPGA configuration
 -> HIL-Link PRBS
 -> DAC static output
 -> 8-channel LDAC synchronization
 -> PWM -> Plant -> DAC latency
 -> 20 kHz controller-HIL closed loop
```
