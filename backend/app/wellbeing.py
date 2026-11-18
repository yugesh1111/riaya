"""Wellbeing outcomes, behaviour-change design, just-in-time nudges, relapse recovery and Ramadan mode.

- WHO-5 Well-Being Index (Topp et al. 2015, Psychother Psychosom 84:167): five items, 0-5 each; raw x4 = 0-100.
  <=50 suggests poor wellbeing and is a reason to screen for depression; <=28 suggests likely depression.
  A change of 10 points is clinically meaningful. Asked at the start (day 0), week 5 (~day 30) and week 12 (~day 84).
- Behaviour-change design: every part of the 12-week companion is mapped to COM-B (Michie et al. 2011) and to the
  Behaviour Change Technique Taxonomy v1 (Michie et al. 2013), with Self-Determination Theory principles.
- JITAI (Nahum-Shani et al. 2018): decision points, tailoring variables, intervention options and decision rules, each
  decision explained. Quiet hours, a frequency cap and his own reminder switch always win.
- Relapse recovery: a lapse is expected, not a failure (Marlatt & Gordon relapse-prevention model). Two weak weeks in a
  row, or two missed check-ins, offer a fresh start with one smaller goal and an if-then plan for the barrier he names.
- Ramadan mode: timing-aware advice, check-ins after iftar, no nudges while fasting.
"""
import time
from datetime import date, datetime, timedelta, timezone

GST = timezone(timedelta(hours=4))

# ------------------------------------------------------------------ WHO-5
WHO5_ITEMS = [
    ("I have felt cheerful and in good spirits", "شعرتُ بالبهجة وبمزاج جيد"),
    ("I have felt calm and relaxed", "شعرتُ بالهدوء والاسترخاء"),
    ("I have felt active and vigorous", "شعرتُ بالنشاط والحيوية"),
    ("I woke up feeling fresh and rested", "استيقظتُ وأنا أشعر بالانتعاش والراحة"),
    ("My daily life has been filled with things that interest me", "كانت حياتي اليومية مليئة بأشياء تهمّني"),
]
WHO5_SCALE = {
    "en": ["At no time", "Some of the time", "Less than half of the time", "More than half of the time", "Most of the time", "All of the time"],
    "ar": ["ولا مرة", "بعض الوقت", "أقل من نصف الوقت", "أكثر من نصف الوقت", "معظم الوقت", "طوال الوقت"],
}
WHO5_WEEKS = {1: "day0", 5: "day30", 12: "day84"}   # plan week -> time point
MEANINGFUL = 10
WHO5_SOURCE = "Topp CW et al. The WHO-5 Well-Being Index: a systematic review. Psychother Psychosom 2015;84:167-76"


def who5_form(lang):
    L = "ar" if lang == "ar" else "en"
    return {"title": "كيف كنت خلال الأسبوعين الماضيين؟" if L == "ar" else "Over the last two weeks…",
            "items": [{"i": i, "text": it[1] if L == "ar" else it[0]} for i, it in enumerate(WHO5_ITEMS)],
            "scale": WHO5_SCALE[L], "source": WHO5_SOURCE}


def who5_score(answers):
    if len(answers) != 5 or any((not isinstance(a, int)) or not 0 <= a <= 5 for a in answers):
        raise ValueError("WHO-5 needs five answers from 0 to 5")
    return sum(answers) * 4


def who5_band(score, lang="en"):
    ar = lang == "ar"
    if score <= 28:
        return {"band": "low", "text": "قد يكون مزاجك منخفضاً منذ فترة. نقترح أن يتحدث معك طبيب، فهذا شائع ويتحسن بالعلاج." if ar else
                "Your mood may have been low for a while. We suggest a doctor talks with you; this is common and treatable.",
                "action": "clinician_review"}
    if score <= 50:
        return {"band": "fair", "text": "صحتك النفسية أقل مما ينبغي. خطوة صغيرة في خطتك قد تساعد، ويمكنك طلب حديث مع طبيب." if ar else
                "Your wellbeing is lower than it should be. A small step in your plan can help, and you can ask to talk with a doctor.",
                "action": "offer_support"}
    return {"band": "good", "text": "صحتك النفسية جيدة. استمر." if ar else "Your wellbeing is good. Keep going.", "action": None}


