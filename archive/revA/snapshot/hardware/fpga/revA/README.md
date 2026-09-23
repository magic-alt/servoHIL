# Rev.A Local I/O FPGA pin planning

Candidate device: **XC7A35T-1FGG484I**.

Exact PACKAGE_PIN assignments are intentionally not guessed. Generate them in Vivado I/O Planner after bank voltage, clock-capable pin and escape requirements are reviewed.

| Function | VCCO | Requirement |
|---|---:|---|
| configuration/QSPI/debug | 3.3 V | compatible flash/JTAG |
| HIL-Link | 1.8 V | source-synchronous 100 MHz DDR; clock-capable input pin |
| AD3542R digital | 1.8 V | SCLK/CS/SDIO/LDAC/RESET |
| future I/O | TBD | reserved for Rev.B |

Before schematic freeze:
- fill real FGG484 balls in `pin_plan.csv`;
- generate `servohil_io_revA.xdc` with PACKAGE_PIN and IOSTANDARD;
- add HIL-Link timing constraints;
- cross-check schematic pins against XDC;
- pass Vivado DRC for bank voltage and clock placement.
