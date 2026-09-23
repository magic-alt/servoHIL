# Rev.A HIL-Link electrical interface

Status: **schematic-complete; FGG484 PACKAGE_PIN and post-layout timing remain UNASSIGNED**.

## Boundary

ServoHIL-I/O mates AXU2CGB `J12` through board connector `J10`.

The deterministic path is direct **1.8 V LVCMOS**. Rev.A deliberately avoids
level translators, isolation and TVS devices in the FPGA-to-FPGA data path.

Mapping authority:

`docs/icd/j12-hil-link.csv`

## Direction convention

Names are from the ZU2CG/Plant point of view:

```text
HL_TX* : ZU2CG -> Local I/O FPGA
HL_RX* : Local I/O FPGA -> ZU2CG
```

Local-FPGA directions:

- `HL_TX_CLK`, `HL_TX[7:0]`: input
- `HL_RX_CLK`, `HL_RX[7:0]`: output
- `HL_SYNC`: input
- `HL_IRQ`: output
- `HL_SAFE_N`, `HL_RESET_N`, `HL_HEARTBEAT`: input
- `TRIG[1:0]`: input
- `DBG[1:0]`, `SPARE[3:0]`, `SPARE_GC[2:0]`: bidirectional reserve

## Connector policy

- J10 pins 2, 39 and 40 are **NC**.
- ServoHIL never consumes/back-feeds AXU connector 5 V or 3.3 V.
- J10 pins 1, 37 and 38 are GND.
- all **34 PL I/O pins** are retained end-to-end.
- GC-capable reserve pins stay available for later clocking experiments instead
  of being permanently discarded.
- connector family / stack height remains a mechanical freeze item.

## Signal-integrity policy

The interface is intended as a short board-to-board/stack path.

### ZU2CG-driven direction

```text
J12 -> Local FPGA
HL_TX_CLK
HL_TX[7:0]
HL_SYNC / SAFE / RESET / HEARTBEAT / TRIG
```

Source termination belongs at the **ZU2CG source**. ServoHIL therefore does not
put a receiver-side resistor in this path and should use conservative source
DRIVE/SLEW constraints on the AXU design.

### Local-FPGA-driven direction

```text
Local FPGA -> J12
HL_RX_CLK
HL_RX[7:0]
HL_IRQ
```

Rev.A has 33 Ω starting series-damping footprints. The schematic groups these
on sheet 04, but PCB placement must put the physical resistors close to the
Local FPGA source pins. Final values remain an SI/bring-up decision.

## Timing contract

Nominal link:

```text
source clock        100 MHz
data                DDR
width               8 bit / direction
raw rate            1.6 Gbit/s / direction
fast TX frame       208 bit
serialization       ~130 ns
```

The incoming `HL_TX_CLK` is constrained as a 10 ns source-synchronous clock.

Input/output delay numbers remain intentionally absent until:

1. XC7A35T FGG484 balls are frozen in Vivado I/O Planner;
2. connector/stack/trace flight time is known;
3. forwarded `HL_RX_CLK` implementation is selected;
4. implementation timing proves whether IDELAY/ISERDES is actually needed.

Do not add IDELAY/ISERDES speculatively.

## Five-way consistency contract

CI must keep the following mutually consistent:

```text
J12 ICD
  <-> 04 KiCad connector pin/net
  <-> 05 Local-FPGA logical ports
  <-> pin_plan.csv
  <-> hil_link_ports.xdc.tmpl
```

The HIL-Link contract checks:

- J12 pin numbers are exactly 1..40;
- exactly 34 PL I/O nets are active;
- only pins 2/39/40 are NC;
- connector-side source-resistor nets map to the correct HL_RX/IRQ signals;
- all active J12 nets terminate on the Local FPGA;
- every HIL-Link pin-plan row is LVCMOS18 / 1.8 V;
- PACKAGE_PIN remains blank until Vivado pin freeze;
- XDC contains every HDL port group and the 100 MHz clock constraint.

## Freeze gate

Passing the schematic contract does **not** set `j12_xdc_crosscheck: true`.

That gate closes only after real XC7A35T package pins are assigned and a
reviewed XDC passes Vivado DRC/timing checks.
