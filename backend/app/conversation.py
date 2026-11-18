"""Riaya over WhatsApp (and the in-app WhatsApp-style demo): the quick check as numbered replies.

The phone number is never stored. A salted hash of it keys the conversation state, and the check itself
lives under an anonymous session like any other, reachable through a private link. *delete* erases it all.
"""
import hashlib
import os
import re
import time
import uuid

from . import assessment, db, security

SALT = os.environ.get("RIAYA_WA_SALT", "riaya-wa")
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
T = {
    "en": {"welcome": "Welcome to Riaya, a private men's health check. No app, no name, about 3 minutes.\nReply *delete* at any time to erase everything, or *restart* to begin again.",
           "menu": "Sorry, I didn't catch that. Send a number from the list.", "num": "Please send a number.",
           "several": "(you can send several, e.g. 1 3)", "top": "Your top opportunities:",
           "link": "Full private summary, IFHAS hand-off and doctor messages:", "erase": "Reply *delete* to erase everything.",
           "done": "Your summary is above. Reply *restart* for a new check or *delete* to erase everything.",
           "deleted": "Everything has been erased. Send any message to start again.", "no": "No problem. Send any message when you're ready."},
    "ar": {"welcome": "أهلاً بك في رعاية، فحص خاص لصحة الرجل. بلا تطبيق ولا اسم، نحو ٣ دقائق.\nأرسل *حذف* في أي وقت لمسح كل شيء، أو *إعادة* للبدء من جديد.",
           "menu": "عذراً، لم أفهم. أرسل رقماً من القائمة.", "num": "أرسل رقماً من فضلك.",
           "several": "(يمكنك إرسال أكثر من رقم، مثل 1 3)", "top": "أهم فرصك:",
           "link": "الملخص الخاص الكامل وتسليم «إفحص» ورسائل الطبيب:", "erase": "أرسل *حذف* لمسح كل شيء.",
           "done": "ملخصك في الأعلى. أرسل *إعادة* لفحص جديد أو *حذف* لمسح كل شيء.",
           "deleted": "تم مسح كل شيء. أرسل أي رسالة للبدء من جديد.", "no": "لا بأس. أرسل أي رسالة عندما تكون مستعداً."},
}
YN = [("yes", "Yes", "نعم"), ("no", "No", "لا")]
STEPS = [
    {"id": "consent_review", "en": "If something needs a doctor, may a licensed doctor review your summary? You still get it if you say no.",
     "ar": "إذا احتاج الأمر إلى طبيب، هل تسمح لطبيب مرخّص بمراجعة ملخصك؟ ستحصل عليه حتى لو رفضت.", "opts": YN},
    {"id": "age", "num": (18, 80), "en": "How old are you?", "ar": "كم عمرك؟"},
    {"id": "height_cm", "num": (130, 220), "skip": True, "en": "Height in cm? (or 'skip')", "ar": "طولك بالسنتيمتر؟ (أو «تخطي»)"},
    {"id": "weight_kg", "num": (40, 250), "skip": True, "en": "Weight in kg? (or 'skip')", "ar": "وزنك بالكيلوغرام؟ (أو «تخطي»)"},
    {"id": "reason", "multi": True, "en": "What brings you here?", "ar": "ما الذي جاء بك؟",
     "opts": [("general", "General check", "فحص عام"), ("future", "Planning ahead", "تخطيط للمستقبل"),
              ("trying", "Trying for a child now", "نحاول الإنجاب الآن"), ("fitness", "Energy / fitness", "الطاقة / اللياقة")]},
    {"id": "months_trying", "num": (0, 240), "when": lambda a: "trying" in (a.get("reason") or []),
     "en": "How many months have you been trying?", "ar": "منذ كم شهراً وأنتم تحاولون؟"},
    {"id": "smoking", "en": "Cigarettes or vaping?", "ar": "السجائر أو السجائر الإلكترونية؟",
     "opts": [("never", "Never", "أبداً"), ("former", "I stopped", "أقلعت"), ("occasional", "Sometimes", "أحياناً"), ("daily", "Daily", "يومياً")]},
    {"id": "waterpipe", "en": "Shisha, midwakh or dokha?", "ar": "الشيشة أو المدواخ أو الدوخة؟",
     "opts": [("never", "Never", "أبداً"), ("monthly", "Now and then", "أحياناً"), ("weekly", "Weekly", "أسبوعياً"), ("daily", "Daily", "يومياً")]},
    {"id": "aas", "en": "No judgement: testosterone, steroids or SARMs for the gym or any reason?",
     "ar": "بلا أحكام: هل استخدمت التستوستيرون أو المنشطات أو SARMs للنادي أو لأي سبب؟",
     "opts": [("never", "Never", "أبداً"), ("past_old", "Over a year ago", "قبل أكثر من سنة"), ("past_recent", "In the last year", "خلال السنة الماضية"),
              ("current", "Currently", "حالياً"), ("skip", "Prefer not to say", "أفضّل عدم الإجابة")]},
    {"id": "sitting_h", "num": (0, 20), "en": "Hours sitting on a normal day (desk + car + sofa)?", "ar": "كم ساعة تجلس في يوم عادي (مكتب + سيارة + أريكة)؟"},
    {"id": "sleep_h", "num": (2, 14), "en": "Hours you actually sleep on a typical night?", "ar": "كم ساعة تنام فعلياً في ليلة عادية؟"},
    {"id": "snore", "en": "Loud snoring, or has anyone seen you stop breathing in sleep?", "ar": "شخير عالٍ، أو هل رآك أحد تتوقف عن التنفس أثناء النوم؟",
     "opts": [("yes", "Yes", "نعم"), ("no", "No", "لا"), ("unsure", "Not sure", "لست متأكداً")]},
    {"id": "tired", "en": "Often sleepy during the day?", "ar": "هل تشعر بالنعاس غالباً خلال النهار؟", "opts": YN},
    {"id": "underwear", "en": "Usual underwear?", "ar": "ملابسك الداخلية عادةً؟",
     "opts": [("loose", "Loose (boxers, sirwal)", "فضفاضة (بوكسر، سروال)"), ("mixed", "Mix", "مختلطة"), ("tight", "Tight (briefs)", "ضيقة")]},
    {"id": "phq1", "en": "Last 2 weeks, how often have you had little interest or pleasure in things?",
     "ar": "خلال الأسبوعين الماضيين، كم مرة شعرت بقلة الاهتمام أو المتعة؟",
     "opts": [(0, "Not at all", "إطلاقاً"), (1, "Some days", "بعض الأيام"), (2, "More than half the days", "أكثر من نصف الأيام"), (3, "Nearly every day", "تقريباً كل يوم")]},
    {"id": "phq2", "en": "And how often have you felt down or hopeless?", "ar": "وكم مرة شعرت بالإحباط أو اليأس؟",
     "opts": [(0, "Not at all", "إطلاقاً"), (1, "Some days", "بعض الأيام"), (2, "More than half the days", "أكثر من نصف الأيام"), (3, "Nearly every day", "تقريباً كل يوم")]},
    {"id": "red_flags", "multi": True, "en": "Right now, any of these? (or 'none')", "ar": "الآن، هل لديك أي مما يلي؟ (أو «لا شيء»)",
     "opts": [("none", "None", "لا شيء"), ("rf_torsion", "Sudden testicle pain or swelling", "ألم أو تورم مفاجئ في الخصية"), ("rf_lump", "A new lump", "كتلة جديدة"),
              ("rf_hematospermia", "Blood in semen", "دم في السائل المنوي"), ("rf_mood", "Thoughts of harming myself", "أفكار لإيذاء النفس")]},
]
DELETE = {"delete", "erase", "stop", "حذف", "امسح", "مسح"}
RESTART = {"restart", "reset", "start again", "إعادة", "اعادة", "من جديد"}
SKIP = {"skip", "تخطي", "تخطى", "none", "لا شيء"}


