"""Prescriptive and predictive layers on top of the evidence graph.

best_changes(): PRESCRIPTIVE. For each change he could make, the expected drop in his signal load if he made only
    that change (counterfactual through the evidence graph), the strength of the evidence, how hard it is and how long
    it takes to show. Ranked by expected effect x evidence / effort, plus the best set of three chosen together
    (greedy on the combined counterfactual, so overlapping changes aren't double-counted).

projection(): PREDICTIVE. Week-by-week, how his signal load could change over 12 weeks if he does nothing, follows
    the plan about half the time, or follows it fully. Each change ramps in over its own time to show (sperm take
    about 74 days to develop). Educational: a projection of signals, never a chance of pregnancy.

dropout_risk(): PREDICTIVE, for the care team. An early warning that a man may fall off the pathway, from predictors
    with published evidence. It is a transparent points score until the pilot has enough real outcomes to fit a model.
"""
import time

from . import explain, triage
from .knowledge import graph

# effort (1 easy .. 3 hard), days until the change shows, and a concrete first step
CHANGE = {
    "smoking": (3, 74, "Pick a quit date in the next 2 weeks and ask your doctor about free quit support.",
                "اختر موعداً للإقلاع خلال أسبوعين واسأل طبيبك عن دعم الإقلاع المجاني."),
    "waterpipe": (2, 74, "Halve your shisha sessions this month.", "قلّل جلسات الشيشة إلى النصف هذا الشهر."),
    "alcohol": (2, 74, "Set alcohol-free days, at least 5 a week.", "حدّد أياماً بلا كحول، ٥ أيام أسبوعياً على الأقل."),
    "sedentary": (1, 74, "Set an hourly reminder to stand for 5 minutes.", "اضبط تذكيراً كل ساعة للوقوف ٥ دقائق."),
    "sleep_loss": (1, 21, "Fix your wake-up time, 7 days a week.", "ثبّت وقت استيقاظك طوال الأسبوع."),
    "circadian": (1, 21, "Keep weekend wake-up within an hour of weekdays.", "اجعل استيقاظ العطلة قريباً من أيام العمل بساعة."),
    "screen_night": (1, 21, "Phone out of the bedroom 60 minutes before sleep.", "أبعد الهاتف عن غرفة النوم قبل النوم بساعة."),
    "caffeine_late": (1, 14, "Last coffee or karak before 2 pm.", "آخر قهوة أو كرك قبل الثانية ظهراً."),
    "obesity": (3, 84, "Aim for 0.5 kg a week: one less sweet drink and a 20-minute walk daily.",
                "استهدف نصف كيلو أسبوعياً: مشروب محلّى أقل ومشي ٢٠ دقيقة يومياً."),
    "western_diet": (2, 74, "Swap two processed meals a week for fish, nuts and vegetables.", "استبدل وجبتين مصنّعتين أسبوعياً بالسمك والمكسرات والخضار."),
    "late_eating": (1, 21, "Last meal 3 hours before sleep.", "آخر وجبة قبل النوم بثلاث ساعات."),
    "glycaemic_spikes": (2, 42, "No sweet drinks after 9 pm.", "لا مشروبات محلاة بعد التاسعة مساءً."),
    "tight_underwear": (1, 74, "Switch to loose cotton boxers or sirwal this week.", "انتقل إلى بوكسر قطني فضفاض أو سروال هذا الأسبوع."),
    "synthetic_textile": (1, 74, "Choose cotton underwear.", "اختر ملابس داخلية قطنية."),
    "hot_bath": (1, 74, "Pause sauna and jacuzzi for 3 months.", "أوقف الساونا والجاكوزي ٣ أشهر."),
    "laptop_lap": (1, 74, "Laptop on a desk, not your lap.", "الحاسوب على المكتب لا على الحِجر."),
    "phone_pocket": (1, 74, "Phone in a bag or jacket, not a trouser pocket.", "الهاتف في الحقيبة أو السترة لا في جيب البنطال."),
    "psych_stress": (2, 28, "Ten minutes a day that resets you: a walk, prayer or slow breathing.", "عشر دقائق يومياً تعيد توازنك: مشي أو صلاة أو تنفس هادئ."),
    "low_mood": (2, 28, "Book one confidential conversation with a professional.", "احجز محادثة سرية واحدة مع مختص."),
    "osa": (2, 42, "Ask for a home sleep test.", "اطلب اختبار نوم منزلي."),
    "low_sun": (1, 56, "15 minutes of morning sun, or ask for a vitamin D test.", "١٥ دقيقة من شمس الصباح أو اطلب فحص فيتامين د."),
    "occupational_heat": (2, 74, "Cool breaks and loose clothing at work.", "استراحات باردة وملابس فضفاضة في العمل."),
}
DEFAULT_CHANGE = (2, 74, None, None)
GRADE_W = {"A": 1.0, "B": 0.8, "C": 0.55, "D": 0.35, None: 0.5}
EFFORT = {"en": {1: "Easy", 2: "Moderate", 3: "Hard"}, "ar": {1: "سهل", 2: "متوسط", 3: "صعب"}}
WHEN = {"en": lambda d: f"shows in about {round(d / 7)} weeks", "ar": lambda d: f"يظهر أثره خلال نحو {round(d / 7)} أسابيع"}
NOTE = {"en": "Educational estimate from the evidence map: how your signals could change, not a prediction of fertility or pregnancy.",
        "ar": "تقدير تعليمي من خريطة الأدلة: كيف قد تتغير مؤشراتك، وليس توقعاً للخصوبة أو الحمل."}


