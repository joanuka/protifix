"""Downloads a real photo of every alternative food into images/alt/ (from Wikimedia Commons).

Run it from your jojo folder, with internet on:
    py get_food_photos.py

- The website automatically shows a real photo instead of the drawing (no other change needed).
- It only accepts a photo whose title really names the food, and it throws away earlier photos that don't.
- It goes slowly on purpose (Wikimedia blocks fast downloaders with "429 Too Many Requests"). Takes a few minutes.
- Safe to run again: it only fills the gaps. Foods it can't find keep their drawing.
- Want a different photo for one food?  py get_food_photos.py tofu   (picks the next-best one)
  Or drop your own tofu.jpg into images/alt/. Your own photos are never overwritten.
- images/alt/CREDITS.txt lists who took each photo. Many licences require credit, so keep it,
  or replace the photos with your own before using the site commercially.
"""
import html, json, pathlib, re, sys, time, urllib.error, urllib.parse, urllib.request

OUT = pathlib.Path(__file__).resolve().parent / "images" / "alt"
UA = "MamaTolu-menu/1.0 (restaurant website; contact: owner)"  # Wikimedia asks every app to identify itself
GAP = 3.0  # seconds between requests

SEARCH = {  # picture name: searches to try, in order
    "tofu": ["tofu", "fried tofu", "tofu cubes"], "tsp": ["textured soy protein", "soy chunks"],
    "tempeh": ["tempeh"], "seitan": ["seitan"], "oyster-mushroom": ["oyster mushrooms", "Pleurotus ostreatus"],
    "button-mushroom": ["button mushrooms", "Agaricus bisporus mushrooms"], "shiitake": ["shiitake mushrooms", "shiitake"],
    "king-oyster": ["king oyster mushroom", "Pleurotus eryngii"], "jackfruit": ["jackfruit meat", "cooked jackfruit", "jackfruit"],
    "banana-blossom": ["banana blossom", "banana flower food"], "cowpea": ["black-eyed peas", "cowpeas"],
    "bambara": ["Bambara groundnut", "Vigna subterranea seeds"], "soybean": ["soybeans", "soya beans dried"],
    "chickpea": ["chickpeas", "garbanzo beans"], "lentil": ["lentils"], "pigeon-pea": ["pigeon peas"],
    "lima-bean": ["lima beans", "butter beans"], "yam-bean": ["African yam bean", "Sphenostylis stenocarpa"],
    "egusi": ["egusi seeds", "egusi melon seeds", "egusi"], "akara": ["akara", "acaraje bean fritters", "bean fritters"],
    "moi-moi": ["moin moin", "moi moi"], "groundnut": ["peanuts", "groundnuts"], "kuli-kuli": ["kuli kuli"],
    "pumpkin-seed": ["pumpkin seeds"], "sunflower-seed": ["sunflower seeds", "sunflower kernels"],
    "tiger-nut": ["tiger nuts", "tigernuts"], "cashew": ["cashew nuts", "roasted cashews"],
    "ugba": ["ugba", "African oil bean"], "ukwa": ["ukwa", "African breadfruit seeds"],
    "african-walnut": ["African walnut", "Tetracarpidium conophorum"], "jackfruit-seed": ["jackfruit seeds"],
    "plantain": ["plantain", "plantain slices"], "maize": ["sweet corn kernels", "corn kernels", "maize"],
}
MUST = {  # the photo's title must contain one of these words, so we never get a stir-fry when we asked for tofu
    "tofu": "tofu|bean curd|awara|doufu", "tsp": "soy|soya|textured|tvp", "tempeh": "tempeh|tempe",
    "seitan": "seitan|wheat gluten", "oyster-mushroom": "oyster|ostreatus", "button-mushroom": "button|champignon|agaricus",
    "shiitake": "shiitake|shitake|lentinula", "king-oyster": "king oyster|eryngii|king trumpet|seitling",
    "jackfruit": "jackfruit|nangka|chakka|kathal", "banana-blossom": "banana (blossom|flower|heart)|blossom",
    "cowpea": "black.?eyed|cowpea", "bambara": "bambara", "soybean": "soybean|soya bean|soy bean|edamame",
    "chickpea": "chickpea|chick pea|garbanzo|chana", "lentil": "lentil", "pigeon-pea": "pigeon",
    "lima-bean": "lima bean|butter bean", "yam-bean": "yam bean|sphenostylis", "egusi": "egusi|melon seed",
    "akara": "akara|acaraj|bean cake|bean fritter", "moi-moi": "moin|moi.?moi|moyin", "groundnut": "peanut|groundnut",
    "kuli-kuli": "kuli", "pumpkin-seed": "pumpkin seed|pepita", "sunflower-seed": "sunflower seed|sunflower kernel",
    "tiger-nut": "tiger.?nut|chufa", "cashew": "cashew", "ugba": "ugba|oil bean", "ukwa": "ukwa|breadfruit",
    "african-walnut": "walnut|conophor", "jackfruit-seed": "jackfruit seed|seeds? of jackfruit", "plantain": "plantain",
    "maize": "maize|corn",
}
SKIP = re.compile(r"diagram|logo|map\b|icon|drawing|illustration|packag|label|\btree|flower\b|field|farm|market|stall|"
                  r"plant\b|leaf|leaves|harvest|poster|chart|graph|cartoon|sign\b|\bbox\b|\bbag\b|sack|shop|store|"
                  r"specimen|herbarium|mhnt|bot\.|grinder|machine|processing|deshell|workers?|women|woman|man\b|children|"
                  r"stir.?fry|salad|soup|curry|pizza", re.I)