def key_for(phone):
    return hashlib.sha256((SALT + phone).encode()).hexdigest()


def _load(c, key):
    r = c.execute("SELECT state FROM wa_sessions WHERE key=?", (key,)).fetchone()
    return security.unseal(r["state"]) if r else None


def _save(c, key, st):
    c.execute("INSERT OR REPLACE INTO wa_sessions VALUES (?,?,?)", (key, security.seal(st), time.time()))


def _q(step, lang):
    lines = [step[lang]]
    for i, o in enumerate(step.get("opts", []), 1):
        lines.append(f"{i}. {o[2] if lang == 'ar' else o[1]}")
    if step.get("multi"):
        lines.append(T[lang]["several"])
    return "\n".join(lines)


def _next(st):
    while st["step"] < len(STEPS) and STEPS[st["step"]].get("when") and not STEPS[st["step"]]["when"](st["answers"]):
        st["step"] += 1
    return STEPS[st["step"]] if st["step"] < len(STEPS) else None


def _num(text):
    m = re.search(r"\d+(?:[.,]\d+)?", text.translate(AR_DIGITS))
    return float(m.group(0).replace(",", ".")) if m else None


def _create_session(c, st):
    token, uid, aid = security.new_token(), str(uuid.uuid4()), str(uuid.uuid4())
    now = time.time()
    c.execute("INSERT INTO users VALUES (?,?,?,?)", (uid, security.token_hash(token), now, st["lang"]))
    for p, v in (("core", 1), ("clinician_review", int(st["review"])), ("wearables", 0), ("research", 0)):
        c.execute("INSERT INTO consents VALUES (?,?,?,?,?)", (uid, p, v, "1.0", now))
    c.execute("INSERT INTO assessments (id, user_id, started_at, channel) VALUES (?,?,?,?)", (aid, uid, now, "whatsapp"))
    st.update(token=token, user_id=uid, aid=aid)


