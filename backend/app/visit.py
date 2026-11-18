"""Getting the most out of the specialist visit, and hearing how it went.

prepare(): a checklist built from HIS summary, the tests his referral asks for and the results he already has,
so the first visit answers the question instead of just starting it. Sample-collection advice follows the
WHO 2021 laboratory manual; the morning testosterone advice follows the Endocrine Society 2018 guideline.

Visit feedback: three short ratings after a visit. Only k-anonymised averages per clinic ever leave this module.
"""
from .knowledge import graph

SEMEN_WORDS = ("semen", "sperm", "سائل", "منوي")
HORMONE_WORDS = ("testosterone", "hormone", "تستوستيرون", "هرمون")

T = {
    "en": {
        "bring_title": "Bring with you", "before_title": "Before the visit", "ask_title": "Questions worth asking", "rights_title": "Your choices at the visit",
        "bring_results": "Results you already have, so they aren't repeated: {r}",
        "bring_meds": "A list of every medicine, supplement and gym product you take, including anything you stopped in the last year.",
        "bring_code": "Your handover code, if the clinic hasn't opened your referral yet.",
        "bring_wife": "Your wife, if she's comfortable coming. A couple's fertility visit checks you both at the same time.",
        "semen": "For a semen analysis: no ejaculation for 2 to 7 days before. Collect at the lab if you can; if at home, deliver it within an hour, kept close to the body.",
        "semen_fever": "Tell the lab if you've had a fever in the last 3 months. It can lower results for a while, so the test may be repeated later.",
        "hormone": "For testosterone: a blood test before 10–11 am, ideally after fasting. Levels are highest in the morning.",
        "write_down": "Write down what worries you most, so it gets asked even if the visit feels rushed.",
        "q_driver": "Could {d} be affecting this, and what would help most?",
        "q_tests": "Which tests do I need, and can any results I already have be used?",
        "q_next": "What happens after the results, and when should I come back?",
        "q_wife": "Should my wife be assessed at the same time?",
        "q_who": "Who will see my results, and will anything be shared without asking me?",
        "r_doctor": "You can ask for a male doctor.", "r_share": "You choose what the clinic sees in Riaya, and you can change it any time.",
        "r_stop": "You can stop the examination or ask questions at any point.",
        "r_lang": "You can ask for the visit in Arabic.",
    },
    "ar": {
        "bring_title": "أحضر معك", "before_title": "قبل الزيارة", "ask_title": "أسئلة تستحق أن تسألها", "rights_title": "خياراتك في الزيارة",
        "bring_results": "النتائج التي لديك حتى لا تُعاد: {r}",
        "bring_meds": "قائمة بكل دواء ومكمل ومنتج رياضي تتناوله، بما في ذلك ما أوقفته خلال السنة الماضية.",
        "bring_code": "رمز التسليم، إن لم تكن العيادة قد فتحت إحالتك بعد.",
        "bring_wife": "زوجتك إن كانت مرتاحة للحضور. زيارة الخصوبة للزوجين تفحصكما معاً في الوقت نفسه.",
        "semen": "لتحليل السائل المنوي: امتنع عن القذف من يومين إلى ٧ أيام قبله. اجمع العينة في المختبر إن أمكن؛ وإن كانت في المنزل فسلّمها خلال ساعة مع إبقائها قريبة من الجسم.",
        "semen_fever": "أخبر المختبر إن أصبت بحمّى خلال الأشهر الثلاثة الماضية. قد تخفض النتائج مؤقتاً، فيُعاد الفحص لاحقاً.",
        "hormone": "للتستوستيرون: فحص دم قبل الساعة ١٠–١١ صباحاً، ويفضل صائماً. المستويات أعلى في الصباح.",
        "write_down": "اكتب أكثر ما يقلقك، حتى تسأل عنه ولو بدت الزيارة سريعة.",
        "q_driver": "هل يمكن أن يؤثر {d} في هذا، وما الذي يساعد أكثر؟",
        "q_tests": "ما الفحوصات التي أحتاجها، وهل يمكن استخدام نتائج لدي؟",
        "q_next": "ماذا يحدث بعد النتائج، ومتى أعود؟",
        "q_wife": "هل ينبغي أن تُقيَّم زوجتي في الوقت نفسه؟",
        "q_who": "من سيرى نتائجي، وهل سيُشارك شيء دون سؤالي؟",
        "r_doctor": "يمكنك طلب طبيب رجل.", "r_share": "أنت تختار ما تراه العيادة في رعاية، ويمكنك تغييره في أي وقت.",
        "r_stop": "يمكنك إيقاف الفحص أو طرح الأسئلة في أي لحظة.",
        "r_lang": "يمكنك طلب أن تكون الزيارة بالعربية.",
    },
}