def who5_due(week, entries):
    """The time point due this plan week, if it has not been answered yet."""
    have = {e["point"] for e in entries or []}
    for w, point in sorted(WHO5_WEEKS.items()):
        if week >= w and point not in have and (w == 1 or week <= w + 2):
            return point
    return None


def who5_change(entries):
    by = {e["point"]: e["score"] for e in entries or []}
    base = by.get("day0")
    out = {"baseline": base, "day30": by.get("day30"), "day84": by.get("day84"), "change": None, "meaningful": None}
    last = by.get("day84", by.get("day30"))
    if base is not None and last is not None:
        out["change"] = last - base
        out["meaningful"] = "improved" if last - base >= MEANINGFUL else "worse" if base - last >= MEANINGFUL else "stable"
    return out


# ------------------------------------------------------------------ behaviour-change design (COM-B, BCT v1, SDT)
BCT = {
    "1.1": "Goal setting (behaviour)", "1.2": "Problem solving", "1.4": "Action planning", "1.5": "Review behaviour goal(s)",
    "2.2": "Feedback on behaviour", "2.3": "Self-monitoring of behaviour", "2.4": "Self-monitoring of outcome(s) of behaviour",
    "3.1": "Social support (unspecified)", "4.1": "Instruction on how to perform the behaviour",
    "5.1": "Information about health consequences", "7.1": "Prompts/cues", "8.3": "Habit formation",
    "9.1": "Credible source", "12.1": "Restructuring the physical environment", "12.5": "Adding objects to the environment",
    "15.1": "Verbal persuasion about capability",
}
BCT_AR = {
    "1.1": "تحديد هدف سلوكي", "1.2": "حل المشكلات", "1.4": "خطة عمل", "1.5": "مراجعة الهدف", "2.2": "ملاحظات على السلوك",
    "2.3": "متابعة السلوك ذاتياً", "2.4": "متابعة النتيجة ذاتياً", "3.1": "دعم اجتماعي", "4.1": "تعليمات التنفيذ",
    "5.1": "معلومات عن العواقب الصحية", "7.1": "تذكيرات", "8.3": "تكوين العادة", "9.1": "مصدر موثوق",
    "12.1": "تغيير البيئة", "12.5": "إضافة أدوات إلى البيئة", "15.1": "تعزيز الثقة بالقدرة",
}
# Each part of the product, the COM-B component it targets, and the techniques it delivers.
COMPONENTS = [
    ("summary", "Explained summary with evidence grades", "ملخص مشروح بدرجات الدليل", "Capability (psychological)", ["5.1", "9.1"]),
    ("goals", "He picks up to 3 goals from his own drivers", "يختار حتى ٣ أهداف من عوامله", "Motivation (reflective)", ["1.1"]),
    ("first_step", "A first step for each goal", "خطوة أولى لكل هدف", "Capability (psychological)", ["1.4", "4.1"]),
    ("checkin", "Weekly check-in with adherence and a measure", "متابعة أسبوعية للالتزام وقياس", "Motivation (reflective)", ["2.3", "2.4"]),
    ("trend", "Trend chart of his own weeks", "رسم بياني لأسابيعه", "Motivation (reflective)", ["2.2"]),
    ("nudges", "Just-in-time nudges and a discreet calendar cue", "تنبيهات في الوقت المناسب وتذكير تقويم خفي", "Opportunity (physical)", ["7.1"]),
    ("habit", "Same time, same cue every day", "نفس الوقت ونفس الإشارة كل يوم", "Motivation (automatic)", ["8.3"]),
    ("environment", "Change the setting: laptop off lap, phone out of pocket, loose cotton", "تغيير البيئة: الحاسوب والهاتف والملابس", "Opportunity (physical)", ["12.1", "12.5"]),
    ("doctor", "Doctor reviews the plan and writes a note", "طبيب يراجع الخطة ويكتب ملاحظة", "Motivation (reflective)", ["9.1", "15.1"]),
    ("partner", "Partner mode: she sees only that he acted", "وضع الشريكة: ترى فقط أنه اتخذ خطوة", "Opportunity (social)", ["3.1"]),
    ("relapse", "Fresh start after a lapse, with an if-then plan", "بداية جديدة بعد التعثّر مع خطة «إذا… فإن»", "Capability (psychological)", ["1.2", "1.5"]),
]
SDT = {
    "autonomy": ("He chooses his goals, how many, and whether a doctor reviews them; he can stop any time.",
                 "يختار أهدافه وعددها وهل يراجعها طبيب، ويمكنه التوقف متى شاء."),
    "competence": ("Small first steps, weekly feedback, and a smaller goal after a lapse.",
                   "خطوات أولى صغيرة، ملاحظات أسبوعية، وهدف أصغر بعد التعثّر."),
    "relatedness": ("A doctor's note on his plan, private messages, and an optional partner link.",
                    "ملاحظة طبيب على خطته، رسائل خاصة، ورابط اختياري للشريكة."),
}
# The main barrier each goal targets, so the plan says why this technique fits him.
GOAL_COMB = {
    "smoking": ("Motivation (automatic)", ["1.1", "1.4", "2.3", "8.3", "1.2"]),
    "waterpipe": ("Opportunity (social)", ["1.1", "1.2", "2.3", "3.1"]),
    "obesity": ("Motivation (reflective)", ["1.1", "1.4", "2.4", "2.2"]),
    "western_diet": ("Capability (psychological)", ["4.1", "1.4", "12.5"]),
    "sleep_loss": ("Opportunity (physical)", ["1.4", "8.3", "2.4", "12.1"]),
    "sedentary": ("Opportunity (physical)", ["1.1", "1.4", "2.3", "8.3"]),
    "psych_stress": ("Motivation (automatic)", ["4.1", "8.3", "2.3"]),
    "circadian": ("Motivation (automatic)", ["8.3", "7.1"]),
    "laptop_lap": ("Opportunity (physical)", ["12.1", "7.1"]),
    "tight_underwear": ("Opportunity (physical)", ["12.5", "2.3"]),
    "phone_pocket": ("Opportunity (physical)", ["12.1", "8.3"]),
    "glycaemic_spikes": ("Motivation (automatic)", ["1.4", "12.1"]),
    "screen_night": ("Motivation (automatic)", ["8.3", "12.1", "2.3"]),
    "caffeine_late": ("Motivation (automatic)", ["1.4", "2.3"]),
    "hot_bath": ("Capability (psychological)", ["5.1", "1.1"]),
    "late_eating": ("Motivation (automatic)", ["1.4", "8.3"]),
    "synthetic_textile": ("Opportunity (physical)", ["12.5"]),
    "alcohol": ("Motivation (automatic)", ["1.1", "1.2", "2.3"]),
    "occupational_heat": ("Opportunity (physical)", ["1.4", "12.1"]),
}


