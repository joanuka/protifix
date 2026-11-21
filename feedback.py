"""Feedback for alternative proteins: scan QR -> /feedback -> saved -> shown on the same page.
Add to app.py:
    from feedback import router as feedback_router
    app.include_router(feedback_router)
"""
import sqlite3, time, pathlib, socket
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

HERE = pathlib.Path(__file__).parent
DB = HERE / "feedback.db"
router = APIRouter()

def _db():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, dish TEXT,
        rating INTEGER, comment TEXT, created REAL)""")
    return c

class Feedback(BaseModel):
    name: str = Field("", max_length=40)
    dish: str = Field("", max_length=80)
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=3, max_length=500)

@router.get("/feedback")
def feedback_page():
    return FileResponse(HERE / "feedback.html")

@router.post("/api/feedback")
def add_feedback(f: Feedback):
    with _db() as c:
        # light spam guard: same comment text twice in a row is ignored
        last = c.execute("SELECT comment FROM feedback ORDER BY id DESC LIMIT 1").fetchone()
        if last and last[0] == f.comment.strip():
            raise HTTPException(409, "You already sent this feedback.")
        c.execute("INSERT INTO feedback(name,dish,rating,comment,created) VALUES(?,?,?,?,?)",
                  (f.name.strip() or "Anonymous", f.dish.strip(), f.rating, f.comment.strip(), time.time()))
    return {"ok": True}

@router.get("/api/feedback")
def list_feedback(limit: int = 50):
    with _db() as c:
        rows = c.execute("SELECT name,dish,rating,comment,created FROM feedback ORDER BY id DESC LIMIT ?",
                         (min(limit, 200),)).fetchall()
        avg = c.execute("SELECT AVG(rating), COUNT(*) FROM feedback").fetchone()
    return {"average": round(avg[0], 1) if avg[0] else None, "count": avg[1],
            "items": [dict(name=r[0], dish=r[1], rating=r[2], comment=r[3], created=r[4]) for r in rows]}


@router.get("/api/lan-url")
def lan_url(request: Request):
    """The address a phone on the same Wi-Fi can open (127.0.0.1 only works on this PC)."""
    ip = "127.0.0.1"
    try:
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sk.connect(("8.8.8.8", 80))
        ip = sk.getsockname()[0]
        sk.close()
    except OSError:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            pass
    return {"url": f"http://{ip}:{request.url.port or 80}"}