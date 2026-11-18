"""Explanations: for every finding, what was seen, why it matters, what to do, how strong the evidence
is and what the limits are. Plus data coverage, contradictions between sources, a personal baseline,
an educational what-if, and what the devices alone suggest."""
from . import features, plan, triage
from .knowledge import graph

END = {"en": "fertility potential", "ar": "القدرة على الإنجاب"}
LIMITS = {
    "questionnaire": ("Based on your own answers.", "مبني على إجاباتك."),
    "watch": ("Consumer wearables estimate this. They do not diagnose a condition.", "الأجهزة القابلة للارتداء تقدّر هذا ولا تشخّص حالة."),
    "cgm": ("Glucose-sensor patterns are for screening, not a diabetes diagnosis.", "أنماط جهاز قياس السكر للفحص الأولي، وليست تشخيصاً للسكري."),
    "lab": ("One result. Values vary from test to test, so a repeat confirms it.", "نتيجة واحدة. تتفاوت القيم بين فحص وآخر، والإعادة تؤكدها."),
    "semen": ("One result. Values vary from test to test, so a repeat confirms it.", "نتيجة واحدة. تتفاوت القيم بين فحص وآخر، والإعادة تؤكدها."),
    "ADAM": ("Very sensitive but not specific; a blood test is needed.", "حساس جداً لكنه غير نوعي؛ يلزم فحص دم."),
    "STOP-Bang": ("A screening questionnaire. Many people who score high do not have sleep apnoea.",
                  "استبيان للفحص الأولي. كثير ممن يحصلون على درجة عالية لا يعانون من انقطاع النفس أثناء النوم."),
    "PSS-4": ("A short stress questionnaire; it reflects the last month only.", "استبيان قصير للتوتر؛ يعكس الشهر الأخير فقط."),
    "PHQ-2": ("A short screening questionnaire, not a diagnosis.", "استبيان قصير للفحص الأولي وليس تشخيصاً."),
    "AUDIT-C": ("A short screening questionnaire, not a diagnosis.", "استبيان قصير للفحص الأولي وليس تشخيصاً."),
}
OUTCOME_ADVICE = {
    "low_count": ("A lab semen analysis confirms or rules this out.", "تحليل السائل المنوي في المختبر يؤكد هذا أو ينفيه."),
    "low_motility": ("A lab semen analysis confirms or rules this out.", "تحليل السائل المنوي في المختبر يؤكد هذا أو ينفيه."),
    "abn_morph": ("A lab semen analysis confirms or rules this out.", "تحليل السائل المنوي في المختبر يؤكد هذا أو ينفيه."),
    "azoospermia": ("A specialist should review this with a repeat test.", "يجب أن يراجع مختص هذا مع إعادة الفحص."),
    "dna_frag": ("A specialist can advise whether a DNA fragmentation test would help.", "يمكن للمختص تحديد ما إذا كان فحص تفتت الحمض النووي مفيداً."),
}
WEAK = ("The research behind this link is limited (grade {g}). Treat it as a possibility, not a fact.",
        "الأبحاث وراء هذا الرابط محدودة (درجة {g}). اعتبره احتمالاً وليس حقيقة.")
NOT_MOD = ("This can't be changed, but knowing it helps your doctor.", "لا يمكن تغيير هذا، لكن معرفته تساعد طبيبك.")
STATUS = {"measured": ("Measured", "مُقاس"), "screened": ("Screened with a questionnaire", "فُحص باستبيان"),
          "reported": ("From your answers", "من إجاباتك"), "not_answered": ("Not answered", "لم تتم الإجابة"),
          "not_measured": ("Not measured yet", "لم يُقس بعد")}
DOMAINS = [("body", "Weight and waist", "الوزن ومحيط الخصر"), ("sleep", "Sleep", "النوم"), ("activity", "Activity", "النشاط"),
           ("substances", "Smoking, shisha, alcohol, steroids", "التدخين والشيشة والكحول والمنشطات"),
           ("breathing", "Breathing during sleep", "التنفس أثناء النوم"), ("mood", "Mood and stress", "المزاج والتوتر"),
           ("metabolic", "Blood sugar", "سكر الدم"), ("hormones", "Hormones", "الهرمونات"), ("semen", "Semen analysis", "تحليل السائل المنوي")]


def _i(lang):
    return 1 if lang == "ar" else 0


def label(n, lang):
    nd = graph().nodes[n]
    return nd.get("label_ar", nd["label"]) if lang == "ar" else nd["label"]


def relevance(node, lang):
    g = graph()
    ps = g.paths(node)
    if not ps:
        return None, None, []
    p = ps[0]
    labels = [label(n, lang) for n in p["nodes"][:-1]] + [END[lang]]
    return " → ".join(labels), p["grade"], p["refs"]


