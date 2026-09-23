# Shared I/O contract / native KiCad design source

Generate: `python tools/revb.py generate --carrier axu2cgb --output build/revB`.
Open `build/revB/servohil_io_revB.kicad_pro`.

The checked-in design sources are the common signal contract, carrier tables and
`tools/revb_schematic.py`; the generated `.kicad_sch` and `.kicad_sym` files are real
native KiCad documents, reproducible without editing opaque embedded text blobs.
Do not edit build outputs as the source of truth.

The initial native project is interface-plus-DAC review only. Onboard I/O power,
ADC/PHY and independent safety implementation remain open. Gate status is NOT_RUN;
ERC can check the modeled connector/circuit boundaries, not prove the missing
hardware. All PCB layout/fabrication is blocked.

Neither common logical net names nor Plant equations contain carrier-specific
J12/J15 pins. Changing to a qualified SoM changes its binding, not the Plant API.
