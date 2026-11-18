"""Riaya companion: plain-language answers about HIS OWN summary, and safe next steps.

Deliberately deterministic. Answers are assembled only from his summary, the evidence map and fixed,
clinician-written safety text, so nothing he types is sent to an outside AI service and the companion
cannot invent a diagnosis, a dose or a probability. Three guardrails run before anything else:
  1. danger words (sudden pain, lump, blood, self-harm) -> urgent help, nothing else;
  2. medicine, dose, steroid-cycle or supplement questions -> no advice, a route to his doctor;
  3. 'am I infertile / what are my chances' -> screening is not a prediction, and what does help.
"""
import re

from . import explain, triage
from .knowledge import graph

AR_NORM = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})


def _norm(s):
    s = re.sub(r"[ًٌٍَُِّْـ]", "", (s or "").lower()).translate(AR_NORM)
    return re.sub(r"\s+", " ", s)


def _has(text, words):
    """Latin words must start a word ('cialis' is not in 'specialist'); Arabic matches inside words because of prefixes like ال."""
    for w in words:
        w = _norm(w)
        if re.match(r"[a-z]", w):
            if re.search(r"(?<![a-z])" + re.escape(w), text):
                return True
        elif w in text:
            return True
    return False


URGENT_WORDS = ["sudden pain", "severe pain", "swollen", "swelling", "lump", "blood in", "bleeding", "kill myself", "suicide",
                "harm myself", "end my life", "hopeless", "can't go on", "ألم مفاجئ", "ألم شديد", "تورم", "ورم", "كتلة", "دم في",
                "انتحار", "اؤذي نفسي", "أؤذي نفسي", "انهي حياتي", "يائس"]
MED_WORDS = ["dose", "dosage", "mg", "clomid", "clomiphene", "hcg", "tamoxifen", "anastrozole", "letrozole", "pct",
             "steroid cycle", "sarm", "trt", "testosterone injection", "testosterone gel", "should i take", "can i take", "supplement", "pill", "tablet",
             "medicine", "medication", "viagra", "cialis", "جرعة", "حبوب", "دواء", "ادوية", "أدوية", "مكمل", "كلوميد", "ابر", "إبر",
             "كورس", "هل اخذ", "هل آخذ"]
CHANCE_WORDS = ["infertile", "sterile", "can i have children", "can i have kids", "chance", "chances", "probability", "percent",
                "%", "will i be able", "serious", "how bad", "dangerous", "diagnose", "diagnosis", "what do i have", "what's wrong with me",
                "تشخيص", "شخصني", "شخّصني", "ما مرضي", "عقيم", "عقم", "هل استطيع الانجاب", "هل أستطيع الإنجاب",
                "احتمال", "نسبة", "خطير", "فرص"]
VISIT_WORDS = ["visit", "specialist said", "doctor said", "the doctor found", "what did", "after my appointment", "my appointment", "follow-up", "follow up",
               "زيارة", "الزيارة", "قال الطبيب", "قال المختص", "ماذا وجد", "بعد الموعد", "موعدي", "المتابعة", "متابعة"]
INTENTS = [
    ("why_next", ["why", "next step", "referral", "doctor", "see a", "specialist", "clinic", "لماذا", "ليش", "الخطوة", "احالة", "إحالة", "طبيب", "عيادة", "مختص"]),
    ("first", ["first", "start", "priority", "most important", "what should i do", "what can i do", "improve", "fix", "change",
               "ابدا", "أبدأ", "اول", "أول", "اهم", "أهم", "ماذا افعل", "ماذا أفعل", "احسن", "أحسن", "تحسين"]),
    ("time", ["how long", "when will", "months", "weeks", "time", "كم من الوقت", "متى", "اشهر", "أشهر", "اسابيع", "أسابيع"]),
    ("tests", ["test", "analysis", "blood", "semen", "lab", "فحص", "تحليل", "مختبر", "دم"]),
    ("wife", ["wife", "partner", "spouse", "couple", "together", "زوجتي", "زوجة", "الزوجة", "معا", "معاً"]),
    ("privacy", ["privacy", "private", "who can see", "who sees", "share", "data", "delete", "خصوصية", "خاص", "من يرى", "مشاركة", "بيانات", "حذف"]),
]

