"""Customer accounts: sign up, log in, saved details, order history. No extra packages needed.
Optional (keeps customers logged in after a server restart):   $env:ACCOUNT_SECRET="any-long-random-text"
Passwords are never stored: only a salted PBKDF2 hash."""
import hashlib, hmac, json, os, pathlib, re, secrets, sqlite3, time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

HERE = pathlib.Path(__file__).resolve().parent
DB = HERE / "accounts.db"
ORDERS = HERE / "orders.jsonl"
STATUS = HERE / "order_status.json"
SESSION_DAYS = 30
ITER = 200_000
AVOID_OK = {"soy", "gluten", "nut"}
_SECRET = (os.getenv("ACCOUNT_SECRET") or secrets.token_hex(32)).encode()
_tries, _signups = {}, {}  # ip -> (wrong tries, locked until) / ip -> sign-up times
router = APIRouter()


def _db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE, email TEXT UNIQUE,
        pw TEXT NOT NULL, address TEXT DEFAULT '', avoid TEXT DEFAULT '', created REAL)""")
    return c


def _hash(pw):
    salt = secrets.token_bytes(16)
    return f"pbkdf2${ITER}${salt.hex()}${hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, ITER).hex()}"


def _verify(pw, stored):
    try:
        _, it, salt, h = stored.split("$")
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(it)).hex(), h)
    except Exception:
        return False


_DUMMY = _hash("not-a-real-password")  # so a wrong phone number takes as long as a wrong password


def _sign(uid, exp):
    return hmac.new(_SECRET, f"u{uid}|{exp}".encode(), hashlib.sha256).hexdigest()


def _set_cookie(request, response, uid):
    exp = int(time.time()) + SESSION_DAYS * 86400
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie("mt_session", f"{uid}|{exp}|{_sign(uid, exp)}", httponly=True, samesite="lax", secure=secure,
                        max_age=SESSION_DAYS * 86400)


def account_id(request: Request):
    """The logged-in customer's id, or None for a guest. app.py stores this on each order."""
    try:
        uid, exp, sig = request.cookies.get("mt_session", "").split("|")
        if int(exp) < time.time() or not hmac.compare_digest(sig, _sign(uid, exp)):
            return None
        return int(uid)
    except Exception:
        return None


def current(request: Request):
    uid = account_id(request)
    row = None
    if uid is not None:
        with _db() as c:
            row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Please log in.")
    return row


def norm_phone(p):
    d = re.sub(r"\D", "", p)
    return "0" + d[3:] if d.startswith("234") and len(d) == 13 else d


def _ip(request):
    return request.client.host if request.client else "?"


class Register(BaseModel):
    name: str = Field(..., min_length=2, max_length=60)
    phone: str = Field(..., max_length=30)
    email: str = Field("", max_length=120)
    password: str = Field(..., min_length=8, max_length=100)


class LoginIn(BaseModel):
    who: str = Field(..., max_length=120)  # phone number or email
    password: str = Field(..., max_length=100)


class Profile(BaseModel):
    name: str = Field(..., min_length=2, max_length=60)
    address: str = Field("", max_length=200)
    avoid: list[str] = []


class NewPassword(BaseModel):
    old: str = Field(..., max_length=100)
    new: str = Field(..., min_length=8, max_length=100)


class Confirm(BaseModel):
    password: str = Field(..., max_length=100)


@router.get("/account")
def account_page():
    return FileResponse(HERE / "account.html", headers={"Cache-Control": "no-store"})


@router.get("/account-nav.js")
def account_nav():
    return FileResponse(HERE / "account-nav.js", media_type="application/javascript", headers={"Cache-Control": "no-cache"})


@router.post("/api/register")
def register(b: Register, request: Request, response: Response):
    ip, now = _ip(request), time.time()
    recent = [t for t in _signups.get(ip, []) if now - t < 3600]
    if len(recent) >= 10:
        raise HTTPException(status_code=429, detail="Too many new accounts from this device. Please try again later.")
    phone = norm_phone(b.phone)
    if not 10 <= len(phone) <= 15:
        raise HTTPException(status_code=400, detail="Please enter a phone number we can call, like 0803 000 0000.")
    email = b.email.strip().lower()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=400, detail="That email address doesn't look right.")
    try:
        with _db() as c:
            uid = c.execute("INSERT INTO users(name,phone,email,pw,created) VALUES(?,?,?,?,?)",
                            (b.name.strip(), phone, email or None, _hash(b.password), now)).lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="An account with this phone number or email already exists. Try logging in.")
    _signups[ip] = recent + [now]
    _set_cookie(request, response, uid)
    return {"ok": True}


@router.post("/api/login")
def login(b: LoginIn, request: Request, response: Response):
    ip = _ip(request)
    n, until = _tries.get(ip, (0, 0))
    if until > time.time():
        raise HTTPException(status_code=429, detail="Too many wrong tries. Please wait 5 minutes.")
    who = b.who.strip()
    with _db() as c:
        row = (c.execute("SELECT * FROM users WHERE email=?", (who.lower(),)) if "@" in who
               else c.execute("SELECT * FROM users WHERE phone=?", (norm_phone(who),))).fetchone()
    ok = _verify(b.password, row["pw"] if row else _DUMMY) and row is not None
    if not ok:
        n += 1
        _tries[ip] = (0, time.time() + 300) if n >= 8 else (n, 0)
        raise HTTPException(status_code=401, detail="Wrong phone/email or password.")
    _tries.pop(ip, None)
    _set_cookie(request, response, row["id"])
    return {"ok": True}


@router.post("/api/logout")
def logout(response: Response):
    response.delete_cookie("mt_session")
    return {"ok": True}


def _profile(u):
    return dict(name=u["name"], phone=u["phone"], email=u["email"] or "", address=u["address"] or "",
                avoid=[a for a in (u["avoid"] or "").split(",") if a])


@router.get("/api/me")
def me(u=Depends(current)):
    return _profile(u)


@router.put("/api/account")
def update_profile(b: Profile, u=Depends(current)):
    avoid = ",".join(sorted(set(a for a in b.avoid if a in AVOID_OK)))
    with _db() as c:
        c.execute("UPDATE users SET name=?, address=?, avoid=? WHERE id=?", (b.name.strip(), b.address.strip(), avoid, u["id"]))
    return {"ok": True}


@router.post("/api/account/password")
def change_password(b: NewPassword, u=Depends(current)):
    if not _verify(b.old, u["pw"]):
        raise HTTPException(status_code=400, detail="Your current password is wrong.")
    with _db() as c:
        c.execute("UPDATE users SET pw=? WHERE id=?", (_hash(b.new), u["id"]))
    return {"ok": True}


@router.post("/api/account/delete")
def delete_account(b: Confirm, response: Response, u=Depends(current)):
    if not _verify(b.password, u["pw"]):
        raise HTTPException(status_code=400, detail="Wrong password.")
    with _db() as c:
        c.execute("DELETE FROM users WHERE id=?", (u["id"],))
    response.delete_cookie("mt_session")
    return {"ok": True}


@router.get("/api/my-orders")
def my_orders(u=Depends(current)):
    try:
        st = json.loads(STATUS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    out = []
    if ORDERS.exists():
        for line in ORDERS.read_text(encoding="utf-8").splitlines():
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("user") == u["id"]:
                out.append(dict({k: o.get(k) for k in ("order_id", "created", "mode", "address", "items", "total")},
                                status=st.get(o.get("order_id"), "new")))
    return {"orders": out[::-1][:50]}