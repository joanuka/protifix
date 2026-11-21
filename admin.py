"""Staff login + orders dashboard (no extra packages needed).
Set these before starting the server (PowerShell):
    $env:ADMIN_USER="owner"
    $env:ADMIN_PASSWORD="a-long-password-only-you-know"
    $env:ADMIN_SECRET="any-long-random-text"      # optional: keeps staff logged in after a restart
Open  http://127.0.0.1:8001/admin
"""
import hashlib, hmac, json, os, pathlib, secrets, sqlite3, threading, time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

HERE = pathlib.Path(__file__).resolve().parent
ORDERS = HERE / "orders.jsonl"        # written by app.py when a customer sends an order
STATUS = HERE / "order_status.json"   # order id -> new / preparing / ready / done / cancelled
FB_DB = HERE / "feedback.db"
STATUSES = ["new", "preparing", "ready", "done", "cancelled"]
SESSION_HOURS = 12
_SECRET = (os.getenv("ADMIN_SECRET") or secrets.token_hex(32)).encode()
_lock = threading.Lock()
_fails = {}  # ip -> (wrong tries, locked until)
router = APIRouter()

if not os.getenv("ADMIN_PASSWORD"):
    print("ADMIN: login is OFF. Set the ADMIN_PASSWORD environment variable and restart to use /admin.")
elif len(os.getenv("ADMIN_PASSWORD", "")) < 8:
    print("ADMIN: that password is short. Use at least 8 characters, ideally 12 or more.")


def _sign(user, exp):
    return hmac.new(_SECRET, f"{user}|{exp}".encode(), hashlib.sha256).hexdigest()


def _token(user):
    exp = int(time.time()) + SESSION_HOURS * 3600
    return f"{user}|{exp}|{_sign(user, exp)}"


def _valid(token):
    try:
        user, exp, sig = token.split("|")
        if int(exp) < time.time() or not hmac.compare_digest(sig, _sign(user, exp)):
            return None
        return user
    except Exception:
        return None


def require_admin(request: Request):
    user = _valid(request.cookies.get("admin_session", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Please log in.")
    return user


class Login(BaseModel):
    username: str = Field("", max_length=60)
    password: str = Field(..., max_length=200)


class StatusIn(BaseModel):
    status: str


@router.get("/admin")
def admin_page():
    return FileResponse(HERE / "admin.html", headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})


@router.post("/admin/api/login")
def login(body: Login, request: Request, response: Response):
    user, pw = os.getenv("ADMIN_USER", "admin"), os.getenv("ADMIN_PASSWORD", "")
    if not pw:
        raise HTTPException(status_code=503, detail="Admin login is switched off. Set ADMIN_PASSWORD and restart the server.")
    ip = request.client.host if request.client else "?"
    n, until = _fails.get(ip, (0, 0))
    if until > time.time():
        raise HTTPException(status_code=429, detail="Too many wrong tries. Please wait 5 minutes.")
    ok = hmac.compare_digest(body.username.encode(), user.encode()) & hmac.compare_digest(body.password.encode(), pw.encode())
    if not ok:
        n += 1
        _fails[ip] = (0, time.time() + 300) if n >= 5 else (n, 0)
        raise HTTPException(status_code=401, detail="Wrong username or password.")
    _fails.pop(ip, None)
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie("admin_session", _token(user), httponly=True, samesite="lax", secure=secure, max_age=SESSION_HOURS * 3600)
    return {"ok": True}


@router.post("/admin/api/logout")
def logout(response: Response):
    response.delete_cookie("admin_session")
    return {"ok": True}


@router.get("/admin/api/me")
def me(user=Depends(require_admin)):
    return {"user": user}


def _read_orders():
    out = []
    if ORDERS.exists():
        for line in ORDERS.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def _statuses():
    try:
        return json.loads(STATUS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


@router.get("/admin/api/orders")
def orders(user=Depends(require_admin)):
    st = _statuses()
    rows = [dict(o, status=st.get(o.get("order_id"), "new")) for o in _read_orders()]
    rows.reverse()  # newest first
    return {"orders": rows[:300]}


@router.post("/admin/api/orders/{oid}/status")
def set_status(oid: str, body: StatusIn, user=Depends(require_admin)):
    if body.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Unknown status.")
    if not any(o.get("order_id") == oid for o in _read_orders()):
        raise HTTPException(status_code=404, detail="Order not found.")
    with _lock:
        st = _statuses()
        st[oid] = body.status
        STATUS.write_text(json.dumps(st), encoding="utf-8")
    return {"ok": True}


@router.get("/admin/api/feedback")
def feedback_list(user=Depends(require_admin)):
    if not FB_DB.exists():
        return {"items": []}
    with sqlite3.connect(FB_DB) as c:
        rows = c.execute("SELECT id,name,dish,rating,comment,created FROM feedback ORDER BY id DESC LIMIT 200").fetchall()
    return {"items": [dict(id=r[0], name=r[1], dish=r[2], rating=r[3], comment=r[4], created=r[5]) for r in rows]}


@router.delete("/admin/api/feedback/{fid}")
def feedback_delete(fid: int, user=Depends(require_admin)):
    if FB_DB.exists():
        with sqlite3.connect(FB_DB) as c:
            c.execute("DELETE FROM feedback WHERE id=?", (fid,))
    return {"ok": True}