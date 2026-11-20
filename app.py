import csv, difflib, hashlib, itertools, json, math, os, re, threading, time, urllib.request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Mama Tolu Menu Consultant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

AV = {"High": 3, "Medium": 2, "Low": 1}
DF = {"Easy": 1, "Medium": 2, "Hard": 3}
NUM = ["protein_g", "fat_g", "cost_per_portion_ngn", "chewiness_score", "umami_score",
       "prep_time_mins", "familiarity_score", "co2_kg_per_portion"]
SENS = ["protein_g", "fat_g", "chewiness_score", "umami_score"]
W = [0.8, 0.5, 1.4, 1.2]  # texture + umami decide whether it "feels like meat"

rows = []
with open("ingredients.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        for k in NUM:
            r[k] = float(r[k])
        r["av"], r["df"] = AV[r["availability_abuja"]], DF[r["cooking_difficulty"]]
        r["allergen_list"] = [a for a in r.get("allergens", "none").split("/") if a and a != "none"]
        rows.append(r)

# Pure Python (no numpy/sklearn): scaling + a tiny deterministic k-means over 26 rows.
MEAN = [sum(r[k] for r in rows) / len(rows) for k in SENS]
STD = [math.sqrt(sum((r[k] - m) ** 2 for r in rows) / len(rows)) or 1 for k, m in zip(SENS, MEAN)]


def z(o):
    return [(o[k] - m) / s for k, m, s in zip(SENS, MEAN, STD)]


def kmeans(pts, k=3, iters=50):
    cents = [pts[0]]
    while len(cents) < k:  # farthest-point init, no randomness
        cents.append(max(pts, key=lambda p: min(sum((a - b) ** 2 for a, b in zip(p, c)) for c in cents)))
    for _ in range(iters):
        lab = [min(range(k), key=lambda i: sum((a - b) ** 2 for a, b in zip(p, cents[i]))) for p in pts]
        new = []
        for i in range(k):
            mem = [p for p, l in zip(pts, lab) if l == i]
            new.append([sum(c) / len(mem) for c in zip(*mem)] if mem else cents[i])
        if new == cents:
            break
        cents = new
    return lab


for r, c in zip(rows, kmeans([z(r) for r in rows])):
    r["cluster"] = c

PROTEINS = {  # the meat being replaced: per-plate profile + estimated cost and CO2e
    "beef": dict(protein_g=26, fat_g=15, chewiness_score=8.5, umami_score=9.0, cost=1000, co2=5.0),
    "goat": dict(protein_g=25, fat_g=12, chewiness_score=9.0, umami_score=9.0, cost=1100, co2=4.0),
    "chicken": dict(protein_g=24, fat_g=8, chewiness_score=7.0, umami_score=8.0, cost=1000, co2=1.8),
    "turkey": dict(protein_g=24, fat_g=10, chewiness_score=7.5, umami_score=8.0, cost=1100, co2=2.0),
    "fish": dict(protein_g=22, fat_g=6, chewiness_score=5.0, umami_score=8.0, cost=900, co2=2.5),
    # extra animal proteins people actually cook with. Rough estimates: replace cost with your own price.
    "ponmo": dict(protein_g=26, fat_g=2, chewiness_score=9.5, umami_score=4.0, cost=500, co2=3.0),
    "shaki": dict(protein_g=14, fat_g=4, chewiness_score=8.5, umami_score=6.0, cost=600, co2=3.5),
    "liver": dict(protein_g=26, fat_g=5, chewiness_score=5.0, umami_score=8.0, cost=900, co2=4.0),
    "gizzard": dict(protein_g=30, fat_g=3, chewiness_score=8.0, umami_score=7.0, cost=800, co2=1.8),
    "stockfish": dict(protein_g=25, fat_g=1, chewiness_score=8.0, umami_score=9.5, cost=1200, co2=2.5),
    "prawns": dict(protein_g=24, fat_g=1, chewiness_score=6.0, umami_score=8.5, cost=1500, co2=3.5),
    "snail": dict(protein_g=16, fat_g=1.5, chewiness_score=8.0, umami_score=5.0, cost=1200, co2=1.5),
    "egg": dict(protein_g=13, fat_g=10, chewiness_score=3.0, umami_score=6.0, cost=500, co2=0.6)}
PKW = {"ponmo": ["ponmo", "kpomo", "pomo", "cow skin", "cowskin"], "shaki": ["shaki", "tripe"],
       "liver": ["liver"], "gizzard": ["gizzard"], "stockfish": ["stockfish", "panla"],
       "prawns": ["prawn", "prawns", "shrimp", "shrimps"], "snail": ["snail", "snails"],
       "egg": ["egg", "eggs", "omelette", "omelet"],
       "goat": ["goat", "asun", "mutton"], "chicken": ["chicken", "wings", "poultry", "drumstick"],
       "turkey": ["turkey"], "fish": ["fish", "catfish", "tilapia", "titus", "mackerel"],
       "beef": ["beef", "cow", "steak", "minced meat"]}
DEFAULT_PROTEIN = {"egg": "egg", "grill": "beef", "wrap": "beef", "soup": "chicken", "stew": "beef", "fried": "chicken", "rice": "chicken"}
DEFAULT_STYLE = {"beef": "grill", "goat": "soup", "chicken": "stew", "turkey": "fried", "fish": "soup",
                 "ponmo": "stew", "shaki": "soup", "liver": "fried", "gizzard": "grill", "stockfish": "soup",
                 "prawns": "stew", "snail": "grill", "egg": "egg"}
STYLES = {  # order matters: first keyword match wins
    "wrap": dict(label="Shawarma", prep=20, wet=False, kw=["shawarma", "wrap", "burger", "sandwich"],
                 adj=dict(protein_g=-4, fat_g=-1, chewiness_score=-.5, umami_score=-1, cost=-50),
                 kit="smoked paprika and garlic seasoning, sear hot, then a garlic-pepper cream sauce (plant mayo or yoghurt) with cabbage and cucumber"),
    "rice": dict(label="Rice Topper", prep=25, wet=False, kw=["jollof", "rice"], adj=dict(protein_g=-2, chewiness_score=-.5),
                 kit="curry, thyme, smoked paprika and a little tomato paste, seared hard, then laid on the rice so it keeps its bite"),
    "soup": dict(label="Pepper Soup", prep=25, wet=True, kw=["soup", "broth", "egusi", "ogbono", "okra"], adj={},
                 kit="pepper-soup spice (ehuru, uda, uziza), scent leaf, ginger and garlic, simmered hard so the broth carries the flavour"),
    "stew": dict(label="Stew", prep=30, wet=True, kw=["stew", "ofada", "obe ata", "sauce", "curry"],
                 adj=dict(fat_g=2, chewiness_score=-.5, umami_score=.5),
                 kit="a tomato-tatashe-rodo base fried down until the oil rises, thyme, curry, bay leaf and a little iru or stock cube for depth"),
    "grill": dict(label="Suya", prep=20, wet=False, kw=["suya", "skewer", "kebab", "grill", "asun", "barbecue", "bbq", "roast"], adj={},
                  kit="yaji (ground kuli-kuli, ginger, cayenne, onion powder, smoked paprika), a thin coat of groundnut oil, raw onion and tomato on the side"),
    "egg": dict(label="Scramble", prep=15, wet=False, kw=["egg", "omelette", "omelet", "scramble", "egg sauce"], adj={},
                kit="turmeric, onion, tatashe and pepper, fried in a little oil and stirred gently, with a crushed pinch of iru for the savoury note"),
    "fried": dict(label="Crispy Bites", prep=25, wet=False, kw=["fried", "fry", "nugget", "crispy"], adj=dict(fat_g=5, chewiness_score=.5),
                  kit="a seasoned flour or breadcrumb coat (thyme, curry, garlic, pepper), shallow-fried until deep golden")}


STYLES["egg"] = STYLES.pop("egg")  # make sure it is checked last


def get_dish(c):
    d, st = dict(PROTEINS[c["protein"]]), STYLES[c["style"]]
    for k, v in st["adj"].items():
        d[k] += v
    nm = "Goat Asun" if (c["protein"], c["style"]) == ("goat", "grill") else f"{c['protein'].title()} {st['label']}"
    kit = "ata rodo and scotch bonnet, onions, thyme and a hard char so it smells smoky" if nm == "Goat Asun" else st["kit"]
    if "peanut" in c.get("avoid", []):
        kit = kit.replace("yaji (ground kuli-kuli,", "peanut-free yaji (ground egusi instead of kuli-kuli,").replace("groundnut oil", "vegetable oil")
    return dict(d, name=(c.get("label") or nm).title(), short=st["label"], prep=st["prep"], wet=st["wet"], kit=kit)


GOALS = {  # weights: texture, cost saving, familiarity, speed, protein
    "balanced": (.40, .25, .15, .10, .10), "cost": (.30, .40, .10, .10, .10),
    "taste": (.55, .10, .15, .10, .10), "protein": (.30, .15, .10, .05, .40)}


class Chat(BaseModel):
    message: str
    history: list[dict] = []
    state: dict = {}


# ---------- 1. understand the request ----------
ALIASES = {"garden egg": "aubergine", "eggplant": "aubergine", "cow leg": "ponmo", "towel tripe": "shaki",
           "sharwama": "shawarma", "shwarma": "shawarma", "shawama": "shawarma", "sharwarma": "shawarma",
           "shawerma": "shawarma", "shaorma": "shawarma", "swarma": "shawarma", "gyro": "wrap",
           "pepper soup": "soup", "peppersoup": "soup", "efo": "stew", "ayamase": "stew", "designer stew": "stew",
           "jollof": "jollof", "fried rice": "rice", "asun": "asun", "balangu": "suya", "tsire": "suya"}
VOCAB = sorted({w for v in STYLES.values() for w in v["kw"]} | {w for ws in PKW.values() for w in ws})


def fix_spelling(t):
    """Fix typos word by word: known aliases first, then closest keyword (so 'sharwama', 'chiken', 'stwe' still work)."""
    for bad, good in ALIASES.items():
        t = t.replace(bad, good)
    out = []
    for w in re.findall(r"[a-z']+|[^a-z']+", t):
        if w.isalpha() and len(w) >= 4 and w not in VOCAB:
            m = [v for v in difflib.get_close_matches(w, VOCAB, n=3, cutoff=0.74) if v[0] == w[0]]
            w = m[0] if m else w
        out.append(w)
    return "".join(out)


ALLERGENS = {  # allergen tag in the CSV: words a customer might use
    "soy": ["soy", "soya", "soybean"], "gluten": ["gluten", "wheat", "celiac", "coeliac"],
    "peanut": ["peanut", "peanuts", "groundnut", "groundnuts"], "sesame": ["sesame", "beniseed"],
    "tree nut": ["tree nut", "tree nuts", "cashew", "walnut"]}


def _tags_of(x):
    if x in ("nut", "nuts"):
        return {"peanut", "tree nut"}  # 'nut allergy' is ambiguous: avoid both to be safe
    return {tag for tag, ws in ALLERGENS.items() if x in ws}


def detect_avoid(t):
    """'peanut allergy', 'no soy', 'gluten free', 'allergic to soy, wheat and nuts' -> allergen tags to exclude."""
    toks = re.findall(r"[a-z]+|[,&/]", t)
    TRIG = {"allergic", "allergy", "allergies", "allergen", "allergens", "intolerant", "intolerance",
            "avoid", "avoiding", "without", "no"}
    FILL = {"to", "of", "any", "all", "the", "with", "i", "am", "have", "a", "an", "my", "customer", "is", "has", "are"}
    CONN = {"and", "or", "&", ",", "/", "plus", "also"}
    TAIL = {"allergy", "allergies", "allergic", "free", "intolerant", "intolerance"}
    found = set()
    for i, w in enumerate(toks):
        if w in TRIG:  # trigger word, then a list of allergens: 'allergic to soy, wheat and nuts'
            j, skipped, got = i + 1, 0, False
            while j < len(toks) and toks[j] in FILL and skipped < 3:
                j += 1; skipped += 1
            while j < len(toks):
                tg = _tags_of(toks[j])
                if tg:
                    found |= tg; got = True
                elif not (toks[j] in CONN and got):
                    break
                j += 1
        if w in TAIL:  # allergen list, then the word: 'soy and wheat free', 'peanut allergy'
            j = i - 1
            while j >= 0:
                tg = _tags_of(toks[j])
                if tg:
                    found |= tg
                elif toks[j] not in CONN:
                    break
                j -= 1
    return found


def mentions_dish(t):
    return any(w in t for ws in PKW.values() for w in ws) or any(w in t for v in STYLES.values() for w in v["kw"])


def regex_parse(text, prev):
    t, c = fix_spelling(text.lower()), dict(prev)
    c.pop("label", None); c["assumed"] = ""
    av_new = detect_avoid(t)
    if av_new:
        c["avoid"] = sorted(set(prev.get("avoid", [])) | av_new)
    if re.search(r"(no|remove|clear|ignore)\s+(more\s+)?(allerg\w*|restrictions?)", t) and not av_new:
        c["avoid"] = []
    pm = next((p for p, ws in PKW.items() if any(w in t for w in ws)), None)
    sm = next((k for k, v in STYLES.items() if any(w in t for w in v["kw"])), None)
    if sm == "stew" and "egg" in t and "stew" not in t:
        sm = "egg"  # 'egg sauce' is a scramble-type dish, not a stew
    if sm: c["style"] = sm
    if pm:
        c["protein"], c["protein_explicit"] = pm, True  # remember a meat the customer actually named
    elif sm and sm != prev.get("style") and not (prev.get("protein_explicit") and prev.get("protein")):
        c["protein"] = DEFAULT_PROTEIN[sm]
        c["assumed"] = f"I assumed {c['protein']} for this {STYLES[sm]['label'].lower()}. Tell me if it's a different meat."
    for m in re.finditer(r"₦?\s?(\d[\d,]{2,5})(?!\d)(\s*(?:plates|portions|servings|covers|a week|per week))?", t):
        v = int(m.group(1).replace(",", ""))
        if m.group(2):
            c["plates"] = v
        elif 150 <= v <= 20000:
            c["budget"] = v
    if any(w in t for w in ["easy", "quick", "fast", "simple", "busy", "rush"]):
        c["df"] = 1
    if any(w in t for w in ["abuja market", "easy to find", "wuse", "kubwa", "readily", "everywhere"]):
        c["av"] = 3
    if any(w in t for w in ["cheaper", "cheapest", "cheap", "save", "profit", "affordable"]):
        c["goal"] = "cost"
    if any(w in t for w in ["protein", "gym", "muscle"]):
        c["goal"] = "protein"
    if any(w in t for w in ["authentic", "meaty", "just like", "taste", "texture", "chewy", "smoky"]):
        c["goal"] = "taste"
    if "cheaper" in t and not re.search(r"\d{3}", t) and "budget" in prev:
        c["budget"] = max(150, int(prev["budget"] * 0.85 // 50 * 50))
    if "easier" in t:
        c["df"] = 1
    return c


def gemini(system, messages, max_tokens):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    body = json.dumps({"system_instruction": {"parts": [{"text": system}]},
                       "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages],
                       "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.4}}).encode()
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                                 data=body, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return "".join(p.get("text", "") for p in json.load(r)["candidates"][0]["content"]["parts"])
    except Exception as e:
        print("Gemini unavailable, using offline engine:", e)
        return None


_bedrock_client = None


def bedrock(system, messages, max_tokens):
    """Amazon Bedrock Converse API. Uses the AWS credentials in the environment (hackathon sandbox, us-east-1).
    Set BEDROCK_MODEL_ID to a model from the hackathon allowlist, e.g. a Nova or Claude Haiku model ID from the Bedrock console."""
    global _bedrock_client
    model = os.getenv("BEDROCK_MODEL_ID")
    if not model:
        return None
    try:
        if _bedrock_client is None:
            import boto3
            _bedrock_client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
        resp = _bedrock_client.converse(
            modelId=model, system=[{"text": system}],
            messages=[{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.4})
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as e:
        print("Bedrock unavailable, using offline engine:", e)
        return None


def provider():
    """Which AI backend is switched on (the engine falls back to offline if its call fails)."""
    if os.getenv("BEDROCK_MODEL_ID"):
        return "bedrock"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return "claude" if os.getenv("ANTHROPIC_API_KEY") else "offline"


_lock, _last, _cache = threading.Lock(), [0.0], {}


def llm(system, messages, model, max_tokens=700):
    """One AI call with a cache (same input, same answer, no new call) and a 1-request-per-second limit (hackathon rule)."""
    k = hashlib.sha256(json.dumps([system, messages, max_tokens], sort_keys=True).encode()).hexdigest()
    if k in _cache:
        return _cache[k]
    if provider() == "offline":
        return None
    with _lock:
        wait = 1.1 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        out = _llm_call(system, messages, model, max_tokens)
        _last[0] = time.time()
    if out:
        if len(_cache) > 300:
            _cache.clear()
        _cache[k] = out
    return out


def _llm_call(system, messages, model, max_tokens=700):
    if os.getenv("BEDROCK_MODEL_ID"):
        return bedrock(system, messages, max_tokens)
    if os.getenv("GEMINI_API_KEY"):
        return gemini(system, messages, max_tokens)
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = json.dumps({"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return "".join(b.get("text", "") for b in json.load(r)["content"])
    except Exception as e:
        print("LLM unavailable, using offline engine:", e)
        return None


def parse(text, prev):
    c = regex_parse(text, prev)
    out = llm("Extract restaurant constraints. Return ONLY JSON with keys: protein (" + "|".join(PROTEINS) + "), style (" + "|".join(STYLES) + "), label (the dish name as the user said it), "
              "budget (naira per plate, number), plates (per week, number), availability (High|Medium|Low), "
              "difficulty (Easy|Medium|Hard), goal (cost|taste|protein|balanced). Start from PREVIOUS and change "
              "only what the new message changes. Omit keys you are unsure about.",
              [{"role": "user", "content": f"PREVIOUS: {json.dumps(prev)}\nMESSAGE: {text}"}],
              os.getenv("PARSE_MODEL", "claude-haiku-5-5"), 200)
    try:
        j = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
        if j.get("protein") in PROTEINS: c["protein"] = j["protein"]
        if j.get("style") in STYLES: c["style"] = j["style"]
        if isinstance(j.get("label"), str) and j["label"].strip(): c["label"] = j["label"].strip()[:40]
        if j.get("protein") in PROTEINS or j.get("style") in STYLES: c["assumed"] = ""
        if isinstance(j.get("budget"), (int, float)) and 150 <= j["budget"] <= 20000: c["budget"] = int(j["budget"])
        if isinstance(j.get("plates"), (int, float)) and j["plates"] > 0: c["plates"] = int(j["plates"])
        if j.get("availability") in AV: c["av"] = AV[j["availability"]]
        if j.get("difficulty") in DF: c["df"] = DF[j["difficulty"]]
        if j.get("goal") in GOALS: c["goal"] = j["goal"]
    except Exception:
        pass
    if "style" not in c and c.get("protein") in DEFAULT_STYLE:  # meat named, no dish: keep the meat, assume its usual dish
        c["style"] = DEFAULT_STYLE[c["protein"]]
        c["assumed"] = (f"You gave me {c['protein']} but not the dish, so I assumed {c['protein']} "
                        f"{STYLES[c['style']]['label'].lower()}. Tell me if you want it as something else "
                        "(suya, shawarma, stew, pepper soup, jollof topper, crispy bites) and I'll redo it.")
    if "style" not in c:
        c["style"], c["protein"] = "grill", "beef"
        c["assumed"] = ("I didn't catch a specific dish in that, so I assumed Beef Suya. Tell me the dish "
                        "(for example chicken stew or goat pepper soup) and I'll redo it.")
    if not mentions_dish(fix_spelling(text.lower())) and not re.search(r"\d|cheap|easy|easier|quick|protein|taste|authentic|budget|plates|allerg|free|no soy|no nut|no gluten|without|avoid", text.lower()):
        c["unknown"] = True  # message had no dish and no refinement: ask instead of guessing
    if prev.get("style") and (c["protein"], c["style"]) != (prev.get("protein"), prev["style"]) and c.get("budget") == prev.get("budget"):
        c["budget"] = int(get_dish(c)["cost"] * 0.7 // 50 * 50)  # new dish, no new budget: reset
    c.setdefault("budget", 700); c.setdefault("plates", 100)
    c.setdefault("av", 3); c.setdefault("df", 2); c.setdefault("goal", "balanced")
    return c


# ---------- 2. rank swaps (single ingredients and chef blends) ----------
def fit(p, d, goal):
    x, t = z(p), z(d)
    texture = 100 * math.exp(-math.sqrt(sum(w * (a - b) ** 2 for w, a, b in zip(W, x, t))) / 2.2)
    cost = 100 * min(max((d["cost"] - p["cost_per_portion_ngn"]) / d["cost"] / 0.6, 0), 1)
    fam = p["familiarity_score"] * 10
    speed = 100 * max(0, 1 - max(p["prep_time_mins"] - d["prep"], 0) / 30)
    prot = 100 * min(p["protein_g"] / d["protein_g"], 1)
    parts = (texture, cost, fam, speed, prot)
    total, m = sum(w * s for w, s in zip(GOALS[goal], parts)), p["best_cooking_method"].lower()
    if d["short"].lower() in p["name"].lower():  # ingredient built for this exact dish
        total += 8
    if d["wet"]:
        if re.search(r"simmer|boil|broth|steam|soup|stew", m): total += 5
        elif re.search(r"patties|fritters|fried|crumble|battered|crushed|coating", m): total *= 0.8
    return total, texture, cost


def warnings(p, d):
    w = []
    if p["protein_g"] - d["protein_g"] <= -5: w.append(f"{d['protein_g'] - p['protein_g']:g}g less protein per plate than the meat version")
    if p["chewiness_score"] - d["chewiness_score"] <= -2: w.append("softer bite than the original, so it may not feel meaty")
    if p["umami_score"] - d["umami_score"] <= -2: w.append("milder savoury depth, so season it harder")
    if p["familiarity_score"] < 6: w.append("unfamiliar to many diners, so run a taste-test special first")
    if p["prep_time_mins"] > d["prep"]: w.append(f"{int(p['prep_time_mins'])} min prep, above the {d['prep']} min target")
    return w


def rank(c):
    d = get_dish(c)
    budget, av, df, notes = c["budget"], c["av"], c["df"], []
    avoid = set(c.get("avoid", []))
    ok = lambda r: (r["cost_per_portion_ngn"] <= budget and r["av"] >= av and r["df"] <= df
                    and not (set(r.get("allergen_list", [])) & avoid))
    suits = (lambda r: re.search(r"Scramble|Omelette|Akara|Moi Moi|Fritters", r["name"])) if c.get("style") == "egg" else (lambda r: True)
    pool = [r for r in rows if ok(r) and suits(r)]
    if not pool and df < 3:
        df = 3; notes.append("allowed harder prep"); pool = [r for r in rows if ok(r) and suits(r)]
    if not pool and av > 1:
        av = 1; notes.append("allowed less-available ingredients"); pool = [r for r in rows if ok(r) and suits(r)]
    if not pool:
        budget = int(budget * 1.3); notes.append(f"raised the cap to ₦{budget}"); pool = [r for r in rows if ok(r) and suits(r)]
    if not pool:
        return []
    cands = []
    for r in pool:
        f, tx, cs = fit(r, d, c["goal"])
        cands.append((f, tx, cs, r, "single", r["cluster"]))
    top = sorted(pool, key=lambda r: -fit(r, d, c["goal"])[0])[:10]
    for a, b in itertools.combinations(top, 2):
        for wa in (0.5, 0.7):
            p = {k: wa * a[k] + (1 - wa) * b[k] for k in NUM}
            p.update(prep_time_mins=max(a["prep_time_mins"], b["prep_time_mins"]),
                     av=min(a["av"], b["av"]), df=max(a["df"], b["df"]),
                     allergen_list=sorted(set(a["allergen_list"]) | set(b["allergen_list"])),
                     price_confidence="Low" if "Low" in (a["price_confidence"], b["price_confidence"]) else "Medium")
            if not ok(p):
                continue
            sa, sb = a["name"].split(" (")[0], b["name"].split(" (")[0]
            p.update(name=f"{round(wa * 100)}% {sa} + {round((1 - wa) * 100)}% {sb}",
                     best_cooking_method=f"Blend {sa} and {sb}, season together, then {a['best_cooking_method'].lower()}",
                     availability_abuja="High" if p["av"] == 3 else "Medium" if p["av"] == 2 else "Low",
                     cooking_difficulty=[k for k, v in DF.items() if v == p["df"]][0])
            f, tx, cs = fit(p, d, c["goal"])
            cands.append((f, tx, cs, p, "blend", "blend"))
    cands.sort(key=lambda x: -x[0])
    picked, seen = [], set()
    for x in cands:  # best overall first, then different ingredient families for real choice
        if x[5] not in seen and len(picked) < 3:
            picked.append(x); seen.add(x[5])
    out = []
    for f, tx, cs, p, kind, _ in picked:
        sv = d["cost"] - p["cost_per_portion_ngn"]
        out.append(dict(name=p["name"], kind=kind, fit=round(min(f, 99), 1), texture=round(tx), cost_score=round(cs),
                        cost=round(p["cost_per_portion_ngn"]), save_plate=round(sv), save_week=round(sv * c["plates"]),
                        save_month=round(sv * c["plates"] * 4.3), protein=round(p["protein_g"], 1),
                        co2_week=round(max(d["co2"] - p["co2_kg_per_portion"], 0) * c["plates"], 1),
                        prep=int(p["prep_time_mins"]), difficulty=p["cooking_difficulty"],
                        availability=p["availability_abuja"], how=p["best_cooking_method"],
                        allergens=p.get("allergen_list", []), price_confidence=p.get("price_confidence", "Low"),
                        warnings=warnings(p, d)))
    if notes and out:
        out[0]["relaxed"] = "To find a match I " + " and ".join(notes) + "."
    return out


# ---------- 3. write the answer ----------
PREP = [  # how to get each ingredient ready (so the advice is about the actual ingredient)
    ("tsp", "soak in hot seasoned stock for 10 minutes, squeeze it dry, so it soaks up flavour instead of tasting like sponge"),
    ("soy chunks", "soak in hot seasoned stock for 10 minutes and squeeze dry"),
    ("tofu", "press it under a weight for 15 minutes, then pat dry so it browns instead of steaming"),
    ("awara", "press it under a weight for 15 minutes, then pat dry so it browns instead of steaming"),
    ("mushroom", "dry-sear in a hot pan first to drive out the water, then season, otherwise it goes rubbery and grey"),
    ("seitan", "slice thin against the grain so it chews like meat, not like bread"),
    ("melon", "shape into firm balls or patties and chill 15 minutes so they hold together"),
    ("bean", "mash coarsely (not smooth) so there is still some bite, and chill before shaping"),
    ("cowpea", "mash coarsely (not smooth) so there is still some bite, and chill before shaping"),
    ("bambara", "mash coarsely (not smooth) so there is still some bite, and chill before shaping"),
    ("jackfruit", "drain well and shred, then roast dry before adding any sauce"),
    ("kuli", "use it as the coating, not the main body"),
    ("groundnut", "roast the chunks dry first so they stay crunchy"),
]
METHOD = {
    "egg": "Crumble it and fry in hot oil with onion, pepper and turmeric, stirring gently until just set",
    "grill": "Skewer it, rub on the yaji, rest 20 minutes, then grill over high heat 3 to 4 minutes a side so it chars on the edges",
    "wrap": "Slice into thin strips, season and sear hard in a very hot pan, then pile into the wrap with the sauce, cabbage and cucumber",
    "soup": "Make the pepper soup base first and simmer it, then add the protein for the last 10 to 15 minutes so it keeps its shape",
    "stew": "Fry the stew base until the oil rises, then add the protein for the last 10 to 15 minutes so it keeps its shape",
    "fried": "Coat it, then shallow-fry in hot oil until deep golden, and drain on paper before serving",
    "rice": "Sear the protein hard on its own, then lay it on top of the rice so it keeps its bite",
}


def prep_for(a):
    nm = a["name"].lower()
    seen, notes = set(), []
    for key, note in PREP:
        if key in nm and note not in seen:
            seen.add(note); notes.append(note)
    return notes[:2]

def allergen_line(c, a):
    al = ", ".join(a.get("allergens") or []) or "no major allergens in the recipe"
    avoid = c.get("avoid") or []
    s = f"**Allergens:** {('contains ' + al) if a.get('allergens') else al}."
    if avoid:
        s += f" Filtered out everything containing {', '.join(avoid)}."
    s += (" This only covers the ingredients in the recipe: check bought-in spice mixes and labels, and keep a separate "
          "pan and surface for customers with allergies.")
    if a.get("price_confidence") == "Low":
        s += (f" **Price check:** the ₦{a['cost']} is an estimate (market prices for some of these ingredients are not "
              "published), so confirm with your supplier before you cost the menu.")
    return s


def offline_answer(c, recs):
    d, a = get_dish(c), recs[0]
    short = a["name"].split(" (")[0]
    menu = f"Chef's Plant {d['short']}" if a["kind"] == "blend" else f"{short} {d['short']}"
    s = (c["assumed"] + "\n\n") if c.get("assumed") else ""
    pn = prep_for(a)
    how = ("First, " + "; and ".join(pn) + ". " if pn else "") + METHOD[c["style"]]
    s += f"For **{d['name']}** with a **₦{c['budget']}** cap, I'd go with **{a['name']}**. "
    s += (f"It scores {a['texture']}/100 on texture against the real thing and costs ₦{a['cost']} a plate.\n\n"
          f"**How to make it work:** {how}. Flavour it with {d['kit']}.\n\n"
          f"**The money:** ₦{a['cost']} vs about ₦{d['cost']} for the animal version (a rough estimate, so use your own price) saves ₦{a['save_plate']} a plate. "
          f"At {c['plates']} plates a week that is about **₦{a['save_week']:,} a week** (₦{a['save_month']:,} a month), "
          f"and roughly {a['co2_week']} kg CO₂e less.\n\n")
    s += "**Watch out:** " + ("; ".join(a["warnings"]) if a["warnings"] else "texture is the one thing to taste-test: cook one batch and let two regulars try it blind before it goes on the menu") + ". "
    s += f"Sell it as \"{menu}\" as a weekend special and track how many plates sell.\n\n"
    s += allergen_line(c, a) + "\n\n"
    if len(recs) > 1:
        s += f"**Runner-up:** {recs[1]['name']} at ₦{recs[1]['cost']} a plate if you want a different texture."
    return s


def answer(msg, hist, c, recs):
    data = {"constraints": c, "meat_dish": {k: get_dish(c)[k] for k in ("name", "cost", "protein_g", "kit")},
            "top3": recs}
    sysmsg = ("You are the AI menu consultant for Abuja restaurants moving dishes to plant-based. Use ONLY the numbers "
              "in DATA; never invent prices, protein or savings. Answer the person's actual message first. Then give: "
              "your pick and why, a concrete cooking plan (method, seasoning, timing) using the flavour kit, the money "
              "maths, one honest risk with how to test it, a menu name, and a one-line runner-up. Under 220 words, plain "
              "text, **bold** for key numbers, speak like a practical chef-advisor. If the note says the limits were "
              "relaxed, say so plainly. 'how' is how the ingredient is usually cooked; adapt it to the dish (for stew or soup, add it late so it holds its shape). If constraints.assumed is set, say that first. Always say which allergens the pick contains (the 'allergens' list) "
              "and, if constraints.avoid is set, that those were excluded; remind them to check bought-in spice mixes and keep allergen-safe prep. "
              "If the pick's price_confidence is Low, say the cost is an estimate to confirm with the supplier.")
    msgs = [{"role": h["role"], "content": h["content"]} for h in hist[-6:] if h.get("role") in ("user", "assistant")]
    msgs.append({"role": "user", "content": f"{msg}\n\nDATA: {json.dumps(data, ensure_ascii=False)}"})
    return llm(sysmsg, msgs, os.getenv("ANSWER_MODEL", "claude-sonnet-5-5"), 700)


@app.post("/chat")
def chat(req: Chat):
    c = parse(req.message, req.state)
    if c.pop("unknown", False):
        low = req.message.lower()
        if any(w in low for w in ["bean", "moi", "akara", "tofu", "soy", "egusi", "okpa", "groundnut", "plantain", "mushroom", "vegetable"]):
            msg = ("That already sounds like a plant food, so there is nothing to swap. Tell me the animal protein you "
                   "want to replace and how you cook it, for example ponmo stew, egg sauce or chicken suya.")
        else:
            msg = ("I didn't recognise that one yet. I can swap beef, goat, chicken, turkey, fish, egg, snail, prawns, "
                   "stockfish, ponmo, shaki (tripe), liver and gizzard, cooked as suya, shawarma, pepper soup, stew, "
                   "fried, jollof topper or egg scramble. Tell me which one and I'll redo it.")
        return {"answer": msg,
                "recommendations": [], "state": req.state, "mode": "offline"}
    recs = rank(c)
    if not recs:
        msg = "Nothing in the database fits those limits. Try a higher budget or allow harder prep."
        if c.get("avoid"):
            msg = (f"Nothing in the database fits those limits while avoiding {', '.join(c['avoid'])}. "
                   "Try a different dish style or a higher budget. I never relax allergy filters.")
        return {"answer": msg,
                "recommendations": [], "state": c, "mode": "offline"}
    ans = answer(req.message, req.history, c, recs)
    return {"answer": ans or offline_answer(c, recs), "recommendations": recs, "state": c,
            "mode": provider() if ans else "offline",
            "understood": {"dish": get_dish(c)["name"], "assumed": c.get("assumed", ""), "budget": c["budget"], "plates": c["plates"],
                           "goal": c["goal"], "avoid": c.get("avoid", []), "max_difficulty": [k for k, v in DF.items() if v == c["df"]][0]}}


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "restaurant.html")


@app.get("/plant-based")
def ui():
    return FileResponse(BASE_DIR / "index.html")


# ---- Images: finds your photos whatever the extension (.jpg .png .webp) or capitalisation ----
import pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "images"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".jfif", ".gif"}
IMG_DIR.mkdir(exist_ok=True)


def _norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _image_files():
    return [f for f in IMG_DIR.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT]


@app.get("/images-check")
def images_check():
    return {"looking_in": str(IMG_DIR), "images_found": sorted(f.name for f in _image_files())}


@app.get("/images/{name}")
def get_image(name: str):
    key = _norm(pathlib.Path(name).stem)
    files = _image_files()
    for f in files:
        if _norm(f.stem) == key:
            return FileResponse(f)
    for f in files:
        n = _norm(f.stem)
        if len(n) >= 3 and (key in n or n in key):
            return FileResponse(f)
    raise HTTPException(status_code=404)