T = {
    "en": {
        "urgent": "This could need help today. If you have sudden or severe pain or swelling in a testicle, go to the nearest emergency department or call 998. "
                  "For a new lump or blood in semen, see a doctor within a few days. If you are thinking of harming yourself, call 800-HOPE (800 4673) now, "
                  "or 999. You are not alone, and talking to someone helps.",
        "med": "I can't advise on medicines, doses, supplements or steroid cycles. That needs a doctor who knows your history. Two things are safe to know: "
               "taking testosterone, steroids or SARMs lowers your own sperm production, and stopping a prescribed medicine on your own can be harmful. "
               "You can send your question to a doctor privately from your summary page.",
        "chance": "Riaya is a screening summary, not a prediction. It cannot tell whether you can have children or put a number on it. "
                  "What it shows is how many everyday signals are present ({tier}), which of them you can change, and whether a doctor should look sooner. "
                  "Most men with signals like these go on to father children, and many of the factors improve within about 3 months of changing habits. "
                  "A semen analysis is the test that actually answers the question.",
        "why_next": "Your suggested next step: {next}\nWhy: {reasons}",
        "why_review": "A licensed doctor checks every specialist referral before it is final.",
        "first": "Start with the change that does the most for you:\n{items}\nIf you made the first two changes, the signals from habits would fall by about {pct}% in our evidence model. "
                 "That is an educational estimate, not a prediction.",
        "time": "Sperm take about 74 days to develop, so changes in habits show in results after about 3 months. Energy and sleep often improve sooner. "
                "A follow-up check is suggested around {due}.",
        "tests": "Tests a doctor may suggest for you: {tests}. {done}One result is never enough on its own: values vary from test to test, so an unusual result is repeated.",
        "tests_done": "You already have: {have}. Bring them so they aren't repeated. ",
        "wife": "Fertility is a couple's question. If you are trying for a child, guidelines advise that both of you are assessed at the same time, not one after the other. "
                "You can give your wife a private link that shows only that you completed the check and the kind of next step, with no answers or results.",
        "privacy": "Right now: {doctor}. {clinic} You can change this, see who opened your record, download everything or delete it from Privacy & sharing.",
        "privacy_doctor_on": "a Riaya doctor may review your summary",
        "privacy_doctor_off": "no doctor can see your summary unless you send it",
        "privacy_clinic": "The clinic you choose sees: {cats}.",
        "about": "{label}: {obs}\nWhy it matters: {rel} (evidence grade {grade}).\nWhat helps: {rec}\nLimits: {lim}",
        "fallback": "I can explain your own summary. Try one of these:",
        "suggest": ["Why this next step?", "What should I change first?", "How long until things improve?", "Which tests might I need?",
                    "What about my wife?", "Who can see my data?"],
        "src_summary": "Your summary", "src_safety": "Riaya safety guidance",
    },
    "ar": {
        "urgent": "قد يحتاج هذا إلى مساعدة اليوم. إذا كان لديك ألم أو تورم مفاجئ أو شديد في الخصية، توجّه إلى أقرب قسم طوارئ أو اتصل بالرقم ٩٩٨. "
                  "إذا لاحظت كتلة جديدة أو دماً في السائل المنوي، راجع طبيباً خلال أيام. إذا كانت لديك أفكار لإيذاء نفسك، اتصل الآن بالرقم 800-HOPE ‏(800 4673) "
                  "أو ٩٩٩. لست وحدك، والحديث مع أحد يساعد.",
        "med": "لا أستطيع تقديم نصيحة عن الأدوية أو الجرعات أو المكملات أو كورسات المنشطات، فهذا يحتاج إلى طبيب يعرف حالتك. من الآمن أن تعرف أمرين: "
               "التستوستيرون والمنشطات وSARMs تخفض إنتاج الحيوانات المنوية لديك، وإيقاف دواء موصوف من تلقاء نفسك قد يضر. "
               "يمكنك إرسال سؤالك إلى طبيب بشكل خاص من صفحة ملخصك.",
        "chance": "رعاية ملخص فحص أولي وليست توقعاً. لا يمكنها أن تحدد إن كنت تستطيع الإنجاب ولا أن تعطي نسبة. "
                  "ما تُظهره هو عدد المؤشرات اليومية الموجودة ({tier})، وأيها يمكنك تغييره، وهل ينبغي أن يراك طبيب قريباً. "
                  "معظم الرجال الذين لديهم مؤشرات مشابهة يُنجبون، وكثير من هذه العوامل يتحسن خلال نحو ٣ أشهر من تغيير العادات. "
                  "تحليل السائل المنوي هو الفحص الذي يجيب فعلاً عن هذا السؤال.",
        "why_next": "خطوتك التالية المقترحة: {next}\nالسبب: {reasons}",
        "why_review": "يراجع طبيب مرخّص كل إحالة إلى مختص قبل اعتمادها.",
        "first": "ابدأ بالتغيير الأكثر فائدة لك:\n{items}\nلو طبّقت أول تغييرين، لانخفضت المؤشرات الناتجة عن العادات بنحو {pct}٪ في نموذج الأدلة. "
                 "هذا تقدير تثقيفي وليس توقعاً.",
        "time": "تحتاج الحيوانات المنوية نحو ٧٤ يوماً لتتكوّن، لذا يظهر أثر تغيير العادات في النتائج بعد نحو ٣ أشهر. وغالباً ما تتحسن الطاقة والنوم أسرع. "
                "يُقترح فحص متابعة في حدود {due}.",
        "tests": "فحوصات قد يقترحها الطبيب: {tests}. {done}نتيجة واحدة لا تكفي وحدها: تتفاوت القيم بين فحص وآخر، لذا تُعاد النتيجة غير المعتادة.",
        "tests_done": "لديك بالفعل: {have}. أحضرها معك حتى لا تُعاد. ",
        "wife": "الخصوبة سؤال يخص الزوجين. إذا كنتما تحاولان الإنجاب، توصي الإرشادات بفحصكما معاً في الوقت نفسه، لا واحداً بعد الآخر. "
                "يمكنك إعطاء زوجتك رابطاً خاصاً يُظهر فقط أنك أكملت الفحص ونوع الخطوة التالية، دون أي إجابات أو نتائج.",
        "privacy": "حالياً: {doctor}. {clinic} يمكنك تغيير ذلك، ومعرفة من فتح سجلك، وتحميل كل شيء أو حذفه من «الخصوصية والمشاركة».",
        "privacy_doctor_on": "يمكن لطبيب في رعاية مراجعة ملخصك",
        "privacy_doctor_off": "لا يستطيع أي طبيب رؤية ملخصك إلا إذا أرسلته",
        "privacy_clinic": "العيادة التي تختارها ترى: {cats}.",
        "about": "{label}: {obs}\nلماذا يهم: {rel} (درجة الدليل {grade}).\nما الذي يساعد: {rec}\nالحدود: {lim}",
        "fallback": "يمكنني شرح ملخصك أنت. جرّب أحد هذه الأسئلة:",
        "suggest": ["لماذا هذه الخطوة؟", "ماذا أغيّر أولاً؟", "متى تتحسن الأمور؟", "ما الفحوصات التي قد أحتاجها؟", "ماذا عن زوجتي؟", "من يمكنه رؤية بياناتي؟"],
        "src_summary": "ملخصك", "src_safety": "إرشادات السلامة في رعاية",
    },
}
TIER = {"en": {"low": "a few signals", "moderate": "some signals", "high": "several signals"},
        "ar": {"low": "مؤشرات قليلة", "moderate": "بعض المؤشرات", "high": "عدة مؤشرات"}}


