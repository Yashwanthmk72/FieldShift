# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Static agronomy content for FieldShift v0.4.

General guidance compiled from widely published extension-style knowledge (FAO crop
guides, ECHO, university extension fact sheets). It is *general*: planting dates,
durations and pest lists vary by variety and region. The UI labels it accordingly.
"""
from __future__ import annotations

from typing import Any

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# crop id -> {zone: (sow_months, harvest_months)} for the NORTHERN hemisphere.
# "temperate" = |lat| >= 23.5, "tropics" = |lat| < 23.5. Southern hemisphere is shifted by 6 months.
# Tropical windows describe the *main rainy-season* crop; check your local rainfall calendar.
SOW: dict[str, dict[str, tuple[list[int], list[int]]]] = {
    "maize":     {"temperate": ([4, 5], [9, 10]),  "tropics": ([6, 7], [10, 11])},
    "sorghum":   {"temperate": ([5, 6], [9, 10]),  "tropics": ([6, 7], [10, 11])},
    "millet":    {"temperate": ([5, 6], [8, 9]),   "tropics": ([6, 7], [9, 10])},
    "soybean":   {"temperate": ([5, 6], [9, 10]),  "tropics": ([6, 7], [10, 11])},
    "cowpea":    {"temperate": ([5, 6], [8, 9]),   "tropics": ([6, 7], [9, 10])},
    "rice":      {"temperate": ([5, 6], [9, 10]),  "tropics": ([6, 7], [10, 11])},
    "groundnut": {"temperate": ([5, 6], [9, 10]),  "tropics": ([6, 7], [10, 11])},
    "chickpea":  {"temperate": ([3, 4], [7, 8]),   "tropics": ([10, 11], [2, 3])},
    "wheat":     {"temperate": ([10, 11], [6, 7]), "tropics": ([11, 12], [3, 4])},
    "potato":    {"temperate": ([3, 4], [7, 8]),   "tropics": ([10, 11], [1, 2])},
    "sunflower": {"temperate": ([4, 5], [8, 9]),   "tropics": ([6, 7], [9, 10])},
}

MATURITY_DAYS: dict[str, tuple[int, int]] = {
    "maize": (90, 140), "sorghum": (100, 130), "millet": (70, 100), "soybean": (90, 130),
    "cowpea": (60, 100), "rice": (105, 150), "groundnut": (100, 140), "chickpea": (90, 120),
    "wheat": (110, 150), "potato": (90, 120), "sunflower": (90, 125),
}

# Each stage: (name, typical timing, what is happening, image search term appended to the crop name)
CONTENT: dict[str, dict[str, Any]] = {
    "maize": {
        "stages": [
            ("Sowing & emergence", "Days 0–10", "Seed is sown 3–5 cm deep once soil is warm; seedlings emerge in about a week.", "seedling emergence"),
            ("Vegetative growth", "Days 10–55", "Rapid leaf and stalk growth. Nitrogen demand peaks; keep weeds down.", "vegetative field"),
            ("Tasselling & silking", "Days 55–75", "The most water-sensitive window. Drought here cuts grain set.", "tassel silk flowering"),
            ("Grain fill & harvest", "Days 75–140", "Kernels fill and dry down; harvest when husks are dry and kernels hard.", "cob harvest"),
        ],
        "pests": ["Fall armyworm", "Stem borers", "Maize streak virus", "Grey leaf spot"],
        "prev": ["Soybean", "Cowpea", "Groundnut", "Chickpea"], "next": ["Soybean", "Cowpea", "Groundnut"],
        "tips": ["Apply nitrogen in split doses rather than all at planting.", "Ensure moisture around tasselling and silking.", "Scout weekly for armyworm from seedling stage.", "Follow with a legume to rebuild soil nitrogen."],
        "nutrients": "Heavy nitrogen feeder; benefits from phosphorus at planting and zinc on low-zinc soils.",
    },
    "sorghum": {
        "stages": [
            ("Sowing & emergence", "Days 0–10", "Sow into warm soil (>18 °C); shallow sowing helps emergence.", "seedling"),
            ("Tillering & growth", "Days 10–50", "Plants tiller and build leaf area; tolerates short dry spells well.", "plant field growth"),
            ("Heading & flowering", "Days 50–75", "Panicles emerge and flower; avoid late heavy nitrogen.", "panicle flowering"),
            ("Grain fill & harvest", "Days 75–130", "Grain hardens; harvest when seed is firm and at the 'black layer' stage.", "grain harvest"),
        ],
        "pests": ["Sorghum midge", "Shoot fly", "Stem borers", "Birds at grain fill", "Striga (witchweed) in parts of Africa"],
        "prev": ["Cowpea", "Groundnut", "Soybean"], "next": ["Cowpea", "Groundnut", "Chickpea"],
        "tips": ["Choose short-cycle varieties where rains end early.", "Thin seedlings to avoid competition.", "Bird scaring or early harvest protects ripe heads.", "Rotate with a legume to reduce Striga and disease build-up."],
        "nutrients": "Moderate nitrogen and phosphorus needs; responds well to manure on poor soils.",
    },
    "millet": {
        "stages": [
            ("Sowing & emergence", "Days 0–7", "Very small seed; sow shallowly in warm soil at rain onset.", "seedling"),
            ("Tillering", "Days 7–35", "Fast early growth; tolerates heat and low fertility.", "plants field"),
            ("Heading & flowering", "Days 35–60", "Spike-like heads emerge and flower; pollination is sensitive to heavy rain.", "head flowering"),
            ("Grain fill & harvest", "Days 60–100", "Short cycle; harvest when heads are dry and grain is hard.", "harvest heads"),
        ],
        "pests": ["Downy mildew", "Head miner", "Birds", "Striga"],
        "prev": ["Cowpea", "Groundnut"], "next": ["Cowpea", "Groundnut", "Soybean"],
        "tips": ["Use treated, disease-free seed against downy mildew.", "Sow early in the rains for best yields.", "Intercrop with cowpea for stability and soil cover."],
        "nutrients": "Thrives on low fertility; small amounts of phosphorus and compost help.",
    },
    "soybean": {
        "stages": [
            ("Sowing & emergence", "Days 0–10", "Inoculate seed with Bradyrhizobium; sow 3–4 cm deep in warm, moist soil.", "seedling emergence"),
            ("Vegetative growth", "Days 10–45", "Leaves and nodules develop; nitrogen fixation begins.", "vegetative field"),
            ("Flowering & pod set", "Days 45–85", "Moisture stress here lowers pod number. Watch for pod-feeding bugs.", "flowers pods"),
            ("Seed fill & harvest", "Days 85–130", "Pods turn yellow-brown and rattle; harvest before shattering.", "harvest pods"),
        ],
        "pests": ["Soybean rust", "Pod-sucking bugs", "Aphids", "Cyst nematode"],
        "prev": ["Maize", "Sorghum", "Wheat", "Millet"], "next": ["Maize", "Wheat", "Sorghum"],
        "tips": ["Inoculate seed, especially on new land.", "Avoid waterlogged sites.", "Keep weeds out for the first 6 weeks.", "Harvest promptly to limit shattering losses."],
        "nutrients": "Fixes most of its own nitrogen; needs phosphorus, potassium and often sulphur.",
    },
    "cowpea": {
        "stages": [
            ("Sowing & emergence", "Days 0–7", "Fast germination in warm soil; sow 2–4 cm deep.", "seedling"),
            ("Vegetative growth", "Days 7–30", "Spreading or erect growth; leaves can be picked as a vegetable.", "plant field growth"),
            ("Flowering & pod set", "Days 30–50", "Flowers form in clusters; aphids and thrips can be a problem.", "flowers"),
            ("Pod fill & harvest", "Days 50–100", "Green pods can be picked early; dry pods are harvested in several passes.", "pods harvest"),
        ],
        "pests": ["Aphids", "Pod borers (Maruca)", "Thrips", "Bruchid weevils in storage"],
        "prev": ["Maize", "Sorghum", "Millet", "Rice"], "next": ["Maize", "Sorghum", "Millet"],
        "tips": ["A good quick cover crop and nitrogen builder.", "Store dry grain in airtight bags against bruchids.", "Intercrop with cereals to use space efficiently.", "Pick leaves lightly so pod yield is not hurt."],
        "nutrients": "Fixes nitrogen; responds to phosphorus on poor soils.",
    },
    "rice": {
        "stages": [
            ("Nursery / sowing", "Days 0–25", "Seedlings are raised in a nursery or direct-seeded; keep soil saturated.", "seedlings nursery"),
            ("Tillering", "Days 25–60", "Transplanted plants tiller; maintain shallow water or alternate wetting and drying.", "paddy field tillering"),
            ("Panicle & flowering", "Days 60–90", "Water stress now is costly; panicles emerge and flower.", "panicle flowering"),
            ("Grain fill & harvest", "Days 90–150", "Drain fields 1–2 weeks before harvest; harvest when 80–85% of grains are golden.", "harvest"),
        ],
        "pests": ["Rice blast", "Brown planthopper", "Stem borers", "Bacterial leaf blight"],
        "prev": ["Cowpea", "Chickpea", "Legume green manure"], "next": ["Chickpea", "Cowpea", "Wheat"],
        "tips": ["Level the field to use water evenly.", "Alternate wetting and drying can cut water use where local advice supports it.", "Use certified, disease-resistant varieties.", "Rotate with a dryland legume to break pest cycles."],
        "nutrients": "Needs nitrogen, phosphorus and zinc; split nitrogen between tillering and panicle initiation.",
    },
    "groundnut": {
        "stages": [
            ("Sowing & emergence", "Days 0–10", "Sow shelled seed 4–6 cm deep into loose, warm soil.", "seedling"),
            ("Vegetative growth", "Days 10–35", "Bushy growth; nodulation and early weeding are critical.", "plants field"),
            ("Flowering & pegging", "Days 35–70", "Flowers self-pollinate; pegs push into the soil to form pods. Keep soil loose.", "flower peg"),
            ("Pod fill & harvest", "Days 70–140", "Lift when leaves yellow and pods show dark inner shell markings; dry well.", "pods harvest"),
        ],
        "pests": ["Leaf spot", "Aflatoxin (storage mould)", "Aphids", "Termites in dry soils"],
        "prev": ["Maize", "Sorghum", "Millet"], "next": ["Maize", "Sorghum", "Wheat"],
        "tips": ["Gypsum or calcium supports pod filling on low-calcium soils.", "Dry pods quickly to avoid aflatoxin.", "Loose sandy loam helps pegs penetrate.", "Avoid following other legumes to limit disease."],
        "nutrients": "Fixes nitrogen; needs calcium, phosphorus and sometimes sulphur.",
    },
    "chickpea": {
        "stages": [
            ("Sowing & emergence", "Days 0–10", "Sow into moist, cool soil; avoid waterlogging.", "seedling"),
            ("Vegetative growth", "Days 10–50", "Slow early growth; nodulation fixes nitrogen.", "plants field"),
            ("Flowering & podding", "Days 50–85", "Frost and heavy rain at flowering reduce pod set.", "flower pods"),
            ("Pod fill & harvest", "Days 85–120", "Plants turn straw-coloured; harvest when pods rattle.", "harvest"),
        ],
        "pests": ["Ascochyta blight", "Fusarium wilt", "Pod borer (Helicoverpa)"],
        "prev": ["Wheat", "Rice", "Sorghum", "Maize"], "next": ["Wheat", "Rice", "Maize"],
        "tips": ["Choose wilt-resistant varieties.", "Avoid heavy irrigation late in the season.", "Rotate every 3–4 years to reduce disease.", "Use well-drained loams."],
        "nutrients": "Fixes nitrogen; responds to phosphorus and sulphur.",
    },
    "wheat": {
        "stages": [
            ("Sowing & establishment", "Days 0–20", "Sow into a fine, moist seedbed at the recommended cool-season window.", "seedling"),
            ("Tillering", "Days 20–70", "Plants tiller; apply early nitrogen if soil is low.", "tillering field"),
            ("Stem elongation & heading", "Days 70–110", "Rapid growth, boot stage, heads emerge. Rust and moisture stress matter.", "heading ear"),
            ("Grain fill & harvest", "Days 110–150", "Grain fills and dries; harvest at about 13–14% moisture.", "harvest golden field"),
        ],
        "pests": ["Rusts (stripe, leaf, stem)", "Aphids", "Fusarium head blight", "Septoria"],
        "prev": ["Chickpea", "Soybean", "Cowpea", "Potato"], "next": ["Chickpea", "Soybean", "Sunflower"],
        "tips": ["Use rust-resistant, locally adapted varieties.", "Time nitrogen to tillering and stem elongation.", "Include a legume break to cut disease.", "Retain straw or incorporate it to build organic matter."],
        "nutrients": "Needs nitrogen, phosphorus and sulphur; zinc on some soils.",
    },
    "potato": {
        "stages": [
            ("Planting seed tubers", "Days 0–20", "Plant certified seed tubers 8–12 cm deep in loose, cool soil.", "planting seed tubers"),
            ("Vegetative growth", "Days 20–50", "Haulm grows; earth up ridges to protect tubers from light.", "field plants"),
            ("Tuber initiation & bulking", "Days 50–90", "Steady moisture is essential; late blight risk is highest in cool, wet weather.", "flowers tubers"),
            ("Maturity & harvest", "Days 90–120", "Haulm dies back; cure skins before lifting and storing.", "harvest tubers"),
        ],
        "pests": ["Late blight", "Potato beetle / tuber moth", "Bacterial wilt", "Nematodes"],
        "prev": ["Maize", "Wheat", "Legumes"], "next": ["Wheat", "Legumes", "Maize"],
        "tips": ["Never replant on land that grew potato or tomato last season.", "Keep moisture even to avoid cracked or hollow tubers.", "Ridge soil up around plants.", "Use certified seed to cut disease."],
        "nutrients": "Heavy potassium and nitrogen feeder; avoid fresh manure that increases scab.",
    },
    "sunflower": {
        "stages": [
            ("Sowing & emergence", "Days 0–10", "Sow 3–5 cm deep into warm soil; emerges quickly.", "seedling"),
            ("Vegetative growth", "Days 10–55", "Deep taproot builds; plants become drought-tolerant once established.", "field growth"),
            ("Flowering", "Days 55–80", "Heads track the sun and open; bees pollinate. Protect from heavy downpours.", "flowering"),
            ("Seed fill & harvest", "Days 80–125", "Back of the head turns yellow-brown; harvest when seed moisture is low.", "harvest heads"),
        ],
        "pests": ["Head moth / head-boring caterpillars", "Downy mildew", "Sclerotinia head rot", "Birds"],
        "prev": ["Wheat", "Soybean", "Chickpea"], "next": ["Wheat", "Cowpea", "Chickpea"],
        "tips": ["Wait at least 3–4 years between sunflower crops on the same land.", "Plant at moderate density for larger heads.", "Protect ripening heads from birds.", "Leave stalks as ground cover."],
        "nutrients": "Moderate nitrogen needs; boron can be limiting on some soils.",
    },
}

# Whitelisted media lookups: (kind, key) -> Wikimedia Commons search query.
MEDIA_QUERIES: dict[tuple[str, str], str] = {
    ("soil", "sand"): "sandy soil texture", ("soil", "loamy-sand"): "sandy soil field",
    ("soil", "sandy-loam"): "sandy loam soil", ("soil", "loam"): "loam soil profile",
    ("soil", "silt-loam"): "silt loam soil", ("soil", "silt"): "silt soil",
    ("soil", "sandy-clay-loam"): "sandy clay loam soil", ("soil", "clay-loam"): "clay loam soil",
    ("soil", "silty-clay-loam"): "silty clay loam soil", ("soil", "sandy-clay"): "sandy clay soil",
    ("soil", "silty-clay"): "silty clay soil", ("soil", "clay"): "clay soil field",
    ("soil", "peat"): "peat soil", ("soil", "acidic"): "acid soil liming agriculture",
    ("soil", "organic"): "compost organic matter soil",
    ("weather", "heavy-rain"): "heavy rain over farmland", ("weather", "light-rain"): "rain on crops field",
    ("weather", "dry"): "dry cracked soil drought field", ("weather", "heat"): "heat wave hot sun farmland",
    ("weather", "cool"): "cool morning mist farmland", ("weather", "humid"): "humid tropical farmland clouds",
    ("weather", "sunny"): "sunny day wheat field", ("weather", "cloudy"): "cloudy sky farmland",
    ("manage", "drainage"): "agricultural drainage ditch field", ("manage", "irrigation"): "drip irrigation field",
    ("manage", "mulch"): "mulch vegetable garden", ("manage", "lime"): "agricultural lime spreading",
    ("manage", "compost"): "compost heap farm", ("manage", "cover-crop"): "cover crop field",
    ("manage", "residue"): "crop residue no-till", ("manage", "scouting"): "farmer inspecting crops field",
    ("manage", "heat"): "mulched crop rows shade", ("manage", "texture"): "raised bed farming",
    ("season", "sowing"): "sowing seeds farm field", ("season", "growing"): "green crop field growing",
    ("season", "flowering"): "crop field flowering", ("season", "harvest"): "harvest crops field",
    ("season", "fallow"): "fallow field cover crop",
}


def shift_months(months: list[int], lat: float) -> list[int]:
    return [((m - 1 + 6) % 12) + 1 for m in months] if lat < 0 else list(months)


def sow_window(crop_id: str, lat: float) -> dict[str, Any]:
    zone = "temperate" if abs(lat) >= 23.5 else "tropics"
    sow, harvest = SOW.get(crop_id, {"temperate": ([5], [9]), "tropics": ([6], [10])})[zone]
    note = (
        "Main rainy-season window for the tropics; check your local rainfall calendar."
        if zone == "tropics"
        else "Typical window for your latitude; adjust for local frost dates and variety."
    )
    return {"sow_months": shift_months(sow, lat), "harvest_months": shift_months(harvest, lat), "zone": zone, "note": note}


def maturity_days(crop_id: str) -> int:
    lo, hi = MATURITY_DAYS.get(crop_id, (100, 120))
    return (lo + hi) // 2


def month_list(months: list[int]) -> str:
    return " – ".join([MONTH_NAMES[months[0] - 1], MONTH_NAMES[months[-1] - 1]]) if len(months) > 1 else MONTH_NAMES[months[0] - 1]


def crop_extra(crop_id: str, lat: float = 0.0) -> dict[str, Any]:
    data = CONTENT.get(crop_id, {})
    lo, hi = MATURITY_DAYS.get(crop_id, (100, 120))
    return {
        "days_to_maturity": [lo, hi],
        "window": sow_window(crop_id, lat),
        "stages": [{"name": n, "when": w, "text": t, "term": q} for n, w, t, q in data.get("stages", [])],
        "pests": data.get("pests", []),
        "good_previous": data.get("prev", []),
        "good_next": data.get("next", []),
        "tips": data.get("tips", []),
        "nutrients": data.get("nutrients", ""),
        "guidance_note": "General guidance compiled from public extension-style sources; varieties, local pests and planting dates differ. Confirm with your local agricultural office.",
    }


# Land-management templates: key -> (why, steps, when, benefit)
MANAGE: dict[str, dict[str, Any]] = {
    "drainage": {"why": "Standing water starves roots of oxygen and invites root diseases.", "steps": ["Walk the field after rain and mark wet spots.", "Open furrows or small drains along the low side.", "Delay sowing or choose a waterlogging-tolerant crop on persistent wet patches."], "when": "Within 1–3 days of heavy rain", "benefit": "Healthier roots and fewer disease losses"},
    "irrigation": {"why": "Gridded moisture is regional; a hand check tells you what plants actually feel.", "steps": ["Dig 15 cm in a few spots and squeeze a handful of soil.", "If it crumbles and will not hold a ball, irrigate.", "Water in short, targeted cycles, early morning."], "when": "Before the next irrigation", "benefit": "Saves water and avoids stress"},
    "heat": {"why": "High temperatures speed up evaporation and stress flowering crops.", "steps": ["Irrigate early morning or evening.", "Mulch the soil surface with straw or crop residue.", "Avoid heavy fertiliser during extreme heat."], "when": "During hot spells", "benefit": "Less evaporation and heat damage"},
    "lime": {"why": "Acid soil locks up phosphorus and reduces root growth.", "steps": ["Take a local soil test to confirm pH.", "Apply agricultural lime at the rate the test recommends.", "Mix into the topsoil and re-test after a season."], "when": "2–3 months before sowing", "benefit": "Better nutrient availability and yields"},
    "alkaline": {"why": "High pH can lock up iron, zinc and phosphorus.", "steps": ["Add compost or well-rotted manure.", "Favour tolerant crops such as sorghum or chickpea.", "Test locally before correcting with sulphur."], "when": "Before the next planting", "benefit": "Fewer nutrient deficiencies"},
    "compost": {"why": "Organic carbon feeds soil life, holds water and stores nutrients.", "steps": ["Spread 5–10 t/ha of compost or manure.", "Leave crop residue on the surface rather than burning it.", "Add a cover crop between main seasons."], "when": "Before ploughing or in the off-season", "benefit": "Steadily better soil structure and water holding"},
    "texture-clay": {"why": "Heavy soil is easy to compact and slow to drain.", "steps": ["Avoid working soil when it is wet.", "Use raised beds or drainage lines for sensitive crops.", "Add organic matter to open the structure."], "when": "At land preparation", "benefit": "Better drainage and root growth"},
    "texture-sand": {"why": "Light soil drains fast and holds few nutrients.", "steps": ["Apply fertiliser in small split doses.", "Keep the surface mulched.", "Add compost to raise water-holding capacity."], "when": "Throughout the season", "benefit": "Less leaching and more even growth"},
    "cover-crop": {"why": "Bare soil loses water and topsoil to sun, wind and rain.", "steps": ["Leave residue on the surface after harvest.", "Sow a fast cover such as cowpea or a grass mix in the gap between seasons.", "Terminate it before it sets seed."], "when": "Between seasons", "benefit": "Protects soil and adds organic matter"},
    "scouting": {"why": "Catching pests early keeps treatment cheap and targeted.", "steps": ["Walk a zig-zag path weekly and check 10 plants per stop.", "Note leaf damage, insects and disease spots.", "Ask your extension office before spraying."], "when": "Weekly", "benefit": "Lower pest losses and chemical use"},
    "rotation": {"why": "Repeating the same crop family builds up pests and disease.", "steps": ["Follow the rotation plan on the Rotation tab.", "Record what you grow each season.", "Keep at least one legume in every 3–4 seasons."], "when": "At each planting decision", "benefit": "Lower disease risk and better nitrogen"},
}


# v0.7: merge the 16 added crops (kept in a separate module so the original tables stay untouched)
from . import content_more as _more  # noqa: E402

SOW.update(_more.SOW)
MATURITY_DAYS.update(_more.MATURITY_DAYS)
CONTENT.update(_more.CONTENT)
