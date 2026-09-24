# Native editable AXU2CGB expansion — 15-page development source

Open `servohil_io_revB.kicad_pro`. Checked-in native KiCad files and local libraries
are the hardware source of truth. Edit them directly; never run the early review
generator into this directory. Normal CI only validates and exports.

PR #21 added the watchdog, eight-channel AO disconnect and normally-open DUT
permit. PR #22 replaces reserved J3/J4 with native ADC/PWM/encoder/RS485 circuits:
`70_adc_frontend`, `80_encoder_phy` and updated `03_peripheral_boundaries`.
There are 409 physical components: 263 prior - 2 headers + 148 peripheral parts.
The existing 64-signal carrier pin allocation is unchanged. No dedicated CAN or
EtherCAT hardware was allocated or added. The SoM alternative remains unbound.

[ADC/PHY circuit contract, native evidence and physical acceptance](../../../../docs/review/revb-peripherals/README.md)
records pin mapping, serial initialization, roles, load/RC calculations and open
qualifications. [Safety-chain history](../../../../docs/review/revb-safety/README.md)
remains a PR #21 checkpoint, not current full-board qualification.

Independent checks freeze the historical power/DAC connections except explicit
J5 output rerouting and J3/J4 removal. Existing safety checks cover 47 parts/168
pins; additional peripheral checks cover 148 parts/461 pins and reject ADC supply,
reference, lane and input swaps, DE bypass and PWM bypass. The historical netlist
baseline was not silently regenerated. `expected_connections.json` alone is not
an independent design oracle. Actual KiCad export/ERC is required.

New footprint identifiers have local library files, not final package/MPN sign-off.
The new ADC is a low-energy single-ended candidate; its configuration, calibration,
alias filter, timing and input-fault energy need qualification. The directional
encoder profile is SSI/BiSS, not arbitrary ABZ/SPI. PWM/AUX are low-voltage logic.
Non-isolated cables, unpowered-host backfeed and source roles must be reviewed.

This is NOT fabrication-ready. Power EDV, full BOM/footprints, real DUT neutral
bias/permit leakage/shutdown timing, partial power, AON/thermal and measurements
remain open. The standalone health RTL is not a complete board bitstream.
`hardware/revB/gates.json` remains unchanged with `layout_allowed=false`.
Temporary native writers/workbench were removed after reviewed blobs were committed.
