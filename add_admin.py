"""Run ONCE from the jojo folder:   py add_admin.py
 - adds the staff login + orders dashboard (/admin)
 - turns /ai-check and /images-check OFF (they only work when DEBUG_TOOLS=1)
 - closes the open CORS setting (your pages are served by the same app, so they do not need it)
Your original is saved as app.py.before_admin. Nothing is written unless every change fits. Safe to run twice."""
import pathlib, shutil, sys
for need in ("admin.py", "admin.html"):
    if not pathlib.Path(need).exists():
        sys.exit(f"Missing {need}. Save it in this folder with exactly this name.")
p = pathlib.Path("app.py")
raw = p.read_bytes()
crlf = b"\r\n" in raw
s = raw.decode("utf-8").replace("\r\n", "\n")
orig = s

def swap(old, new):
    global s
    if s.count(old) != 1:
        sys.exit("Could not find this exactly once, so NOTHING was changed:\n" + old)
    s = s.replace(old, new)

if "admin_router" not in s:
    swap("from feedback import router as feedback_router\n",
         "from feedback import router as feedback_router\nfrom admin import router as admin_router\n")
    swap("app.include_router(feedback_router)\n", "app.include_router(feedback_router)\napp.include_router(admin_router)\n")
    print("admin login and dashboard: added")
if "DEBUG_TOOLS" not in s:
    swap('    prov = provider()\n    if prov == "offline":',
         '    if os.getenv("DEBUG_TOOLS") != "1":\n        raise HTTPException(status_code=404)\n    prov = provider()\n    if prov == "offline":')
    swap('def images_check():\n    return {',
         'def images_check():\n    if os.getenv("DEBUG_TOOLS") != "1":\n        raise HTTPException(status_code=404)\n    return {')
    print("/ai-check and /images-check: switched off")
OLD_CORS = 'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])'
if OLD_CORS in s:
    swap(OLD_CORS, 'app.add_middleware(CORSMiddleware, allow_origins=[o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o],\n'
                   '                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])')
    print("CORS: closed")
if s != orig:
    if not pathlib.Path("app.py.before_admin").exists():
        shutil.copy(p, "app.py.before_admin")
    p.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))
print("Done. Set ADMIN_PASSWORD, restart uvicorn, open /admin.")