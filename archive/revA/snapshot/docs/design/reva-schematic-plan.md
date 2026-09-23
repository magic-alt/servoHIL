# Rev.A schematic implementation plan

Status: **PRELIMINARY / no layout authorization**

The KiCad project is hierarchical. This baseline establishes sheet ownership and electrical contracts before exact FPGA BGA balls and regulator magnetics are frozen.

| Sheet | Purpose | Freeze prerequisite |
|---|---|---|
| 01_POWER_ENTRY | input connector, TVS, eFuse, current limit, power-good | input range/current budget |
| 02_ANALOG_POWER | +5.0 V, +5.2 V, -5.2 V, 2.5 V reference | DAC load assumptions |
| 03_DIGITAL_POWER | 1.0/1.8/3.3 V, sequencing, supervisor | FPGA power estimator |
| 04_AXU_HIL_LINK | AXU2CGB J12 and 1.8 V HIL-Link | J12/manual cross-check |
| 05_IO_FPGA | XC7A35T configuration, clock, banks, hardware safety | Vivado pin plan |
| 06_DAC_0_3 | AD3542R U20/U21, AO0-AO3 | latest datasheet/eval review |
| 07_DAC_4_7 | AD3542R U22/U23, AO4-AO7, shared reference | latest datasheet/eval review |

## Electrical contracts

### HIL-Link
- 1.8 V LVCMOS, direct FPGA-to-FPGA connection.
- 100 MHz source-synchronous DDR.
- eight data bits in each direction.
- per-frame sequence number and CRC.
- source damping footprint on FPGA-driven lines.
- link timeout forces hardware safe state.

### Local FPGA
Candidate: `XC7A35T-1FGG484I`.
- configuration bank: 3.3 V;
- HIL-Link bank: 1.8 V;
- DAC digital bank: 1.8 V;
- exact FGG484 balls remain UNASSIGNED until Vivado I/O Planner/DRC.

### DAC
- 4 x AD3542R-16, two outputs each.
- shared DAC_LDAC_N, DAC_RESET_N and precision reference.
- one chip-select per DAC.
- four devices preloaded in parallel, then one shared LDAC edge.
- Rev.A output target: +/-5 V class.
- DUT-specific 0-3.3 V scaling/clamping belongs to DUT Adapter.

### Hardware safety
`DAC_RESET_N` defaults low through a physical pull-down. FPGA firmware is not the sole safety mechanism.
