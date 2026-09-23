# servoHIL

Open Servo Hardware-in-the-Loop platform for robot-joint and servo-drive controller validation.

## Rev.A status

**PRELIMINARY / schematic phase / NO PCB LAYOUT**

Rev.A is deliberately limited to the chain that determines whether the single-axis platform is electrically viable:

    POWER -> HIL-Link -> Local I/O FPGA -> 8ch fast DAC -> DUT Adapter

Targets:
- ZU2CG plant model on AXU2CGB
- deterministic 1.8 V FPGA-to-FPGA HIL-Link
- local I/O FPGA for edge timestamping, DAC serialization and hardware safety
- 8-channel, 16-bit fast AO using 4 x AD3542R-16
- PWM/event timestamp granularity <= 5 ns
- PWM-to-DAC deterministic latency target < 1 us
- 20 kHz FOC Controller-HIL closed-loop PASS

ADC, general DIO, encoder PHY, CAN/RS485 and FIU hardware are deferred until the core path is frozen.

## Start here

- Architecture: `docs/architecture/servohil-io-v1-reva.md`
- System block: `docs/architecture/servohil-io-v1-reva-system-block.svg`
- Schematic plan: `docs/design/reva-schematic-plan.md`
- Power design: `docs/design/power-tree.md`
- J12 HIL-Link ICD: `docs/icd/j12-hil-link.csv`
- Local FPGA pin plan: `hardware/fpga/revA/`
- KiCad project: `hardware/kicad/revA/servohil_io_revA.kicad_pro`
- Core BOM: `bom/reva-core-bom.csv`

## Layout policy

PCB layout must not begin until:
1. power-tree values are frozen;
2. XC7A35T package/bank pin planning passes Vivado I/O review;
3. AXU2CGB J12 mapping matches XDC and schematic;
4. AD3542R output/reference/compensation network is reviewed;
5. KiCad ERC and schematic review pass.

`hardware/kicad/revA/layout_gate.yaml` is the machine-readable authority. CI rejects a `.kicad_pcb` file while `layout_allowed: false`.
