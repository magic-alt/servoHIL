# Rev.B Electrical Design Verification

**Engineering screening, NOT layout or purchase approval.** Native KiCad remains
unchanged. In particular, the currently requested +/-5 V output and the +/-5.2 V
rail tolerance/headroom conflict are not fixed by a successful simulator job.

## Reproduce

Use Python 3.11+ and ngspice on PATH, in a clean checkout of the PR branch.
The CI records the actual simulator version and executable SHA256. Linux CI uses
ngspice-42 at the reviewed checkpoint; do not assume another simulator version
has identical solver behavior. For tests only, `NGSPICE` may name an executable.
The `spice.py` command resolves `ngspice` from PATH.

```sh
python -m unittest discover -s tests -p 'test_edv*.py' -v
python sim/power/analysis.py --output build/edv/analysis
python sim/power/qualification.py --output build/edv/components
python sim/power/capacitors.py --output build/edv/capacitors
python sim/power/spice.py --output build/edv/run-001
python sim/power/evidence.py build/edv/run-001 --expected-source-commit "$(git rev-parse HEAD)"
python sim/power/analysis.py --strict-design --output build/edv/analysis
```

The final command must currently exit **2**, because design blockers exist.
Other commands exiting zero mean the calculation/execution/integrity work ran;
they do not clear `hardware/revB/gates.json`. On PowerShell, inspect
`$LASTEXITCODE` after the strict command. Never run all commands under an
unconditional `|| true` that hides simulation failures.

Every executed SPICE run requires a **new output directory**. Existing output is
refused, including a previous successful run. Keep failed runs for diagnosis;
choose `run-002` instead of overwriting evidence. A failure leaves a `FAILED`
manifest with the completed case count and original logs. A process killed
without cleanup may leave `RUNNING`; neither status passes `evidence.py`.

For one-case debugging use `--case buck_6V2_PRE_8V`. This produces a valid
single-case execution, but intentionally fails the **full-matrix** integrity
gate. `--emit-only` creates portable `.cir` decks and prints `EMITTED_NOT_RUN`.

## What the models cover

| Layer | Current implementation | What it cannot establish |
|---|---|---|
| Analytical | Native R/L/C values; FB and SET corners; 162 Cuk sensitivity points; thermal envelopes; nine capacitor banks | Dynamic stability, actual temperature, lifetime/production qualification |
| Switched power network | 12 buck + 4 Cuk cases; input ramps, half-to-full **resistive** load steps, switching-disable discharge | AP63201/LT8330 compensation, IC soft-start, Burst Mode, short-circuit/current limit or hiccup |
| LDO envelope | Nine SET-current/RSET corners; native CSET and Cout; assumed gm, fast-start, dropout and current ceiling | LT3045/LT3094 loop stability, PSRR, noise, thermal shutdown, reverse current, real PG timing |
| Vendor preparation | Exact LT3045/LT3094/LT8330 `.asy`/`.SUBCKT` pin-order binding and deck/model hashes | No manufacturer macro-model simulation has been executed here |
| Physical bench | No new board measurements | No hardware PASS |

The power topologies are explicit hand-authored bench networks with native-value
binding, not an automatic SPICE export of every KiCad wire or parasitic. A
native topology change requires reviewing the bench network as well as rerunning
the digest/connection checks; the source hash alone cannot prove physical fidelity.

`startup_s` is the first 90% crossing in the **imposed stimulus**, not a guaranteed
IC startup or monotonic-settling specification. `shutdown_v` is measured at
99.9% of the finite simulation end time, not an acceptance of safe discharge.
Buck/Cuk shutdown removes gate drive while holding the bus; LDO shutdown ramps
the input down. These are different cases, not a common system power-off test.
No AC loop-gain/phase-margin sweep is claimed.

The switched clock uses finite rise/fall of `T/100` and width `D*T - edge` to
preserve its integrated duty. The original 1 ns edge gave D=0.7744167 rather than
0.773 on ngspice-42. The original 0.001 duty-error gate remains unchanged, and a
real-simulator half-max-timestep regression checks mean/peak convergence.

### Cuk model applicability

For the uncoupled-inductor approximation, check the valley of the **sum** of the
currents flowing through the diode/switch. An individual inductor current
reversing is not, by itself, the diode discontinuous-mode criterion. Ninety-nine
of the 162 current analytical sensitivity points fail the positive-sum valley
check. Their CCM arithmetic remains visible for diagnosis, **not as a guaranteed
peak/RMS bound**. Exact feedback limits include the LT8330 Rev D p3 negative-FBX
range, pin-bias current and line regulation; `assumptions.json` records the source.

All four imposed-duty Cuk cases are outside the 5% mean-output screen. Retain
those results: do not adjust duty merely to turn the report green. Actual
closed-loop regulation/current stress still needs the correct manufacturer
model and independent bench evidence, including light-load mode.

## Exact components and MLCC curves

`component_candidates.json` binds five magnetic references to catalog candidates:
L201/L301/L302 XAL5050-103MEC, L202 XAL5050-682MEC and L203 XAL5030-472MEC.
Catalog typical Isat at 30% inductance drop and catalog temperature-rise current
are not guaranteed current limits on this PCB. Close L(I,T), high-frequency core
and winding loss, startup/fault current, footprint/height and actual temperature
before freezing parts. Cuk candidate rows expose the invalid-CCM screening status.

`capacitor_candidates.json` is a **candidate** catalog, not a BOM edit:

| Native bank | Candidate | Recorded caveat |
|---|---|---|
| Six 2x22 uF banks | TDK C3225X7R1C226M250AC, 16 V X7R 1210 | Production catalog part is **+/-20%**, max height 2.8 mm; do not apply generic +/-10% tolerance |
| C414/C415 | TDK C3225X7R1E106K250AC, 10 uF 25 V X7R 1210 | Higher voltage rating is not proof of interchangeability; effective-capacitance target still open |
| C410 | TDK C3225X7R1H105K160AA, 1 uF 50 V X7R 1210 | **NRND**, reference only; replacement, RMS current and effective-C target open |
| C105 | No exact MPN bound | 47 uF / 35 V, native 2220; MPN and bias evidence remain blocked |

Manufacturer source URLs, lifecycle check date and height are in the catalog.
Every reference's native capacitance, case and minimum voltage rating is checked.
Changing the second parallel capacitor cannot silently reuse a stale candidate.
The catalog-specific report takes precedence over `analysis.py`'s explicitly
named generic 10%-tolerance sensitivity. With the 20%-tolerance 22 uF candidate,
20 uF effective requires at least 68.91% bias retention under the assumed 15%
temperature and 3% aging losses. That is a **requirement**, not imported data.
The 3% aging and 50 mV voltage reserve are still engineering assumptions.

No actual manufacturer curve CSV has been imported. To import reviewed evidence:

```sh
python sim/power/capacitors.py --curve-dir /path/to/reviewed-packs --output build/edv/capacitors-with-curves
```

For each MPN, provide `<MPN>.json` containing `schema: 1`, exact `part_number`,
HTTPS `source_url`, ISO `retrieved_on`, named `reviewer`, `normalization_note`,
and `conditions` with `temperature_c`, `ac_voltage_rms_v`, `frequency_hz`.
Both `original` and `normalized_csv` records must contain a relative `file` path
and the actual lowercase SHA256. Retain the original vendor export or source
snapshot and the reviewer-controlled normalized CSV together in the pack.
CSV columns are exactly `voltage_v,retention`; normalize to 1 at 0 V, retain
strictly increasing voltage and finite positive fractions <=1. No extrapolation.
The importer calculates from the **hashed CSV bytes**, never optional JSON
`points`. Traversal, escaping symlinks, wrong MPN, missing conditions and hash
mismatch are rejected. Test fixtures are explicitly SYNTHETIC and are not vendor
curves. Hash matching proves byte identity, not source authenticity. Reference
curves at one temperature do not establish simultaneous bias/temperature or
lifetime bounds, and even a successful screen stays `NOT_QUALIFIED`.

## Manufacturer LTspice workflow

Obtain the exact device symbol and matching readable library from an authorized
ADI/LTspice installation or official device page, subject to its license. Do not
commit or publish vendor IP in this repo or generic CI artifacts. For example:

```sh
python sim/power/vendor_ltspice.py --device LT3045 --rail 5v2 --symbol /vendor/LT3045.asy --model /vendor/LT3045.lib --output build/edv/vendor-lt3045
python sim/power/vendor_ltspice.py --device LT3094 --symbol /vendor/LT3094.asy --model /vendor/LT3094.lib --output build/edv/vendor-lt3094
python sim/power/vendor_ltspice.py --device LT8330 --symbol /vendor/LT8330.asy --model /vendor/LT8330.lib --output build/edv/vendor-lt8330
```

These paths are examples, not a claim that those files are installed. Pin order
comes from `SpiceOrder`, not package pin numbers. Missing/encrypted/incompatible
headers mean BLOCKED; use the official demo workflow rather than guessing pins.
Do not substitute LT3045-1 or AP63200 for LT3045 or AP63201.

After preparation, inspect model licensing, all `.include` dependencies, pin
mapping, convergence and the vendor model's supported behaviors. Run the clean
bench in the actual licensed LTspice environment, retaining tool/version,
model/dependency hashes, deck, raw measurements and all stepped conditions.
Verify output polarity and realistic startup, full load, release and shutdown.
Repeat with reviewed effective C/ESR/DCR and temperature/load corners. The
preparation report stays `PREPARED_NOT_RUN`; it is **not** a result importer.
AP63201 exact vendor-model availability/coverage remains open. The preparation
uses assumed diode/ESR/DCR and does not independently qualify those components.

## Evidence and release boundary

`evidence.py` requires all 25 current case IDs, a clean source identity, matching
source digest, 125 artifact hashes, native-bound deck hashes and raw-log/JSON
measurement/assessment consistency. It rejects stale source, subsets, duplicated
cases and incomplete output. This is integrity verification, not cryptographic
simulator attestation or a full waveform-physics validator. `--root` permits
verifying an archived run against its accompanying exact source snapshot; never
silently point an old report at new source.

GitHub PR workflows may execute a **merge-test SHA**, not the PR head SHA.
`source_commit.txt`, `source_tree.txt`, `source.zip`, `results.json` and the
integrity report record that distinction. Match native-source files before
reusing a KiCad netlist from another read-only CI job.

The closure sequence is: resolve DAC supply/headroom architecture; run correct
vendor closed-loop/mode models; archive real MLCC and magnetic curves; close
thermal and input-protection/backfeed stress; then independent hardware tests
and a separate layout-gate review. Do not expand ADC/PHY or start PCB layout
because Python tests or ngspice returned success. See
[review evidence and open findings](../../docs/review/revb-edv/README.md).