def _card_for(text, cards, lang):
    g = graph()
    best, score = None, 0
    for c in cards:
        nd = g.nodes[c["node"]]
        words = set(_norm(nd["label"]).replace("/", " ").replace("(", " ").replace(")", " ").split()) | \
            set(_norm(nd.get("label_ar", "")).split()) | {c["node"].replace("_", " ")}
        words = {w for w in words if len(w) > 3}
        hit = sum(1 for w in words if w in text)
        if hit > score:
            best, score = c, hit
    return best


VISIT = {
    "en": {"summary": "What your specialist recorded: {summary}", "tests": "Tests ordered: {tests}.", "tests_left": "Still to do: {left}.",
           "tests_done": "All ordered tests are done. Bring the results to your follow-up.", "plan": "Plan: {plan}", "next": "Next: {next}.",
           "fu": "Follow-up due {date}.", "src": "Your specialist's visit summary", "none": "No visit summary has been recorded yet. "
           "After your specialist visit, the clinic sends it here and your next steps update.",
           "ns_follow": "Follow your specialist's plan: {plan}", "ns_tests": "Do the tests your specialist ordered: {left}",
           "ns_tests_why": "Save the results in Lab results and they are ticked off here, so nothing is repeated.",
           "ns_fu": "Your follow-up is due {date}. Add it to your calendar from My journey.",
           "ns_paused": "You've paused sharing, so your care team can't see your record right now. Turn sharing back on in Privacy when you're ready.",
           "ns_spec_first": "Your specialist's advice comes first. The suggestions below are general and don't replace it."},
    "ar": {"summary": "ما سجّله المختص: {summary}", "tests": "الفحوصات المطلوبة: {tests}.", "tests_left": "المتبقي: {left}.",
           "tests_done": "أُنجزت كل الفحوصات المطلوبة. أحضر نتائجها إلى المتابعة.", "plan": "الخطة: {plan}", "next": "التالي: {next}.",
           "fu": "موعد المتابعة {date}.", "src": "ملخص زيارة المختص", "none": "لم يُسجَّل ملخص زيارة بعد. بعد زيارة المختص ترسله العيادة إلى هنا وتتحدّث خطواتك التالية.",
           "ns_follow": "اتبع خطة المختص: {plan}", "ns_tests": "أجرِ الفحوصات التي طلبها المختص: {left}",
           "ns_tests_why": "احفظ النتائج في «نتائج المختبر» فتُعلَّم هنا تلقائياً ولا تُعاد.",
           "ns_fu": "موعد متابعتك {date}. أضفه إلى التقويم من «مساري».",
           "ns_paused": "أوقفت المشاركة مؤقتاً، لذا لا يستطيع فريق الرعاية رؤية سجلك الآن. أعد تشغيلها من «الخصوصية» متى كنت مستعداً.",
           "ns_spec_first": "نصيحة المختص تأتي أولاً. الاقتراحات أدناه عامة ولا تحل محلها."},
}


