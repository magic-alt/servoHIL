# AD3542RBCPZ16 / CP-28-15 footprint evidence review

**Date:** 2026-09-28  
**Scope:** U20..U23 exact land-pattern closure for Rev.B.  
**Result:** **OPEN — official sources located; Gerber/exact-CAD bytes not yet archived and geometry not independently reviewed.**

## Confirmed current manufacturer identity

The active DAC part is **Analog Devices AD3542RBCPZ16**. Analog Devices Rev.C
documentation identifies the package as **CP-28-15**, a 28-lead LFCSP with a
4 mm × 4 mm body, 0.95 mm nominal height and 0.40 mm BSC lead pitch.

Manufacturer sources:

- product/CAD entry:
  https://www.analog.com/en/products/AD3542R.html
- Rev.C data sheet:
  https://www.analog.com/media/en/technical-documentation/data-sheets/ad3542r.pdf
- CP-28-15 package drawing:
  https://www.analog.com/media/en/package-pcb-resources/package/pkg_pdf/lfcspcp/cp-28/cp-28-15.pdf

The ADI product page exposes exact-part CAD through Ultra Librarian and SamacSys.
Those links establish that manufacturer-linked CAD exists; they do not qualify a
footprint until the downloaded bytes and geometry are reviewed.

## Official evaluation-board cross-check

Analog Devices' EVAL-AD3542RFMCZ schematic uses **AD3542RBCPZ16 as U1**.

Official board files:

- schematic:
  https://wiki.analog.com/_media/resources/eval/user-guides/dac/eval-ad3542r/02_050892d_top.pdf
- Gerber ZIP:
  https://wiki.analog.com/_media/resources/eval/user-guides/dac/eval-ad3542r/09-050892-01c.zip
- BOM:
  https://wiki.analog.com/_media/resources/eval/user-guides/dac/eval-ad3542r/05-050892-01-d.xlsx

These URLs are also pinned by the current Analog Devices public documentation
repository:

- repository: `analogdevicesinc/system-level`
- commit: `76eb29d83e6eaca9ce4470921d315938b2b1aa17`
- source: `docs/solutions/reference-designs/eval-ad35xxr/user-guide.rst`
- source blob: `6327c05006caf900728a31445a3c4fdf3d31253a`
- relevant source lines: 721–726.

This gives an independent manufacturer-maintained path to the exact evaluation-board
Gerber archive instead of relying on an arbitrary third-party footprint.

## Why the four blockers are not closed yet

A generic KiCad footprint such as a nominal 28-pin 4 mm QFN with 0.40 mm pitch is not
sufficient evidence. Body size, pin count and pitch do not uniquely determine:

- side-pad length/width and toe/heel allowance;
- solder-mask expansion;
- paste aperture strategy;
- pin-1 orientation;
- center/exposed-pad presence and size;
- center-pad electrical treatment.

There is also a revision-history reason to fail closed. An early preliminary AD3542R
document explicitly described an exposed pad connected to AGND, while the current
Rev.C pin table enumerates pins 1..28 and does not independently define a numbered
exposed-pad terminal. This is not evidence that the pad disappeared; it is evidence
that package terminology alone must not be used to guess the PCB land pattern.

The current manufacturing decision therefore requires direct inspection of either:

1. current exact-part CAD downloaded from the ADI-linked Ultra Librarian/SamacSys
   entry, or
2. the actual U1 copper/mask/paste geometry from the official EVAL-AD3542RFMCZ
   Gerber archive,

preferably both.

## Close criteria for U20..U23

The four blockers may be removed only after all of the following are recorded:

1. exact Gerber/CAD artifact bytes and SHA-256;
2. 28-pin count and pin-1 orientation review;
3. 0.40 mm pitch review;
4. side-pad dimensions checked against the current package/CAD evidence;
5. center/exposed-pad presence, dimensions and electrical treatment resolved;
6. solder-mask and paste strategy reviewed;
7. resulting KiCad footprint vendored locally with provenance;
8. U20..U23 bound to that footprint;
9. native netlist/ERC and source-closure regressions pass.

Until then the correct state is **OPEN**, not PASS. Closing these four items is a
physical-package binding action only and still does not authorize Layout or qualify
the DAC electrically or thermally.
