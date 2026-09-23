# Rev.A power schematic implementation review

Status: **POWER sheets populated; ERC/freeze gates still open**.

This document records what is intentionally real, what is preliminary, and what must be verified before layout.

## 01_POWER_ENTRY

Implemented:

- J1 9-15 V DC input.
- SMBJ16A-class input TVS.
- input bulk + ceramic decoupling.
- TPS259474L eFuse.
- UVLO/OVLO divider.
- ~4 A current-limit programming.
- dV/dt capacitor.
- fault timer capacitor.
- programmable PGTH divider.
- 3V3_AON pull-up for `EFUSE_PG`.
- 12V_PROT output decoupling.

Current candidate thresholds:

```text
UVLO ≈ 8.0 V
OVLO ≈ 15.9 V
ILIM ≈ 4 A class
```

The exact surge profile and TVS energy rating remain an input-interface verification item.

## 02_ANALOG_POWER

Implemented:

- LT3045 +5V0_DAC post-regulator.
- LT3045 +5V2_PVDD post-regulator.
- LTC7149 negative preregulator to -6V0_PRE.
- LT3094 negative post-regulator to -5V2_PVSS.
- ADR4525 VREF_2V5.
- input/output and SET capacitors.
- LT3045 PG left unused while PGFB is tied to input per the device guidance.
- LT3045 and LT3094 exposed-pad electrical connections are represented.
- LT3094 unused PG/VIOC handling is explicit.

The LTC7149 switching components are deliberately marked PRELIM.

## 03_DIGITAL_POWER

Implemented:

- TPS70933 3V3_AON supply.
- delayed `SEQ_START` from `EFUSE_PG`.
- ADM1186-1 rail sequencing/monitoring.
- explicit pull-ups for open-drain sequencer outputs.
- ADP5054 channel assignment.
- external low-side Q1/Q2 for ADP5054 CH1/CH2.
- RT programming and VDD/VREG decoupling.
- CFG12/CFG34 and SYNC/MODE baseline states.
- four bootstrap capacitors.
- four feedback-divider networks.
- four compensation starting networks.
- CH1/CH2 DL current-limit programming.
- per-channel input bypass and output bulk capacitors.

### ADP5054 symbol status

The schematic currently uses a **functional pre-layout symbol** containing the pins required to review the power topology. It intentionally has no footprint assignment.

Before `fpga_pinplan_frozen` / `power_tree_frozen` allow layout, replace it with a complete verified 48-lead LFCSP symbol including every duplicated PVIN/SW/PGND pin and exposed pad, then cross-check against the vendor pin table.

This is intentional: a fake complete footprint mapping is worse than an explicit pre-layout functional symbol.

## Safety / sequencing rule

The power tree alone does not release the DAC path. Later core sheets must still enforce:

```text
DAC_RESET_N =
  FPGA_CONFIG_OK
  AND MANDATORY_POWER_GOOD
  AND HIL_LINK_WATCHDOG_OK
```

The default unpowered/unconfigured state remains SAFE.

## Exit requirements for the power phase

- [ ] KiCad CLI parses all Rev.A hierarchy sheets.
- [ ] KiCad ERC report generated and reviewed.
- [ ] no duplicate references across Rev.A hierarchy.
- [ ] power-schematic contract test passes.
- [ ] Vivado/XPE current budget imported.
- [ ] ADP5054 passives calculated/frozen.
- [ ] Q1/Q2 MOSFET selected and loss checked.
- [ ] LTC7149 negative-rail design verified.
- [ ] thermal budget reviewed.
- [ ] `power_tree_frozen` set true only in a dedicated reviewed change.
