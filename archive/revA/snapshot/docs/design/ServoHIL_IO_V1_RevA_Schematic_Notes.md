# ServoHIL-I/O V1 Rev.A — schematic freeze notes

Scope: **POWER → HIL-Link → Local FPGA → 8ch DAC**. PCB layout is explicitly out of scope until the layout gate passes.

## Frozen architecture

- AXU2CGB J12 / Bank66 / 1.8 V is the deterministic HIL-Link boundary.
- ZU2CG remains the Plant solver.
- XC7A35T-1FGG484I is the Local I/O FPGA candidate.
- 4× AD3542R-16 provide 8 fast analog outputs.
- LDAC, RESET and precision reference are shared; CS remains per DAC.
- Rev.A targets a ±5 V-class output path using +5.2 V / -5.2 V output-stage rails.
- The hardware default state is SAFE.

## Intentionally not frozen yet

- ADP5054 inductors, switching frequencies and compensation.
- exact XC7A35T FGG484 PACKAGE_PIN assignments.
- DAC CAPx compensation value.
- final AO source-series resistance.
- PCB placement/routing.

## Schematic freeze prerequisites

1. Vivado/XPE rail estimates are available.
2. J12 pinout is cross-checked against the ALINX manual.
3. Local-FPGA bank plan passes Vivado I/O DRC.
4. AD3542R network is reviewed against current vendor primary documentation.
5. KiCad ERC passes.
6. power/current/thermal budget is reviewed.
7. fail-safe logic is proven independent of application firmware.
