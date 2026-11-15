# AI-assisted: written with an AI coding assistant. General guidance, NOT verified against a source; the UI labels it "general guidance".
"""Content for the 16 crops added in v0.7: sowing windows, maturity, stages, pests, tips.
Windows are general (northern-hemisphere months; the loader shifts them for the southern hemisphere) and vary by variety and region."""
from __future__ import annotations

SOW = {
    "barley": {"temperate": ([3, 4], [7, 8]), "tropics": ([11, 12], [3, 4])},
    "cassava": {"temperate": ([5, 6], [11, 12]), "tropics": ([4, 5], [1, 2])},
    "sweet_potato": {"temperate": ([5, 6], [9, 10]), "tropics": ([5, 6], [9, 10])},
    "lentil": {"temperate": ([3, 4], [7, 8]), "tropics": ([10, 11], [2, 3])},
    "pigeonpea": {"temperate": ([5, 6], [11, 12]), "tropics": ([6, 7], [12, 1])},
    "mungbean": {"temperate": ([5, 6], [8, 9]), "tropics": ([6, 7], [9, 10])},
    "mustard": {"temperate": ([9, 10], [6, 7]), "tropics": ([10, 11], [2, 3])},
    "sesame": {"temperate": ([5, 6], [9, 10]), "tropics": ([6, 7], [9, 10])},
    "tomato": {"temperate": ([4, 5], [7, 8]), "tropics": ([10, 11], [1, 2])},
    "onion": {"temperate": ([3, 4], [8, 9]), "tropics": ([10, 11], [2, 3])},
    "okra": {"temperate": ([5, 6], [8, 9]), "tropics": ([6, 7], [9, 10])},
    "chili": {"temperate": ([4, 5], [8, 9]), "tropics": ([6, 7], [10, 11])},
    "watermelon": {"temperate": ([4, 5], [7, 8]), "tropics": ([11, 12], [2, 3])},
    "cotton": {"temperate": ([4, 5], [9, 10]), "tropics": ([6, 7], [11, 12])},
    "sugarcane": {"temperate": ([3, 4], [1, 2]), "tropics": ([2, 3], [1, 2])},
    "banana": {"temperate": ([4, 5], [2, 3]), "tropics": ([5, 6], [4, 5])},
}

MATURITY_DAYS = {
    "barley": (90, 130), "cassava": (240, 365), "sweet_potato": (90, 150), "lentil": (90, 120), "pigeonpea": (120, 200), "mungbean": (60, 90),
    "mustard": (90, 140), "sesame": (80, 120), "tomato": (90, 140), "onion": (110, 170), "okra": (50, 100), "chili": (90, 150),
    "watermelon": (75, 110), "cotton": (150, 200), "sugarcane": (300, 540), "banana": (270, 420),
}

def _s(a, b, c, d):  # four stages: name, timing, text, image term
    return [("Establishment", a[0], a[1], "seedling"), ("Vegetative growth", b[0], b[1], "plant growth"), ("Flowering & fruit/seed set", c[0], c[1], "flowering"), ("Maturity & harvest", d[0], d[1], "harvest")]

