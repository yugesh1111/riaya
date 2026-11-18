"""12-week companion: up to three goals he picks from his own summary, weekly check-ins, trends.

Sperm take about 74 days to develop, so a habit change shows in results after roughly three months.
When he has agreed to doctor review the plan starts only after a doctor has looked at it.
"""
import time
from datetime import datetime, timedelta, timezone

WEEKS = 12
MAX_GOALS = 3
WEEK_S = 7 * 86400
ADHERENCE = {"en": ["Not this week", "A few days", "Most days", "Every day"],
             "ar": ["ليس هذا الأسبوع", "بضعة أيام", "معظم الأيام", "كل يوم"]}

# node -> (goal en, goal ar, measure or None); measure = (key, label en, label ar, min, max, better)
GOALS = {
    "smoking": ("Smoke less, then stop", "قلّل التدخين ثم توقف", ("cigs_per_day", "Cigarettes a day", "عدد السجائر يومياً", 0, 80, "lower")),
    "waterpipe": ("Cut down on shisha", "قلّل الشيشة", ("sessions", "Shisha sessions this week", "جلسات الشيشة هذا الأسبوع", 0, 30, "lower")),
    "obesity": ("Lose 5–10% of body weight", "اخسر ٥–١٠٪ من وزنك", ("weight_kg", "Weight (kg)", "الوزن (كغ)", 40, 250, "lower")),
    "western_diet": ("More fish, nuts and vegetables", "المزيد من السمك والمكسرات والخضار", None),
    "sleep_loss": ("Sleep 7 hours or more", "نم ٧ ساعات أو أكثر", ("sleep_h", "Average sleep (hours a night)", "متوسط النوم (ساعات في الليلة)", 3, 12, "higher")),
    "sedentary": ("Move more, sit less", "تحرّك أكثر واجلس أقل", ("active_days", "Days with 30+ minutes of walking", "أيام فيها ٣٠ دقيقة مشي أو أكثر", 0, 7, "higher")),
    "psych_stress": ("Ten minutes a day to reset", "عشر دقائق يومياً لاستعادة التوازن", None),
    "circadian": ("Keep the same wake-up time", "ثبّت وقت الاستيقاظ", None),
    "laptop_lap": ("Laptop off your lap", "أبعد الحاسوب عن حضنك", None),
    "tight_underwear": ("Wear loose cotton underwear", "ارتدِ ملابس داخلية قطنية فضفاضة", ("days", "Days in loose cotton underwear", "أيام بملابس داخلية قطنية فضفاضة", 0, 7, "higher")),
    "phone_pocket": ("Phone out of your trouser pocket", "أخرج الهاتف من جيب البنطال", None),
    "glycaemic_spikes": ("No sweet drinks after 9 pm", "لا مشروبات محلاة بعد التاسعة مساءً", None),
    "screen_night": ("Phone away an hour before bed", "أبعد الهاتف قبل النوم بساعة", ("nights", "Nights the phone was away an hour before sleep", "ليالٍ أبعدت فيها الهاتف قبل النوم بساعة", 0, 7, "higher")),
    "caffeine_late": ("No caffeine after 2 pm", "لا كافيين بعد الثانية ظهراً", ("days", "Days with no caffeine after 2 pm", "أيام بلا كافيين بعد الثانية ظهراً", 0, 7, "higher")),
    "hot_bath": ("Pause sauna and jacuzzi", "أوقف الساونا والجاكوزي", None),
    "late_eating": ("Last meal 2–3 hours before sleep", "آخر وجبة قبل النوم بساعتين إلى ثلاث", None),
    "synthetic_textile": ("Cotton or linen underwear", "ملابس داخلية من القطن أو الكتان", None),
    "alcohol": ("Keep alcohol low or none", "قلّل الكحول أو امتنع عنه", None),
    "occupational_heat": ("Cool breaks out of the heat", "استراحات باردة بعيداً عن الحرارة", None),
}


def _measure(m, lang):
    if not m:
        return None
    key, en, ar, lo, hi, better = m
    return {"key": key, "label": ar if lang == "ar" else en, "min": lo, "max": hi, "better": better}


