"""One-off data builder used to extend crops.json from 11 to 27 crops (FieldShift v0.7).
AI-assisted: written with an AI coding assistant. All NEW agronomic parameters are 'heuristic':
they were NOT verified against a source in this session. Reference URLs say where to verify them."""
import json, pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "backend/app/data/crops.json"
doc = json.loads(P.read_text(encoding="utf-8"))

ECO = "https://ecocrop.apps.fao.org/ecocrop/srv/en/home"
FAO56 = "https://www.fao.org/4/x0490e/x0490e0b.htm"
HEUR_RANGE = "Author estimate (not verified in v0.7). Cross-check against FAO EcoCrop and local extension before relying on it."
KC_NOTE = "Value recalled from FAO-56 Table 12 (Kc) / Table 11 (stage lengths); NOT re-verified in v0.7, so it stays heuristic. Where FAO prints a range the midpoint is used."
GUIDE = "FieldShift v0.4 crop guide (unreviewed). Cross-check against FAO EcoCrop / local extension before relying on it."

def prov(proxy_kc=False, kc_status="heuristic", kc_src=None):
    h = lambda s: {"status": "heuristic", "source": s, "url": ECO}
    return {
        "temp": h(HEUR_RANGE), "rain": h(HEUR_RANGE), "ph": h(HEUR_RANGE), "water": h(HEUR_RANGE),
        "resilience": {"status": "heuristic", "source": "FieldShift editorial score of drought/heat tolerance (0-100). Not a measured quantity."},
        "soil": h(HEUR_RANGE), "fixer": h("General agronomy knowledge (legumes fix nitrogen via rhizobia). Not cited to a specific page."),
        "kc": {"status": kc_status, "source": kc_src or KC_NOTE, "url": FAO56},
        "stage_fraction": {"status": "heuristic", "source": kc_src or KC_NOTE, "url": FAO56},
    }

def frac(*days):
    t = sum(days)
    f = [round(d / t, 3) for d in days]
    f[-1] = round(1 - sum(f[:-1]), 3)
    return dict(zip(("ini", "dev", "mid", "late"), f))

N = []
def add(id, name, family, season, water, temp, rain, ph, soil, fixer, res, kc, days, desc, uses, q, perennial=False, kc_src=None):
    c = {"id": id, "name": name, "family": family, "season": season, "water": water, "temp": temp, "rain": rain, "ph": ph, "soil": soil,
         "fixer": fixer, "resilience": res, "description": desc, "uses": uses, "image_query": q,
         "kc": dict(zip(("ini", "mid", "end"), kc)), "stage_fraction": frac(*days), "provenance": prov(kc_src=kc_src)}
    if perennial:
        c["perennial"] = True
    N.append(c)

add("barley", "Barley", "Grass", "Cool season", "Low–medium", [8, 22], [300, 750], [6, 8], "Well-drained loam; tolerates saline and alkaline soils better than wheat", False, 76, (0.3, 1.15, 0.25), (20, 25, 60, 30),
    "A fast-maturing cool-season cereal that copes with drier and saltier land than wheat. Useful for feed, malting and food.", "Livestock feed, malting, food grain.", "barley field")
add("cassava", "Cassava", "Tuber", "Warm season", "Low–medium", [20, 30], [800, 1800], [5.5, 7], "Light, well-drained sandy loam", False, 88, (0.3, 0.8, 0.3), (20, 40, 90, 60),
    "A drought-tolerant root crop for warm climates that keeps well in the ground as a food reserve. Needs a long, frost-free season.", "Food (roots, flour), starch, animal feed.", "cassava field plants")
add("sweet_potato", "Sweet potato", "Tuber", "Warm season", "Medium", [20, 30], [750, 1500], [5.5, 6.5], "Loose, well-drained sandy loam", False, 70, (0.5, 1.15, 0.65), (20, 30, 60, 40),
    "A quick-growing vine crop whose storage roots and leaves are both eaten. Dislikes waterlogging and heavy clay.", "Food (roots and leaves), animal feed.", "sweet potato field")
add("lentil", "Lentil", "Legume", "Cool season", "Low", [10, 25], [300, 600], [6, 8], "Well-drained loam; avoid waterlogging", True, 75, (0.4, 1.1, 0.3), (20, 30, 60, 40),
    "A cool-season pulse that fixes nitrogen and suits drier, well-drained fields. Weak competitor against weeds early on.", "Food (dal, soups), protein-rich rotation crop.", "lentil crop field")
add("pigeonpea", "Pigeon pea", "Legume", "Warm season", "Low", [20, 32], [600, 1000], [5, 7.5], "Well-drained loam; deep roots tolerate dry spells", True, 88, (0.4, 1.1, 0.35), (30, 50, 80, 40),
    "A deep-rooted, drought-hardy pulse that fixes nitrogen and is often intercropped with cereals. Long duration in many varieties.", "Food (dal), fodder, fuelwood stalks.", "pigeon pea field", kc_src="Pulse-group proxy values recalled from FAO-56; pigeon pea has no printed row. NOT verified; heuristic.")
add("mungbean", "Mung bean", "Legume", "Warm season", "Low", [22, 35], [350, 700], [6, 7.5], "Well-drained sandy loam to loam", True, 80, (0.4, 1.05, 0.475), (20, 30, 30, 20),
    "A short-season pulse that fixes nitrogen and fits well between cereal crops. Sensitive to waterlogging and cold.", "Food (whole grain, sprouts, dal).", "mung bean green gram field")
