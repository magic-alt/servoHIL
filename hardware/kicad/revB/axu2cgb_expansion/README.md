# Native editable AXU2CGB expansion — 16-page Rev.B development source

Open `servohil_io_revB.kicad_pro`. Checked-in native KiCad files and project-local
symbol/footprint snapshots are the hardware source of truth. Normal CI is read-only:
it validates, exports netlist/ERC/PDF and checks that validation does not rewrite the source.

PR #21 added watchdog/AO-disconnect/DUT-permit safety hardware; PR #22 added native
AD7606C-16, PWM, SSI/BiSS and RS-485 circuits; PR #23 added ADC initialization/acquisition
RTL, completion-only runtime-health integration and strict qualification/Vivado-evidence
contracts. The current schematic-closure work adds deterministic package bindings and
`90_connector_protection.kicad_sch`.

## Current source state

- 16 sheets total; the original 64-signal AXU2CGB allocation is unchanged.
- 439 physical `in_bom=yes && on_board=yes` instances by source audit.
- J12/J15 are purchased AXU2CGB host boundaries and are deliberately excluded from
  expansion-board BOM/placement.
- 37 connector-protection devices cover AI0..7, DUT_AO0..7, six PWM inputs, AUX0..5,
  I2C, four SSI/BiSS differential pairs, RS-485 and the dry-contact interlock cable.
- `hardware/revB/schematic_open_items.json` contains the only 14 allowed blank
  footprints. `tools/check_revb_schematic_closure.py` fails if any unlisted blank
  footprint appears or an expected open item silently disappears.
- Exact local footprints are now bound for LT3045/LT3094 MSOP-12+EP, TPS3430 DRC,
  SN74LVC1G74 DCT, AQY212GS SOP-4, Littelfuse 451 fuse and XAL5030.
- U20..U23 remain explicitly marked `CP-28-15 land pattern OPEN`; TPS259474 RPW
  HotRod, four XAL5050 parts and connector/switch mechanical selections also remain open.

The remaining open list is a fabrication blocker, not an incomplete functional page.
Do not substitute a “similar” QFN/inductor/connector footprint simply to make the count zero.

## Interface protection boundary

`90_connector_protection` uses 15 V bidirectional low-leakage TVS devices for the
low-energy AI and +/-5 V AO lines, 5 V bidirectional TVS devices for 3.3 V logic cables,
and SM712 devices for SSI/BiSS and RS-485 differential pairs. DUT_PERMIT_A/B remains
floating; it is intentionally not clamped to board GND because the real DUT voltage,
cable and isolation contract is still unbound.

This closes source-level ESD topology only. Actual connector-entry placement, return path,
powered-off injection/backfeed, cable common mode, IEC ESD/surge, temperature and fault
energy remain physical qualification gates.

## Verification

Run at minimum:

```sh
python tools/check_revb_schematic_closure.py
python tools/check_native_readability.py
kicad-cli sch export netlist --format kicadxml -o build/native/netlist.xml servohil_io_revB.kicad_sch
python ../../../../tools/check_native_readability.py --normalize build/native/netlist.xml --output build/native/canonical.xml
python ../../../../tools/verify_native_all.py build/native/canonical.xml --stage supervision
python ../../../../tools/check_native_safety.py build/native/canonical.xml
```

Use the repository-root CI workflow for the full paths, ERC, Icarus, ngspice and artifact export.
`hardware/revB/gates.json:layout_allowed` remains `false`.
