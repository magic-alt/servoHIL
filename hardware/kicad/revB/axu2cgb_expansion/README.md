# Native editable AXU2CGB expansion

Open `servohil_io_revB.kicad_pro`. These checked-in `.kicad_sch` files are the
hardware source of truth. Edit them in KiCad. Do not run the Rev.B review
builder into this directory. `tools/migrations/pr17_native.py` is a one-shot
migration and refuses to replace an existing child sheet.

This is ongoing board development, not a manufacturing release. No second
FPGA; SoM remains a separate unbound carrier contract. ADC/PHY and complete
DUT safety are not yet populated. `hardware/revB/gates.json` remains blocked.

`expected_connections.json` is a migration checkpoint, NOT an independent
hardware oracle. Native checks must also inspect actual IC pin identities,
source paths, resistor values and the current netlist. Tests cannot substitute
for power/thermal/transient bench qualification.
