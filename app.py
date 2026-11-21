import csv, datetime, difflib, hashlib, html, itertools, json, math, os, pathlib, re, threading, time, urllib.request
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel

from smalltalk import smalltalk
from feedback import router as feedback_router
from admin import router as admin_router
from accounts import router as accounts_router, account_id
from make_alt_images import SLUGS, render as draw_alt  # names + one-line descriptions of every alternative food picture

BASE_DIR = pathlib.Path(__file__).resolve().parent  # all files are found relative to app.py, so the server can start from any folder

app = FastAPI(title="Mama Tolu Menu Consultant")
app.add_middleware(CORSMiddleware, allow_origins=[o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o],
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])
app.include_router(feedback_router)
app.include_router(admin_router)
app.include_router(accounts_router)

AV = {"High": 3, "Medium": 2, "Low": 1}
DF = {"Easy": 1, "Medium": 2, "Hard": 3}
NUM = ["protein_g", "fat_g", "cost_per_portion_ngn", "chewiness_score", "umami_score",
       "prep_time_mins", "familiarity_score", "co2_kg_per_portion"]
SENS = ["protein_g", "fat_g", "chewiness_score", "umami_score"]
W = [0.8, 0.5, 1.4, 1.2]  # texture + umami decide whether it "feels like meat"

