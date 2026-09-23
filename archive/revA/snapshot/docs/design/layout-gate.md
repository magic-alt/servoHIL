# Rev.A layout gate

`hardware/kicad/revA/layout_gate.yaml` is the machine-readable authority for whether a `.kicad_pcb` may exist.

Layout is blocked until all are PASS:
- power_tree_frozen
- fpga_pinplan_frozen
- j12_xdc_crosscheck
- dac_network_review
- schematic_erc

CI intentionally fails if a `.kicad_pcb` appears while `layout_allowed` is false.