def techniques_for(node, lang="en"):
    comb, codes = GOAL_COMB.get(node, ("Motivation (reflective)", ["1.1", "2.3"]))
    ar = lang == "ar"
    return {"com_b": comb, "bct": [{"code": c, "name": BCT_AR[c] if ar else BCT[c]} for c in codes]}


def design(lang="en"):
    ar = lang == "ar"
    return {"components": [{"key": k, "what": a if ar else e, "com_b": comb, "bct": [{"code": c, "name": BCT_AR[c] if ar else BCT[c]} for c in codes]}
                           for k, e, a, comb, codes in COMPONENTS],
            "sdt": {k: v[1] if ar else v[0] for k, v in SDT.items()},
            "sources": ["Michie S et al. The behaviour change wheel. Implement Sci 2011;6:42",
                        "Michie S et al. BCT Taxonomy (v1) of 93 techniques. Ann Behav Med 2013;46:81-95",
                        "Ryan RM, Deci EL. Self-determination theory. Am Psychol 2000;55:68-78",
                        "Lally P et al. How are habits formed. Eur J Soc Psychol 2010;40:998-1009",
                        "Nahum-Shani I et al. Just-in-time adaptive interventions. Ann Behav Med 2018;52:446-62"]}


# ------------------------------------------------------------------ Ramadan mode
# 1 Ramadan to 1 Shawwal (Umm al-Qura), astronomical estimates; the UAE announces the exact day by moon sighting.
RAMADAN = [(date(2025, 3, 1), date(2025, 3, 30)), (date(2026, 2, 18), date(2026, 3, 20)), (date(2027, 2, 8), date(2027, 3, 10)),
           (date(2028, 1, 28), date(2028, 2, 27)), (date(2029, 1, 16), date(2029, 2, 14)), (date(2030, 1, 6), date(2030, 2, 5))]