def _mod(result):
    g = graph()
    return {k: v for k, v in result["inputs"].items() if k in g.nodes and g.nodes[k].get("modifiable")}


def _load(mod, scale=None):
    """Subfertility signal from the modifiable inputs, with some scaled down (0 = fully changed)."""
    scale = scale or {}
    return graph().propagate({k: v * scale.get(k, 1.0) for k, v in mod.items()})["subfertility"]


def best_changes(result, lang="en", top=3):
    L = "ar" if lang == "ar" else "en"
    mod = _mod(result)
    if not mod:
        return {"ranked": [], "bundle": None, "note": NOTE[L]}
    before = _load(mod)
    cards = {c["node"]: c for c in explain.cards(result, L)}
    ranked = []
    for node in mod:
        if node not in CHANGE:  # only things he can do himself; conditions (e.g. low testosterone) go to a doctor, not a habit list
            continue
        effort, days, step_en, step_ar = CHANGE.get(node, DEFAULT_CHANGE)
        drop = before - _load(mod, {node: 0.0})
        if drop <= 1e-4:
            continue
        card = cards.get(node, {})
        grade = card.get("grade")
        pct = 100 * drop / before
        ranked.append({"node": node, "label": explain.label(node, L), "impact_pct": round(pct, 1), "grade": grade, "effort": effort,
                       "effort_label": EFFORT[L][effort], "days_to_show": days, "when": WHEN[L](days),
                       "first_step": (step_ar if L == "ar" else step_en) or card.get("recommendation"),
                       "score": round(pct * GRADE_W.get(grade, 0.5) / effort, 2)})
    ranked.sort(key=lambda r: -r["score"])
    # best set of `top`: greedy on the combined counterfactual, value per unit of effort
    chosen, left = [], [r["node"] for r in ranked]
    while left and len(chosen) < top:
        cur = _load(mod, {n: 0.0 for n in chosen})
        best = max(left, key=lambda n: (cur - _load(mod, {**{c: 0.0 for c in chosen}, n: 0.0})) * GRADE_W.get(cards.get(n, {}).get("grade"), .5)
                   / CHANGE.get(n, DEFAULT_CHANGE)[0])
        chosen.append(best)
        left.remove(best)
    after = _load(mod, {n: 0.0 for n in chosen})
    bundle = {"nodes": chosen, "labels": [explain.label(n, L) for n in chosen], "impact_pct": round(100 * (before - after) / before, 1),
              "before_tier": triage.tier_of(result["scores"]["subfertility"]),
              "after_tier": triage.tier_of(result["scores"]["subfertility"] * after / before) if before else None,
              "sum_of_parts_pct": round(sum(r["impact_pct"] for r in ranked if r["node"] in chosen), 1)}
    return {"ranked": ranked, "bundle": bundle, "one_thing": ranked[0] if ranked else None, "note": NOTE[L]}


