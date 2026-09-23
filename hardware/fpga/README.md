# Local I/O FPGA hardware contract

Candidate device: `XC7A35T-1FGG484I`.

The Local FPGA is a deterministic I/O engine, not the plant solver.

Responsibilities:

- HIL-Link endpoint,
- edge/event timestamping,
- frame CRC and FIFO,
- AD3542R serialization and LDAC scheduling,
- autonomous watchdog/safe-state generation,
- future ADC/DIO/encoder PHY glue.

The Rev.A FPGA source-of-truth is under `hardware/fpga/revA/`.

Concrete PACKAGE_PIN constraints must originate from Vivado I/O Planner and then be cross-checked against the KiCad schematic. No BGA ball assignment is to be invented in documentation first.
