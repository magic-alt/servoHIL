# Rev.B schematic readability repair

Approved user scope: repair the existing native editable schematic, avoid global labels except for real cross-sheet connections, draw readable page-local circuit wiring, and submit a new PR. Do not add a second FPGA or begin PCB layout.

Baseline: main 49cdeb395d31e2844b1f50189508aa9dbf940d40 (merged PR17).

## Execution stages (commit each verified stage)

1. Audit native sheets; reproduce page-only global-label misuse. Capture the actual KiCad netlist partition and component values/footprints. Introduce explicit label-scope policy with fail-closed net equivalence checks.
2. Rewire the input protection, positive converters/LDOs, and negative converter/reference into actual local circuits. Preserve physical component references, pin numbers, values, and electrical connectivity. Ground symbols replace repetitive GND text. Annotate functional blocks and preserve qualification warnings.
3. Rewire DAC feedback, output resistors and decoupling; clean page-local labels across the remaining sheets without turning unfinished PHY/watchdog functions into fake completed circuitry.
4. Run raw KiCad XML graph equivalence, existing electrical checks (with scope-aware canonical names), ERC, and PDF export. Review exported pages; commit native source, documentation and read-only CI. Open a new PR; no merge/fabrication claims.

Native .kicad_sch is the hardware source of truth. Any migration tool is one-shot and must never run during normal generation or overwrite human edits. Electrical net equivalence compares actual pin membership, not just text or names. Local net path prefixes are expected; global labels must have consumers on other sheets.
