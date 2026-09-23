# Rev.A power architecture

Status: **topology selected; magnetics/compensation not frozen**.

    9-15 V input
      -> TVS / input protection
      -> TPS25947-class eFuse / current limiting
      -> 12V_PROT
          -> ADP5054-class quad buck
               -> 1V0_FPGA
               -> 1V8_D
               -> 3V3_D
               -> 6V0_PRE
                   -> LT3045 -> +5V0_DAC
                   -> LT3045 -> +5V2_PVDD
          -> LTC7149-class negative preregulator -> -6V0_PRE -> LT3094 -> -5V2_PVSS

A small always-on 3.3 V rail powers sequencer/watchdog before main FPGA rails.

| Rail | Main load | Preliminary budget | Status |
|---|---|---:|---|
| 1V0_FPGA | XC7A35T VCCINT/VCCBRAM | 1.5 A | pending XPE |
| 1V8_D | VCCAUX/VCCO + HIL-Link + DAC logic | 1.2 A | pending XPE |
| 3V3_D | config flash / Bank0 / debug | 1.2 A | pending pin plan |
| 6V0_PRE | positive analog preregulator | 0.8 A | pending DAC load |
| +5V0_DAC | DAC AVDD + reference | 0.25 A | pending model |
| +5V2_PVDD | DAC positive output stage | 0.25 A + load | pending load |
| -5V2_PVSS | DAC negative output stage | 0.25 A + load | pending load |

Target sequence: `1.0 V -> 1.8 V -> 3.3 V -> analog preregulator -> +/- analog rails`.

`DAC_RESET_N` stays asserted until FPGA configuration, mandatory rail PGOOD and HIL-Link watchdog are healthy.

## Intentionally not frozen

Do not select final ADP5054 inductors, switching frequencies, compensation components or output capacitance from rules of thumb. Freeze only after Vivado/XPE rail estimates, DAC load assumptions, regulator design calculation, transient review and junction-temperature review.