def _finish(c, st, base_url, submit):
    a = dict(st["answers"])
    a["red_flags"] = [x for x in a.get("red_flags", []) if x != "none"]
    c.execute("UPDATE assessments SET answers=? WHERE id=?", (security.seal(a), st["aid"]))
    c.commit()
    view = submit(st["aid"], st["user_id"], st["lang"])
    L = st["lang"]
    msg = [f"*{view['next_step']}*", view["summary"]]
    if view["plan"]:
        msg += ["", T[L]["top"]] + [f"{i}. {p['action']}" for i, p in enumerate(view["plan"], 1)]
    msg += ["", view["disclaimer"], "", f"{T[L]['link']} {base_url.rstrip('/')}/index.html#t={st['token']}&a={st['aid']}", "", T[L]["erase"]]
    st["done"] = True
    return "\n".join(msg)


def handle(key, text, base_url, submit, erase):
    """Returns the list of replies. `submit(aid, user_id, lang)` runs the assessment; `erase(user_id)` deletes a person."""
    text = (text or "").strip()
    low = text.lower()
    with db.tx() as c:
        st = _load(c, key)
        if low in DELETE:
            if st and st.get("user_id"):
                erase(st["user_id"])
            c.execute("DELETE FROM wa_sessions WHERE key=?", (key,))
            lang = (st or {}).get("lang") or ("ar" if re.search(r"[؀-ۿ]", text) else "en")
            return [T[lang]["deleted"]]
        if not st or low in RESTART:
            lang = (st or {}).get("lang")
            if not lang:
                _save(c, key, {"stage": "lang"})
                return ["Riaya | رعاية\n1. العربية\n2. English"]
            st = {"stage": "q", "lang": lang, "step": 0, "answers": {}}
            _save(c, key, st)
            return [T[lang]["welcome"], _q(_next(st), lang)]
        if st["stage"] == "lang":
            n = _num(low)
            lang = "ar" if (n == 1 or "عرب" in low) else "en" if (n == 2 or "eng" in low) else None
            if not lang:
                return ["Riaya | رعاية\n1. العربية\n2. English"]
            st = {"stage": "q", "lang": lang, "step": 0, "answers": {}}
            _save(c, key, st)
            return [T[lang]["welcome"], _q(_next(st), lang)]
        L = st["lang"]
        if st.get("done"):
            return [T[L]["done"]]
        step = _next(st)
        if step.get("num"):
            if low in SKIP and step.get("skip"):
                value = None
            else:
                n = _num(low)
                lo, hi = step["num"]
                if n is None or not lo <= n <= hi:
                    return [T[L]["num"], _q(step, L)]
                value = n
        else:
            opts = step["opts"]
            picks = [int(x) for x in re.findall(r"\d+", low.translate(AR_DIGITS))]
            if step["id"] == "red_flags" and low in SKIP:
                picks = [1]
            if not picks or any(not 1 <= p <= len(opts) for p in picks) or (len(picks) > 1 and not step.get("multi")):
                return [T[L]["menu"], _q(step, L)]
            vals = [opts[p - 1][0] for p in picks]
            value = vals if step.get("multi") else vals[0]
        if step["id"] == "consent_review":
            st["review"] = value == "yes"
            _create_session(c, st)
        elif value is not None and value != "skip":
            st["answers"][step["id"]] = value
        st["step"] += 1
        nxt = _next(st)
        if nxt:
            _save(c, key, st)
            return [_q(nxt, L)]
        _save(c, key, st)
    with db.tx() as c:
        out = _finish(c, st, base_url, submit)
        _save(c, key, st)
    return [out]


def twiml(replies):
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response>" + "".join(f"<Message>{esc(r)}</Message>" for r in replies) + "</Response>"


def twilio_valid(url, params, signature):
    """Checks X-Twilio-Signature when RIAYA_TWILIO_AUTH_TOKEN is set."""
    token = os.environ.get("RIAYA_TWILIO_AUTH_TOKEN")
    if not token:
        return True
    import base64
    import hmac
    data = url + "".join(k + params[k] for k in sorted(params))
    expected = base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(expected, signature or "")
