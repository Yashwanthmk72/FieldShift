# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
import copy
import json

import pytest

from app.engine import crops
from app.engine.crops import CropDataError, DATA, heuristic_params, load_crops, validate


def test_crops_json_validates_and_has_provenance():
    cs = load_crops()
    assert len(cs) == 27  # 11 original + 16 added in v0.7
    for c in cs:
        for k in crops.REQUIRED_PROVENANCE:
            assert c["provenance"][k]["status"] in ("sourced", "heuristic") and c["provenance"][k]["source"]


def test_unsourced_parameters_are_marked_heuristic_not_sourced():
    for c in load_crops():
        assert {"temp", "rain", "ph"} <= set(heuristic_params(c))  # nothing in the v0.4 ranges was verified against a source
        assert c["provenance"]["kc"]["status"] in ("sourced", "heuristic") and c["provenance"]["kc"]["url"].startswith("https://www.fao.org")


def test_every_sourced_parameter_has_a_url():
    for c in load_crops():
        for k, p in c["provenance"].items():
            if p["status"] == "sourced":
                assert p.get("url"), (c["id"], k)


def doc():
    return json.loads((DATA / "crops.json").read_text(encoding="utf-8"))


def test_loader_rejects_missing_provenance():
    d = doc(); del d["crops"][0]["provenance"]["temp"]
    with pytest.raises(CropDataError, match="provenance"):
        validate(d)


def test_loader_rejects_bad_ranges_and_duplicates():
    d = doc(); d["crops"][0]["temp"] = [30, 10]
    with pytest.raises(CropDataError, match="increasing"):
        validate(d)
    d = doc(); d["crops"].append(copy.deepcopy(d["crops"][0]))
    with pytest.raises(CropDataError, match="duplicate"):
        validate(d)


def test_loader_rejects_sourced_without_url_and_bad_fractions():
    d = doc(); d["crops"][0]["provenance"]["kc"] = {"status": "sourced", "source": "x"}
    with pytest.raises(CropDataError, match="url"):
        validate(d)
    d = doc(); d["crops"][0]["stage_fraction"]["mid"] = 0.9
    with pytest.raises(CropDataError, match="sum to 1"):
        validate(d)
