# KiCad hardware development rules

The native Rev.A project lives in `hardware/kicad/revA/`.

Rev.A is currently in the **schematic phase**. The machine-readable layout authority is `hardware/kicad/revA/layout_gate.yaml`.

## Sheet ownership

- 01_POWER_ENTRY
- 02_ANALOG_POWER
- 03_DIGITAL_POWER
- 04_AXU_HIL_LINK
- 05_IO_FPGA
- 06_DAC_0_3
- 07_DAC_4_7

Future ADC/DIO/Encoder/CAN/RS485/FIU sheets remain deferred.

## Rules

- Do not guess regulator magnetics/compensation.
- Do not guess XC7A35T BGA balls directly in KiCad.
- Treat `docs/icd/j12-hil-link.csv` as the J12 mapping authority.
- Treat Vivado I/O Planner/XDC as the FPGA pin-placement authority.
- Treat KiCad ERC plus schematic review as mandatory before layout.
- Generated fabrication output is not source-of-truth.

## Before layout

All entries in `layout_gate.yaml` must pass in a reviewed commit. CI intentionally blocks premature PCB layout.
