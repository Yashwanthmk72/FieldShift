# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Shared helpers for the frontend tests: seed a field through the app's own save API against the mock server."""
import json
import urllib.request

WS = "123e4567-e89b-12d3-a456-426614174000"
GEOM = {"type": "Polygon", "coordinates": [[[78.4800, 17.3800], [78.4850, 17.3800], [78.4850, 17.3850], [78.4800, 17.3850], [78.4800, 17.3800]]]}


def call(base, path, body=None, method=None, headers=None):
    h = {"Content-Type": "application/json", "X-Workspace-ID": WS, **(headers or {})}
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), headers=h, method=method or ("POST" if body is not None else "GET"))
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def seed_field(base, name="Test field"):
    an = call(base, "/api/analyze", {"geometry": GEOM, "priorities": {"resilience": .34, "profit": 0, "soil": .33, "water": .33}, "previous_crops": [], "seasons": 4})
    farm = {"name": name, "geometry": GEOM, "latitude": an["centroid"]["lat"], "longitude": an["centroid"]["lon"], "area_ha": an["area_ha"], "soil": {}, "priorities": {}, "notes": "", "previous_crops": [], "analysis": an, "done_actions": []}
    return call(base, "/api/farms", farm)