def options(result, graph, lang):
    """Goals drawn from his own drivers, strongest first."""
    lab = lambda n: graph.nodes[n].get("label_ar" if lang == "ar" else "label", graph.nodes[n]["label"])
    out = []
    for p in (result.get("plan") or []) + (result.get("plan_more") or []):
        n = p["node"]
        if n in GOALS and n not in [o["node"] for o in out]:
            g = GOALS[n]
            out.append({"node": n, "label": g[1] if lang == "ar" else g[0], "factor": lab(n),
                        "action": p["action_" + ("ar" if lang == "ar" else "en")], "measure": _measure(g[2], lang)})
    return out


def items_for(nodes, result, graph):
    """Stored bilingually so the plan reads correctly in either language later."""
    by = {p["node"]: p for p in (result.get("plan") or []) + (result.get("plan_more") or [])}
    items = []
    for n in nodes:
        if n not in GOALS or n not in by:
            continue
        g = GOALS[n]
        items.append({"node": n, "label_en": g[0], "label_ar": g[1], "action_en": by[n]["action_en"], "action_ar": by[n]["action_ar"],
                      "factor_en": graph.nodes[n]["label"], "factor_ar": graph.nodes[n].get("label_ar", graph.nodes[n]["label"]),
                      "measure": g[2]})
    return items


def week_of(start_at, now=None):
    if not start_at:
        return 1
    return int(((now or time.time()) - start_at) // WEEK_S) + 1


def view(row, items, checkins, lang, doctor_note=None):
    status = row["status"]
    week = min(WEEKS, week_of(row["start_at"])) if row["start_at"] else 1
    if status in ("active", "self_guided") and row["start_at"] and week_of(row["start_at"]) > WEEKS:
        status = "completed"
    L = "ar" if lang == "ar" else "en"
    out_items = []
    for it in items:
        weeks = [{"week": w, "adherence": None, "value": None} for w in range(1, WEEKS + 1)]
        for c in checkins:
            v = (c.get("items") or {}).get(it["node"])
            if v and 1 <= c["week"] <= WEEKS:
                weeks[c["week"] - 1] = {"week": c["week"], "adherence": v.get("adherence"), "value": v.get("value")}
        logged = [w for w in weeks if w["adherence"] is not None]
        recent = logged[-4:]
        vals = [w["value"] for w in logged if w["value"] is not None]
        out_items.append({"node": it["node"], "label": it["label_" + L], "factor": it["factor_" + L], "action": it["action_" + L],
                          "measure": _measure(it.get("measure"), L), "weeks": weeks,
                          "summary": {"weeks_logged": len(logged),
                                      "recent_adherence": round(sum(w["adherence"] for w in recent) / (3 * len(recent)), 2) if recent else None,
                                      "first": vals[0] if vals else None, "latest": vals[-1] if vals else None}})
    energy = [None] * WEEKS
    for c in checkins:
        if 1 <= c["week"] <= WEEKS:
            energy[c["week"] - 1] = c.get("energy")
    due = status in ("active", "self_guided") and not any(c["week"] == week for c in checkins)
    return {"id": row["id"], "status": status, "assessment_id": row["assessment_id"], "created_at": row["created_at"],
            "start_at": row["start_at"], "week": week, "weeks": WEEKS, "items": out_items, "reminders": bool(row["reminders"]),
            "doctor_note": doctor_note, "reviewed_at": row["reviewed_at"], "due": due, "energy": energy,
            "adherence_labels": ADHERENCE[L]}


def reminders_ics(plan_id, start_at):
    """Weekly 'Weekly check-in' at 20:00 Gulf time for the rest of the 12 weeks. Says nothing about health."""
    now = time.time()
    weeks_left = max(1, WEEKS - week_of(start_at, now) + 1)
    gst = timezone(timedelta(hours=4))
    first = datetime.fromtimestamp(now, gst).replace(hour=20, minute=0, second=0, microsecond=0) + timedelta(days=7)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Riaya//Companion//EN",
        "BEGIN:VTIMEZONE", "TZID:Asia/Dubai", "BEGIN:STANDARD", "DTSTART:19700101T000000", "TZOFFSETFROM:+0400",
        "TZOFFSETTO:+0400", "TZNAME:GST", "END:STANDARD", "END:VTIMEZONE",
        "BEGIN:VEVENT", f"UID:{plan_id}-weekly@riaya", f"DTSTAMP:{stamp}", f"DTSTART;TZID=Asia/Dubai:{first.strftime('%Y%m%dT%H%M%S')}",
        "DURATION:PT10M", f"RRULE:FREQ=WEEKLY;COUNT={weeks_left}", "SUMMARY:Weekly check-in",
        "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Weekly check-in", "TRIGGER:PT0M", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR", ""])
