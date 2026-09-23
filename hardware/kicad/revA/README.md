# KiCad Rev.A project

This directory is the native KiCad 8 hierarchy scaffold for the first ServoHIL-I/O board.

Current state:
- hierarchy created;
- system architecture and sheet ownership frozen;
- regulator passives deliberately not guessed;
- XC7A35T FGG484 ball assignment deliberately not guessed;
- placement/routing has not started;
- `layout_gate.yaml` has `layout_allowed: false`.

Open `servohil_io_revA.kicad_pro` / `servohil_io_revA.kicad_sch` in KiCad 8+.

Child sheets are populated only after their freeze prerequisites are satisfied. The review documents under `docs/design/` are the electrical baseline until then.
