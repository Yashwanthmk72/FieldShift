# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Geometry helpers. Pure functions."""
from __future__ import annotations

import math
from typing import Any


class GeometryError(ValueError):
    pass


def _ring(geometry: dict[str, Any]) -> list[list[float]]:
    coords = geometry.get("coordinates") or []
    if geometry.get("type") == "MultiPolygon" and coords:
        coords = coords[0]
    if geometry.get("type") not in ("Polygon", "MultiPolygon") or not coords or len(coords[0]) < 4:
        raise GeometryError("Send a Polygon boundary with at least 3 corners")
    if len(coords[0]) > 5000:
        raise GeometryError("Boundary has too many points (max 5000)")
    try:
        return [[float(x), float(y)] for x, y, *_ in coords[0]]
    except (TypeError, ValueError) as exc:
        raise GeometryError("Boundary coordinates must be numbers") from exc


def ring_area_ha(ring: list[list[float]]) -> float:
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:] + ring[:1]):
        total += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))
    return abs(total * 6378137 ** 2 / 2) / 10000


def inside(pt: tuple[float, float], ring: list[list[float]]) -> bool:
    x, y, hit = pt[0], pt[1], False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1:
            hit = not hit
    return hit


def polygon_centroid(ring: list[list[float]]) -> dict[str, float] | None:
    """Area-weighted centroid (planar approximation; fine at field scale). None for degenerate rings."""
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(a) < 1e-14:
        return None
    return {"lat": cy / (3 * a), "lon": cx / (3 * a)}


def interior_point(ring: list[list[float]]) -> dict[str, float]:
    """A point guaranteed inside the polygon: midpoint of the widest horizontal chord (scanline)."""
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    ys = [p[1] for p in pts]
    lo, hi = min(ys), max(ys)
    best: tuple[float, float, float] | None = None
    for k in range(1, 20):
        y = lo + (hi - lo) * k / 20
        xs = sorted((x1 + (y - y1) * (x2 - x1) / ((y2 - y1) or 1e-12)) for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]) if (y1 > y) != (y2 > y))
        for a, b in zip(xs[::2], xs[1::2]):
            if best is None or b - a > best[0]:
                best = (b - a, (a + b) / 2, y)
    return {"lat": best[2], "lon": best[1]} if best else {"lat": sum(ys) / len(ys), "lon": sum(p[0] for p in pts) / len(pts)}


def sample_points(ring: list[list[float]], limit: int = 4) -> tuple[dict[str, float], list[dict[str, float]]]:
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring = ring[:-1]
    centre = polygon_centroid(ring) or {"lat": sum(p[1] for p in ring) / len(ring), "lon": sum(p[0] for p in ring) / len(ring)}
    if not inside((centre["lon"], centre["lat"]), ring):  # concave shapes: use a point guaranteed to be inside
        centre = interior_point(ring)
    points = []
    for i in (1, 2, 3):
        for j in (1, 2, 3):
            p = (min(xs) + (max(xs) - min(xs)) * i / 4, min(ys) + (max(ys) - min(ys)) * j / 4)
            if inside(p, ring):
                points.append({"lat": round(p[1], 5), "lon": round(p[0], 5)})
    step = max(1, len(points) // limit)
    points = points[::step][:limit] or [centre]
    return centre, points
