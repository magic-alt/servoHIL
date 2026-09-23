# KiCad hardware source

Target tool: KiCad 8.x or newer.

## Rev.A source tree

The first board is developed under `hardware/kicad/servohil_io_v1_rev_a/`.

Schematic hierarchy:

```text
00_TOP
01_POWER_ENTRY
02_ANALOG_POWER
03_DIGITAL_POWER
04_AXU_HIL_LINK
05_IO_FPGA
06_DAC_0_3
07_DAC_4_7
```

Future sheets for ADC/DIO/Encoder/CAN/RS485/FIU are intentionally excluded until the core path is electrically frozen.

## Layout gate

Do not create or route `.kicad_pcb` as the implementation baseline until:

- schematic ERC passes,
- FPGA bank/ball planning passes,
- J12 schematic and XDC match,
- power budget and compensation values are frozen,
- AD3542R feedback/output network is reviewed,
- Rev.A schematic review is accepted.

Generated Gerbers, plots, caches and temporary files are not source-of-truth.
