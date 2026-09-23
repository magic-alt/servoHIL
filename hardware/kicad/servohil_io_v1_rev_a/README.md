# ServoHIL-I/O V1 Rev.A KiCad project

Status: **schematic-entry phase**.

Current implementation scope:

1. POWER entry and rail sequencing
2. AXU2CGB J12 HIL-Link
3. XC7A35T local I/O FPGA
4. 4× AD3542R-16 / 8-channel fast AO

## Required sheets

- `00_TOP.kicad_sch`
- `01_POWER_ENTRY.kicad_sch`
- `02_ANALOG_POWER.kicad_sch`
- `03_DIGITAL_POWER.kicad_sch`
- `04_AXU_HIL_LINK.kicad_sch`
- `05_IO_FPGA.kicad_sch`
- `06_DAC_0_3.kicad_sch`
- `07_DAC_4_7.kicad_sch`

## Net naming

Power:
- `12V_PROT`
- `3V3_AON`
- `1V0_FPGA`
- `1V8_D`
- `3V3_D`
- `6V0_PRE`
- `+5V0_DAC`
- `+5V2_PVDD`
- `-6V0_PRE`
- `-5V2_PVSS`
- `VREF_2V5`

HIL-Link:
- `HL_TX[0..7]`
- `HL_RX[0..7]`
- `HL_TX_CLK`
- `HL_RX_CLK`
- `HL_SYNC`
- `HL_IRQ`
- `HL_SAFE_N`
- `HL_RESET_N`
- `HL_HEARTBEAT`

DAC:
- `DAC_SCLK`
- `DAC_CS[0..3]_N`
- `DAC_SDIO[0..7]`
- `DAC_LDAC_N`
- `DAC_RESET_N`
- `AO[0..7]`

Do not assign Artix-7 BGA balls in KiCad before the Vivado I/O planning file is reviewed.
