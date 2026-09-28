# Rev.B AXU2CGB Vivado I/O DRC harness

This directory is a **constraint-validation harness**, not the functional ServoHIL FPGA top.

It exists to answer one narrow question before functional integration:

> Do the current Rev.B AXU2CGB package-pin and IOSTANDARD assignments load and pass strict Vivado I/O DRC for the bound device `xczu2cg-sfvc784-1-e`?

It deliberately does **not** claim functional timing, latency, CDC correctness, plant execution, ADC timing, PWM capture timing or a production bitstream.

## Inputs

- target part: `xczu2cg-sfvc784-1-e`
- top: `servohil_io_drc_top`
- port contract: `hardware/revB/io_contract.json`
- physical assignment provenance: `hardware/carriers/axu2cgb/profile.json` plus the native `carrier.xdc.preview`
- harness XDC: `axu2cgb_io_drc.xdc`

The harness XDC is only approved for this I/O-DRC scope. It contains package-pin and IOSTANDARD assignments only. It is not the future functional timing XDC.

## Run

From repository root with Vivado on PATH:

```sh
vivado -mode batch -source fpga/revb/io_drc/run_io_drc.tcl -tclargs build/revb-vivado-io-drc "$(git rev-parse HEAD)"
```

PowerShell:

```powershell
vivado -mode batch -source fpga/revb/io_drc/run_io_drc.tcl -tclargs build/revb-vivado-io-drc $(git rev-parse HEAD)
```

Expected raw outputs:

- `report_drc.rpt`
- `report_io.rpt`
- `report_utilization.rpt`
- `io_drc_placed.dcp`
- `run_identity.txt`

The Tcl exits non-zero when Vivado reports an Error or Critical Warning DRC violation.

## Evidence boundary

A successful local command is not yet a checked-in PASS. The raw reports must be imported through the Rev.B source-bound evidence envelope with:

- exact source commit/digest;
- exact target part and harness top;
- Vivado version;
- raw report path and SHA-256.

Functional STA remains blocked until a real functional top, clock/generated-clock definitions, I/O delays and timing/CDC policy are bound.

## Import source-bound raw evidence

After a successful Vivado run, validate the raw directory independently:

```sh
python tools/revb_vivado_io_evidence.py validate-run build/revb-vivado-io-drc
```

Then prepare a non-overwriting evidence pack under the repository top-level
`evidence/` directory:

```sh
python tools/revb_vivado_io_evidence.py prepare \
  build/revb-vivado-io-drc \
  evidence/revb/vivado_io_drc/<run-id> \
  --source-commit "$(git rev-parse HEAD)" \
  --reviewer "<reviewer>" \
  --reviewed-on YYYY-MM-DD
```

The prepared `evidence.json` may be registered as
`prelayout_evidence_status.json -> vivado -> VIVADO_IO_DRC` only after review.
The importer checks the Vivado runtime I/O table against all 64 expected pins and
I/O standards, requires zero Error/Critical Warning DRC findings, and SHA-256
binds every retained raw artifact.

This still leaves `VIVADO_TIMING=NOT_RUN`.