def is_ramadan(when=None):
    if when is None:
        d = datetime.now(GST).date()
    elif isinstance(when, datetime):
        d = when.astimezone(GST).date() if when.tzinfo else when.date()
    else:
        d = when
    return any(a <= d < b for a, b in RAMADAN)


def ramadan_on(setting, when=None):
    """setting: 'auto' (follow the calendar), 'on' or 'off'."""
    return setting == "on" or (setting in (None, "auto") and is_ramadan(when))


# Goal wording while fasting: same aim, timing that works between suhoor and iftar.
RAMADAN_GOALS = {
    "smoking": ("Ramadan is a ready-made quit window: keep the fasting-day break going after iftar",
                "رمضان فرصة جاهزة للإقلاع: حافظ على انقطاع النهار بعد الإفطار أيضاً"),
    "waterpipe": ("Skip the after-taraweeh shisha; meet friends somewhere smoke-free",
                  "تجنّب شيشة ما بعد التراويح؛ قابل أصدقاءك في مكان بلا دخان"),
    "sleep_loss": ("Two blocks: core sleep after taraweeh, a short nap after dhuhr; 7 hours in total",
                   "فترتان: نوم أساسي بعد التراويح وقيلولة قصيرة بعد الظهر؛ ٧ ساعات في المجموع"),
    "caffeine_late": ("One coffee at iftar, none after taraweeh; water between iftar and suhoor",
                      "قهوة واحدة عند الإفطار ولا شيء بعد التراويح؛ ماء بين الإفطار والسحور"),
    "glycaemic_spikes": ("Break the fast with dates and water; no sweet drinks at suhoor",
                         "أفطر على التمر والماء؛ لا مشروبات محلاة عند السحور"),
    "late_eating": ("Light suhoor with protein and fibre; avoid a heavy meal right before sleeping",
                    "سحور خفيف بالبروتين والألياف؛ تجنّب وجبة ثقيلة قبل النوم مباشرة"),
    "sedentary": ("A 30-minute walk after iftar or after taraweeh, not while fasting in the heat",
                  "مشي ٣٠ دقيقة بعد الإفطار أو التراويح، لا أثناء الصيام في الحر"),
    "obesity": ("Keep iftar to one plate; Ramadan is a good month to start losing weight",
                "اكتفِ بطبق واحد عند الإفطار؛ رمضان شهر مناسب للبدء بخسارة الوزن"),
    "screen_night": ("Phone away 30 minutes before your core sleep after taraweeh",
                     "أبعد الهاتف قبل نومك الأساسي بعد التراويح بنصف ساعة"),
    "circadian": ("Keep the same suhoor alarm every night", "ثبّت منبّه السحور كل ليلة"),
}
RAMADAN_NOTES = {
    "en": ["Check-ins and reminders move to after iftar (9:30 pm); nothing is sent while you fast.",
           "Blood tests: a morning test while fasting is fine for testosterone; drink water at suhoor.",
           "Semen analysis: fasting does not stop you giving a sample; keep the 2-7 days of abstinence.",
           "If you take regular medicines, ask your doctor how to time them around the fast."],
    "ar": ["تنتقل المتابعة والتذكيرات إلى ما بعد الإفطار (٩:٣٠ مساءً)، ولا يُرسل شيء أثناء صيامك.",
           "تحاليل الدم: تحليل التستوستيرون صباحاً أثناء الصيام مناسب؛ اشرب الماء عند السحور.",
           "تحليل السائل المنوي: الصيام لا يمنع إعطاء العينة؛ حافظ على الامتناع من ٢ إلى ٧ أيام.",
           "إن كنت تتناول أدوية بانتظام، اسأل طبيبك عن توقيتها مع الصيام."],
}