CONTENT = {
    "barley": {"stages": _s(("Days 0–15", "Sow into a firm seedbed; emerges quickly in cool soil."), ("Days 15–55", "Tillering; weed control and nitrogen matter most now."), ("Days 55–85", "Heading and flowering; drought here reduces grain number."), ("Days 85–130", "Grain fills and dries; harvest when grain is hard.")),
        "pests": ["Aphids", "Powdery mildew", "Net blotch", "Rusts"], "prev": ["Lentil", "Chickpea", "Mustard"], "next": ["Lentil", "Chickpea", "Soybean"],
        "tips": ["Choose early varieties where terminal drought is likely.", "Avoid very acid soils; barley is less tolerant than wheat.", "Rotate with a pulse or oilseed to break disease cycles."], "nutrients": "Moderate nitrogen; too much nitrogen can reduce malting quality and cause lodging."},
    "cassava": {"stages": _s(("Months 0–1", "Plant healthy stem cuttings; keep weeds down while sprouts establish."), ("Months 1–4", "Rapid canopy growth; early weeding pays off."), ("Months 4–8", "Roots bulk up; drought slows but rarely kills the crop."), ("Months 8–12+", "Harvest roots when needed; quality falls if left too long.")),
        "pests": ["Cassava mosaic disease", "Cassava brown streak disease", "Mealybugs", "Green mites"], "prev": ["Cowpea", "Groundnut", "Pigeon pea"], "next": ["Cowpea", "Groundnut", "Maize"],
        "tips": ["Use disease-free cuttings from healthy plants.", "Roots deteriorate within days after harvest; plan processing before you harvest.", "Needs a long, frost-free season."], "nutrients": "Takes a lot of potassium from the soil over a long cycle; return residues or add manure."},
    "sweet_potato": {"stages": _s(("Days 0–20", "Plant vine cuttings on ridges; water to establish."), ("Days 20–50", "Vines spread and cover the ground."), ("Days 50–110", "Storage roots swell; steady moisture gives even roots."), ("Days 110–150", "Harvest before cold or heavy rain; cure roots for storage.")),
        "pests": ["Sweet potato weevil", "Virus complex", "Vine borers"], "prev": ["Maize", "Cowpea"], "next": ["Cowpea", "Groundnut", "Sorghum"],
        "tips": ["Plant on ridges for drainage and easier harvest.", "Use clean vine tips rather than old vines.", "Too much nitrogen gives vines but few roots."], "nutrients": "Responds to potassium; avoid heavy nitrogen."},
    "lentil": {"stages": _s(("Days 0–15", "Sow shallowly into moist, well-drained soil."), ("Days 15–60", "Slow early growth; keep weeds out."), ("Days 60–100", "Flowering and pod set; avoid waterlogging and late heavy irrigation."), ("Days 100–120", "Harvest when lower pods turn brown to limit shatter losses.")),
        "pests": ["Aphids", "Ascochyta blight", "Fusarium wilt", "Pod borers"], "prev": ["Wheat", "Barley", "Maize"], "next": ["Wheat", "Barley", "Mustard"],
        "tips": ["Avoid fields with a recent lentil or pea history to reduce disease.", "Seed treatment helps against seed-borne disease.", "Inoculate seed with rhizobia if the field is new to lentil."], "nutrients": "Fixes most of its own nitrogen; may need phosphorus."},
    "pigeonpea": {"stages": _s(("Days 0–20", "Sow at wide spacing; early growth is slow."), ("Days 20–90", "Deep roots and branches develop; good for intercropping."), ("Days 90–150", "Flowering and podding; pod borers peak."), ("Days 150–200", "Harvest when most pods are dry; may be picked in two rounds.")),
        "pests": ["Pod borers (Helicoverpa)", "Pod fly", "Fusarium wilt", "Sterility mosaic disease"], "prev": ["Sorghum", "Millet", "Maize"], "next": ["Sorghum", "Millet", "Maize"],
        "tips": ["Intercrop with sorghum, millet or maize to use space during slow early growth.", "Choose a variety whose duration fits your season length.", "Scout for pod borers at flowering."], "nutrients": "Fixes nitrogen; responds to phosphorus on poor soils."},
    "mungbean": {"stages": _s(("Days 0–7", "Sow into warm, moist soil."), ("Days 7–30", "Fast leaf growth; weeding is critical."), ("Days 30–50", "Flowering and pod set; heat and drought hurt pod fill."), ("Days 50–75", "Pods ripen unevenly; pick in rounds or harvest when most are dark.")),
        "pests": ["Whitefly (yellow mosaic virus)", "Aphids", "Pod borers", "Powdery mildew"], "prev": ["Maize", "Rice", "Wheat"], "next": ["Wheat", "Maize", "Sorghum"],
        "tips": ["Fits a short gap between two main crops.", "Avoid waterlogged soil.", "Yellow mosaic virus spreads by whitefly; control early."], "nutrients": "Fixes nitrogen; light phosphorus helps."},
    "mustard": {"stages": _s(("Days 0–15", "Sow shallow in a fine seedbed."), ("Days 15–50", "Rosette and stem growth; thin if crowded."), ("Days 50–85", "Yellow flowering; the water-sensitive stage."), ("Days 85–140", "Pods turn yellow-brown; harvest before shattering.")),
        "pests": ["Aphids", "Flea beetles", "Alternaria blight", "White rust"], "prev": ["Rice", "Maize", "Pulses"], "next": ["Wheat", "Barley", "Pulses"],
        "tips": ["Sulphur supports oil content on sulphur-poor soils.", "Avoid sowing too late; aphids and heat reduce yield.", "Harvest on time; ripe pods shatter."], "nutrients": "Needs nitrogen and sulphur."},
    "sesame": {"stages": _s(("Days 0–10", "Tiny seed; sow shallow into warm, fine soil."), ("Days 10–35", "Thin to a good stand and control weeds."), ("Days 35–70", "Flowering for several weeks; avoid waterlogging."), ("Days 70–110", "Capsules ripen from the bottom; cut and dry before they split.")),
        "pests": ["Leaf webber and capsule borer", "Phyllody disease", "Leaf spots"], "prev": ["Sorghum", "Millet", "Maize"], "next": ["Cowpea", "Groundnut", "Sorghum"],
        "tips": ["Needs a dry spell at harvest; rain at ripening causes losses.", "Very sensitive to waterlogging.", "Do not follow sesame with sesame."], "nutrients": "Modest nitrogen; responds to phosphorus on poor soils."},
    "tomato": {"stages": _s(("Weeks 0–5", "Raise seedlings, then transplant."), ("Weeks 5–9", "Vines grow; stake and prune where needed."), ("Weeks 9–14", "Flowering and fruit set; steady water avoids blossom-end rot and cracking."), ("Weeks 12–20", "Pick as fruit colours; harvest runs for weeks.")),
        "pests": ["Late blight and early blight", "Whitefly and leaf-curl virus", "Fruit borers", "Bacterial wilt"], "prev": ["Maize", "Cowpea", "Onion"], "next": ["Maize", "Cowpea", "Soybean"],
        "tips": ["Do not follow tomato, potato, chili or eggplant in the same field.", "Drip irrigation and mulch cut disease and water use.", "Scout weekly; disease can run through a field in days in wet weather."], "nutrients": "Heavy feeder; needs balanced nitrogen, phosphorus, potassium and calcium."},
    "onion": {"stages": _s(("Weeks 0–6", "Nursery or direct sowing; seedlings are weak competitors."), ("Weeks 6–14", "Leaf growth sets bulb size; keep weeds out."), ("Weeks 14–18", "Bulbing triggered by day length; stop nitrogen."), ("Weeks 18–24", "Tops fall over; lift, cure and store dry.")),
        "pests": ["Thrips", "Purple blotch", "Downy mildew", "Onion fly"], "prev": ["Maize", "Cowpea"], "next": ["Maize", "Cowpea", "Groundnut"],
        "tips": ["Choose a variety suited to your day length.", "Shallow roots need frequent, light irrigation.", "Cure bulbs well before storage."], "nutrients": "Needs nitrogen early and sulphur; avoid late nitrogen."},
    "okra": {"stages": _s(("Days 0–10", "Soak seed; sow into warm soil."), ("Days 10–40", "Leaf and stem growth."), ("Days 40–55", "Flowering begins; first pods soon after."), ("Days 55–100", "Pick pods every 1–2 days while young.")),
        "pests": ["Fruit and shoot borer", "Whitefly (yellow vein mosaic)", "Jassids", "Powdery mildew"], "prev": ["Maize", "Cowpea"], "next": ["Cowpea", "Maize"],
        "tips": ["Pick often; overripe pods stop new ones forming.", "Avoid heavy soils that crust after rain.", "Rotate away from cotton and other mallows."], "nutrients": "Moderate nitrogen; responds to compost."},
    "chili": {"stages": _s(("Weeks 0–6", "Raise seedlings; transplant when strong."), ("Weeks 6–10", "Branching and leaf growth."), ("Weeks 10–16", "Flowering and fruit set; heat above about 35 °C drops flowers."), ("Weeks 14–24", "Pick green or ripe; repeated harvests.")),
        "pests": ["Thrips and mites", "Leaf-curl virus", "Anthracnose", "Bacterial wilt"], "prev": ["Maize", "Cowpea"], "next": ["Maize", "Cowpea", "Groundnut"],
        "tips": ["Avoid following potato, tomato or eggplant.", "Mulch to hold moisture and cut weeds.", "Control thrips and mites early; they spread viruses."], "nutrients": "Balanced nitrogen, phosphorus, potassium; calcium helps fruit quality."},
    "watermelon": {"stages": _s(("Days 0–15", "Sow into warm, light soil."), ("Days 15–40", "Vines run; keep weeds down."), ("Days 40–65", "Flowering and fruit set; needs bees for pollination."), ("Days 65–100", "Harvest when the tendril near the fruit dries and the underside turns yellow.")),
        "pests": ["Aphids", "Fruit flies", "Fusarium wilt", "Powdery and downy mildew"], "prev": ["Maize", "Cowpea"], "next": ["Maize", "Cowpea", "Groundnut"],
        "tips": ["Reduce water near ripening to improve sweetness.", "Do not grow after other cucurbits.", "Protect bees; avoid spraying at flowering."], "nutrients": "Moderate nitrogen early; potassium helps fruit quality."},
    "cotton": {"stages": _s(("Days 0–30", "Sow into warm soil (above about 15 °C)."), ("Days 30–80", "Squares (flower buds) form; manage pests and weeds."), ("Days 80–140", "Flowering and boll set; the water-critical window."), ("Days 140–200", "Bolls open; pick in dry weather.")),
        "pests": ["Bollworms", "Whitefly", "Aphids", "Pink bollworm"], "prev": ["Cowpea", "Sorghum", "Groundnut"], "next": ["Cowpea", "Sorghum", "Wheat"],
        "tips": ["Scouting and local pest advice matter more than any single input.", "Avoid heavy nitrogen late in the season.", "Rotate with cereals or legumes to reduce pest and disease carryover."], "nutrients": "Moderate to high nitrogen and potassium; sensitive to boron deficiency."},
    "sugarcane": {"stages": _s(("Months 0–2", "Plant setts (stem pieces); keep moist."), ("Months 2–6", "Tillering."), ("Months 6–10", "Grand growth; peak water demand."), ("Months 10–14+", "Ripening; withhold water, then harvest. Ratoon crops regrow from stubble.")),
        "pests": ["Stem borers", "Red rot", "Smut", "Termites"], "prev": ["Cowpea", "Soybean"], "next": ["Soybean", "Cowpea", "Groundnut"],
        "tips": ["Needs a nearby mill; cane loses sugar within days of cutting.", "Ratoon crops yield less each year.", "Water demand is high; check irrigation supply before planting."], "nutrients": "Heavy nitrogen and potassium feeder."},
    "banana": {"stages": _s(("Months 0–3", "Plant suckers or tissue-culture plants; protect from wind."), ("Months 3–8", "Leaf production; water and mulch."), ("Months 8–11", "Flower emergence and bunch formation."), ("Months 11–14", "Harvest bunches when fruits are full; suckers continue the cycle.")),
        "pests": ["Black sigatoka", "Panama disease (Fusarium TR4 in some regions)", "Banana weevil", "Nematodes"], "prev": ["Cowpea", "Pigeon pea"], "next": ["Cowpea", "Maize"],
        "tips": ["Use clean planting material; soil-borne disease persists for years.", "Windbreaks and propping reduce lodging.", "A perennial: plan for multi-year cropping, not one season."], "nutrients": "Very high potassium demand; also nitrogen and magnesium."},
}