def _date(ts):
    import time as _t
    return _t.strftime("%Y-%m-%d", _t.gmtime(ts))


def _visit_answer(consult, L):
    v = VISIT[L]
    if not consult:
        return v["none"]
    parts = [v["summary"].format(summary=consult["summary"])]
    if consult["tests"]:
        parts.append(v["tests"].format(tests=", ".join(t["name"] for t in consult["tests"])))
        left = [t["name"] for t in consult["tests"] if not t["done"]]
        parts.append(v["tests_left"].format(left=", ".join(left)) if left else v["tests_done"])
    if consult.get("plan"):
        parts.append(v["plan"].format(plan=consult["plan"]))
    parts.append(v["next"].format(next=consult["next_label"]))
    if consult.get("followup_at") and not consult.get("followup_done_at"):
        parts.append(v["fu"].format(date=_date(consult["followup_at"])))
    return "\n".join(parts)


def ask(question, answers, result, view, sharing_prefs, review_on, lang="en", consult=None):
    L = "ar" if lang == "ar" else "en"
    t = T[L]
    q = _norm(question)[:500]
    tr = result["triage"]
    sugg = ([("What did the specialist find?" if L == "en" else "ماذا وجد المختص؟")] if consult else []) + t["suggest"]
    out = lambda kind, text, sources, safety="ok": {"intent": kind, "answer": text, "sources": sources, "safety": safety,
                                                    "suggestions": sugg[:4]}
    if _has(q, URGENT_WORDS):
        return out("urgent", t["urgent"], [{"label": t["src_safety"], "grade": None}], "urgent")
    if _has(q, MED_WORDS):
        return out("medicine", t["med"], [{"label": t["src_safety"], "grade": None}], "redirect")
    if _has(q, CHANCE_WORDS):
        return out("chance", t["chance"].format(tier=TIER[L][tr["tier"]]), [{"label": t["src_summary"], "grade": None}])
    if _has(q, VISIT_WORDS) or (consult and _has(q, ["specialist", "found", "المختص", "وجد"])):
        return out("visit", _visit_answer(consult, L), [{"label": VISIT[L]["src"], "grade": None}] if consult else [])
    cards = explain.cards(result, L)
    card = _card_for(q, cards, L)
    intent = next((name for name, words in INTENTS if _has(q, words)), None)
    if card and intent not in ("why_next", "first", "time", "privacy", "wife"):
        return out("about", t["about"].format(label=card["label"], obs=card["observation"] or "—", rel=card["relevance"] or "—",
                                              grade=card["grade"] or "—", rec=card["recommendation"] or "—",
                                              lim=" ".join(card["limitations"]) or "—"),
                   [{"label": e["text"], "grade": card["grade"]} for e in card["evidence"][:3]])
    if intent == "why_next":
        reasons = "; ".join(r["reason"] for r in tr["reasons"][:3]) or (TIER[L][tr["tier"]])
        text = t["why_next"].format(next=view["next_step"], reasons=reasons)
        if tr["requires_review"]:
            text += "\n" + t["why_review"]
        return out("why_next", text, [{"label": t["src_summary"], "grade": None}])
    if intent == "first":
        items = "\n".join(f"{i}. {p['action']}" for i, p in enumerate(view["plan"][:3], 1)) or "—"
        w = explain.whatif(result, [p["node"] for p in result["plan"][:2]], L)
        return out("first", t["first"].format(items=items, pct=round(w["reduction_pct"])),
                   [{"label": " → ".join(p["why"]["labels"]), "grade": p["why"]["grade"]} for p in view["plan"][:3] if p.get("why")])
    if intent == "time":
        import time as _t
        due = _t.strftime("%Y-%m-%d", _t.gmtime(_t.time() + 90 * 86400))
        return out("time", t["time"].format(due=due), [{"label": "WHO (2021) semen manual; spermatogenesis ~74 days", "grade": "A"}])
    if intent == "tests":
        have = [f"{n} {v}" for n, v, _ in ((result.get("labs") or {}).get("already_done") or [])]
        done = t["tests_done"].format(have=", ".join(have)) if have else ""
        return out("tests", t["tests"].format(tests=", ".join(view["tests"]) or "—", done=done), [{"label": t["src_summary"], "grade": None}])
    if intent == "wife":
        return out("wife", t["wife"], [{"label": "AUA/ASRM 2021 guideline: evaluate both partners together", "grade": "A"}])
    if intent == "privacy":
        from .sharing import LABELS
        cats = ", ".join(LABELS[L][c] for c in sharing_prefs["clinic"])
        return out("privacy", t["privacy"].format(doctor=t["privacy_doctor_on"] if review_on else t["privacy_doctor_off"],
                                                  clinic=t["privacy_clinic"].format(cats=cats)), [{"label": t["src_summary"], "grade": None}])
    if card:
        return ask(card["label"], answers, result, view, sharing_prefs, review_on, lang, consult)
    return {"intent": "fallback", "answer": t["fallback"], "sources": [], "safety": "ok", "suggestions": sugg}