def ramadan_goal(node, lang):
    g = RAMADAN_GOALS.get(node)
    return (g[1] if lang == "ar" else g[0]) if g else None


def ramadan_view(setting, lang, when=None):
    on = ramadan_on(setting, when)
    return {"setting": setting or "auto", "active": on, "in_calendar": is_ramadan(when),
            "notes": RAMADAN_NOTES["ar" if lang == "ar" else "en"] if on else [], "checkin_time": "21:30" if on else "20:00"}


# ------------------------------------------------------------------ relapse
BARRIERS = {
    "time": ("No time this week", "لم يكن لدي وقت هذا الأسبوع",
             "If my day is full, then I do just the first step, for 5 minutes, right after {anchor}.",
             "إن كان يومي مزدحماً، فسأقوم بالخطوة الأولى فقط لمدة ٥ دقائق مباشرة بعد {anchor}."),
    "urge": ("Cravings or old habits", "رغبة قوية أو عادة قديمة",
             "If the urge comes, then I wait 10 minutes and drink a glass of water first.",
             "إن جاءت الرغبة، فسأنتظر ١٠ دقائق وأشرب كوب ماء أولاً."),
    "social": ("Friends or family around me", "الأصدقاء أو العائلة من حولي",
               "If friends offer, then I say \"not this month, doctor's plan\" and suggest something else.",
               "إن عرض علي الأصدقاء، فسأقول «ليس هذا الشهر، خطة الطبيب» وأقترح شيئاً آخر."),
    "work": ("Work, shifts or heat", "العمل أو المناوبات أو الحرّ",
             "If my shift changes, then I move the step to the first break of my shift.",
             "إن تغيّرت مناوبتي، فسأنقل الخطوة إلى أول استراحة فيها."),
    "mood": ("Low mood or stress", "مزاج منخفض أو ضغط",
             "If I feel low, then I do the 10-minute reset first, and message the team if it lasts.",
             "إن شعرت بانخفاض المزاج، فسأبدأ بعشر دقائق لاستعادة التوازن، وأراسل الفريق إن استمر."),
    "forgot": ("I forgot", "نسيت",
               "If it is 9 pm, then my phone reminder tells me to do the step before sleep.",
               "إذا كانت الساعة التاسعة مساءً، فسيذكّرني الهاتف بالخطوة قبل النوم."),
}
ANCHOR = {"en": "my first prayer of the day", "ar": "أول صلاة في يومي"}


def lapse(plan_view):
    """A lapse: his last two logged weeks average 1 or less out of 3 after a better start, or two check-ins missed."""
    if plan_view["status"] not in ("active", "self_guided"):
        return None
    week = plan_view["week"]
    logged = sorted({w["week"] for it in plan_view["items"] for w in it["weeks"] if w["adherence"] is not None})
    missed = [w for w in range(max(1, week - 2), week) if w not in logged]
    if week >= 3 and len(missed) >= 2:
        return {"reason": "missed", "weeks": missed}
    if len(logged) >= 2:
        last2 = logged[-2:]
        avg = [sum(w["adherence"] for it in plan_view["items"] for w in it["weeks"] if w["week"] == k and w["adherence"] is not None) /
               max(1, sum(1 for it in plan_view["items"] for w in it["weeks"] if w["week"] == k and w["adherence"] is not None)) for k in last2]
        if all(a <= 1 for a in avg):
            return {"reason": "low_adherence", "weeks": last2}
    return None


