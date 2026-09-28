# AD3542RBCPZ16 / CP-28-15 footprint evidence review

**Date:** 2026-09-28  
**Scope:** U20..U23 exact land-pattern closure for Rev.B.  
**Result:** **RESOLVED IN SOURCE — official EVAL Gerber/BOM and current package documentation reviewed; Layout remains blocked.**

## Exact device and package identity

The active DAC is **Analog Devices AD3542RBCPZ16**. Current Rev.C documentation
identifies package option **CP-28-15**, a 28-lead LFCSP with a 4 mm × 4 mm body,
0.95 mm nominal height and 0.40 mm pitch.

Manufacturer sources remain:

- product/CAD entry:
  https://www.analog.com/en/products/AD3542R.html
- Rev.C data sheet:
  https://www.analog.com/media/en/technical-documentation/data-sheets/ad3542r.pdf
- CP-28-15 package drawing:
  https://www.analog.com/media/en/package-pcb-resources/package/pkg_pdf/lfcspcp/cp-28/cp-28-15.pdf
- EVAL-AD3542RFMCZ Gerber:
  https://wiki.analog.com/_media/resources/eval/user-guides/dac/eval-ad3542r/09-050892-01c.zip
- EVAL-AD3542RFMCZ BOM:
  https://wiki.analog.com/_media/resources/eval/user-guides/dac/eval-ad3542r/05-050892-01-d.xlsx

The official EVAL files are also discoverable through the Analog Devices public
documentation repository at
`analogdevicesinc/system-level@76eb29d83e6eaca9ce4470921d315938b2b1aa17`.

## Source artifacts reviewed

The review pins the exact downloaded artifacts by SHA-256 rather than redistributing
manufacturer binary files:

| Artifact | SHA-256 |
| --- | --- |
| `ad3542r.pdf` Rev.C | `a9536b981e1dc140082ddff947487faaaa47874cd8b648966ee9c6b92fa292fa` |
| `cp-28-15.pdf` | `f6aab2aa746e79a01b4d9067bde56c886001a4cb1b7ed83e198d480ab0845b73` |
| `eval-ad3542r-ug-2258.pdf` | `ed5afa177bce6c907a3981c71f49cc3964078a6b6ff79ecfd24ae78f6a1093b4` |
| `09-050892-01c.zip` | `87eee7f3ed85e81798918b1977bc0b416d72699a39c771d95e9ea3839ef461e8` |
| `05-050892-01-d.xlsx` | `4608d8884754e5768424832af2331fa0490ab90e05a990a1292bf8f7bab0f7df` |

The deterministic review record is:

`hardware/revB/evidence/ad3542r/u1_geometry_review.json`

It retains source/member hashes, all 28 U1 IPC-356 records, the exact Gerber U1
flash coordinates/apertures, the EVAL BOM U1 identity and the canonical KiCad pad
mapping.

## Official EVAL U1 identity

The EVAL BOM binds:

- reference: **U1**
- manufacturer: **ANALOG DEVICES**
- manufacturer part: **AD3542RBCPZ16**
- JEDEC field: **QFN28_4X4**

The IPC-356 file contains exactly U1 terminals **1 through 28**, with 0.40 mm pitch.
There is no U1 terminal 29 or exposed-pad terminal.

## Exact reviewed land pattern

The EVAL U1 pad-center offset from package center is **1.8933 mm**.

Official Gerber apertures are:

| Layer | Side pads | Top/bottom pads |
| --- | --- | --- |
| Top copper `L1_TOP.art` | 0.7366 × 0.2286 mm obround | 0.2286 × 0.7366 mm obround |
| Top paste `PMT.art` | 0.7366 × 0.2286 mm obround | 0.2286 × 0.7366 mm obround |
| Top solder mask `SMT.art` | 0.8382 × 0.2794 mm obround | 0.2794 × 0.8382 mm obround |

All three layers resolve exactly 28 perimeter positions for U1.

The local source footprint is:

`Package_DFN_QFN:AnalogDevices_CP-28-15_AD3542R`

at:

`hardware/kicad/revB/axu2cgb_expansion/footprints/Package_DFN_QFN.pretty/AnalogDevices_CP-28-15_AD3542R.kicad_mod`

Numbered pads reproduce the official EVAL copper/paste dimensions. Independent,
unnumbered F.Mask aperture pads reproduce the asymmetric official solder-mask
openings rather than approximating them with one isotropic mask expansion.

## Center/exposed-pad decision

The earlier preliminary-document ambiguity is now resolved for the current
manufacturing decision.

The following current evidence agrees:

1. Rev.C pin configuration enumerates pins 1..28 without an exposed-pad terminal.
2. CP-28-15 bottom view shows 28 perimeter terminals and no center pad.
3. EVAL IPC-356 contains exactly U1 pins 1..28.
4. EVAL top solder-mask and paste files contain 28 perimeter apertures and no center
   aperture.

Therefore the reviewed footprint **must not add a center/exposed pad**.

Several unrelated small copper/via flashes exist under the 4 mm × 4 mm body
projection on the EVAL PCB, but they have no matching U1 pin in IPC-356 and no
center F.Mask/F.Paste aperture. They are board routing/via features, not an exposed
package land.

## Rev.B binding result

U20, U21, U22 and U23 are now bound to the reviewed footprint and their displayed
value is the exact `AD3542RBCPZ16`.

`hardware/revB/schematic_open_items.json` records them under
`resolved_bindings`, not `open_footprints`.

The closure checker independently verifies:

- the exact source artifact/member hashes;
- EVAL BOM U1 identity;
- all 28 IPC-356 pins and Gerber aperture groups;
- no center pad/mask/paste aperture;
- 28 numbered KiCad copper/paste pads;
- 28 explicit KiCad F.Mask aperture pads;
- exact coordinates and dimensions;
- native U20..U23 value/footprint bindings.

## Boundary of this closure

This closes only the **exact physical package land-pattern blocker** for U20..U23.

It does **not** establish:

- DAC static/dynamic accuracy on the Rev.B board;
- output stability with the real DUT/cable;
- thermal qualification;
- EMC;
- manufacturing process qualification;
- complete PCB placement/routing;
- permission to enter Layout.

`layout_allowed=false` remains invariant until the remaining pre-layout gates and
engineering review are complete.
