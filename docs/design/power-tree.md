# Rev.A power architecture

Status: **real schematic populated; switching-stage values remain PRELIM until freeze gates pass**.

## Topology

```text
9-15 V input
  -> SMBJ16A-class TVS
  -> TPS259474L eFuse
       UVLO ~8.0 V
       OVLO ~15.9 V
       current limit ~4 A
       controlled dV/dt
       PG -> 3V3_AON domain
  -> 12V_PROT
       |
       +-> TPS70933 -> 3V3_AON
       |
       +-> ADP5054
       |     CH1 -> 1V0_FPGA
       |       external low-side NFET required
       |     CH3 -> 1V8_D
       |     CH4 -> 3V3_D
       |     CH2 -> 6V0_PRE
       |       external low-side NFET required
       |
       +-> LTC7149 -> -6V0_PRE

6V0_PRE
  +-> LT3045 -> +5V0_DAC
  +-> LT3045 -> +5V2_PVDD

-6V0_PRE -> LT3094 -> -5V2_PVSS
+5V0_DAC -> ADR4525 -> VREF_2V5
```

## Sequencing

A TPS70933 3.3 V always-on rail powers the sequencer and safety logic.

`EFUSE_PG` is RC-delayed and passed through a Schmitt input before driving the ADM1186 `UP` input. This is intentional: ADM1186 `UP` must receive a valid rising edge after its supply is established rather than being hard-wired high at power-up.

Sequence intent:

```text
1V0_FPGA
  -> 1V8_D
  -> 3V3_D
  -> 6V0_PRE
  -> ANALOG_EN
  -> +5V0_DAC / +5V2_PVDD / -6V0_PRE path
  -> -5V2_PVSS
```

The current schematic maps ADM1186 outputs as:

| Sequencer output | ADP5054 channel | Rail |
|---|---|---|
| OUT1 | CH1 | 1V0_FPGA |
| OUT2 | CH3 | 1V8_D |
| OUT3 | CH4 | 3V3_D |
| OUT4 | CH2 | 6V0_PRE |

`ANALOG_EN` is derived from the sequencer PWRGD path and enables the low-noise analog supply chain.

## Preliminary rail budget

| Rail | Main load | Preliminary budget | Status |
|---|---|---:|---|
| 1V0_FPGA | XC7A35T VCCINT/VCCBRAM | 1.5 A | pending XPE |
| 1V8_D | VCCAUX/VCCO + HIL-Link + DAC logic | 1.2 A | pending XPE |
| 3V3_D | config flash / Bank0 / debug | 1.2 A | pending pin plan |
| 6V0_PRE | positive analog preregulator | 0.8 A | pending DAC load |
| +5V0_DAC | DAC AVDD + reference | 0.25 A | pending model |
| +5V2_PVDD | DAC positive output stage | 0.25 A + load | pending load |
| -6V0_PRE | LT3094 input | 0.25 A class | pending DAC load |
| -5V2_PVSS | DAC negative output stage | 0.25 A + load | pending load |

## Values currently placed in the schematic

These values are engineering starting points, not PCB-freeze values:

- TPS259474L UV/OV divider: 680 kΩ / 60.4 kΩ / 60.4 kΩ.
- TPS259474L RILM: 825 Ω, approximately 4 A class.
- TPS259474L dV/dt capacitor: 3.3 nF.
- ADP5054 oscillator: 32.4 kΩ RT, 600 kHz class.
- ADP5054 CH1/CH2 low-side current-limit programming: 47 kΩ class.
- ADP5054 output inductors: 1.0 / 4.7 / 3.3 / 4.7 µH for CH1/CH2/CH3/CH4, all **PRELIM**.
- ADP5054 compensation: 10 kΩ + 2.2 nF starting network, **PRELIM**.
- LT3045 SET: 49.9 kΩ for +5.0 V and 52.0 kΩ for +5.2 V.
- LTC7149 SET: 120 kΩ for -6 V class, with demo-derived magnetics/compensation marked **PRELIM**.
- LT3094 SET: 52.0 kΩ for -5.2 V; ILIM 15 kΩ for ~250 mA class.
- ADR4525 provides VREF_2V5.

## Important ADP5054 implementation detail

ADP5054 Channels 1 and 2 integrate the high-side FET but use **external low-side NFETs** driven from DL1/DL2. Channels 3 and 4 integrate both high- and low-side switches. The Rev.A schematic explicitly includes Q1/Q2; their exact part number remains a freeze item.

## Not frozen yet

Do not authorize PCB placement based on the current power-stage passives.

The following still require review:

- Vivado/XPE current estimates for the XC7A35T;
- ADP5054 inductor saturation/ripple design;
- CH1/CH2 low-side MOSFET selection and thermal loss;
- output capacitance after DC-bias derating;
- loop compensation/stability;
- 9-15 V min/max duty-cycle and timing margins;
- load-step response;
- startup monotonicity;
- regulator junction temperature;
- LTC7149 negative-rail transient/stability behavior.

Until those close, `power_tree_frozen` in `layout_gate.yaml` remains false.