add("mustard", "Mustard / rapeseed", "Oilseed", "Cool season", "Low–medium", [10, 25], [300, 700], [5.5, 7.5], "Well-drained loam", False, 66, (0.35, 1.075, 0.35), (20, 25, 60, 30),
    "A cool-season oilseed grown for oil and meal. Needs adequate moisture at flowering and sulphur on poor soils.", "Edible oil, meal for livestock, condiment seed.", "mustard rapeseed field yellow flowers")
add("sesame", "Sesame", "Oilseed", "Warm season", "Low", [24, 35], [400, 800], [5.5, 8], "Light, well-drained soils", False, 85, (0.35, 1.1, 0.25), (20, 30, 40, 20),
    "A heat-loving, drought-tolerant oilseed that suits light soils. Very sensitive to waterlogging and to rain at harvest.", "Oil, seed, tahini.", "sesame field")
add("tomato", "Tomato", "Vegetable", "Warm season", "Medium–high", [18, 28], [400, 800], [6, 7], "Fertile, well-drained loam rich in organic matter", False, 40, (0.6, 1.15, 0.8), (30, 40, 40, 25),
    "A high-value vegetable that needs steady moisture, staking and close disease scouting. Prices and yields swing widely.", "Fresh market, processing (paste, sauce).", "tomato crop field")
add("onion", "Onion", "Vegetable", "Cool season", "Medium", [12, 25], [350, 750], [6, 7.5], "Fertile, friable, well-drained soil", False, 45, (0.7, 1.05, 0.75), (15, 25, 70, 40),
    "A bulb vegetable with shallow roots that needs frequent light irrigation and weed control. Storage quality depends on curing.", "Fresh market, storage, processing.", "onion field")
add("okra", "Okra", "Vegetable", "Warm season", "Medium", [22, 35], [500, 1200], [6, 7], "Well-drained loam", False, 62, (0.6, 1.05, 0.8), (20, 25, 35, 20),
    "A warm-season vegetable that tolerates heat and keeps producing pods for weeks if picked often.", "Fresh vegetable, processing.", "okra field",
    kc_src="No dedicated FAO-56 row recalled; vegetable-group proxy values. NOT verified; heuristic.")
add("chili", "Chili pepper", "Vegetable", "Warm season", "Medium", [20, 32], [600, 1250], [5.5, 7], "Well-drained, fertile loam", False, 55, (0.6, 1.05, 0.9), (25, 35, 40, 20),
    "A warm-season spice and vegetable crop that is sensitive to waterlogging, cold nights and viral diseases.", "Fresh, dried spice, sauces.", "chili pepper field")
add("watermelon", "Watermelon", "Fruit", "Warm season", "Medium", [22, 32], [400, 700], [6, 7], "Light, well-drained sandy loam", False, 60, (0.4, 1.0, 0.75), (20, 30, 30, 30),
    "A sprawling warm-season fruit crop that likes sandy soil, full sun and moisture during fruit set.", "Fresh fruit, seed.", "watermelon field")
add("cotton", "Cotton", "Fibre & sugar", "Warm season", "Medium", [21, 35], [500, 1000], [5.5, 8], "Deep, well-drained loam or clay loam", False, 66, (0.35, 1.175, 0.6), (30, 50, 60, 55),
    "A long-season fibre crop that needs a warm, frost-free period and dry weather at boll opening. Heavy pest pressure in many regions.", "Fibre (lint), seed oil, cake.", "cotton field")
add("sugarcane", "Sugarcane", "Fibre & sugar", "Warm season", "High", [22, 32], [1100, 1800], [6, 7.5], "Deep, fertile, well-drained loam", False, 42, (0.4, 1.25, 0.75), (50, 70, 220, 140),
    "A tall perennial grass grown for sugar, usually as a 12–18 month crop with ratoon regrowth. Needs plenty of water and a nearby mill.", "Sugar, ethanol, jaggery, bagasse.", "sugarcane field", perennial=True)
add("banana", "Banana", "Fruit", "Warm season", "High", [22, 32], [1200, 2200], [5.5, 7], "Deep, fertile, well-drained loam; wind-sheltered", False, 35, (0.5, 1.1, 1.0), (120, 90, 120, 60),
    "A tropical perennial fruit crop that needs steady water, warmth and shelter from wind. Cropping runs over several years.", "Fresh fruit, cooking bananas, processing.", "banana plantation", perennial=True)

for c in doc["crops"]:  # existing crops: record where to verify heuristic values (no value is changed)
    for k in ("temp", "rain", "ph", "water", "soil"):
        p = c["provenance"].get(k)
        if p and p["status"] == "heuristic" and "url" not in p:
            p["url"] = ECO
    f = c["provenance"].get("fixer")
    if f and f["status"] == "heuristic" and "url" not in f:
        f["url"] = ECO
have = {c["id"] for c in doc["crops"]}
doc["crops"] += [c for c in N if c["id"] not in have]
doc["schema_version"] = 2
doc["retrieved"] = "2026-11-14"
doc["note"] = ("Agronomic ranges are heuristics and are labelled as such. Only Kc and stage fractions of 9 original crops carry a verified FAO-56 source. "
               "The 16 crops added in v0.7 are ALL heuristic: Kc and stage values were recalled from FAO-56 and not re-verified. Every parameter has a url saying where to verify it. "
               "Set status to 'sourced' only after checking the value against that source. 'perennial': true marks crops that do not fit a season-by-season rotation.")
P.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(len(doc["crops"]), "crops")