def _any(texts, words):
    return any(w in (x or "").lower() for x in texts for w in words)


def prepare(result, view, answers, level, have, consult=None, lang="en"):
    L = "ar" if lang == "ar" else "en"
    t, g = T[L], graph()
    tests = list(view.get("tests") or []) + [x["name"] for x in (consult or {}).get("tests", []) if not x["done"]]
    bring = []
    if have:
        bring.append(t["bring_results"].format(r=", ".join(have)))
    bring.append(t["bring_meds"])
    bring.append(t["bring_code"])
    if level == "fertility_services":
        bring.append(t["bring_wife"])
    before = []
    if _any(tests, SEMEN_WORDS):
        before.append({"text": t["semen"], "source": "WHO laboratory manual, 6th ed. (2021)"})
        before.append({"text": t["semen_fever"], "source": "WHO laboratory manual, 6th ed. (2021)"})
    if _any(tests, HORMONE_WORDS) or "adam_positive" in (result.get("instruments") or {}):
        before.append({"text": t["hormone"], "source": "Endocrine Society guideline (2018)"})
    before.append({"text": t["write_down"], "source": None})
    lab = lambda n: g.nodes[n].get("label_ar" if L == "ar" else "label", g.nodes[n]["label"])
    drivers = [k for k, v in result.get("attribution", {}).items() if v > 0 and g.nodes[k].get("modifiable")][:2]
    ask = [t["q_driver"].format(d=lab(d).lower() if L == "en" else lab(d)) for d in drivers] + [t["q_tests"], t["q_next"]]
    if level == "fertility_services" or "trying" in (answers.get("reason") or []):
        ask.append(t["q_wife"])
    ask.append(t["q_who"])
    rights = [t["r_share"], t["r_stop"], t["r_lang"]]
    if answers.get("pref_clinician") == "male" or L == "ar":
        rights.insert(0, t["r_doctor"])
    return {"sections": [{"title": t["bring_title"], "items": [{"text": x, "source": None} for x in bring]},
                         {"title": t["before_title"], "items": before},
                         {"title": t["ask_title"], "items": [{"text": x, "source": None} for x in ask]},
                         {"title": t["rights_title"], "items": [{"text": x, "source": None} for x in rights]}]}


def clinic_quality(c, k):
    """Average visit ratings per clinic, only for clinics with at least k ratings."""
    rows = c.execute("""SELECT f.provider_id, p.name_en, COUNT(*) n, AVG(f.respect) respect, AVG(f.privacy) privacy, AVG(f.explained) explained,
                               AVG(f.recommend) recommend, AVG(f.wait_days) wait FROM visit_feedback f JOIN providers p ON p.id=f.provider_id
                        GROUP BY f.provider_id""").fetchall()
    out = []
    for r in rows:
        if r["n"] < k:
            out.append({"clinic": r["name_en"], "suppressed": True})
        else:
            out.append({"clinic": r["name_en"], "n": r["n"], "respect": round(r["respect"], 1), "privacy": round(r["privacy"], 1),
                        "explained": round(r["explained"], 1), "recommend_pct": round(100 * r["recommend"]),
                        "avg_wait_days": round(r["wait"], 1) if r["wait"] is not None else None})
    return sorted(out, key=lambda x: x.get("n", 0), reverse=True)