NS = {
    "en": {
        "now_emergency": "Go to an emergency department now, or call 998.",
        "now_mental": "Talk to someone now: call 800-HOPE (800 4673), the UAE mental support line.",
        "review": "A doctor will review your summary, usually within {h} hours. You'll get a private message.",
        "visit": "{msg}", "visit_why": "This is the level of care your answers point to. A doctor confirms it before it is final.",
        "test": "Ask about: {t}", "test_why": "So the first visit can answer the question, not just start it.",
        "bring": "Bring your results so they aren't repeated: {t}", "share": "Share your summary with the clinic using a one-time code.",
        "sleep": "Ask about a home sleep test for snoring and daytime tiredness.", "sleep_why": "Sleep apnoea is common, treatable and lowers testosterone.",
        "mood": "Consider a confidential conversation about stress or mood.", "mood_why": "Stress and low mood affect hormones and are worth support in their own right.",
        "genetic": "Ask about genetic counselling (optional and private).", "genetic_why": "Your answers include a pattern where it can help.",
        "habit_why": "Evidence grade {g}: {path}",
        "plan": "Choose up to three of these as a 12-week plan, with weekly check-ins.",
        "recheck": "Repeat the check in about 3 months to see what changed.", "recheck_why": "Sperm take about 74 days to develop.",
        "dont_stop": "Don't stop a prescribed medicine on your own. Ask your doctor whether a fertility-friendly alternative exists.",
        "dont_t": "Don't start testosterone, steroids, SARMs or 'fertility boosters' to fix this. Testosterone lowers your own sperm production.",
        "dont_online": "Don't rely on one home test or one lab result. Unusual results are repeated before any decision.",
        "net_title": "Get help sooner if any of these happen",
    },
    "ar": {
        "now_emergency": "توجّه إلى قسم الطوارئ الآن أو اتصل بالرقم ٩٩٨.",
        "now_mental": "تحدّث مع أحد الآن: اتصل بخط الدعم النفسي 800-HOPE ‏(800 4673).",
        "review": "سيراجع طبيب ملخصك، عادةً خلال {h} ساعة. ستصلك رسالة خاصة.",
        "visit": "{msg}", "visit_why": "هذا مستوى الرعاية الذي تشير إليه إجاباتك. يؤكده طبيب قبل اعتماده.",
        "test": "اسأل عن: {t}", "test_why": "حتى تجيب الزيارة الأولى عن السؤال، لا أن تبدأه فقط.",
        "bring": "أحضر نتائجك حتى لا تُعاد: {t}", "share": "شارك ملخصك مع العيادة برمز لمرة واحدة.",
        "sleep": "اسأل عن اختبار نوم منزلي بسبب الشخير والتعب النهاري.", "sleep_why": "انقطاع النفس أثناء النوم شائع وقابل للعلاج ويخفض التستوستيرون.",
        "mood": "فكّر في محادثة سرية عن التوتر أو المزاج.", "mood_why": "التوتر وتدني المزاج يؤثران في الهرمونات ويستحقان الدعم لذاتهما.",
        "genetic": "اسأل عن الاستشارة الوراثية (اختيارية وسرية).", "genetic_why": "تتضمن إجاباتك نمطاً قد تفيد فيه.",
        "habit_why": "درجة الدليل {g}: {path}",
        "plan": "اختر حتى ثلاثة منها كخطة لمدة ١٢ أسبوعاً مع متابعة أسبوعية.",
        "recheck": "أعد الفحص بعد نحو ٣ أشهر لترى ما تغيّر.", "recheck_why": "تحتاج الحيوانات المنوية نحو ٧٤ يوماً لتتكوّن.",
        "dont_stop": "لا توقف دواءً موصوفاً من تلقاء نفسك. اسأل طبيبك عن بديل مناسب للخصوبة.",
        "dont_t": "لا تبدأ التستوستيرون أو المنشطات أو SARMs أو «معززات الخصوبة» لعلاج هذا. التستوستيرون يخفض إنتاج الحيوانات المنوية لديك.",
        "dont_online": "لا تعتمد على فحص منزلي واحد أو نتيجة مخبرية واحدة. تُعاد النتائج غير المعتادة قبل أي قرار.",
        "net_title": "اطلب المساعدة أسرع إذا حدث أي مما يلي",
    },
}
NET_AR = {"rf_torsion": "ألم أو تورم مفاجئ وشديد في الخصية: الطوارئ فوراً",
          "rf_lump": "كتلة أو تصلّب جديد في الخصية: طبيب مسالك خلال أيام",
          "rf_hematospermia": "دم مستمر في السائل المنوي: طبيب مسالك خلال أيام",
          "rf_fever_pain": "كيس صفن مؤلم ومتورم مع حمّى أو إفرازات: طبيب اليوم",
          "rf_mood": "أفكار لإيذاء النفس أو يأس: اتصل بـ 800-HOPE الآن"}
