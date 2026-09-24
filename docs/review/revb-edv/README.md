# Rev.B EDV review checkpoint — 2026-09-24

**Electrical design: BLOCKED. PCB layout: not authorized.**
This is an engineering screening/automation checkpoint, not a board sign-off.
Native hardware, archive/revA and hardware release gates are unchanged.

## Implemented continuation

| Remote commit | Delivered and tested |
|---|---|
| c931882 | Install ngspice before EDV tests; preserve executable/version/hash provenance |
| d189832 + ccc7df1 | Real PWM convergence regression; finite-edge area fix; fresh-output/failed-run evidence |
| 3ce032b | All nine native capacitor banks; Cuk full/half-load applicability and feedback limits; explicit thermal blockers |
| a914037 | Exact MLCC catalog candidates, native value/case/rating checks and hashed reference-curve importer |
| 83a3bb2 | Complete matrix/source/deck/log/artifact integrity verifier; CI magnetic and capacitor reports |

The initial local continuation baseline was PR head
`eb5a8ae8f7396f6824e4af7c12ec7c1b9373f8a9`, whose EDV CI failed on numerical duty.
No local synthetic-repository commit SHA is presented as an upstream SHA.

## Reviewed immutable simulation checkpoint

The following run was downloaded and independently checked against its archived
source, not inferred merely from a green job:

- PR head: `3ce032bcde461a112a64dc2a5c4a995c57e8274b`.
- PR merge-test/source SHA: `c9a236530aacbe70fe788daf2aa9ecb8a63ac4cf`.
- GitHub Actions EDV run: `35955460209`; artifact: `10789424427`.
- Artifact SHA256: `7e97734bc6fe91abafad65c96eed005ca58b16fde99257ca26b02e9f527ea219`.
- Source digest: `7209132fd10ec4540c00ce6ff782af5de896f0346ea29916424ee9bc54eebc1a`.
- SPICE manifest SHA256: `a232017e3b996ec573a6dfbef72bfa00b704c015703b4c13292da892af44b4de`.
- 25/25 cases, 125 artifact hashes, clean worktree, `EXECUTED_NOT_QUALIFIED`.
- Actual simulator: ngspice-42; executable SHA256
  `820658317b0b54035208da41936fd6871ce924036e5ea4113a4168b821b7fc45`.
- Manufacturer macro-model cases: 0. Actual board measurements: 0.

This historical checkpoint predates the capacitor importer and final integrity
CI step. **Do not treat its source digest as the current head digest.** New CI
runs regenerate source-bound reports. The procedure is in `sim/power/README.md`.

## Electrical findings retained, not hidden

| Finding | Current result | Required action |
|---|---|---|
| DAC static span | 10.622608 V vs 10.6 V boundary | Review tighter rail accuracy or allowed analog output span; do not blindly lower RSET |
| Negative rail magnitude | 5.311304 V vs 5.3 V boundary | Close full-condition voltage margin, including dynamic effects |
| Minimum +/-5 V output headroom | 0.088904 V vs recommended 0.2 V | Current tolerance assumptions do not satisfy both headroom and supply constraints |
| RSET feasibility with 50 mV dynamic reserve | >=53.135 kohm for headroom, <=51.400 kohm for PVSS | No overlap under current assumptions |
| Cuk analytical mode | 99/162 sensitivity points inconsistent with CCM | Do not qualify inductor/switch stress from those CCM numbers |
| Cuk imposed-duty mean magnitude | 6.662 / 7.297 / 7.847 / 9.790 V in 8/12/15 V and derated cases | All outside 5% screen; not a measurement of real LT8330 closed-loop regulation |
| U201 thermal sensitivity | Up to about 210 C at 85 C ambient, eta=0.75, Rtheta=120 C/W | Assumed total-loss envelope, **not actual PCB temperature**; close losses/thermal path |
| 2x22 uF production candidate | +/-20%, requires about 68.91% DC-bias retention to retain 20 uF with current temperature/aging assumptions | Archive real exact-MPN curves; do not borrow a different tolerance/part's plot |

The 5% portable output screen is a diagnostic threshold, not a device datasheet
specification. Startup is the first 90% crossing in an imposed-input-ramp case;
shutdown values do not establish a safe-discharge deadline.

### Component qualification status

Five inductor references have exact Coilcraft catalog candidates. Three exact TDK
capacitor candidates cover eight banks; C105 remains MPN-unbound, C410's candidate
is NRND, and the two Cuk effective-capacitance targets remain open. No real DC-bias
curve has been imported. L(I,T), AC/core loss, ESR/ripple-current, land-pattern and
height verification, sourcing and mounted-board temperature remain open.
Manufacturer facts and source URLs are in `sim/power/*candidates.json` and
`assumptions.json`; engineering assumptions are separately labelled.

## Regression evidence at the documentation checkpoint

- Full repository suite: **123 tests, 123 passed, 0 skipped** with real ngspice
  and native canonical XML from the separately recorded KiCad job.
- Includes **66 EDV tests**, with real coarse/half-timestep ngspice execution.
- GitHub/Notion synchronization regression: **15/15 passed**.
- Read-only native label audit: no errors.
- Native cumulative supervision checks: passed.
- Native netlist contract: **705 generated assertions plus independent checks**.
- Native ERC: 11 sheets clean, using the actual CI-generated KiCad **10.0.6** report.
- Carrier validator: AXU2CGB `MAPPING_CANDIDATE`, 64 assigned GPIO; SoM
  `BLOCKED_VENDOR_BINDING`. Neither is relabelled hardware-verified.
- `analysis.py --strict-design`: expected exit **2** with unresolved blockers.
- Hardware/archive diff against the starting snapshot: empty.

Native evidence job: `35955460158`, artifact `10790481423`, artifact SHA256
`cd31e570bb022202a55a5c2892cfeb0aa2abc803084e86c52e67a1930ee8512f`.
Its **37 native source files** were compared byte-for-byte with the continuation
checkout before consuming its canonical XML. KiCad export/ERC ran in CI; local
Python checks consumed those actual outputs. No claim of locally executing KiCad.

Review was performed inline; no independent human or separate-agent sign-off is
claimed. Passing these tests establishes implementation/evidence integrity, not
that the electrical design or hardware safety requirements are complete.