def restart_plan(items, keep_node, barrier, lang):
    """Fresh start: keep one goal, make it smaller, and write his if-then plan for the barrier."""
    b = BARRIERS[barrier]
    L = "ar" if lang == "ar" else "en"
    kept = next((it for it in items if it["node"] == keep_node), items[0])
    plan_text = (b[3] if L == "ar" else b[2]).format(anchor=ANCHOR[L])
    return kept, {"barrier": barrier, "barrier_label_en": b[0], "barrier_label_ar": b[1],
                  "if_then_en": b[2].format(anchor=ANCHOR["en"]), "if_then_ar": b[3].format(anchor=ANCHOR["ar"]),
                  "kept": kept["node"], "at": time.time(), "text": plan_text}


def barriers(lang):
    ar = lang == "ar"
    return [{"key": k, "label": v[1] if ar else v[0]} for k, v in BARRIERS.items()]


# ------------------------------------------------------------------ JITAI
QUIET = (23, 7)          # no nudges 11 pm to 7 am Gulf time
FASTING = (5, 18)        # Ramadan: none between suhoor and iftar
CAP_HOURS = 72           # at most one nudge every three days
NUDGES = {
    "who5": ("Two-minute wellbeing check: five questions, for you only.", "فحص سريع لصحتك النفسية: خمسة أسئلة، لك وحدك."),
    "checkin": ("Your weekly check-in is ready. One minute.", "متابعتك الأسبوعية جاهزة. دقيقة واحدة."),
    "lapse": ("A rough week is normal. Want a smaller goal for a fresh start?", "الأسبوع الصعب أمر طبيعي. هل تريد هدفاً أصغر لبداية جديدة؟"),
    "low_wellbeing": ("You told us things have been hard. A doctor can talk with you privately; reply here if you'd like that.",
                      "أخبرتنا أن الأمور صعبة. يمكن لطبيب أن يتحدث معك بخصوصية؛ رد هنا إن أردت ذلك."),
}


def jitai_decide(plan_view, who5_entries, last_nudge_at, reminders_on, ramadan, now=None):
    """Decision point: is now the right moment, and which single nudge helps most? Returns the decision with every reason."""
    now = now or time.time()
    hour = datetime.fromtimestamp(now, GST).hour
    why = []
    if not reminders_on:
        return {"send": None, "why": ["He turned reminders off."]}
    if hour >= QUIET[0] or hour < QUIET[1]:
        return {"send": None, "why": ["Quiet hours (11 pm to 7 am)."]}
    if ramadan and FASTING[0] <= hour < FASTING[1]:
        return {"send": None, "why": ["Ramadan: no nudges while he fasts; they wait until after iftar."]}
    if last_nudge_at and now - last_nudge_at < CAP_HOURS * 3600:
        return {"send": None, "why": ["A nudge was sent in the last three days."]}
    change = who5_change(who5_entries)
    latest = (who5_entries or [{}])[-1].get("score") if who5_entries else None
    if latest is not None and latest <= 28 and not any(e.get("escalated") for e in who5_entries):
        return {"send": "low_wellbeing", "why": [f"Latest WHO-5 is {latest} (28 or less)."]}
    due = who5_due(plan_view["week"], who5_entries)
    if due:
        return {"send": "who5", "why": [f"WHO-5 {due} is due in week {plan_view['week']}."]}
    lp = lapse(plan_view)
    if lp and not plan_view.get("restart"):
        return {"send": "lapse", "why": ["Two weak or missed weeks in a row." if lp["reason"] == "low_adherence" else "Two check-ins missed."]}
    if plan_view.get("due"):
        weekday = datetime.fromtimestamp(now, GST).weekday()
        start_wd = datetime.fromtimestamp(plan_view["start_at"] or now, GST).weekday()
        if (weekday - start_wd) % 7 >= 2:
            return {"send": "checkin", "why": ["This week's check-in is two or more days late."]}
        why.append("Check-in due but not late yet.")
    return {"send": None, "why": why or ["Nothing needs a nudge."], "change": change}


def nudge_text(kind, lang):
    t = NUDGES[kind]
    return t[1] if lang == "ar" else t[0]
