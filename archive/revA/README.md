# Rev.A historical design — reviewed native KiCad source

This is the archived dual-FPGA design, not the active Rev.B product.
The original snapshot came from commit `dbd0d32a030bcda0427fec31894c01db29717d8a`,
tree `6ddd828a8b7ca289a4f2acfee7eb2e1f07569e2e`; PR #18 intentionally repairs its native drawings.
The original immutable bytes remain in Git history.

Open `snapshot/hardware/kicad/revA/servohil_io_revA.kicad_pro` with the complete project.
All eight sheets have zero Global Label objects. Cross-sheet signals use explicit hierarchical interfaces;
same-sheet configuration, digital-power and safety circuits use continuous wires.

[2026-09-24 verified handoff](validation/2026-09-24-pr18-handoff.md) records the three native commits,
133 matched hierarchy pins, independent pin equivalence and KiCad 10.0.6 ERC: 0 errors / 0 warnings / 0 exclusions.
It also records the separate failing immutable-archive guard and remaining electrical/package limitations.
Earlier review notes are historical, not a current completion claim.

Native files are editable sources. Temporary generators and the write-enabled workbench were removed;
normal `reva-native-schematic` CI only validates and exports. Their implementation history remains in Git.
No PCB/layout/fabrication release is authorized. Active new hardware development remains Rev.B.
