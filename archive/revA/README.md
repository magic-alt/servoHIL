# Rev.A historical snapshot — NOT the current design

`snapshot/` is the exact tree from commit
`dbd0d32a030bcda0427fec31894c01db29717d8a`, tree
`6ddd828a8b7ca289a4f2acfee7eb2e1f07569e2e`.

This intentionally retains the old second FPGA, local power/configuration circuits,
BOM, pin plan, documents and tests for traceability. None is a current build or
fabrication target. New development uses Rev.B only.

The old `feat/reva-hil-link-schematic` / PR #15 is retained in Git history and is
superseded by the single-SoC migration; its validation is not a Rev.B PASS.
