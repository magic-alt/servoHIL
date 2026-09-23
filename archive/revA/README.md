# Rev.A historical snapshot — NOT the current design

`snapshot/` originated from commit
`dbd0d32a030bcda0427fec31894c01db29717d8a`, tree
`6ddd828a8b7ca289a4f2acfee7eb2e1f07569e2e`.

On 2026-09-23, only the archived native KiCad schematics under
`snapshot/hardware/kicad/revA/` were repaired for readability and continued
editing. The repair replaces pin-mounted global-label clutter with explicit short
wire stubs, restores visible reference/value fields to the embedded-symbol
placement, and pulls the affected Rev.A power-sheet objects back inside the A3
drawing area. Net names, reference designators, component values, explicit
no-connect markers, sheet names, and the Rev.A architecture are preserved.

This directory intentionally retains the old second FPGA, local
power/configuration circuits, BOM, pin plan, documents and tests for
traceability. None is a current build or fabrication target. New development
uses Rev.B only.

The old `feat/reva-hil-link-schematic` / PR #15 is retained in Git history and is
superseded by the single-SoC migration; its validation is not a Rev.B PASS.
