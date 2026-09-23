# ServoHIL-I/O V1 Rev.A — schematic freeze notes

Scope: **POWER → HIL-Link → Local FPGA → 8ch DAC**. No PCB layout in this revision.

## Fixed architecture

- AXU2CGB J12 / Bank66 / 1.8 V is the deterministic HIL-Link.
- Local I/O FPGA: XC7A35T-1FGG484I.
- 4× AD3542R-16 = 8 fast AO.
- Shared LDAC, RESET and 2.5 V reference; independent CS per DAC.
- Rev.A analog output capability: ±5 V, +5.2/-5.2 V output-stage rails.
- Hardware default state is SAFE: DAC_RESET_N is pulled low until config + PGOOD + HIL watchdog all pass.

## Power topology

```text
9–15 V IN
  -> TVS
  -> TPS259470L eFuse
  -> 12V_PROT
       -> ADP5054: 1V0 / 1V8 / 3V3 / 6V0_PRE
       -> LT3045: +5V0_DAC
       -> LT3045: +5V2_PVDD
       -> LTC7149: -6V0_PRE
            -> LT3094: -5V2_PVSS
```

ADR4525 provides the shared 2.5 V DAC reference.

## HIL-Link

- 1.8 V LVCMOS
- 100 MHz source-synchronous DDR
- 8-bit each direction
- 1.6 Gbit/s theoretical per direction
- CRC protected fast frames
- dedicated heartbeat / safe / reset control signals

## DAC architecture

- U20: AO0 Ia, AO1 Ib
- U21: AO2 Ic, AO3 Vbus
- U22: AO4 Torque, AO5 Temperature
- U23: AO6 AUX0, AO7 AUX1
- shared SCLK / LDAC_N / RESET_N / VREF
- one CS_N per AD3542R
- two SDIO data lanes per DAC for dual-SPI operation

For the fixed -5 V to +5 V range, use the AD3542R RFB2_x feedback selection and program CHx_OUTPUT_RANGE_SEL=011. CAPx-to-VOUTx uses an NP0/C0G tuning footprint.

The AO source resistor is not frozen. The design keeps a replaceable footprint for 33 / 49.9 / 52.3 ohm validation; 52.3 ohm is the initial reference for high-Z/coax validation.

## Safety

DAC_RESET_N must remain asserted unless all are true:

1. FPGA configuration completed,
2. critical rails are power-good,
3. HIL-Link watchdog is healthy.

A link timeout, clock loss, CRC fault storm, FPGA reset or power fault must return the DAC path to a safe state without software intervention.

## Do not start layout until

1. J12 mapping and ZU2CG XDC are reviewed.
2. ADP5054 load estimates and compensation/inductor values are validated.
3. Artix-7 package-bank pin assignment passes Vivado I/O planning.
4. AD3542R RFB/CAP network is reviewed against the current datasheet/evaluation schematic.
5. ERC and rail/current/thermal review pass.