last_call = [0.0]


def valid(title, slug):
    return bool(re.search(MUST[slug], title, re.I)) and not SKIP.search(title)


def get(url):
    for attempt in range(1, 7):
        wait = GAP - (time.time() - last_call[0])
        if wait > 0:
            time.sleep(wait)
        last_call[0] = time.time()
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == 6:
                raise
            pause = int(e.headers.get("Retry-After", 0) or 0) or 20 * attempt
            print(f"   (Wikimedia says slow down, waiting {pause}s...)")
            time.sleep(pause)


def candidates(query, slug):
    api = ("https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrlimit=30"
           "&prop=imageinfo&iiprop=url|mime|size|extmetadata&iiurlwidth=900&format=json&gsrsearch="
           + urllib.parse.quote(query))
    pages = json.loads(get(api)).get("query", {}).get("pages", {})
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        info = (p.get("imageinfo") or [{}])[0]
        title = p.get("title", "")
        if info.get("mime") != "image/jpeg" or not valid(title, slug):
            continue
        w, h = info.get("width", 0), info.get("height", 0)
        if w < 700 or h < 500 or w < h * 0.9:  # big enough, and landscape-ish so it fits the card
            continue
        meta = info.get("extmetadata", {})
        who = re.sub(r"[<>|]|\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(meta.get("Artist", {}).get("value", "unknown"))))[:80]
        out.append(dict(title=title, url=info.get("thumburl") or info["url"], who=who.strip(),
                        lic=meta.get("LicenseShortName", {}).get("value", "see Commons page"),
                        page="https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))))
    return out


def title_of(line):
    return urllib.parse.unquote(line.split(" | ")[3].split("/wiki/")[-1]).replace("_", " ")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = args or list(SEARCH)
    OUT.mkdir(parents=True, exist_ok=True)
    credits = OUT / "CREDITS.txt"
    old = [l for l in (credits.read_text(encoding="utf-8").splitlines() if credits.exists() else []) if l.count(" | ") >= 3]
    lines = []
    for l in old:  # throw away earlier photos that don't clearly show the right food
        slug = l.split(" | ")[0]
        if slug in MUST and not valid(title_of(l), slug) and slug not in args:
            (OUT / f"{slug}.jpg").unlink(missing_ok=True)
            print(f"x {slug}: removed a wrong photo ({title_of(l)})")
        elif slug not in args:
            lines.append(l)
    got = skipped = failed = 0
    for name in names:
        if name not in SEARCH:
            print(f"? {name}: not a known picture name"); continue
        dest = OUT / f"{name}.jpg"
        if dest.exists() and not args:
            skipped += 1; continue
        try:
            tried = {title_of(l) for l in old if l.startswith(name + " | ")} if args else set()
            pick = None
            for q in SEARCH[name]:
                pick = next((c for c in candidates(q, name) if c["title"] not in tried), None)
                if pick:
                    break
            if not pick:
                print(f"- {name}: no good photo found, keeping the drawing"); failed += 1; continue
            dest.write_bytes(get(pick["url"]))
            lines = [l for l in lines if not l.startswith(name + " | ")] + [f'{name} | {pick["who"]} | {pick["lic"]} | {pick["page"]}']
            credits.write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")
            print(f"+ {name}: {pick['title']}  ({pick['lic']})"); got += 1
        except Exception as e:
            print(f"! {name}: {e}"); failed += 1
    credits.write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")
    print(f"\nDone. {got} downloaded, {skipped} already there, {failed} not found or failed.")
    print("If some failed with 'Too Many Requests', wait 10 minutes and run it again: it only fills the gaps.")
    print("Then refresh the page with Ctrl+Shift+R.")


if __name__ == "__main__":
    main()