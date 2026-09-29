#!/usr/bin/env python3
"""Inspect an ASCII DXF and emit a compact mechanical-geometry inventory.

This is intentionally dependency-free so the pinned AXU2CGB manufacturer DXF
can be audited in CI without installing a CAD stack. It does not infer connector
identity from geometry; it reports source entities for engineering review.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _pairs(text: str) -> list[tuple[int, str]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and not lines[-1].strip():
        lines.pop()
    if len(lines) % 2:
        raise ValueError("DXF group-code stream has an odd number of lines")
    out: list[tuple[int, str]] = []
    for idx in range(0, len(lines), 2):
        try:
            code = int(lines[idx].strip())
        except ValueError as exc:
            raise ValueError(f"invalid DXF group code at line {idx + 1}") from exc
        out.append((code, lines[idx + 1].strip()))
    return out


def _entities(pairs: list[tuple[int, str]]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    section = None
    current: dict[str, Any] | None = None
    pending_section = False

    def finish() -> None:
        nonlocal current
        if current is not None:
            entities.append(current)
            current = None

    for code, value in pairs:
        if code == 0 and value == "SECTION":
            finish()
            pending_section = True
            continue
        if pending_section and code == 2:
            section = value
            pending_section = False
            continue
        if code == 0 and value == "ENDSEC":
            finish()
            section = None
            continue
        if section not in {"ENTITIES", "BLOCKS"}:
            continue
        if code == 0:
            finish()
            if value in {"ENDSEC", "ENDBLK", "BLOCK"}:
                current = None
            else:
                current = {"type": value, "section": section, "groups": defaultdict(list)}
            continue
        if current is not None:
            current["groups"][code].append(value)
    finish()
    return entities


def _num(values: list[str] | None, idx: int = 0) -> float | None:
    if not values or idx >= len(values):
        return None
    try:
        return float(values[idx])
    except ValueError:
        return None


def _points(groups: dict[int, list[str]], xcode: int = 10, ycode: int = 20) -> list[list[float]]:
    xs = groups.get(xcode, [])
    ys = groups.get(ycode, [])
    pts: list[list[float]] = []
    for x, y in zip(xs, ys):
        try:
            pts.append([float(x), float(y)])
        except ValueError:
            pass
    return pts


def inspect(text: str) -> dict[str, Any]:
    pairs = _pairs(text)
    entities = _entities(pairs)
    type_counts = Counter(e["type"] for e in entities)
    circles: list[dict[str, float]] = []
    text_items: list[dict[str, Any]] = []
    inserts: list[dict[str, Any]] = []
    geometry_points: list[list[float]] = []
    per_type_bounds: dict[str, list[list[float]]] = defaultdict(list)

    for ent in entities:
        typ = ent["type"]
        g = ent["groups"]
        pts = _points(g)
        if typ == "LINE":
            p2 = _points(g, 11, 21)
            pts += p2
        if pts:
            geometry_points.extend(pts)
            per_type_bounds[typ].extend(pts)

        if typ in {"CIRCLE", "ARC"}:
            x, y, radius = _num(g.get(10)), _num(g.get(20)), _num(g.get(40))
            if x is not None and y is not None and radius is not None:
                circles.append({"x": x, "y": y, "radius": radius})

        if typ in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION"}:
            raw = "".join(g.get(3, [])) + "".join(g.get(1, []))
            x, y = _num(g.get(10)), _num(g.get(20))
            if raw or x is not None or y is not None:
                text_items.append({"type": typ, "text": raw, "x": x, "y": y})

        if typ == "INSERT":
            inserts.append({
                "name": (g.get(2) or [None])[0],
                "x": _num(g.get(10)),
                "y": _num(g.get(20)),
                "rotation_deg": _num(g.get(50)) or 0.0,
                "scale_x": _num(g.get(41)) or 1.0,
                "scale_y": _num(g.get(42)) or 1.0,
            })

    def bounds(points: list[list[float]]) -> dict[str, float] | None:
        if not points:
            return None
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return {
            "min_x": min(xs),
            "max_x": max(xs),
            "min_y": min(ys),
            "max_y": max(ys),
            "span_x": max(xs) - min(xs),
            "span_y": max(ys) - min(ys),
        }

    radius_hist = Counter(round(row["radius"], 4) for row in circles)
    likely_mounting = [
        row for row in circles
        if 1.0 <= row["radius"] <= 2.5
    ]
    relevant_text = [
        row for row in text_items
        if any(key in str(row["text"]).upper() for key in ("J12", "J15", "100", "85", "MM", "HOLE", "MOUNT"))
    ]

    return {
        "format": "ASCII_DXF",
        "entity_count": len(entities),
        "entity_type_counts": dict(sorted(type_counts.items())),
        "geometry_bounds": bounds(geometry_points),
        "bounds_by_entity_type": {
            typ: bounds(points) for typ, points in sorted(per_type_bounds.items())
        },
        "circle_count": len(circles),
        "circle_radius_histogram": {str(k): v for k, v in sorted(radius_hist.items())},
        "likely_mounting_hole_circles": likely_mounting,
        "text_entity_count": len(text_items),
        "relevant_text": relevant_text,
        "insert_count": len(inserts),
        "inserts": inserts[:200],
        "note": "Geometry inventory only. Connector/hole identity must be confirmed against the manufacturer drawing/STEP before freezing PCB coordinates.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dxf", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = args.dxf.read_text(encoding="utf-8", errors="strict")
    report = inspect(raw)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
