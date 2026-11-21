"""Run ONCE from the jojo folder:   py apply_all.py
Applies every app.py change in the right order (nothing is written unless ALL of them fit):
  1. greetings (smalltalk.py) + feedback routes (feedback.py) + Gemini model fix
  2. shows the real Gemini error text in the terminal if it ever fails again
  3. conversational AI assistant that answers from your real menu numbers
Your original is saved as app.py.before_patches. Safe to run twice."""
import pathlib, shutil, sys
p = pathlib.Path("app.py")
if not p.exists():
    sys.exit("Run this from the jojo folder (the one that contains app.py).")
for need in ("smalltalk.py", "feedback.py", "feedback.html"):
    if not pathlib.Path(need).exists():
        sys.exit(f"Missing file: {need}. Save it in this folder with exactly this name (lowercase, underscore, no spaces).")
s = p.read_text(encoding="utf-8")
orig = s

NEW_FUNCS = 'STRONG_Q = re.compile(r"^\\s*(why|how|what is|what are|what\'s|whats|explain|tell me|who)\\b", re.I)\nSOFT_Q = re.compile(r"^\\s*(can you|can i|could you|do you|do i|does|should i|is |are |which)", re.I)\nSWAP_WORDS = re.compile(r"instead|swap|replace|alternative|substitute|cheap|budget|under|plates")\n\n\ndef is_chat_question(m):\n    """Questions and chat go to the conversational AI. Requests with a budget or number stay with the data engine."""\n    if re.search(r"\\d|₦", m):\n        return False\n    return bool(STRONG_Q.search(m)) or (bool(SOFT_Q.search(m)) and not SWAP_WORDS.search(m.lower()))\n\n\ndef menu_brief():\n    """The real menu and its best swaps, given to the AI so it never has to invent a price or a protein number."""\n    out = []\n    for m in MENU:\n        line = f"{m[\'name\']} N{m[\'price\']}"\n        if m.get("protein"):\n            line += f" ({m[\'protein\']} {m[\'style\']}). Swaps: " + "; ".join(\n                f"{o[\'title\']} N{o[\'price\']} ({o[\'protein\']} g protein, {o[\'off_pct\']}% cheaper, contains {\', \'.join(o[\'allergens\']) or \'no major allergens\'})"\n                for o in swap_options(m)[:2])\n        out.append(line)\n    return "\\n".join(out)\n\n\nCONVO_SYSTEM = (\n    "You are the AI assistant of Mama Tolu Kitchen, a Nigerian restaurant in Abuja. Chat like a warm, friendly server: "\n    "greet back, handle small talk, and answer questions about the menu, plant-based swaps, protein, allergens and cooking. "\n    "Reply in the language the customer writes in (English, Pidgin, Hausa, Yoruba or Igbo). Keep it to 3 sentences or fewer, plain text. "\n    "Your main job: meat is expensive, so help people who cannot afford it or do not eat it find a plant-based swap with the SAME protein for less. "\n    "For any price, protein, saving or allergen use ONLY the MENU data given; never invent numbers, and say so if the data does not have it. "\n    "When it fits, invite the customer to name a dish (for example \'chicken pepper soup\') or open the Swap and save tab. "\n    "You cannot place orders yourself. Give no medical advice: for allergies, say the recipe data lists allergens but they should confirm with staff. "\n    "If asked about something unrelated, answer in one friendly sentence and steer back to food.")\n\n\ndef converse(message, history, state):\n    """A natural conversation grounded in the real menu. Returns None if no AI is switched on or it fails."""\n    msgs = [{"role": h["role"], "content": h["content"]} for h in (history or [])[-6:] if h.get("role") in ("user", "assistant")]\n    msgs.append({"role": "user", "content": f"{message}\\n\\nMENU (prices in naira):\\n{menu_brief()}"})\n    try:\n        return llm(CONVO_SYSTEM, msgs, os.getenv("ANSWER_MODEL", "claude-sonnet-5-5"), 300)\n    except Exception as e:\n        print("converse failed:", e)\n        return None\n\n\n'

OLD_ROUTE = '@app.post("/chat")\ndef chat(req: Chat):'
OLD_SMALL_NEW = """    t = smalltalk(req.message)  # hi / thanks / what can you do
    if t or is_chat_question(req.message):
        ai = converse(req.message, req.history, req.state)
        if ai or t:
            return {"answer": ai or t, "recommendations": [], "state": req.state, "mode": provider() if ai else "offline"}
"""
OLD_SMALL = """    t = smalltalk(req.message)  # hi / thanks / what can you do
    if t:
        return {"answer": t, "recommendations": [], "state": req.state, "mode": "offline"}
"""
OLD_UNK = """    if c.pop("unknown", False):
        low = req.message.lower()
"""
NEW_UNK = """    if c.pop("unknown", False):
        ai = converse(req.message, req.history, req.state)
        if ai:
            return {"answer": ai, "recommendations": [], "state": req.state, "mode": provider()}
        low = req.message.lower()
"""

def once(text, old):
    if text.count(old) != 1:
        sys.exit("Could not find this exactly once, so NOTHING was changed:\n" + old)

def swap(text, old, new):
    once(text, old)
    return text.replace(old, new)

# group 1: greetings + feedback + model
if "from smalltalk import smalltalk" not in s:
    s = swap(s, "from make_alt_images import SLUGS",
             "from smalltalk import smalltalk\nfrom feedback import router as feedback_router\nfrom make_alt_images import SLUGS")
    s = swap(s, 'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])',
             'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])\napp.include_router(feedback_router)')
    s = swap(s, 'os.getenv("GEMINI_MODEL", "gemini-2.5-flash")', 'os.getenv("GEMINI_MODEL", "gemini-3.8-flash")')
    s = swap(s, "    prev = req.state\n    if mentions_dish(", OLD_SMALL + "    prev = req.state\n    if mentions_dish(")
    print("1. greetings, feedback and model name: added")
else:
    print("1. already applied")

# group 2: show the real Gemini error
if "detail = e.read()" not in s:
    s = swap(s, '        print("Gemini unavailable, using offline engine:", e)\n',
             '        detail = e.read().decode("utf-8", "ignore")[:300] if hasattr(e, "read") else ""\n'
             '        print("Gemini unavailable, using offline engine:", e, detail)\n')
    print("2. Gemini error details: added")
else:
    print("2. already applied")

# group 3: conversational assistant
if "def converse" not in s:
    s = swap(s, OLD_ROUTE, NEW_FUNCS + OLD_ROUTE)
    s = swap(s, OLD_SMALL, OLD_SMALL_NEW)
    s = swap(s, OLD_UNK, NEW_UNK)
    print("3. conversational assistant: added")
else:
    print("3. already applied")

if s != orig:
    if not pathlib.Path("app.py.before_patches").exists():
        shutil.copy(p, "app.py.before_patches")
    p.write_text(s, encoding="utf-8")
print("Done. Restart uvicorn.")