def projection(result, nodes=None, weeks=12, lang="en"):
    L = "ar" if lang == "ar" else "en"
    mod = _mod(result)
    nodes = [n for n in (nodes or best_changes(result, L)["bundle"]["nodes"] if mod else []) if n in mod]
    if not mod:
        return {"weeks": [], "scenarios": {}, "milestones": [], "note": NOTE[L]}
    before = _load(mod)

    def series(adherence):
        out = []
        for w in range(weeks + 1):
            scale = {n: 1 - adherence * min(1.0, 7 * w / CHANGE.get(n, DEFAULT_CHANGE)[1]) for n in nodes}
            out.append(round(100 * _load(mod, scale) / before, 1))
        return out

    names = {"en": {"none": "No change", "half": "Plan about half the time", "full": "Plan every week"},
             "ar": {"none": "بلا تغيير", "half": "الخطة نصف الوقت تقريباً", "full": "الخطة كل أسبوع"}}[L]
    ms = {"en": [(3, "Sleep and energy usually feel different"), (11, "New sperm reflect the changes (about 74 days)"), (12, "Re-check to see what changed")],
          "ar": [(3, "يتغير النوم والطاقة عادةً"), (11, "تعكس الحيوانات المنوية الجديدة التغييرات (نحو ٧٤ يوماً)"), (12, "أعد الفحص لترى ما تغيّر")]}[L]
    return {"weeks": list(range(weeks + 1)), "unit": "signal load, today = 100",
            "scenarios": {k: {"label": names[k], "values": series(a)} for k, a in (("none", 0.0), ("half", 0.5), ("full", 1.0))},
            "changes": [explain.label(n, L) for n in nodes], "milestones": [{"week": w, "text": t} for w, t in ms], "note": NOTE[L]}


# ---------------------------------------------------------------- dropout early warning (care team only)
DROPOUT_FACTORS = {
    "prior_missed": (3, "Missed a previous appointment", "Dantas et al. 2018, systematic review of no-shows: prior no-show is the strongest predictor"),
    "barrier": (2, "Said something is in the way", "Self-reported barriers predict non-attendance (Dantas et al. 2018)"),
    "low_mood": (2, "Screened positive for low mood", "DiMatteo et al. 2000, Arch Intern Med: depression ~3x non-adherence"),
    "long_wait": (2, "Appointment more than 14 days after booking", "Longer lead time increases no-shows (Dantas et al. 2018)"),
    "stalled": (2, "Past the usual time for this stage", "Riaya pathway thresholds"),
    "no_review": (1, "Chose no doctor review, so no personal message yet", "Personal follow-up improves attendance (Dantas et al. 2018)"),
}


def dropout_risk(row, ref, appt, answers, stalled=None):
    pts, why = 0, []
    def add(k):
        nonlocal pts
        w, text, src = DROPOUT_FACTORS[k]
        pts += w
        why.append({"factor": k, "text": text, "points": w, "source": src})
    num = lambda v: v if isinstance(v, (int, float)) else 0
    if appt is not None and appt["status"] == "missed":
        add("prior_missed")
    if ref is not None and ref["barrier"]:
        add("barrier")
    if num(answers.get("phq1")) + num(answers.get("phq2")) >= 3:
        add("low_mood")
    if appt is not None and appt["slot_at"] and appt["status"] == "confirmed" and appt["slot_at"] - appt["created_at"] > 14 * 86400:
        add("long_wait")
    if stalled:
        add("stalled")
    if not row["review_consent"]:
        add("no_review")
    band = "high" if pts >= 5 else "medium" if pts >= 3 else "low"
    return {"points": pts, "band": band, "reasons": why,
            "method": "Points from published predictors of missed care. Replaced by a model fitted on pilot outcomes once there are enough."}