NET_EN_ACTION = {"emergency": "emergency department now", "emergency_mental": "call 800-HOPE now", "urgent_urology": "a urologist within days",
                 "same_day_primary": "a doctor today"}


def next_steps(result, view, ref_status, lang="en", consult=None, paused=False):
    """A ladder of safe next steps: now, this month, the next 3 months, things not to do, and when to get help sooner.
    After a specialist visit, his specialist's plan, ordered tests and follow-up lead; general suggestions follow."""
    L = "ar" if lang == "ar" else "en"
    t, tr, g, v = NS[L], result["triage"], graph(), VISIT[L]
    now, soon, later = [], [], []
    if paused:
        now.append({"text": v["ns_paused"], "why": None, "grade": None, "kind": "privacy"})
    if consult:
        if consult.get("plan"):
            now.append({"text": v["ns_follow"].format(plan=consult["plan"]), "why": consult["summary"], "grade": None, "kind": "specialist"})
        left = [x["name"] for x in consult["tests"] if not x["done"]]
        if left:
            now.append({"text": v["ns_tests"].format(left=", ".join(left)), "why": v["ns_tests_why"], "grade": None, "kind": "specialist"})
        if consult.get("followup_at") and not consult.get("followup_done_at"):
            now.append({"text": v["ns_fu"].format(date=_date(consult["followup_at"])), "why": None, "grade": None, "kind": "specialist"})
    if tr["level"] == "emergency":
        now.append({"text": t["now_emergency"], "why": tr["reasons"][0]["reason"] if tr["reasons"] else None, "grade": None, "kind": "urgent"})
    if "mental_health_urgent" in tr["parallel"]:
        now.append({"text": t["now_mental"], "why": None, "grade": None, "kind": "urgent"})
    if tr["level"] not in ("self_care", "emergency") and not consult:
        if tr["requires_review"] and ref_status == "pending_review":
            now.append({"text": t["review"].format(h=tr.get("sla_hours") or 48), "why": None, "grade": None, "kind": "care"})
        soon.append({"text": t["visit"].format(msg=view["next_step"]), "why": t["visit_why"], "grade": None, "kind": "care"})
        if view["tests"]:
            soon.append({"text": t["test"].format(t=", ".join(view["tests"][:4])), "why": t["test_why"], "grade": None, "kind": "test"})
        have = [f"{n} {v}" for n, v, _ in ((result.get("labs") or {}).get("already_done") or [])]
        if have:
            soon.append({"text": t["bring"].format(t=", ".join(have)), "why": None, "grade": None, "kind": "care"})
        soon.append({"text": t["share"], "why": None, "grade": None, "kind": "privacy"})
    if "sleep_study" in tr["parallel"]:
        soon.append({"text": t["sleep"], "why": t["sleep_why"], "grade": "B", "kind": "test"})
    if "mental_health" in tr["parallel"]:
        soon.append({"text": t["mood"], "why": t["mood_why"], "grade": "B", "kind": "care"})
    if "genetic_counselling" in tr["parallel"] or (tr.get("genomic") or {}).get("flag"):
        later.append({"text": t["genetic"], "why": t["genetic_why"], "grade": None, "kind": "care"})
    for p in view["plan"]:
        w = p.get("why") or {}
        soon.append({"text": p["action"], "why": t["habit_why"].format(g=w.get("grade", "—"), path=" → ".join(w.get("labels", []))),
                     "grade": w.get("grade"), "kind": "habit"})
    if view["plan"]:
        soon.append({"text": t["plan"], "why": None, "grade": None, "kind": "plan"})
    later.append({"text": t["recheck"], "why": t["recheck_why"], "grade": "A", "kind": "recheck"})
    dont = [t["dont_stop"], t["dont_t"], t["dont_online"]]
    net = []
    for f in g.red_flags:
        if f["action"] in NET_EN_ACTION:
            net.append(NET_AR.get(f["id"], f["text"]) if L == "ar" else f"{f['text']}: {NET_EN_ACTION[f['action']]}")
    return {"now": now, "soon": soon, "later": later, "dont": dont, "safety_net": {"title": t["net_title"], "items": net},
            "specialist_first": v["ns_spec_first"] if consult else None,
            "tier": tr["tier"], "level": tr["level"], "index_band": triage.tier_of(result["scores"]["subfertility"])}