def cards(result, lang="en"):
    g, out = graph(), []
    actions = {p["node"]: p for p in plan.build({k: 1 for k in result["attribution"]}, g, result["inputs"], limit=999)[0]}
    for node, contribution in result["attribution"].items():
        if contribution <= 0:
            continue
        nd = g.nodes[node]
        prov = result["provenance"].get(node, [])
        sources = []
        for p in prov:
            if p["source"] not in sources:
                sources.append(p["source"])
        rel, grade, refs = relevance(node, lang)
        if node in actions:
            rec = actions[node]["action_ar" if lang == "ar" else "action_en"]
        elif node in OUTCOME_ADVICE:
            rec = OUTCOME_ADVICE[node][_i(lang)]
        elif nd.get("modifiable") is False:
            rec = NOT_MOD[_i(lang)]
        else:
            rec = None
        lim = []
        for s in sources:
            text = LIMITS.get(s, LIMITS["questionnaire"])[_i(lang)]
            if text not in lim:
                lim.append(text)
        if grade in ("C", "D"):
            lim.append(WEAK[_i(lang)].format(g=grade))
        out.append({"node": node, "label": label(node, lang), "value": result["inputs"].get(node), "contribution": contribution,
                    "observation": "; ".join(p["reason"] for p in prov), "sources": sources, "relevance": rel, "grade": grade,
                    "evidence": [{"key": r, "text": g.refs.get(r, r)} for r in refs], "recommendation": rec, "limitations": lim,
                    "modifiable": nd.get("modifiable", True) is not False and node not in OUTCOME_ADVICE})
    return out


def coverage(answers, wearable, semen, labs, lang="en"):
    a, w, lv = answers or {}, wearable or {}, (labs or {}).get("values") or {}
    has = lambda *ks: any(a.get(k) not in (None, "", [], "skip") for k in ks)
    st = {
        "body": "reported" if has("weight_kg", "waist_cm") else "not_answered",
        "sleep": "measured" if w.get("sleep_avg_h") is not None else "reported" if has("sleep_h") else "not_answered",
        "activity": "measured" if w.get("steps_avg") is not None else "reported" if has("sitting_h", "exercise_days") else "not_answered",
        "substances": "reported" if has("smoking", "waterpipe", "audit1", "aas") else "not_answered",
        "breathing": "measured" if w.get("spo2_low_nights") is not None else "screened" if has("snore", "tired") else "not_answered",
        "mood": "reported" if has("pss1", "phq1") else "not_answered",
        "metabolic": "measured" if (w.get("glucose_readings") or lv.get("hba1c") is not None) else "reported" if has("diabetes") else "not_answered",
        "hormones": "measured" if any(lv.get(k) is not None for k in ("testosterone", "fsh", "lh")) else "screened" if has("adam1") else "not_answered",
        "semen": "measured" if semen else "not_measured",
    }
    return [{"domain": d, "label": ar if lang == "ar" else en, "status": st[d], "status_text": STATUS[st[d]][_i(lang)]} for d, en, ar in DOMAINS]


def contradictions(answers, wearable, labs, lang="en"):
    a, w, out = answers or {}, wearable or {}, []
    lv = (labs or {}).get("values") or {}
    ar = lang == "ar"
    try:
        said = float(a.get("sleep_h")) if a.get("sleep_h") is not None else None
    except (TypeError, ValueError):
        said = None
    if said is not None and w.get("sleep_avg_h") is not None and abs(said - w["sleep_avg_h"]) >= 1.5:
        out.append({"severity": "info", "text": (f"قلت إنك تنام نحو {said:g} ساعات، بينما تُظهر ساعتك {w['sleep_avg_h']:.1f}. اعتمدنا قياس الساعة."
                                                 if ar else f"You said you sleep about {said:g} h, your watch shows {w['sleep_avg_h']:.1f} h. We used the watch.")})
    ex = a.get("exercise_days")
    if isinstance(ex, (int, float)) and ex >= 4 and w.get("steps_avg") is not None and w["steps_avg"] < 4000:
        out.append({"severity": "info", "text": ("ذكرت نشاطاً معظم الأيام، لكن متوسط خطواتك أقل من ٤٠٠٠. قد لا تحمل الساعة دائماً."
                                                 if ar else "You reported exercise most days, but your steps average under 4,000. The watch may not always be worn.")})
    t = lv.get("testosterone")
    if t is not None and lv.get("testosterone_unit") == "ng/dL":
        t = t / 28.84
    if t is not None and t < 8 and not any(a.get(f"adam{i}") == "yes" for i in range(1, 11)) and a.get("adam1"):
        out.append({"severity": "review", "text": ("التستوستيرون منخفض بوضوح رغم عدم وجود أعراض في الاستبيان. يحتاج إلى مراجعة طبيب."
                                                   if ar else "Testosterone is clearly low although the symptom questionnaire was negative. A doctor should review this.")})
    if a.get("aas") == "never" and t is not None and t < 8 and lv.get("lh") is not None and lv["lh"] < 1.5:
        out.append({"severity": "review", "text": ("انخفاض التستوستيرون مع LH منخفض جداً يشبه نمط استخدام المنشطات رغم الإجابة بـ«أبداً»."
                                                   if ar else "Low testosterone with very low LH matches the pattern seen with steroid use, although the answer was 'never'.")})
    return out


