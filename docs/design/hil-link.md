# Rev.A HIL-Link electrical interface

Status: **J12 schematic populated; Local-FPGA PACKAGE_PIN assignment remains UNASSIGNED**.

## Boundary

ServoHIL-I/O mates the AXU2CGB `J12` PL expansion connector through board connector `J10`.

The HIL-Link uses the AXU2CGB J12 PL bank at **1.8 V LVCMOS** and intentionally avoids level translators in the deterministic data path.

The J12 mapping authority remains:

`docs/icd/j12-hil-link.csv`

## Direction convention

Names are from the ZU2CG/Plant point of view:

```text
HL_TX* : ZU2CG -> Local I/O FPGA
HL_RX* : Local I/O FPGA -> ZU2CG
```

Local-FPGA directions therefore are:

- `HL_TX_CLK`, `HL_TX[7:0]`: inputs
- `HL_RX_CLK`, `HL_RX[7:0]`: outputs
- `HL_SYNC`: input
- `HL_IRQ`: output
- `HL_SAFE_N`, `HL_RESET_N`, `HL_HEARTBEAT`: inputs
- `TRIG[1:0]`: inputs in Rev.A
- DBG/SPARE/GC-reserve: bidirectional reserve

## Connector rules

- J10 pins 2, 39 and 40 are **NC**.
- ServoHIL does not consume or back-feed AXU connector 5 V / 3.3 V power.
- J10 pins 1, 37 and 38 are GND.
- all 34 PL I/O pins are retained in the pin plan, including reserve pins.
- connector footprint and stack height remain mechanical-TBD.

## Signal integrity policy

The physical connection is a short board-to-board/stack path, so Rev.A does not place TVS or level translation in the HIL-Link path.

For ZU2CG-driven signals:

- use conservative ZU2CG DRIVE/SLEW constraints where available;
- do not pretend a receiver-side resistor is source termination.

For Local-FPGA-driven signals:

- series damping footprints belong **near U10**, not near J10;
- initial candidate for `HL_RX_CLK`, `HL_RX[7:0]` and `HL_IRQ` is 22–33 Ω;
- exact value is an SI/bring-up item and will be implemented on sheet 05.

## Timing contract

Nominal link:

```text
clock              100 MHz
data               DDR
width              8 bit / direction
raw rate           1.6 Gbit/s / direction
TX frame           208 bit
serialization      about 130 ns
```

The incoming `HL_TX_CLK` is constrained as a 10 ns source-synchronous clock.

Input/output delay values are intentionally absent until:

1. FGG484 pin placement is frozen,
2. stack/trace flight time is estimated,
3. timing architecture in the Local FPGA is selected.

## Freeze gate

J12 electrical mapping can be considered schematic-complete only when CI proves:

- ICD active-net set equals KiCad active-net set,
- ICD active-net set equals `pin_plan.csv`,
- J10 has exactly 40 pins,
- pins 2/39/40 are NC,
- all active ports are LVCMOS18,
- XDC template includes every functional port group.

`j12_xdc_crosscheck` remains false until actual FGG484 PACKAGE_PIN values and a reviewed XDC exist.
