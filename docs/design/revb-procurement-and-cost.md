# Rev.B Procurement and Cost Snapshot

**Snapshot date:** 2026-09-29  
**Design baseline:** `193d8bc61edc690c2f8518b8da784f56a821d872`  
**Planning FX:** 1 USD = 6.71 CNY. This is an engineering planning rate, not a
settlement/accounting rate.

## 1. Files

- Complete grouped BOM: `bom/revb-costed.csv`
- Machine-readable summary: `bom/revb-cost-summary.json`
- Price-source ledger: `bom/revb-pricing-sources.csv`
- Coverage checker: `python tools/check_revb_costed_bom.py`

The costed BOM is generated/reviewed against the **native schematic source**, not
against the older hand-maintained `revb-common.csv` list.

Coverage at this snapshot:

- 439 on-board physical instances;
- 431 populated instances;
- 8 DNP feedback capacitors;
- 139 grouped purchasing lines.

## 2. Component-cost result

| Build basis | Component estimate |
|---|---:|
| 1 fully stuffed Rev.B | **CNY 4,085.41** |
| 5 fully stuffed Rev.B boards | **CNY 17,153.21 total** |
| 5-board average component cost | **CNY 3,430.64 / board** |

The 5-board estimate applies known small-quantity breaks where they fit the actual
aggregate quantity. It does not pretend every distributor has identical stock or
price when the purchase order is placed.

**Excluded:** bare PCB, stencil, SMT/THT assembly, freight, VAT/import duties,
AXU2CGB host, J12/J15 mating connector pair while its exact MPN/stack height is
unbound, rework/scrap/yield reserve and qualification-fixture cost.

Because no production-ready `.kicad_pcb`/Gerber and fabricator stackup exist yet,
PCB/assembly cost is deliberately **TBD_VENDOR_QUOTE**, rather than embedding a
false-precision fabrication price in the BOM.

## 3. Main cost drivers

Using the qty-1 snapshot and planning FX:

| Item | Qty/board | Price basis | Approx CNY/board |
|---|---:|---:|---:|
| AD3542RBCPZ16 | 4 | USD 86.38 each | 2,318 |
| AD7606C-16BSTZ | 1 | USD 67.98 | 456 |
| ADG5412FBRUZ | 2 | USD 15.02 each | 202 |
| LT3045EMSE#PBF | 2 | USD 10.00 each | 134 |
| LT3094EMSE#PBF | 1 | USD 10.00 | 67 |
| ADR4525BRZ | 1 | USD 11.86 | 80 |
| LT8330ES6#TRMPBF | 1 | USD 8.27 | 55 |
| C5750X7R1V476M230KC | 1 | USD 5.55 | 37 |

The four DACs alone are about **56.7%** of the one-board component budget.
AD3542R + AD7606C-16 together are about **67.9%**. Prototype cost optimization
should therefore focus on purchasing quantity and staged population, not on
removing cents from ordinary passives.

## 4. Pricing evidence policy

`revb-costed.csv` intentionally distinguishes design truth from procurement
estimates.

### EXACT_QUOTE

Used when the schematic/mechanical contract binds the MPN and a current
authorized source was available. Examples include AD3542RBCPZ16,
AD7606C-16BSTZ, LT3045EMSE#PBF, TPS259474LRPWR, J5/J101/J501/J701 and C105.

### CANDIDATE_QUOTE

Used for exact candidates already present in qualification evidence, for example
Coilcraft XAL50xx and selected TDK MLCCs. A quoted candidate is **not** a release
approval. Magnetic loss/saturation/thermal and MLCC derating evidence still
apply.

### BUDGET_GENERIC

Used for resistors, ordinary capacitors, test points and generic pin headers where
value/package are fixed but manufacturer MPN is not. These prices are conservative
small-quantity engineering allowances. The eventual release BOM must bind any
passive whose tolerance, voltage coefficient, ESR/ESL, pulse rating, temperature,
height or lifetime is electrically relevant.

### ORDERABLE_MPN_MISMATCH

U501 is the current case. The native schematic says `TPS3430DRCR`; TI's current
active orderable part page is `TPS3430WDRCR`. The BOM carries the latter only as a
budget/procurement candidate and **does not silently authorize substitution**.
Resolve the exact variant and update schematic + BOM together before fabrication.

## 5. Availability risks at this snapshot

- AD3542RBCPZ16 is the dominant cost item and has a long manufacturer lead-time
  indicator; secure prototype quantity early after the design is fabrication-ready.
- AD7606C-16BSTZ availability is tighter than common logic/passives.
- AP63201WU-7 and TPS70933DBVR showed no immediate DigiKey stock at the snapshot
  even though they remain active; recheck incoming dates or an approved source
  before PO.
- PESD15VL1BA,115 showed constrained authorized-distributor availability; do not
  silently swap TVS characteristics just because a similar SOD-323 part is stocked.
- J12/J15 exact host/mating connector MPN and stack height are not yet bound and
  are therefore intentionally excluded from the board component total.

## 6. Prototype procurement strategy

For the first physical spin, keep procurement separate from design release:

1. finish J12/J15 exact connector/stack binding and actual PCB Layout;
2. run PCB DRC and fabrication review;
3. re-quote all `EXACT_QUOTE` / `CANDIDATE_QUOTE` rows on the PO date;
4. resolve every `ORDERABLE_MPN_MISMATCH`;
5. freeze electrically significant generic passives to approved MPNs;
6. purchase enough long-lead precision ICs for rework/replacement, but avoid
   stuffing all prototype PCBs before first-board power/analog bring-up succeeds.

A practical engineering strategy remains to order multiple bare PCBs while
staging expensive AD3542R/AD7606 population. The exact number of fully populated
boards should be chosen after Layout and assembly quotes, not encoded as a release
requirement here.

## 7. Revalidation

Run:

```sh
python tools/check_revb_costed_bom.py
python -m unittest tests.test_revb_costed_bom -v
```

The checker ensures all native on-board references are covered exactly once,
DNP cost remains zero, 431/8 population counts remain intact and the U501 mismatch
cannot disappear merely by editing prose.