def explain(answers, result, lang="en"):
    w = result.get("wearable") or {}
    return {"cards": cards(result, lang), "coverage": coverage(answers, w, result.get("semen"), result.get("labs"), lang),
            "contradictions": contradictions(answers, w, result.get("labs"), lang), "baseline": w.get("personal_baseline")}


WHATIF_NOTE = {"en": "Signals from habits and health factors only. An educational scenario based on published links, not a prediction of your fertility.",
               "ar": "المؤشرات الناتجة عن العادات والعوامل الصحية فقط. سيناريو تثقيفي مبني على روابط منشورة، وليس توقعاً لخصوبتك."}


def whatif(result, improve, lang="en"):
    g = graph()
    mod = {k: v for k, v in result["inputs"].items() if g.nodes[k].get("modifiable") and k in g.nodes}
    before = g.propagate(mod)["subfertility"]
    improved = [n for n in improve if n in mod]
    after = g.propagate({k: v for k, v in mod.items() if k not in improved})["subfertility"]
    return {"improved": improved, "before": round(before, 3), "after": round(after, 3),
            "before_tier": triage.tier_of(before), "after_tier": triage.tier_of(after),
            "reduction_pct": round(100 * (before - after) / before, 1) if before else 0.0, "note": WHATIF_NOTE[lang],
            "options": [{"node": k, "label": label(k, lang)} for k in mod]}


PASSIVE = {
    "sleep_loss": ("Your sleep averages under 6 hours. Short sleep is linked to lower testosterone and sperm count.",
                   "متوسط نومك أقل من ٦ ساعات. قلة النوم مرتبطة بانخفاض التستوستيرون وعدد الحيوانات المنوية."),
    "sedentary": ("You average fewer than 5,000 steps a day.", "متوسط خطواتك أقل من ٥٠٠٠ خطوة يومياً."),
    "circadian": ("Your weekend sleep shifts by 2+ hours. This 'social jet lag' is linked to poorer semen quality.",
                  "يتغير نومك في عطلة الأسبوع بساعتين أو أكثر. هذا «الإرهاق الاجتماعي» مرتبط بجودة أقل للسائل المنوي."),
    "caffeine_late": ("Caffeine is logged late in the day on most days.", "يُسجَّل الكافيين في وقت متأخر من اليوم في معظم الأيام."),
    "glycaemic_spikes": ("Your glucose often rises above 140 mg/dL at night.", "يرتفع السكر لديك غالباً فوق ١٤٠ ملغ/دل ليلاً."),
    "osa": ("Your oxygen dipped below 90% on several nights. That can be a sign of sleep apnoea, which is common, treatable and affects hormones.",
            "انخفض الأكسجين لديك تحت ٩٠٪ في عدة ليالٍ. قد تكون هذه علامة على انقطاع النفس أثناء النوم، وهو شائع وقابل للعلاج ويؤثر في الهرمونات."),
}
PASSIVE_ORDER = ["sleep_loss", "sedentary", "circadian", "caffeine_late", "glycaemic_spikes", "osa"]
SUMMARY_KEYS = ["sleep_avg_h", "steps_avg", "social_jetlag_h", "spo2_low_nights", "night_glucose_high_pct",
                "late_caffeine_days_per_week", "resting_hr_avg", "hrv_sdnn_avg"]


def passive(wearable, lang="en"):
    w = wearable or {}
    inputs, prov, _ = features.build_inputs({}, w, None, None)
    findings = []
    for n in PASSIVE_ORDER:
        if inputs.get(n, 0) >= 0.2 and (n != "osa" or w.get("spo2_low_nights", 0) >= 3):
            _, grade, _ = relevance(n, lang)
            findings.append({"node": n, "text": PASSIVE[n][_i(lang)], "label": label(n, lang), "evidence": grade,
                             "sources": [p["reason"] for p in prov.get(n, [])]})
    return {"summary": {k: w[k] for k in SUMMARY_KEYS if w.get(k) is not None}, "findings": findings}
