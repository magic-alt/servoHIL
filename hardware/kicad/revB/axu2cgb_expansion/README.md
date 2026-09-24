# Native editable AXU2CGB expansion

Open `servohil_io_revB.kicad_pro`. The checked-in native KiCad files and local
libraries are the hardware source of truth. Edit them directly. Do not run the
early `tools/revb.py generate` review builder into this directory. One-shot PR21
writers and their temporary write-enabled workflow were removed after the
verified native blobs were committed; their history remains in Git.

## Current 13-page scope

The original power/DAC/interface pages are retained. `50_watchdog_interlock`
adds TPS3430, two heartbeat-edge qualification stages, delayed release and an
AON-domain SAFE_ENABLE gate. `06_analog_outputs` now contains two ADG5412F quad
switches between the DAC nets and J5. `60_dut_permit` contains a normally-open
PhotoMOS permit contact. The existing RAILS_OK net is now explicitly cross-sheet
so the heartbeat qualifier can inhibit the old ARM latch and DAC reset path.

No second FPGA; SoM remains a separate unbound carrier contract. This is ongoing
board development, not a manufacturing release. ADC/PHY are not populated.
**A drawn DUT permit contact does not complete system-level DUT inhibition.**
High-impedance AO must be given an application-specific neutral state by the
adapter, and an open/leaking contact must be interpreted as inhibited by the
actual DUT. The interface is not certified STO and does not switch motor power.

The [safety review and acceptance plan](../../../../docs/review/revb-safety/README.md)
records heartbeat semantics, source-bound evidence and all open qualifications.
U501/U506/U507/U701 and the new connectors still need final package/land-pattern
binding; no blank footprint is an approval. The existing EDV rail/headroom,
thermal, transient, MLCC and power-off blockers remain. Release gates stay blocked.

## Verification boundaries

`expected_connections.json` is a historical migration checkpoint plus the eight
explicit J5 changes, NOT an independent hardware oracle. Use
`tools/check_native_safety.py` together with existing power and converter pin
checks on actual KiCad XML. It preserves the historical old-pin partition,
checks 47 added components / 168 pins, source/drain orientation, default pulls,
no parallel AO bypass and independently floating permit contacts.

Actual KiCad 10.0.6 export/ERC and PDF review were performed. Pin checks and ERC
are not physical power-off, analogue settling, relay reaction-time or safety
qualification. `hardware/revB/gates.json` is intentionally unchanged.
