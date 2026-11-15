# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Client/server scoring parity: 200 random inputs through Python and through the real frontend JS module (node)."""
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from app.engine import scoring

ROOT = Path(__file__).resolve().parents[1]
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def make_cases(n=200, seed=7):
    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        comps = {k: round(rng.uniform(0, 100), rng.choice([0, 1, 3])) for k in ("climate", "soil_and_rotation", "water_fit", "resilience")}
        comps["profit"] = rng.choice([None, round(rng.uniform(0, 100), 1)])
        pr = {k: rng.choice([0, 0, round(rng.uniform(0, 100), 1)]) for k in scoring.PRIORITY_KEYS}
        cases.append({"components": comps, "priorities": pr})
    cases += [{"components": {"climate": 50.0, "soil_and_rotation": 50.0, "water_fit": 50.0, "resilience": 50.0, "profit": None}, "priorities": {"resilience": 1, "water": 0, "soil": 0, "profit": 0}},
              {"components": {"climate": 0.5, "soil_and_rotation": 0, "water_fit": 0, "resilience": 0, "profit": None}, "priorities": {}}]  # .5 boundary: JS Math.round vs Python round
    return cases


@needs_node
def test_python_and_javascript_scores_match_for_200_random_inputs(tmp_path):
    cases = make_cases()
    f = tmp_path / "cases.json"; f.write_text(json.dumps(cases))
    out = subprocess.run(["node", str(ROOT / "tests" / "parity_node.mjs"), str(f)], capture_output=True, text=True, check=True, cwd=ROOT)
    js = json.loads(out.stdout)
    py = [scoring.combine_score(c["components"], scoring.normalize_priorities(c["priorities"])) for c in cases]
    assert len(js) == len(py) >= 200 and js == py