rows = []
with open(BASE_DIR / "ingredients.csv", encoding="utf-8") as f:
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
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    body = json.dumps({"system_instruction": {"parts": [{"text": system}]},
                       "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages],
                       "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.4}}).encode()
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                                 data=body, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return "".join(p.get("text", "") for p in json.load(r)["candidates"][0]["content"]["parts"])
    except Exception as e:
        detail = e.read().decode("utf-8", "ignore")[:300] if hasattr(e, "read") else ""
        print("Gemini unavailable, using offline engine:", e, detail)
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


# Plant foods are listed per 100 g cooked, but they hold less protein than meat. So every ingredient is
# resized to give the SAME protein as the meat it replaces (cost, fat and CO2 grow with the weight).
MAX_SCALE = 3.0  # at most 3x the 100 g portion (300 g) to match the meat's protein
MIN_MATCH = 0.90  # an option must deliver at least 90% of the meat's protein, or it is not shown as a swap


def scaled(r, d):
    """One ingredient row, resized so its protein matches the meat's. Never shrinks a portion below 100 g."""
    k = min(max(d["protein_g"] / r["protein_g"], 1.0), MAX_SCALE)
    return dict(r, portion_g=int(round(100 * k / 5) * 5), protein_g=r["protein_g"] * k, fat_g=r["fat_g"] * k,
                cost_per_portion_ngn=r["cost_per_portion_ngn"] * k, co2_kg_per_portion=r["co2_kg_per_portion"] * k)


def rank(c):
    d = get_dish(c)
    base = [scaled(r, d) for r in rows]  # every candidate sized to match the meat's protein
    budget, av, df, notes = c["budget"], c["av"], c["df"], []
    avoid = set(c.get("avoid", []))
    ok = lambda r: (r["cost_per_portion_ngn"] <= budget and r["av"] >= av and r["df"] <= df
                    and not (set(r.get("allergen_list", [])) & avoid))
    suits = (lambda r: re.search(r"Scramble|Omelette|Akara|Moi Moi|Fritters", r["name"])) if c.get("style") == "egg" else (lambda r: True)
    pool = [r for r in base if ok(r) and suits(r)]
    if not pool and df < 3:
        df = 3; notes.append("allowed harder prep"); pool = [r for r in base if ok(r) and suits(r)]
    if not pool and av > 1:
        av = 1; notes.append("allowed less-available ingredients"); pool = [r for r in base if ok(r) and suits(r)]
    if not pool:
        budget = int(budget * 1.3); notes.append(f"raised the cap to ₦{budget}"); pool = [r for r in base if ok(r) and suits(r)]
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
            p.update(portion_g=int(round(wa * a["portion_g"] + (1 - wa) * b["portion_g"])),
                     prep_time_mins=max(a["prep_time_mins"], b["prep_time_mins"]),
                     av=min(a["av"], b["av"]), df=max(a["df"], b["df"]),
                     allergen_list=sorted(set(a["allergen_list"]) | set(b["allergen_list"])),
                     price_confidence="Low" if "Low" in (a["price_confidence"], b["price_confidence"]) else "Medium")
            if not ok(p):
                continue
            sa, sb = a["name"].split(" (")[0], b["name"].split(" (")[0]
            p["pics"] = list(dict.fromkeys(pics_for(a)[:1] + pics_for(b)[:1]))
            p.update(name=f"{round(wa * 100)}% {sa} + {round((1 - wa) * 100)}% {sb}",
                     best_cooking_method=f"Blend {sa} and {sb}, season together, then {a['best_cooking_method'].lower()}",
                     availability_abuja="High" if p["av"] == 3 else "Medium" if p["av"] == 2 else "Low",
                     cooking_difficulty=[k for k, v in DF.items() if v == p["df"]][0])
            p["title"] = p["name"]
            f, tx, cs = fit(p, d, c["goal"])
            cands.append((f, tx, cs, p, "blend", "blend"))
    cands.sort(key=lambda x: -x[0])
    picked, seen = [], set()
    for x in cands:  # best overall first, then different ingredient families for real choice
        if x[5] not in seen and len(picked) < 3:
            picked.append(x); seen.add(x[5])
    out = []
    for f, tx, cs, p, kind, _ in picked:
        sv = d["cost"] - round(p["cost_per_portion_ngn"])  # use the rounded cost so the maths on screen adds up
        out.append(dict(name=p["name"], kind=kind, fit=round(min(f, 99), 1), texture=round(tx), cost_score=round(cs),
                        cost=round(p["cost_per_portion_ngn"]), save_plate=round(sv), save_week=round(sv * c["plates"]),
                        save_month=round(sv * c["plates"] * 4.3), protein=round(p["protein_g"], 1),
                        co2_week=round(max(d["co2"] - p["co2_kg_per_portion"], 0) * c["plates"], 1),
                        prep=int(p["prep_time_mins"]), difficulty=p["cooking_difficulty"],
                        availability=p["availability_abuja"], how=p["best_cooking_method"],
                        allergens=p.get("allergen_list", []), price_confidence=p.get("price_confidence", "Low"),
                        warnings=warnings(p, d), **show_fields(p, c, d)))
    if notes and out:
        out[0]["relaxed"] = "To find a match I " + " and ".join(notes) + "."
    return out


# ---------- 2b. pictures, "same protein, cheaper" prices, menu, cart and orders ----------
ING_SLUG = [  # (word in the ingredient name, picture slug). First match wins, so order matters.
    ("textured soy", "tsp"), ("tofu", "tofu"), ("tempeh", "tempeh"), ("seitan", "seitan"), ("wheat gluten", "seitan"),
    ("king oyster", "king-oyster"), ("oyster", "oyster-mushroom"), ("button", "button-mushroom"), ("shiitake", "shiitake"),
    ("jackfruit seed", "jackfruit-seed"), ("jackfruit", "jackfruit"), ("banana blossom", "banana-blossom"),
    ("cowpea", "cowpea"), ("bambara", "bambara"), ("soybean", "soybean"), ("chickpea", "chickpea"), ("lentil", "lentil"),
    ("pigeon", "pigeon-pea"), ("yam bean", "yam-bean"), ("lima", "lima-bean"), ("egusi", "egusi"), ("groundnut", "groundnut"),
    ("kuli", "kuli-kuli"), ("walnut", "african-walnut"), ("pumpkin", "pumpkin-seed"), ("sunflower", "sunflower-seed"),
    ("cashew", "cashew"), ("tiger nut", "tiger-nut"), ("ukwa", "ukwa"), ("ugba", "ugba"), ("plantain", "plantain"), ("maize", "maize")]


def pics_for(r):
    """Which picture(s) show this food: 1 for a single ingredient, 2 for a blend (its two main ingredients)."""
    if r.get("pics"):
        return r["pics"]
    nm = r["name"].lower()
    if "moi moi" in nm:
        return ["moi-moi"]
    if "akara" in nm:
        return ["akara"]
    parts = []
    for g, ing in re.findall(r"(\d+)g ([^;]+)", r.get("ingredient_basis", "")):
        slug = next((sl for kw, sl in ING_SLUG if kw in ing.lower()), None)
        if slug:
            parts.append((float(g), slug))
    out = []
    for g, slug in sorted(parts, key=lambda x: -x[0]):
        if slug not in out and (not out or g >= 12):  # a pinch of spice powder doesn't get its own picture
            out.append(slug)
    r["pics"] = out[:2] or ["tofu"]
    return r["pics"]


def what_is(pics):
    label, what = SLUGS[pics[0]][2], SLUGS[pics[0]][3]
    return f"Made from {label} and {SLUGS[pics[1]][2]}. {what}" if len(pics) > 1 else what


def title_of(pics):
    return " + ".join(SLUGS[p][2] for p in pics)


def img_urls(pics):
    return [f"/alt-image/{p}" for p in pics]


# What a customer pays for a plant-based swap.
# Sized to match the meat's protein, and the kitchen's saving on the ingredient goes to the customer:
#   price = plate price - meat cost + plant cost (for the same protein)
SWAP_PASS_THROUGH = 1.0  # 1.0 = the customer gets the whole ingredient saving. Raise it (say 1.5) for bigger discounts
SWAP_MIN_OFF = 0.10      # every swap is at least this much cheaper than the meat dish
SWAP_MAX_OFF = 0.45      # ...and never more than this much cheaper


def swap_price(menu_price, meat_cost, plant_cost):
    saving = max(meat_cost - plant_cost, 0) * SWAP_PASS_THROUGH
    off = min(max(saving / menu_price, SWAP_MIN_OFF), SWAP_MAX_OFF)
    return int(round(menu_price * (1 - off) / 50) * 50)  # nearest ₦50, easy to give change


with open(BASE_DIR / "menu.json", encoding="utf-8") as f:
    MENU = json.load(f)["items"]
MENU_BY_ID = {m["id"]: m for m in MENU}
VARIANT_WORDS = ["Suya Strips", "Shawarma Strips", "Pepper Soup Chunks", "Stew Pieces", "Asun-Style", "Crispy Bites", "Jollof Rice Topper"]
STYLE_VARIANT = {"grill": "Suya Strips", "wrap": "Shawarma Strips", "soup": "Pepper Soup Chunks", "stew": "Stew Pieces",
                 "fried": "Crispy Bites", "rice": "Jollof Rice Topper"}
MAX_PLANT_COST_SHARE = 0.8  # skip alternatives that cost more than 80% of the meat they replace: they can't be sold cheaper
_swap_cache = {}


def row_key(r):
    return re.sub(r"[^a-z0-9]+", "-", r["name"].lower()).strip("-")


def menu_price_for(c, d):
    """Menu price of the meat dish: the real menu item if there is one, otherwise an estimate from the meat's cost."""
    m = next((m for m in MENU if m.get("protein") == c["protein"] and m.get("style") == c["style"]), None)
    return (m["price"], False) if m else (int(round(d["cost"] / 0.30 / 50) * 50), True)


def show_fields(p, c, d):
    pics = pics_for(p)
    menu_price, est = menu_price_for(c, d)
    price = swap_price(menu_price, d["cost"], p["cost_per_portion_ngn"])
    return dict(pics=pics, title=p.get("title") or title_of(pics), images=img_urls(pics), what=what_is(pics), menu_price=menu_price, price=price,
                price_estimated=est, off_pct=round(100 * (menu_price - price) / menu_price),
                portion_g=p.get("portion_g", 100),
                protein_off_pct=round(100 * (d["cost"] - p["cost_per_portion_ngn"]) / d["cost"]),
                meat_cost=d["cost"], meat_protein=d["protein_g"])


def swap_options(item):
    """Every plant-based version of one menu dish: sized to match the meat's protein, cheaper, with picture."""
    if item["id"] in _swap_cache:
        return _swap_cache[item["id"]]
    c = {"protein": item["protein"], "style": item["style"], "goal": "balanced"}
    d = get_dish(c)
    want, best = STYLE_VARIANT[item["style"]], {}
    for r0 in rows:
        if not [w for w in VARIANT_WORDS if w in r0["name"]] or want not in r0["name"]:
            continue  # only foods built for this exact kind of dish
        r = scaled(r0, d)
        if r["protein_g"] < MIN_MATCH * d["protein_g"]:
            continue  # capped portion still falls short on protein: do not sell it as a like-for-like swap
        if r["av"] < 2 or r["cost_per_portion_ngn"] > MAX_PLANT_COST_SHARE * d["cost"]:
            continue  # hard to buy in Abuja, or not actually cheaper once sized to match the protein
        pics = tuple(pics_for(r))
        score = fit(r, d, "balanced")[0]
        if pics not in best or score > best[pics][0]:
            best[pics] = (score, r)
    out = []
    for _, r in sorted(best.values(), key=lambda x: -x[0]):
        pics = pics_for(r)
        cost = r["cost_per_portion_ngn"]
        price = swap_price(item["price"], d["cost"], cost)
        out.append(dict(key=row_key(r), id=f"{item['id']}~{row_key(r)}", name=r["name"], title=title_of(pics), pics=pics, images=img_urls(pics),
                        what=what_is(pics), how=r["best_cooking_method"], protein=round(r["protein_g"], 1),
                        meat_protein=d["protein_g"], price=price, was=item["price"], save=item["price"] - price,
                        off_pct=round(100 * (item["price"] - price) / item["price"]), allergens=r["allergen_list"],
                        portion_g=r["portion_g"], protein_off_pct=round(100 * (d["cost"] - cost) / d["cost"]),
                        portion=f"{r['portion_g']} g cooked, sized to match the meat's protein"))
    _swap_cache[item["id"]] = out
    return out


def cheapest_swap(item):
    opts = swap_options(item) if item.get("protein") else []
    return min((o["price"] for o in opts), default=None)


def priced_line(line_id):
    """The one place a cart line gets its name and price. The browser only ever sends ids and quantities."""
    if "~" in line_id:
        mid, key = line_id.split("~", 1)
        item = MENU_BY_ID.get(mid)
        opt = next((o for o in swap_options(item) if o["key"] == key), None) if item and item.get("protein") else None
        if not opt:
            return None
        return dict(id=line_id, name=f"{item['name']}, plant-based: {opt['title']}", sub=f"Sized to match the meat version's protein. {opt['how']}.", price=opt["price"],
                    images=opt["images"], plant=True)
    item = MENU_BY_ID.get(line_id)
    if not item:
        return None
    return dict(id=line_id, name=item["name"], sub=item["desc"], price=item["price"], images=[f"/images/{item['img']}.jpg"], plant=False)


class Line(BaseModel):
    id: str
    qty: int = 1


class Quote(BaseModel):
    lines: list[Line]


class OrderIn(BaseModel):
    name: str
    phone: str
    mode: str = "pickup"
    address: str = ""
    note: str = ""
    lines: list[Line]


def quote(lines):
    out, missing = [], []
    for ln in lines[:30]:
        pl = priced_line(ln.id)
        if not pl:
            missing.append(ln.id)
            continue
        q = max(1, min(int(ln.qty), 20))
        out.append(dict(pl, qty=q, total=pl["price"] * q))
    return dict(lines=out, unavailable=missing, subtotal=sum(x["total"] for x in out))


_orders_lock = threading.Lock()
ORDERS_FILE = BASE_DIR / "orders.jsonl"


def save_order(o):
    with _orders_lock:
        n = sum(1 for _ in open(ORDERS_FILE, encoding="utf-8")) if ORDERS_FILE.exists() else 0
        o["order_id"] = f"MT-{1001 + n}"
        with open(ORDERS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    return o["order_id"]


# ---------- 3. write the answer (short: one or two sentences, the cards hold the proof) ----------
def offline_answer(c, recs):
    d, a = get_dish(c), recs[0]
    s = (c["assumed"] + "\n\n") if c.get("assumed") else ""
    s += (f"Go with **{a['name']}**: ₦{a['cost']:,} a plate against about ₦{d['cost']:,} for the {c['protein']}, "
          f"so you save **₦{a['save_plate']:,} a plate** (₦{a['save_week']:,} a week at {c['plates']} plates).")
    if a["warnings"]:
        s += f" Watch out: {a['warnings'][0]}."
    return s


def answer(msg, hist, c, recs):
    data = {"constraints": c, "meat_dish": {k: get_dish(c)[k] for k in ("name", "cost", "protein_g", "kit")},
            "top3": recs}
    sysmsg = ("You are the menu consultant for an Abuja restaurant moving dishes to plant-based. Use ONLY the numbers in DATA; "
              "never invent prices, protein or savings. Reply in at most 2 sentences and under 40 words: the pick, its cost per "
              "plate against the meat's cost (meat_dish.cost), and the saving per plate. Add one short warning only if "
              "top3[0].warnings is not empty. Plain text, **bold** the key numbers. No cooking steps and no allergen paragraph: "
              "the cards show those. If constraints.assumed is set, say it first in one sentence.")
    msgs = [{"role": h["role"], "content": h["content"]} for h in hist[-6:] if h.get("role") in ("user", "assistant")]
    msgs.append({"role": "user", "content": f"{msg}\n\nDATA: {json.dumps(data, ensure_ascii=False)}"})
    return llm(sysmsg, msgs, os.getenv("ANSWER_MODEL", "claude-sonnet-5-5"), 200)


STRONG_Q = re.compile(r"^\s*(why|how|what is|what are|what's|whats|explain|tell me|who)\b", re.I)
SOFT_Q = re.compile(r"^\s*(can you|can i|could you|do you|do i|does|should i|is |are |which)", re.I)
SWAP_WORDS = re.compile(r"instead|swap|replace|alternative|substitute|cheap|budget|under|plates")


def is_chat_question(m):
    """Questions and chat go to the conversational AI. Requests with a budget or number stay with the data engine."""
    if re.search(r"\d|₦", m):
        return False
    return bool(STRONG_Q.search(m)) or (bool(SOFT_Q.search(m)) and not SWAP_WORDS.search(m.lower()))


def menu_brief():
    """The real menu and its best swaps, given to the AI so it never has to invent a price or a protein number."""
    out = []
    for m in MENU:
        line = f"{m['name']} N{m['price']}"
        if m.get("protein"):
            line += f" ({m['protein']} {m['style']}). Swaps: " + "; ".join(
                f"{o['title']} N{o['price']} ({o['protein']} g protein, {o['off_pct']}% cheaper, contains {', '.join(o['allergens']) or 'no major allergens'})"
                for o in swap_options(m)[:2])
        out.append(line)
    return "\n".join(out)


CONVO_SYSTEM = (
    "You are the AI assistant of Mama Tolu Kitchen, a Nigerian restaurant in Abuja. Chat like a warm, friendly server: "
    "greet back, handle small talk, and answer questions about the menu, plant-based swaps, protein, allergens and cooking. "
    "For a greeting or small talk, reply warmly in one short sentence and ask what they need. "
    "NEVER list dishes, prices or the menu unless the customer asks about the menu or names a specific food. "
    "Reply in the language the customer writes in (English, Pidgin, Hausa, Yoruba or Igbo). Keep it to 3 sentences or fewer, plain text. "
    "Your main job: meat is expensive, so help people who cannot afford it or do not eat it find a plant-based swap with the SAME protein for less. "
    "For any price, protein, saving or allergen use ONLY the MENU data given; never invent numbers, and say so if the data does not have it. "
    "When it fits, invite the customer to name a dish (for example 'chicken pepper soup') or open the Swap and save tab. "
    "You cannot place orders yourself. Give no medical advice: for allergies, say the recipe data lists allergens but they should confirm with staff. "
    "If asked about something unrelated, answer in one friendly sentence and steer back to food.")


def converse(message, history, state):
    """A natural conversation grounded in the real menu. Returns None if no AI is switched on or it fails."""
    msgs = [{"role": h["role"], "content": h["content"]} for h in (history or [])[-6:] if h.get("role") in ("user", "assistant")]
    msgs.append({"role": "user", "content": f"{message}\n\nMENU (prices in naira):\n{menu_brief()}"})
    try:
        return llm(CONVO_SYSTEM, msgs, os.getenv("ANSWER_MODEL", "claude-sonnet-5-5"), 300)
    except Exception as e:
        print("converse failed:", e)
        return None


@app.post("/chat")
def chat(req: Chat):
    t = smalltalk(req.message)  # hi / how are you / thanks: answered straight away, no menu dump
    if t:
        return {"answer": t, "recommendations": [], "state": req.state, "mode": "offline"}
    if is_chat_question(req.message):
        ai = converse(req.message, req.history, req.state)
        if ai:
            return {"answer": ai, "recommendations": [], "state": req.state, "mode": provider()}
    prev = req.state
    if mentions_dish(fix_spelling(req.message.lower())):  # a new food starts fresh: only allergy filters carry over
        prev = {k: v for k, v in prev.items() if k == "avoid"}
    c = parse(req.message, prev)
    if c.pop("unknown", False):
        ai = converse(req.message, req.history, req.state)
        if ai:
            return {"answer": ai, "recommendations": [], "state": req.state, "mode": provider()}
        low = req.message.lower()
        if any(w in low for w in ["bean", "moi", "akara", "tofu", "soy", "egusi", "okpa", "groundnut", "plantain", "mushroom", "vegetable"]):
            msg = ("That already sounds like a plant food, so there is nothing to swap. Tell me the animal protein you "
                   "want to replace and how you cook it, for example ponmo stew, egg sauce or chicken suya.")
        else:
            msg = ("Sorry, I didn't quite get that. You can ask me a question about our menu, or tell me a dish "
                   "you'd like a cheaper plant-based swap for.")
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


@app.get("/ai-check")
def ai_check():
    """Open http://127.0.0.1:8006/ai-check to see which AI is switched on and whether it answers."""
    if os.getenv("DEBUG_TOOLS") != "1":
        raise HTTPException(status_code=404)
    prov = provider()
    if prov == "offline":
        return {"provider": "offline", "works": False,
                "problem": "No key found. Set GEMINI_API_KEY, BEDROCK_MODEL_ID or ANTHROPIC_API_KEY in the same terminal that runs uvicorn."}
    out = _llm_call("Reply with the single word OK.", [{"role": "user", "content": "ping"}], os.getenv("ANSWER_MODEL", "claude-sonnet-5-5"), 20)
    return {"provider": prov, "works": bool(out), "reply": out,
            "if_not_working": "Look in the uvicorn terminal for the line that says 'unavailable': it names the error."}


def menu_cards_html():
    """The menu cards on the home page, built from menu.json so prices live in one place."""
    out = []
    for m in MENU:
        cheap = cheapest_swap(m)
        swap = (f'<a class="swap" href="/plant-based?dish={m["id"]}">Plant-based version from ₦{cheap:,}</a>' if cheap else "")
        out.append(
            f'<article class="card" data-c="{m["cat"]}"><div class="ph" data-name="{html.escape(m["name"])}">'
            f'<img src="/images/{m["img"]}.jpg" alt="{html.escape(m["name"])}" loading="lazy" onerror="this.remove()"></div>'
            f'<h3>{html.escape(m["name"])}</h3><p>{html.escape(m["desc"])}</p>{swap}'
            f'<div class="row"><span class="price">₦{m["price"]:,}</span>'
            f'<a class="add" href="/order?add={m["id"]}" aria-label="Order {html.escape(m["name"])}">Order</a></div></article>')
    return "\n".join(out)


@app.get("/", response_class=HTMLResponse)
def home():
    page = (BASE_DIR / "restaurant.html").read_text(encoding="utf-8")
    return HTMLResponse(page.replace("<!--MENU_CARDS-->", menu_cards_html()))


@app.get("/order")
def order_page():
    return FileResponse(BASE_DIR / "order.html")


@app.get("/plant-based")
def ui():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/api/menu")
def api_menu():
    return {"items": [dict(m, swap_from=cheapest_swap(m)) for m in MENU]}


@app.get("/api/swaps/{item_id}")
def api_swaps(item_id: str):
    item = MENU_BY_ID.get(item_id)
    if not item or not item.get("protein"):
        raise HTTPException(status_code=404, detail="No plant-based swap for this dish")
    d = get_dish({"protein": item["protein"], "style": item["style"]})
    return {"item": dict(item, image=f"/images/{item['img']}.jpg", meat=item["protein"]), "meat_protein_g": d["protein_g"],
            "options": swap_options(item)}


@app.post("/api/quote")
def api_quote(req: Quote):
    return quote(req.lines)


@app.post("/api/orders")
def api_order(req: OrderIn, request: Request):
    name, phone = req.name.strip()[:80], req.phone.strip()[:30]
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Please tell us your name.")
    digits = re.sub(r"\D", "", phone)
    if not 10 <= len(digits) <= 15:
        raise HTTPException(status_code=400, detail="Please enter a phone number we can call, like 0803 000 0000.")
    mode = req.mode if req.mode in ("pickup", "delivery") else "pickup"
    address = req.address.strip()[:200]
    if mode == "delivery" and len(address) < 6:
        raise HTTPException(status_code=400, detail="Please add your delivery address.")
    q = quote(req.lines)
    if q["unavailable"]:
        raise HTTPException(status_code=409, detail="Something in your order is no longer on the menu. Please check your basket.")
    if not q["lines"]:
        raise HTTPException(status_code=400, detail="Your basket is empty.")
    order = dict(created=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), name=name, phone=phone,
                 mode=mode, address=address if mode == "delivery" else "", note=req.note.strip()[:300],
                 items=[dict(id=x["id"], name=x["name"], qty=x["qty"], price=x["price"], total=x["total"]) for x in q["lines"]],
                 total=q["subtotal"], user=account_id(request))
    oid = save_order(order)
    return {"ok": True, "order_id": oid, "total": order["total"], "mode": mode, "items": order["items"]}


@app.get("/alt-image/{slug}")
def alt_image(slug: str):
    """The picture of an alternative food. A real photo (jpg/png/webp) in images/alt/ beats the drawn picture."""
    slug = re.sub(r"[^a-z0-9-]", "", slug.lower())
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
        f = IMG_DIR / "alt" / (slug + ext)
        if f.is_file():
            return FileResponse(f)
    svg = draw_alt(slug)
    if svg:
        return Response(content=svg, media_type="image/svg+xml")
    raise HTTPException(status_code=404)


@app.get("/credits", response_class=HTMLResponse)
def credits():
    """Photo credits (required by the Creative Commons licences of the alternative-protein photos)."""
    p = BASE_DIR / "images" / "alt" / "CREDITS.txt"
    rows = [l.split(" | ") for l in p.read_text(encoding="utf-8").splitlines() if l.count(" | ") >= 3] if p.exists() else []
    li = "".join(f'<li>{r[0]}: photo by {r[1]}, {r[2]}, <a href="{r[3].strip()}">source</a></li>' for r in rows)
    return f"<!DOCTYPE html><meta charset=utf-8><title>Photo credits</title><body style='font-family:sans-serif;max-width:720px;margin:40px auto;padding:0 20px;line-height:1.7'><h1>Photo credits</h1><p>Photos of alternative proteins are from Wikimedia Commons under Creative Commons licences.</p><ul>{li}</ul><p><a href='/'>Back to the restaurant</a></p>"


@app.get("/cart.js")
def cart_js():
    return FileResponse(BASE_DIR / "cart.js", media_type="application/javascript")


# ---- Images: finds your photos whatever the extension (.jpg .png .webp) or capitalisation ----
IMG_DIR = BASE_DIR / "images"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".jfif", ".gif"}
IMG_DIR.mkdir(exist_ok=True)


def _norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _image_files():
    return [f for f in IMG_DIR.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT]


@app.get("/images-check")
def images_check():
    if os.getenv("DEBUG_TOOLS") != "1":
        raise HTTPException(status_code=404)
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