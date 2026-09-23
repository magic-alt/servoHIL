# Single-SoC migration implementation plan

**Goal:** remove the second FPGA from the active board and support an AXU2CGB
extension plus a vendor-bound ZU2CG SoM carrier through the same I/O contract.
**Architecture:** shared I/O contract and native schematic builder, with separate
physical pinouts and carrier assignments. Rev.A is preserved as historical input.
**Tech stack:** Python standard library, JSON/CSV, KiCad CLI, XDC preview.
**Spec:** `docs/superpowers/specs/2026-09-23-single-soc-design.md`.

## Constraints / review focus

No hardware release claims, no inherited evidence, no fabricated SoM ball map,
no secondary FPGA and no changes to other repositories. Specifically test power
pins assigned as GPIO, voltage mismatch, duplicate bindings, stale evidence and
incomplete carrier definitions.

## Tasks

1. Write migration/validation tests and run them against missing implementation.
2. Add immutable-source physical pin tables, common I/O contract and two profiles.
3. Implement strict contract validation and deterministic assignment/XDC generation.
4. Generate a native interface-plus-DAC review project; validate its real XML
   netlist in KiCad CLI, not just strings appearing in the schematic.
5. Archive the exact old hardware/docs/BOM/tools trees; replace active CI and
   README; keep Notion synchronization untouched.
6. Run unit/mutation tests, deterministic generation, KiCad ERC/netlist/PDF export;
   commit and open a PR. Update Issue #6 and mark the old Local-FPGA tasks superseded.

## Verification commands

```sh
python -m unittest discover -s tests -v
python tools/revb.py validate
python tools/revb.py generate --carrier axu2cgb --output build/revB
python tools/revb.py release --carrier axu2cgb  # expected BLOCKED
python tools/revb.py generate --carrier zu2cg_som --output build/som # expected BLOCKED
```
