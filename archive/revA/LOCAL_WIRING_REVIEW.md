> Historical review log. Current final results and limitations: [2026-09-24 PR18 handoff](validation/2026-09-24-pr18-handoff.md). Earlier label/ERC statements below are superseded.

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


## 2026-09-24 global-label scope audit

PR #18 now applies a strict scope rule to the native Rev.A hierarchy:

- a sheet-local node is represented by a local label or continuous wiring, not a
  global label;
- an actual cross-sheet net keeps exactly one explicit global label per sheet;
- additional occurrences of that same cross-sheet net on the sheet are local
  labels unless a power symbol provides the connection;
- pages 01/02/04 intentionally use `power:GND` symbols, so they do not require
  a separate explicit `GND` global-label object.

Current explicit global/local label counts after the scope cleanup are:

| Sheet | Global | Local |
| --- | ---: | ---: |
| 01_POWER_ENTRY | 3 | 7 |
| 02_ANALOG_POWER | 7 | 13 |
| 03_DIGITAL_POWER | 10 | 172 |
| 04_AXU_HIL_LINK | 25 | 10 |
| 05_IO_FPGA | 50 | 68 |
| 06_DAC_0_3 | 21 | 19 |
| 07_DAC_4_7 | 21 | 79 |

Structural audit of all seven child schematics at the current branch state:

- zero sheet-local nets remain as explicit global labels;
- zero duplicate explicit global labels remain for the same net on one sheet;
- every baseline cross-sheet net retains one global entry on each participating
  sheet, except GND where the reviewed pages use KiCad power symbols;
- S-expression parentheses/strings are balanced on all seven files;
- no duplicate schematic UUID was found in any child sheet;
- all explicit `no_connect` records use the valid two-coordinate KiCad form.

The three pages called out for the remaining label cleanup were committed
independently:

- `03_digital_power.kicad_sch`: `b26e38a`;
- `05_io_fpga.kicad_sch`: `2b935cd`;
- `07_dac_4_7.kicad_sch`: `62072ba`.

The whole-hierarchy audit also found and removed the remaining duplicate
cross-sheet rail entries in analog power and DAC0-3 in follow-up commits
`cc6dac6` and `54fbe28`.

GitHub Actions currently cannot serve as the Rev.A native KiCad gate because the
repository-level Rev.B workflow intentionally rejects any modification of the
historical snapshot with `historical snapshot bytes changed` before reaching
its KiCad stages. Unit/mutation regressions complete first; a native KiCad
open/export/ERC still has to be run from a workstation for final graphical and
electrical acceptance of this archive repair.
