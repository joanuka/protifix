"""Run ONCE from the jojo folder:   py add_accounts.py
Turns on customer accounts (your accounts.py was never connected, and there was no sign-in page):
 - connects accounts.py to app.py (sign up, log in, log out, saved details, order history)
 - saves the logged-in customer's id on each order, so "Your orders" works
 - adds a "Sign in" link (or "Hi, Name") to the menu of every page
 - the order page fills in name, phone and address for logged-in customers
 - the plant-based page switches on the customer's saved allergy filters
Needs account.html, accounts.py and account-nav.js in this folder.
Backups are saved as <file>.before_accounts. Nothing is written unless every change fits. Safe to run twice."""
import pathlib, shutil, sys

for need in ("accounts.py", "account.html", "account-nav.js", "app.py"):
    if not pathlib.Path(need).exists():
        sys.exit(f"Missing {need}. Save it in this folder with exactly this name (underscores and dashes, no spaces).")


def load(path):
    raw = pathlib.Path(path).read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def save(path, text, crlf):
    p = pathlib.Path(path)
    if not pathlib.Path(str(p) + ".before_accounts").exists():
        shutil.copy(p, str(p) + ".before_accounts")
    p.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


plan = {}  # file -> new text, written only if everything fits

# ---- app.py
s, crlf = load("app.py")
orig = s


def swap(old, new):
    global s
    if s.count(old) != 1:
        sys.exit("Could not find this exactly once in app.py, so NOTHING was changed:\n" + old)
    s = s.replace(old, new)


if "accounts_router" not in s:
    swap("from fastapi import FastAPI\n", "from fastapi import FastAPI, Request\n")
    swap("from feedback import router as feedback_router\n",
         "from feedback import router as feedback_router\nfrom accounts import router as accounts_router, account_id\n")
    swap("app.include_router(feedback_router)\n", "app.include_router(feedback_router)\napp.include_router(accounts_router)\n")
    swap("def api_order(req: OrderIn):", "def api_order(req: OrderIn, request: Request):")
    swap('                 total=q["subtotal"])\n    oid = save_order(order)',
         '                 total=q["subtotal"], user=account_id(request))\n    oid = save_order(order)')
    print("app.py: accounts connected")
if s != orig:
    plan["app.py"] = (s, crlf)

# ---- html pages
NAV = '<script src="/account-nav.js" defer></script>\n'
ORDER_FILL = ('<script>fetch("/api/me").then(function(r){return r.ok?r.json():null}).then(function(u){if(!u)return;'
              'var set=function(id,v){var e=document.getElementById(id);if(e&&!e.value)e.value=v||""};'
              'set("name",u.name);set("phone",u.phone);set("address",u.address)}).catch(function(){});</script>\n')
PLANT_FILL = ('<script>fetch("/api/me").then(function(r){return r.ok?r.json():null}).then(function(u){'
              'if(u&&u.avoid&&u.avoid.length){u.avoid.forEach(function(a){filters.add(a)});if(cur)renderSwaps()}}).catch(function(){});</script>\n')
pages = {"restaurant.html": NAV, "order.html": NAV + ORDER_FILL, "index.html": NAV + PLANT_FILL, "feedback.html": NAV}
for name, add in pages.items():
    if not pathlib.Path(name).exists():
        print(f"{name}: not found, skipped")
        continue
    t, c = load(name)
    if "account-nav.js" in t:
        continue
    i = t.rfind("</body>")
    if i < 0:
        sys.exit(f"{name} has no </body>, so NOTHING was changed.")
    plan[name] = (t[:i] + add + t[i:], c)

for name, (text, c) in plan.items():
    save(name, text, c)
    print(f"{name}: updated")
print("Done. Restart uvicorn, then open /account (or click 'Sign in' in the menu).")
print("Tip: so customers stay logged in after a restart, set once per terminal:  $env:ACCOUNT_SECRET=\"any-long-random-text\"")