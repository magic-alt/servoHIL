# Local I/O FPGA hardware contract

Device candidate: `XC7A35T-1FGG484I`.

The local FPGA is an I/O engine, not the plant solver.

Responsibilities:

- source-synchronous HIL-Link endpoint,
- PWM/event timestamp transport,
- frame CRC and event FIFO,
- AD3542R serializer and synchronous LDAC,
- autonomous watchdog and safe-state generation,
- future ADC/DIO/encoder PHY glue.

Initial bank intent:

| Bank | VCCO | Role |
| --- | --- | --- |
| 0 | 3.3 V | configuration / QSPI / JTAG |
| 14 | 1.8 V | AXU2CGB J12 HIL-Link |
| 15 | 1.8 V | AD3542R digital interface |
| 16/34/35 | TBD | future Rev.B I/O |

Concrete PACKAGE_PIN constraints are deliberately deferred until Vivado I/O Planner validates the complete bank assignment.
