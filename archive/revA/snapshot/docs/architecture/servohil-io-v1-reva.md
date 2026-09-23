# ServoHIL-I/O V1 Rev.A architecture

Status: **PRELIMINARY / schematic phase / NO PCB LAYOUT**

## Scope

Rev.A is deliberately limited to:

    POWER -> HIL-Link -> Local I/O FPGA -> 8ch fast DAC -> DUT Adapter

ADC, general DIO, dual encoder PHY, CAN/RS485 and hardware FIU remain outside the Rev.A electrical freeze.

## System partition

    PC / pytest / GUI
           | Ethernet
           v
    AXU2CGB / ZU2CG
      inverter + PMSM + mechanics + gearbox + sensor model
           |
           | J12 / Bank66 / 1.8 V / source-synchronous DDR
           v
    Local I/O FPGA (XC7A35T-1FGG484I candidate)
      edge timestamp / HIL-Link / DAC serializer / watchdog / trace FIFO
           |
           v
    4 x AD3542R-16 = 8 fast analog outputs
           |
           v
    DUT Adapter -> STM32/GD32 joint controller

## Ownership

- ZU2CG PL owns the plant model.
- Local I/O FPGA owns deterministic I/O only.
- DUT Adapter owns DUT-specific scaling/clamping and physical fault insertion.
- Hardware safety holds the DAC and DUT power stage safe before FPGA configuration and after link loss.

## Rev.A targets

| Item | Target |
|---|---:|
| PWM/event timestamp granularity | <= 5 ns |
| HIL-Link source clock | 100 MHz |
| HIL-Link payload | 8-bit DDR each direction |
| Raw HIL-Link rate | 1.6 Gbit/s per direction |
| PWM -> simulated-current DAC latency | < 1 us deterministic target |
| DAC channels | 8 x 16-bit |
| FOC validation | 20 kHz physical Controller-HIL closed-loop PASS |

## Default AO mapping

| AO | Default function |
|---|---|
| AO0 | Ia sensor emulation |
| AO1 | Ib sensor emulation |
| AO2 | Ic sensor emulation |
| AO3 | Vbus sensor emulation |
| AO4 | torque sensor analog |
| AO5 | temperature/NTC emulation |
| AO6 | AUX0 |
| AO7 | AUX1 / calibration |

Mappings are metadata only; all eight channels remain electrically identical.
