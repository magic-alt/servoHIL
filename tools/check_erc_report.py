#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

path = Path(sys.argv[1] if len(sys.argv) > 1 else "build/servohil_io_revA_erc.rpt")
if not path.exists():
    raise SystemExit(f"ERC report not found: {path}")

text = path.read_text(encoding="utf-8-sig", errors="replace")
errors = len(re.findall(r";\s*error\b", text))
warnings = len(re.findall(r";\s*warning\b", text))

rules: dict[str, int] = {}
for rule in re.findall(r"\[([A-Za-z0-9_]+)\]:", text):
    rules[rule] = rules.get(rule, 0) + 1

print(f"ERC summary: errors={errors}, warnings={warnings}")
for rule, count in sorted(rules.items(), key=lambda x: (-x[1], x[0])):
    print(f" - {rule}: {count}")

if errors:
    raise SystemExit(f"ERC contains {errors} error(s)")

print("ERC error gate PASS")
