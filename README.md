# servoHIL

Personal / open Servo Hardware-in-the-Loop platform for robot-joint and servo-drive controller validation.

## Rev.A scope

The first hardware milestone is intentionally limited to the signal path that determines whether the platform is viable:

```text
POWER -> HIL-Link -> Local I/O FPGA -> 8ch fast DAC
```

Rev.A targets:

- ZU2CG plant model on AXU2CGB
- deterministic 1.8 V FPGA-to-FPGA HIL-Link
- local I/O FPGA for timestamping, DAC serialization and hardware safety
- 8-channel, 16-bit fast analog output using 4 x AD3542R-16
- hardware fail-safe path for DAC reset / DUT power-stage kill
- PWM edge timestamp resolution <= 5 ns
- PWM-to-DAC deterministic latency target < 1 us
- 20 kHz FOC controller-HIL closed-loop validation

ADC, general DIO, encoder PHY, CAN/RS485 and fault-insertion hardware are deferred until the core path is electrically frozen.

## Rev.A design baseline

- [System block diagram](docs/architecture/ServoHIL_IO_V1_RevA_System_Block.svg)
- [Schematic review](docs/design/ServoHIL_IO_V1_RevA_Block_and_Schematic.md)
- [Schematic freeze notes](docs/design/ServoHIL_IO_V1_RevA_Schematic_Notes.md)
- [AXU2CGB J12 HIL-Link ICD](docs/icd/ServoHIL_IO_V1_RevA_J12_HIL_Link_ICD.csv)
- [Core BOM](bom/ServoHIL_IO_V1_RevA_Core_BOM.csv)
- [KiCad development rules](hardware/kicad/README.md)
- [Rev.A KiCad project scaffold](hardware/kicad/servohil_io_v1_rev_a/README.md)
- [Local FPGA hardware contract](hardware/fpga/README.md)
- [HIL-Link XDC template](hardware/fpga/constraints/servohil_io_v1_reva_hil_link.xdc.in)
- [Authoritative hardware references](references/README.md)

## Repository structure

- `hardware/kicad/` — KiCad schematic / PCB sources
- `hardware/fpga/` — Local FPGA constraints and pin-planning artifacts
- `docs/architecture/` — system architecture and block diagrams
- `docs/design/` — electrical design notes and review gates
- `docs/icd/` — interface-control documents
- `bom/` — BOM and component decisions
- `references/` — source links and retained design references

## Development rule

PCB layout does **not** begin until:

1. power-tree values are frozen,
2. XC7A35T package/bank pin planning passes Vivado I/O review,
3. AXU2CGB J12 mapping matches XDC and schematic,
4. AD3542R output/reference network is reviewed against the latest datasheet/evaluation design,
5. schematic ERC and rail/current/thermal reviews pass.

Active Rev.A development branch: `feat/servohil-io-v1-reva-core-schematic`.
