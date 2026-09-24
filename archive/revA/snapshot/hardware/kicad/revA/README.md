# ServoHIL-I/O Rev.A — editable native KiCad project

Open `servohil_io_revA.kicad_pro`, then its root schematic. Keep all seven child sheets, project symbol libraries,
`sym-lib-table` and the project file together. Replacing only the two child files leaves an old root without matching sheet pins.

## Reviewed source

The three native repair commits are `615e1f1` (power interfaces), `9e6f133` (FPGA local wiring and complete hierarchy),
and `846ce4a` (library reconciliation and zero-warning ERC).
All eight sheets contain zero Global Label objects; root sheet pins match 133 child interfaces.
GND remains a global power network, represented by the exact archived symbol in the portable `ServoHILGround` project library.

[Full handoff and evidence](../../../../validation/2026-09-24-pr18-handoff.md).
`native-source-2026-09-24.json` is a historical source manifest, not a generator or restriction on future reviewed edits.
Use KiCad 10.0.6 for reproducing the recorded results; newer versions must be revalidated.

## Verification

Read-only checks and actual native XML equivalence passed: 191 components, 209 nets, 716 physical pins.
Complete ERC passed with 0 errors, 0 warnings and no exclusions. Twenty-three Rev.A drawing tests passed.
No temporary generator runs when opening or validating this project.

## Not a fabrication release

FPGA package/ball assignment remains FUNCTIONAL_PRELAYOUT. C230/C231/C232 are bulk capacitors, not a completed per-pin bypass design.
Power magnetics, compensation, startup, MLCC derating, thermal and hardware safety qualification remain open.
Legacy AO0..3 sharing between DAC sheets is preserved for pin equivalence, not approved as a product output architecture.
`layout_gate.yaml` remains unchanged and `layout_allowed` stays false. PCB routing has not been performed by this repair.
The separate whole-repository immutable-archive check still reports `historical snapshot bytes changed`; it was not disabled.
