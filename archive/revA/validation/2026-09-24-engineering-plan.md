# Rev.A native schematic completion plan — PR #18

**Goal:** Finish the native Rev.A schematic connectivity/readability repair on `fix/reva-kicad-connectivity`, following the user's KiCad engineering rules, without converting Rev.A into Rev.B or authorizing fabrication.

**Architecture:** Preserve the existing power / HIL-Link / local FPGA / four-DAC partition. Wire functional circuits continuously inside each sheet. Represent inter-sheet signal interfaces with hierarchical labels and sheet pins; reserve global connections for reviewed shared rails / system safety exceptions. Keep all native files manually editable.

**Tech stack:** Native KiCad schematic/project files, KiCad CLI netlist/ERC/SVG export, Python standard-library checks, GitHub Actions read-only verification.

**Specification:** https://app.notion.com/p/02-2-KiCad-PCB-Layout-3e55ebb6169681528093c01b2f551315 (read 2026-09-24), especially sections 2, 3.2–3.7 and 3.11.

## Baseline and constraints

- Starting PR head: `f351fc7b4ff515eacee660fb2ed28ccd0c0b2c7a`.
- Latest main checked at start: `8a1d00a06bd3dac5758fd14a551b9f27e5e5358e`.
- GitHub comparison reports ahead 24 / behind 0; main is already an ancestor. Do not manufacture an unnecessary merge or rewrite history.
- Native project: `archive/revA/snapshot/hardware/kicad/revA/servohil_io_revA.kicad_pro`.
- No PCB layout, package/pin-plan freeze, regulator component qualification, or hardware safety PASS is implied by this work.
- Preserve references, component values, pin numbers and explicit NC intent unless a separately documented electrical correction is required.
- Preserve existing Rev.B work. Do not weaken its electrical or fabrication gates to make archive-only edits pass.
- The current interactive container has neither KiCad nor direct GitHub DNS access. Connector writes are real Git commits; structural checks are not native ERC. Attempt an independent native Rev.A validation job and report its actual outcome.

## Review focus

1. A moved symbol or passive can leave its wire endpoint at the old coordinate: check pin-to-net membership, not label counts.
2. Replacing a global label with a local label may change scope or merely disguise a fragmented circuit: verify connectivity and review exported pages.
3. Hierarchical interface changes can split existing shared nets: compare physical component-pin groups across the full hierarchy.
4. A clean ERC may reflect disabled severity/exclusions: inspect project rules and report all exceptions.
5. The historical archive checksum gate must not prevent native Rev.A checking, nor be silently disabled for other changes.

## Work packages — separate commits

- [x] Read current PR metadata, main relationship, root README, architecture, core BOM, and engineering rules; record baseline.
- [ ] Establish an independent read-only Rev.A native netlist/ERC/render gate; collect the starting failures.
- [ ] Repair digital-power continuous regulator loops and local support circuits; preserve and test physical pin contracts.
- [ ] Complete FPGA-local configuration/safety support and the remaining DAC page wiring; keep repeated channels visually consistent.
- [ ] Audit all power/DAC sheets for accidental shorts, detached pins, NC changes, duplicate identifiers and property collisions.
- [ ] Make top-level inter-sheet interfaces explicit, with verified hierarchical signal connectivity and documented global exceptions.
- [ ] Run native hierarchy export/ERC plus regression/equivalence checks; inspect rendered pages, then update PR description and completion evidence.

## Reproducible native baseline

From repository root (KiCad installed):

```sh
mkdir -p build/reva
native=archive/revA/snapshot/hardware/kicad/revA
kicad-cli version
kicad-cli sch export netlist --format kicadxml -o build/reva/netlist.xml "$native/servohil_io_revA.kicad_sch"
kicad-cli sch erc --format json --severity-all --exit-code-violations -o build/reva/erc.json "$native/servohil_io_revA.kicad_sch"
kicad-cli sch export svg -o build/reva/svg/ "$native/servohil_io_revA.kicad_sch"
```

An ERC process exit, exported XML, and visual review are separate observations. Never infer electrical completion from successful serialization, historical results, or a workflow that skipped its native steps.
