#!/usr/bin/env python3
"""Hash-bound Coilcraft XAL L-vs-current reference-curve importer and screen.

The imported manufacturer curve remains typical/reference evidence. It cannot
qualify startup/fault saturation, AC/core loss, mounted-board thermal behavior,
or production current limits.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, root: Path = ROOT):
    path = root / "sim/power" / (name + ".py")
    spec = importlib.util.spec_from_file_location("edv_magnetics_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hashed_file(manifest: Path, record: dict, name: str) -> bytes:
    rel = Path(record["file"])
    target = (manifest.parent / rel).resolve()
    if rel.is_absolute() or not target.is_relative_to(manifest.parent.resolve()):
        raise ValueError(name + " file escapes evidence pack")
    raw = target.read_bytes()
    digest = record.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError(name + " SHA-256 missing/invalid")
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(name + " file hash mismatch")
    return raw


def load_curve(path: str | Path, part_number: str) -> dict:
    path = Path(path).resolve()
    blob = path.read_bytes()
    try:
        manifest = json.loads(blob)
        if manifest.get("schema") != 1 or manifest.get("part_number") != part_number:
            raise ValueError("magnetic curve schema/MPN mismatch")
        if manifest.get("manufacturer") != "Coilcraft":
            raise ValueError("magnetic curve manufacturer must be Coilcraft")
        if manifest.get("characteristic") != "L_VS_CURRENT_REFERENCE":
            raise ValueError("unsupported magnetic curve characteristic")
        source = urlparse(manifest["source_url"])
        if source.scheme != "https" or not source.hostname:
            raise ValueError("HTTPS manufacturer source required")
        date.fromisoformat(manifest["retrieved_on"])
        for field in ("reviewer", "normalization_note"):
            if not isinstance(manifest.get(field), str) or not manifest[field].strip():
                raise ValueError("missing " + field)
        conditions = manifest.get("conditions")
        if not isinstance(conditions, dict):
            raise ValueError("missing magnetic curve conditions")
        temperature = conditions.get("temperature_c")
        if type(temperature) not in (int, float) or not math.isfinite(temperature) or temperature <= -273.15:
            raise ValueError("invalid magnetic curve temperature")
        basis = conditions.get("curve_basis")
        if not isinstance(basis, str) or not basis.strip():
            raise ValueError("missing magnetic curve basis")
        original = _hashed_file(path, manifest["original"], "original")
        normalized = _hashed_file(path, manifest["normalized_csv"], "normalized_csv")
        reader = csv.reader(io.StringIO(normalized.decode("utf-8-sig")))
        if next(reader, None) != ["current_a", "inductance_uh"]:
            raise ValueError("wrong magnetic curve CSV columns")
        points = []
        previous = -1.0
        for row in reader:
            if len(row) != 2:
                raise ValueError("wrong magnetic curve CSV row")
            current, inductance = map(float, row)
            if not math.isfinite(current) or not math.isfinite(inductance):
                raise ValueError("nonfinite magnetic curve value")
            if current < 0 or current <= previous or inductance <= 0:
                raise ValueError("invalid/nonmonotonic magnetic curve")
            points.append([current, inductance])
            previous = current
        if len(points) < 2 or points[0][0] != 0:
            raise ValueError("magnetic curve must start at 0 A and contain at least two points")
        return {
            "part_number": part_number,
            "points": points,
            "provenance": {
                "source_url": manifest["source_url"],
                "retrieved_on": manifest["retrieved_on"],
                "reviewer": manifest["reviewer"],
                "normalization_note": manifest["normalization_note"],
                "conditions": conditions,
                "original": manifest["original"],
                "normalized_csv": manifest["normalized_csv"],
                "manifest_sha256": hashlib.sha256(blob).hexdigest(),
                "original_sha256": hashlib.sha256(original).hexdigest(),
                "evidence_class": "REFERENCE_TYPICAL_CURVE_NOT_GUARANTEED",
            },
        }
    except (KeyError, TypeError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
        raise ValueError("invalid magnetic curve evidence schema: " + str(exc)) from exc


def inductance_at(curve: dict, current_a: float, part_number: str) -> float:
    if curve.get("part_number") != part_number:
        raise ValueError("magnetic curve MPN mismatch")
    if not math.isfinite(current_a) or current_a < 0:
        raise ValueError("invalid magnetic screen current")
    points = curve.get("points", [])
    if len(points) < 2:
        raise ValueError("missing magnetic curve points")
    if current_a < points[0][0] or current_a > points[-1][0]:
        raise ValueError("no magnetic curve extrapolation")
    for (i0, l0), (i1, l1) in zip(points, points[1:]):
        if i0 <= current_a <= i1:
            if i1 == i0:
                raise ValueError("duplicate magnetic curve current")
            ratio = (current_a - i0) / (i1 - i0)
            return l0 + ratio * (l1 - l0)
    if current_a == points[-1][0]:
        return points[-1][1]
    raise ValueError("magnetic screen current not covered")


def report(root: str | Path = ROOT, curve_dir: str | Path | None = None) -> dict:
    root = Path(root)
    qualification = load_module("qualification", root)
    base = qualification.report(root)
    registry = json.loads((root / "hardware/revB/component_evidence_sources.json").read_text())
    source = registry["magnetics"]["datasheet_url"]
    catalog = json.loads((root / "sim/power/component_candidates.json").read_text())
    curves: dict[str, dict] = {}
    rows = []
    if curve_dir is not None:
        curve_dir = Path(curve_dir)
    for item in base["magnetics"]:
        mpn = item["part_number"]
        if curve_dir is not None and mpn not in curves:
            path = curve_dir / (mpn + ".json")
            if path.is_file():
                curve = load_curve(path, mpn)
                if curve["provenance"]["source_url"] != source:
                    raise ValueError(mpn + ": curve source URL differs from reviewed Coilcraft source")
                curves[mpn] = curve
        curve = curves.get(mpn)
        row = {
            "reference": item["reference"],
            "part_number": mpn,
            "screen_current_a": item["screen_peak_a"],
            "stress_model_status": item["stress_model_status"],
            "curve_status": "BLOCKED_MISSING_CURVE",
            "curve_provenance": None,
            "screen_inductance_uh": None,
            "screen_retention": None,
            "qualification": "NOT_QUALIFIED",
            "limitations": [
                "manufacturer L-vs-current graph is typical/reference data, not a guaranteed worst-case limit",
                "analytical peak current is a screening point; invalid CCM corners are not safe bounds",
                "AC/core+winding loss, startup/short saturation and mounted-board temperature remain separate evidence",
            ],
        }
        if curve is not None:
            row["curve_provenance"] = curve["provenance"]
            try:
                value_uh = inductance_at(curve, item["screen_peak_a"], mpn)
            except ValueError as exc:
                if "extrapolation" not in str(exc):
                    raise
                row["curve_status"] = "BLOCKED_CURVE_RANGE_NO_EXTRAPOLATION"
            else:
                nominal_uh = catalog["parts"][mpn]["inductance_h"] * 1e6
                row["screen_inductance_uh"] = value_uh
                row["screen_retention"] = value_uh / nominal_uh
                row["curve_status"] = "SCREEN_ONLY_REFERENCE_CURVE"
        rows.append(row)
    return {
        "status": "NOT_QUALIFIED",
        "layout_allowed": False,
        "manufacturer": "Coilcraft",
        "source_url": source,
        "source_status": registry["magnetics"]["source_status"],
        "imported_curve_count": len(curves),
        "rows": rows,
        "warning": "Hash matching proves byte identity and reviewer normalization only. Typical manufacturer curves do not establish guaranteed current limits or board qualification.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curve-dir", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "build/edv/magnetics")
    args = parser.parse_args(argv)
    try:
        result = report(ROOT, args.curve_dir)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "magnetics.json").write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(
            "Magnetic references:",
            len(result["rows"]),
            "; imported exact-MPN reference curves:",
            result["imported_curve_count"],
            "; NOT_QUALIFIED",
        )
    except (OSError, ValueError, KeyError) as exc:
        print("MAGNETIC EVIDENCE ERROR:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
