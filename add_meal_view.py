"""Run ONCE from the jojo folder:   py add_meal_view.py
Shows the WHOLE meal, not just the protein: "your rice (or soup, stew, bread...) stays the same + the plant-based
protein", with the whole-plate price, on both the consultant and the Swap and save tab.
Changes app.py and index.html. Backups: app.py.before_meal, index.html.before_meal. Nothing is written unless everything fits."""
import pathlib, shutil, sys

def load(name):
    p = pathlib.Path(name)
    if not p.exists():
        sys.exit(f"Run this from the jojo folder: {name} not found.")
    raw = p.read_bytes()
    return p, b"\r\n" in raw, raw.decode("utf-8").replace("\r\n", "\n")

def swap(s, old, new):
    if s.count(old) != 1:
        sys.exit("Could not find this exactly once, so NOTHING was changed:\n" + old)
    return s.replace(old, new)

pa, crlf_a, a = load("app.py")
ph, crlf_h, h = load("index.html")
oa, oh = a, h

if "def meal_base" not in a:
    a = swap(a, "def show_fields(p, c, d):",
'''MEAL_BASE = {"rice": "Jollof / fried rice", "wrap": "Shawarma bread, salad and sauce", "soup": "Pepper soup broth",
             "stew": "Stew", "grill": "Suya spice, onion and tomato", "fried": "Seasoned crispy coating", "egg": "Egg sauce base"}


def meal_base(c):
    """What stays on the plate besides the protein (shown next to the swap)."""
    return MEAL_BASE.get(c.get("style"), "Your usual sides")


def show_fields(p, c, d):''')
    a = swap(a, '    return dict(pics=pics, title=p.get("title") or title_of(pics),',
                '    return dict(base_label=meal_base(c), pics=pics, title=p.get("title") or title_of(pics),')
    a = swap(a, '        sv = d["cost"] - round(p["cost_per_portion_ngn"])  # use the rounded cost so the maths on screen adds up\n',
                '        mp, _ = menu_price_for(c, d)  # saving = whole-plate menu price minus the new whole-plate price\n'
                '        sv = mp - swap_price(mp, d["cost"], p["cost_per_portion_ngn"])\n')
    a = swap(a, '''    s += (f"Go with **{a['name']}**: ₦{a['cost']:,} a plate against about ₦{d['cost']:,} for the {c['protein']}, "
          f"so you save **₦{a['save_plate']:,} a plate** (₦{a['save_week']:,} a week at {c['plates']} plates).")''',
'''    s += (f"Keep your {a['base_label'].lower()} and swap the {c['protein']} for **{a['title']}**: the whole plate comes to "
          f"**₦{a['price']:,}** instead of {'about ' if a['price_estimated'] else ''}₦{a['menu_price']:,}, "
          f"so you save **₦{a['save_plate']:,} a plate** (₦{a['save_week']:,} a week at {c['plates']} plates).")''')
    a = swap(a, '''"plate against the meat's cost (meat_dish.cost), and the saving per plate. Add one short warning only if "''',
                '''"whole plate (top3[0].price) against the menu price (top3[0].menu_price), and the saving per plate (top3[0].save_plate). "
              "Say the customer keeps their rice or sides and only the protein changes. Add one short warning only if "''')
    print("app.py: whole-plate wording and price added")

if "mealPics" not in h:
    h = swap(h, "button:focus-visible,a:focus-visible{",
'''.pics .bt{flex:1;min-width:0;position:relative;background:#fff3e4;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:10px;font-size:.8rem}
.bt b{font-size:.9rem}.bt span{color:var(--mut);font-size:.72rem;margin-top:2px}
.bt::after{content:"+";position:absolute;right:-14px;top:50%;transform:translateY(-50%);width:28px;height:28px;border-radius:50%;background:var(--red);color:#fff;display:grid;place-items:center;font-weight:700;z-index:2}
.rc .meal{font-size:.8rem;margin:2px 0 6px}
button:focus-visible,a:focus-visible{''')
    h = swap(h, "const picsHtml=",
'''const mealPics=(imgs,label,sub,off)=>`<div class="pics"><div class="bt"><b>${esc(label)}</b><span>${esc(sub)}</span></div>${imgs.map(u=>`<img src="${esc(u)}" alt="" loading="lazy" onerror="this.remove()">`).join("")}${off?`<span class="off">${off}% cheaper</span>`:""}</div>`;
const picsHtml=''')
    h = swap(h, '<article class="alt">${picsHtml(o.images,o.off_pct)}',
                '<article class="alt">${mealPics(o.images,"Same "+cur.item.name,"only the "+cur.item.meat+" changes",o.off_pct)}')
    h = swap(h, '<div class="rc">${picsHtml(r.images||[])}',
                '<div class="rc">${mealPics(r.images||[],r.base_label||"Your usual sides","stays the same")}')
    h = swap(h, '${r.kind=="blend"?" (blend)":""}</h4>',
                '${r.kind=="blend"?" (blend)":""}</h4>\n<div class="meal">You get <b>${esc(r.base_label||"your usual sides")}</b> as before, with this protein instead of the meat.</div>')
    h = swap(h, "<td>Cost a plate</td>", "<td>Protein cost</td>")
    h = swap(h, '<div class="sell">Sell at <b>', '<div class="sell">Whole plate: <b>')
    print("index.html: rice/sides + protein view added")

def save(p, text, crlf, orig, tag):
    if text != orig:
        b = pathlib.Path(p.name + ".before_meal")
        if not b.exists():
            shutil.copy(p, b)
        p.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
save(pa, a, crlf_a, oa, "app")
save(ph, h, crlf_h, oh, "html")
print("Done. Restart uvicorn if it is not auto-reloading, then press Ctrl+F5 in the browser.")