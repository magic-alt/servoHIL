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

See the Rev.A design documents on the active hardware-development branch.
