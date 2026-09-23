# Rev.A local-wiring repair / PR #18

## Scope and authority

Work is confined to `archive/revA/` on `fix/reva-kicad-connectivity`.
The native `.kicad_sch` files remain editable design artifacts. Rev.A remains
PRELIMINARY and is not a fabrication target. No package, power-stage value,
FPGA pin-plan, or PCB release gate is frozen by this drawing repair.

Starting PR head: `af31036415cdcb8abf51eaa24d6f89be6f098708`.
Electrical intent reference: the archived schematic at main
`3f052eb85ff04d3c54995e66268e03b74d2771f9`, before the readability edits.

## Confirmed findings

1. A global label was used on almost every pin, including divider midpoints,
   compensation nodes, and DAC-local feedback nets. Merely replacing these
   with local labels would leave the circuit just as fragmented.
2. The starting `01_power_entry.kicad_sch` has U1 at (165.1,85.09), but wires
   for IN/OVLO/PGTH and OUT/DVDT/ILM still use the old symbol coordinates.
   C4 and C5 each have a first-pin wire at x=264.16 while their bodies are at
   x=215.9 (first pin x=210.82). A label-name/count check does not catch this.
3. The intended U1 mapping in the pre-repair archive is:
   5=VIN_RAW, 1=UVLO_NODE, 2=OVLO_NODE, 4=PGTH_NODE, 8=GND,
   6=12V_PROT, 3=EFUSE_PG, 7=DVDT_NODE, 9=ILIM_NODE, 10=ITIMER_NODE.
4. The runtime has no KiCad executable and cannot resolve github.com for a
   git clone. Repository changes are published through the GitHub connector.
   Geometry/graph tests must not be reported as native KiCad ERC or export.

## Drawing policy

- Connect nearby components with actual orthogonal wires and junctions.
- Use at most one local net name on a continuously wired internal node.
- Use global labels only for actual cross-sheet nets; shared power rails may
  have one entry per physically separate functional block when this prevents
  unreadable sheet-spanning power wires.
- A ground power symbol is a deliberate shared power connection, not a
  substitute for wiring a regulator's feedback or compensation network.
- Preserve component references, values, pin numbers, NC intent and the
  archived electrical topology. Identify corrections to broken PR geometry
  explicitly instead of claiming equivalence to an already broken drawing.
- Do not overwrite hand edits via automatic regeneration on opening a project.

## Stages (each schematic stage receives its own commit)

- [x] Audit the current PR and record scope / detached-pin regression.
- [ ] Rewire power entry: input filter, eFuse, UV/OV divider, PG divider,
      timing/current-limit components and output capacitors.
- [ ] Rewire analog power: positive LDOs, negative preregulator/LDO, reference.
- [ ] Rewire digital power: sequencing, buck output/feedback/compensation.
- [ ] Rewire HIL-Link and FPGA-local configuration / hardware-safe circuits.
- [ ] Rewire the four DACs: feedback/CFB/output resistors and decoupling.
- [ ] Run whole-hierarchy scope/net/NC checks; record native-tool limitations.

## Validation requirements

A successful S-expression parse alone is insufficient. Check every physical
pin against a reviewed net contract, distinguish NC from dangling pins, detect
conflicting names, check local-vs-global scope, and inspect the drawing geometry.
Native KiCad hierarchy load, netlist export and ERC remain separate acceptance
checks and must be reported with the actual tool version and output when run.
