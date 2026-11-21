"""Answer greetings, thanks, 'how are you' and 'what can you do' before the food engine or the AI runs.
Works with no API key. app.py calls:  t = smalltalk(req.message)"""
import re

_G = r"(hi+|hello+|hey+|good (morning|afternoon|evening)|how far|how you dey|sannu|ina kwana|bawo|e kaaro|nnoo|kedu|what'?s up|sup)"
HELP = ("I can help you swap meat for cheaper plant-based proteins. Try: "
        "\"beef suya under ₦650\", \"shawarma swap, 200 plates a week\" or \"chicken pepper soup, high protein\".")

# short ways people write "you"
_SLANG = {"u": "you", "ur": "your", "r": "are", "wassup": "whats up", "wsup": "whats up"}


def _clean(msg: str) -> str:
    words = re.sub(r"[^a-z' ]", " ", msg.lower()).split()
    return " ".join(_SLANG.get(w, w) for w in words).replace("'", "")

"""Answer greetings, thanks, 'how are you' and 'who are you' instantly, before the food engine or the AI runs.
Replies are short and friendly and never list dishes. Works with no API key.
app.py calls:  t = smalltalk(req.message)"""
import random, re

_G = r"(hi+|hello+|hey+|good (morning|afternoon|evening)|how far|how you dey|sannu|ina kwana|bawo|e kaaro|nnoo|kedu|what'?s up|sup)"
_PIDGIN = re.compile(r"\b(how far|how you dey|how body|wetin dey)\b")

GREET = ["Hi! 👋 I'm the Mama Tolu assistant. What can I get for you today?",
         "Hello! 😊 I'm the Mama Tolu assistant. How can I help you today?",
         "Hey there! I'm the Mama Tolu assistant. What can I do for you?"]
GREET_PIDGIN = ["Hey! 👋 I be Mama Tolu assistant. Wetin I fit do for you today?",
                "How far! 😊 I be Mama Tolu assistant. Wetin you wan chop?"]
HOW_ARE_YOU = ["I'm doing great, thanks for asking! 😊 How about you? What can I get for you today?",
               "All good here, thank you! 😊 How are you? What can I help you with?"]
WHO_AM_I = ("I'm the Mama Tolu assistant. I can answer questions about our menu and help you find "
            "cheaper plant-based swaps that keep the same protein. Tell me what you're craving, or how much you'd like to spend.")

# short ways people write words
_SLANG = {"u": "you", "ur": "your", "r": "are", "wassup": "whats up", "wsup": "whats up"}


def _clean(msg: str) -> str:
    words = re.sub(r"[^a-z' ]", " ", msg.lower()).split()
    return " ".join(_SLANG.get(w, w) for w in words).replace("'", "")


def smalltalk(msg: str):
    m = _clean(msg)
    if not m or len(m.split()) > 7:
        return None
    if re.fullmatch(_G.replace("'", "") + r"( there| o| oh| please| you)?", m):
        return random.choice(GREET_PIDGIN if _PIDGIN.search(m) else GREET)
    if re.search(r"\b(how are you|how you doing|how are things|how is it going|hows it going|how do you do|how body|how you dey)\b", m):
        return random.choice(HOW_ARE_YOU)
    if re.search(r"\b(thanks|thank you|thx|nagode|e se|daalu)\b", m):
        return "You're welcome! Is there anything else I can help you with?"
    if re.search(r"\b(who are you|what are you|what can you do|what do you do|help)\b", m):
        return WHO_AM_I
    if re.fullmatch(r"(ok|okay|cool|nice|great|good|fine|alright|wow)( then| thanks)?", m):
        return "Great! What would you like to get?"
    if re.fullmatch(r"(bye|goodbye|see you|see you later|later)", m):
        return "Bye! Come back anytime. 👋"
    return None