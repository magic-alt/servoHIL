# Rev.A HIL-Link / Local FPGA / DAC schematic review

Status: **electrical hierarchy complete; KiCad ERC 0 errors / 0 warnings; PCB layout still blocked**.

## 04_AXU_HIL_LINK

Implemented from `docs/icd/j12-hil-link.csv`:

- J10 mirrors AXU2CGB J12 2×20 pinout.
- Bank66 interface is treated as 1.8 V logic.
- AXU board 5 V / 3.3 V connector power pins are explicit NC.
- ZU2CG → Local FPGA: `HL_TX[7:0]`, `HL_TX_CLK`, `HL_SYNC`, safety/control inputs.
- Local FPGA → ZU2CG: `HL_RX[7:0]`, `HL_RX_CLK`, `HL_IRQ`.
- ServoHIL-source outputs use 33 Ω starting source-series resistors.
- unused GC/debug/spare pins are explicit NC rather than floating named nets.

The 33 Ω value is a signal-integrity starting point, not a final impedance result.

## 05_IO_FPGA

Implemented:

- U10 `XC7A35T-1FGG484I FUNCTIONAL_PRELAYOUT`.
- 1V0 / 1V8 / 3V3 rail contracts.
- complete logical HIL-Link port set.
- complete DAC serializer/control port set.
- W25Q128-class QSPI configuration flash.
- 100 MHz / 1.8 V oscillator.
- JTAG boundary.
- configuration pull-ups and representative bulk decoupling.
- independent watchdog and hardware safe-release chain.
- `DAC_RESET_N` has a 100 kΩ default-safe pull-down.

Safety qualification is intentionally outside the FPGA application logic:

```text
FPGA_DONE
    AND SEQ_DONE
    AND external watchdog OK
        -> SAFE_RELEASE_3V3
        -> 3.3V / 1.8V safety translation
        -> DAC_RESET_N
```

Exact FGG484 balls are still **UNASSIGNED**. KiCad must not become the source of PACKAGE_PIN truth; Vivado I/O Planner is.

## 06 / 07 AD3542R

Four 28-pin electrical instances are implemented:

| Ref | Outputs |
|---|---|
| U20 | AO0 Ia / AO1 Ib |
| U21 | AO2 Ic / AO3 Vbus |
| U22 | AO4 Torque / AO5 Temperature |
| U23 | AO6 AUX0 / AO7 AUX1 |

Rev.A fixed electrical contract:

- DVDD = 1.8 V
- VLOGIC = 1.8 V
- AVDD = +5.0 V
- PVDD = +5.2 V
- PVSS = -5.2 V
- VREF = 2.5 V external reference
- ±5 V output mode uses `RFB2_y` feedback
- `RFB1_y` and `RFB4_y` are explicit NC
- CFB uses DNP NP0/C0G tuning footprints
- AO source resistance starts at 52.3 Ω and remains tunable
- ALERT pins have 1.8 V pull-ups
- shared `DAC_LDAC_N` / `DAC_RESET_N` / `DAC_SCLK`
- independent chip select and dual-SPI data lanes

J20 now provides the explicit DUT analog-output boundary:

```text
AO0..AO7 + GND + GND
```

Connector family/footprint remains a mechanical-layout decision.

## FPGA constraint artifacts

`hardware/fpga/revA/pin_plan.csv` now includes HIL-Link, DAC, QSPI and watchdog-service signals.

All FGG484 package-pin fields deliberately remain:

```text
package_pin = empty
status = UNASSIGNED
```

Templates:

- `hil_link_ports.xdc.tmpl`
- `dac_ports.xdc.tmpl`

The HIL template establishes 100 MHz source-synchronous intent; exact I/O delays wait for package pin selection and PCB flight time.

The DAC template constrains the 1.8 V interface and uses the AD3542R 66 MHz maximum SCLK basis.

## Validation

Latest full-hierarchy CI:

```text
KiCad CLI             10.0.6
structure check       PASS
layout gate           PASS (layout disabled)
POWER contract        PASS
core contract         PASS
hierarchy parse       PASS
ERC errors            0
ERC warnings          0
schematic PDF export  PASS
```

## Remaining freeze work before PCB layout

- [ ] Vivado/XPE power estimates
- [ ] ADP5054 magnetics / compensation / MOSFET / thermal freeze
- [ ] LTC7149 negative-rail transient/stability freeze
- [ ] full verified package symbols / footprints where still pre-layout
- [ ] XC7A35T FGG484 I/O Planner assignment
- [ ] reviewed PACKAGE_PIN XDC
- [ ] J12 ↔ schematic ↔ XDC sign-off
- [ ] AD3542R footprint / CFB / cable-load / source-resistor analog review
- [ ] only then set `layout_allowed: true`
