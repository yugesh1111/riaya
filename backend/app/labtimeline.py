"""Lab Intelligence: every saved result, judged against the range printed on its own report.

Results the man saved are 'pending' until a doctor accepts, corrects or sets them aside. A rejected
value stays visible (struck through) so nothing silently disappears from his record.
"""
NAMES = {
    "volume_ml": ("Semen volume", "حجم السائل المنوي", "mL"),
    "concentration_m_per_ml": ("Sperm concentration", "تركيز الحيوانات المنوية", "M/mL"),
    "total_count_m": ("Total sperm count", "العدد الكلي للحيوانات المنوية", "M"),
    "progressive_motility_pct": ("Progressive motility", "الحركة التقدمية", "%"),
    "total_motility_pct": ("Total motility", "الحركة الكلية", "%"),
    "normal_forms_pct": ("Normal forms", "الأشكال الطبيعية", "%"),
    "vitality_pct": ("Vitality", "الحيوية", "%"),
    "ph": ("pH", "درجة الحموضة", ""),
    "testosterone": ("Total testosterone", "التستوستيرون الكلي", "nmol/L"),
    "fsh": ("FSH", "FSH", "IU/L"),
    "lh": ("LH", "LH", "IU/L"),
    "hba1c": ("HbA1c", "السكر التراكمي", "%"),
    "vitamin_d": ("Vitamin D", "فيتامين د", "ng/mL"),
}
# typical ranges used only when the report printed none (WHO 2021 lower 5th centiles; common lab ranges)
TYPICAL = {
    "volume_ml": (1.4, None), "concentration_m_per_ml": (16, None), "total_count_m": (39, None),
    "progressive_motility_pct": (30, None), "total_motility_pct": (42, None), "normal_forms_pct": (4, None),
    "vitality_pct": (54, None), "ph": (7.2, None), "testosterone": (8.6, 29), "fsh": (1.5, 12.4), "lh": (1.7, 8.6),
    "hba1c": (None, 5.6), "vitamin_d": (30, 100),
}
HIGHER_BETTER = {"volume_ml", "concentration_m_per_ml", "total_count_m", "progressive_motility_pct", "total_motility_pct",
                 "normal_forms_pct", "vitality_pct", "testosterone", "vitamin_d"}
LOWER_BETTER = {"hba1c"}
SEMEN = {"volume_ml", "concentration_m_per_ml", "total_count_m", "progressive_motility_pct", "total_motility_pct",
         "normal_forms_pct", "vitality_pct", "ph"}

TXT = {
    "en": {"abst_short": "Abstinence was under 2 days, which can lower count and volume.",
           "abst_long": "Abstinence was over 7 days, which can lower movement.",
           "t_time": "Testosterone is highest in the morning. A sample taken after 11 am can read low; repeat at 7–11 am.",
           "fever": "A fever in the 3 months before can lower sperm results for about 3 months.",
           "flag": "The lab flagged this value.",
           "labs": "These results come from different labs. Each one is judged against its own lab's range.",
           "repeat": "One semen result outside the range is not a diagnosis. Guidelines advise a second test, ideally 2–3 months later.",
           "worse": "This is moving the wrong way. Mention it at your next visit.",
           "note": "Screening information, not a diagnosis. Ranges differ between labs; each result is compared with the range printed on its own report."},
    "ar": {"abst_short": "كان الامتناع أقل من يومين، وقد يقلل ذلك العدد والحجم.",
           "abst_long": "كان الامتناع أكثر من ٧ أيام، وقد يقلل ذلك الحركة.",
           "t_time": "يكون التستوستيرون في أعلى مستوياته صباحاً. العينة بعد الساعة ١١ قد تظهر منخفضة؛ أعد الفحص بين ٧ و١١ صباحاً.",
           "fever": "الحمّى خلال الأشهر الثلاثة السابقة قد تخفض نتائج الحيوانات المنوية لنحو ٣ أشهر.",
           "flag": "علّم المختبر هذه القيمة.",
           "labs": "هذه النتائج من مختبرات مختلفة. تُقارن كل نتيجة بمعدل مختبرها.",
           "repeat": "نتيجة واحدة خارج المعدل لا تعني تشخيصاً. توصي الإرشادات بفحص ثانٍ، ويفضّل بعد ٢–٣ أشهر.",
           "worse": "هذه القيمة تتجه في الاتجاه غير المرغوب. اذكرها في زيارتك القادمة.",
           "note": "معلومات فحص أولي وليست تشخيصاً. تختلف المعدلات بين المختبرات؛ تُقارن كل نتيجة بالمعدل المطبوع على تقريرها."},
}


def name(field, lang):
    n = NAMES.get(field, (field, field, ""))
    return n[1] if lang == "ar" else n[0]


def unit(field):
    return NAMES.get(field, ("", "", ""))[2]


def status(field, value, ref):
    """The lab's own range decides. 'Borderline' is kept for bands guidelines name as such."""
    if field == "hba1c" and not ref:
        return "high" if value >= 6.5 else "borderline" if value >= 5.7 else "normal"
    lo, hi = (ref.get("low"), ref.get("high")) if ref else TYPICAL.get(field, (None, None))
    if lo is not None and value < lo:
        return "low"
    if hi is not None and value > hi:
        return "high"
    return "normal"


def notes(field, ctx, lab_flag, lang):
    t, out = TXT[lang], []
    ab = ctx.get("abstinence_days")
    if field in SEMEN and ab is not None:
        if ab < 2:
            out.append(t["abst_short"])
        elif ab > 7:
            out.append(t["abst_long"])
    if field in SEMEN and ctx.get("fever_recent"):
        out.append(t["fever"])
    if field == "testosterone" and ctx.get("time"):
        try:
            if int(ctx["time"][:2]) >= 11:
                out.append(t["t_time"])
        except ValueError:
            pass
    if lab_flag:
        out.append(t["flag"])
    return out


def point(row, detail, lang, review_note=None):
    ref = detail.get("ref")
    ctx = detail.get("context") or {}
    return {"id": row["id"], "field": row["field"], "name": name(row["field"], lang), "value": row["value"], "unit": unit(row["field"]),
            "date": row["collected_on"], "ref": ref, "ref_used": "lab" if ref else "typical",
            "status": status(row["field"], row["value"], ref), "lab_flag": detail.get("lab_flag"), "source": detail.get("source", "report"),
            "lab_name": detail.get("lab_name"), "context": ctx, "notes": notes(row["field"], ctx, detail.get("lab_flag"), lang),
            "review_status": row["review_status"], "review_note": review_note, "edited_by_user": bool(detail.get("edited_by_user")),
            "assessment_id": row["assessment_id"]}


def series(points, lang):
    t, by = TXT[lang], {}
    for p in sorted(points, key=lambda p: (p["date"] or "0000", p["id"])):
        by.setdefault(p["field"], []).append(p)
    out = []
    order = list(NAMES)
    for field in sorted(by, key=lambda f: order.index(f) if f in order else 99):
        pts = by[field]
        good = [p for p in pts if p["review_status"] != "rejected"]
        latest = good[-1] if good else None
        change, advice = None, []
        if len(good) >= 2:
            a, b = good[-2], good[-1]
            diff = round(b["value"] - a["value"], 2)
            pct = round(100 * diff / a["value"], 1) if a["value"] else None
            if abs(diff) < 1e-9:
                direction = "same"
            elif field in HIGHER_BETTER:
                direction = "better" if diff > 0 else "worse"
            elif field in LOWER_BETTER:
                direction = "better" if diff < 0 else "worse"
            else:
                direction = "changed"
            change = {"diff": diff, "pct": pct, "direction": direction, "since": a["date"]}
            if len({p["lab_name"] or p["source"] for p in good}) > 1:
                advice.append(t["labs"])
            if direction == "worse":
                advice.append(t["worse"])
        elif latest and field in SEMEN and latest["status"] in ("low", "high"):
            advice.append(t["repeat"])
        out.append({"field": field, "name": name(field, lang), "unit": unit(field), "points": pts, "latest": latest,
                    "change": change, "advice": advice, "higher_is_better": field in HIGHER_BETTER, "lower_is_better": field in LOWER_BETTER,
                    "forecast": forecast(field, good, lang)})
    return out


# ------------------------------------------------------------------ predictive: where each result is heading
RETEST_DAYS = 90       # sperm take about 74 days to develop; blood markers are usually re-checked at about 3 months
HORIZON_DAYS = 365
FC = {
    "en": {"one": "One result so far. A second test in about 3 months shows which way it is moving.",
           "proj": lambda v, u, lo, hi, d: f"If this trend continues: about {v} {u} by {d} (likely {lo}–{hi}).",
           "below": lambda d: f"On this trend it would fall below the lab's lower limit around {d}.",
           "above": lambda d: f"On this trend it would rise above the lab's upper limit around {d}.",
           "into": lambda d: f"On this trend it would be back in the lab's range around {d}.",
           "flat": "Stable: no clear change between your results.",
           "already": {"below": "On this trend it may already be below the lab's lower limit. A new test would show where it is now.",
                       "above": "On this trend it may already be above the lab's upper limit. A new test would show where it is now.",
                       "into": "On this trend it may already be back in the lab's range. A new test would confirm it."},
           "due_now": "Your next test is due now.",
           "caveat": "A straight line through your own results, not a diagnosis. Two results make a rough guide; three or more are better.",
           "age": lambda a: f"Age on the report: {a}."},
    "ar": {"one": "نتيجة واحدة حتى الآن. فحص ثانٍ بعد نحو ٣ أشهر يُظهر اتجاهها.",
           "proj": lambda v, u, lo, hi, d: f"إذا استمر هذا الاتجاه: نحو {v} {u} بحلول {d} (على الأرجح بين {lo} و{hi}).",
           "below": lambda d: f"على هذا الاتجاه ستنخفض تحت الحد الأدنى للمختبر نحو {d}.",
           "above": lambda d: f"على هذا الاتجاه سترتفع فوق الحد الأعلى للمختبر نحو {d}.",
           "into": lambda d: f"على هذا الاتجاه ستعود إلى معدل المختبر نحو {d}.",
           "flat": "مستقرة: لا تغيّر واضح بين نتائجك.",
           "already": {"below": "على هذا الاتجاه قد تكون الآن تحت الحد الأدنى للمختبر. فحص جديد يُظهر قيمتها الحالية.",
                       "above": "على هذا الاتجاه قد تكون الآن فوق الحد الأعلى للمختبر. فحص جديد يُظهر قيمتها الحالية.",
                       "into": "على هذا الاتجاه قد تكون عادت الآن إلى معدل المختبر. فحص جديد يؤكد ذلك."},
           "due_now": "حان موعد فحصك القادم.",
           "caveat": "خط مستقيم عبر نتائجك أنت، وليس تشخيصاً. نتيجتان تعطيان فكرة تقريبية، وثلاث أو أكثر أفضل.",
           "age": lambda a: f"العمر في التقرير: {a}."},
}


def _days(iso):
    from datetime import date
    y, m, d = (int(x) for x in iso.split("-"))
    return date(y, m, d).toordinal()


def _iso(n):
    from datetime import date
    return date.fromordinal(int(round(n))).isoformat()


AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
EN_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _human(iso, lang):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {AR_MONTHS[m - 1]} {y}" if lang == "ar" else f"{d} {EN_MONTHS[m - 1]} {y}"


def forecast(field, pts, lang):
    """Linear trend through his own dated results: the value expected at the next re-test, a likely range, and when
    (within a year) the trend would cross the lab's limit. One result gives only the re-test date."""
    t = FC["ar" if lang == "ar" else "en"]
    pts = [p for p in pts if p.get("date")]
    if not pts:
        return None
    last = pts[-1]
    nxt = _days(last["date"]) + RETEST_DAYS
    out = {"next_test": _iso(nxt), "caveat": t["caveat"]}
    ages = [p["context"].get("age") for p in pts if p.get("context", {}).get("age")]
    if ages:
        out["age"] = ages[-1]
    if len(pts) < 2:
        out["text"] = t["one"]
        return out
    xs = [_days(p["date"]) for p in pts]
    ys = [p["value"] for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((a - mx) ** 2 for a in xs) or 1
    slope = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sxx
    icpt = my - slope * mx
    resid = [b - (icpt + slope * a) for a, b in zip(xs, ys)]
    sd = (sum(r * r for r in resid) / max(1, len(xs) - 2)) ** 0.5 if len(xs) > 2 else abs(ys[-1] - ys[-2]) * 0.35
    proj = icpt + slope * nxt
    spread = max(sd * 1.5, abs(proj) * 0.05)
    floor = 0
    lo_v, hi_v = max(floor, proj - spread), proj + spread
    r = lambda v: round(v, 2 if abs(v) < 10 else 1)
    out.update(projected=r(max(floor, proj)), low=r(lo_v), high=r(hi_v), slope_per_90d=r(slope * 90))
    if abs(slope * 90) < max(0.03 * abs(my), 1e-6):
        out["direction"] = "flat"
        out["text"] = t["flat"]
        return out
    out["direction"] = "up" if slope > 0 else "down"
    texts = [t["proj"](out["projected"], unit(field), out["low"], out["high"], _human(_iso(nxt), lang))]
    ref = last.get("ref") or {}
    lo, hi = (ref.get("low"), ref.get("high")) if ref else TYPICAL.get(field, (None, None))
    now_x = xs[-1]
    cross = None
    for limit, kind in ((lo, "lo"), (hi, "hi")):
        if limit is None or slope == 0:
            continue
        at = (limit - icpt) / slope
        if now_x < at <= now_x + HORIZON_DAYS:
            cur = ys[-1]
            if kind == "lo":
                cross = ("below" if cur >= limit and slope < 0 else "into" if cur < limit and slope > 0 else None, at)
            else:
                cross = ("above" if cur <= limit and slope > 0 else "into" if cur > limit and slope < 0 else None, at)
            if cross[0]:
                break
            cross = None
    from datetime import date as _date
    today = _date.today().toordinal()
    if cross:
        already = cross[1] <= today
        out["crosses"] = {"kind": cross[0], "date": _iso(cross[1]), "already": already}
        texts.append(t["already"][cross[0]] if already else t[cross[0]](_human(_iso(cross[1]), lang)))
    if nxt <= today:
        out["due_now"] = True
        texts.append(t["due_now"])
    out["text"] = " ".join(texts)
    return out


def dashboard(series, lang):
    """Top of the results page: how many results, how many in range, what is moving, and when the next test is due."""
    latest = [s["latest"] for s in series if s["latest"]]
    moving = [s for s in series if s.get("forecast") and s["forecast"].get("direction") in ("up", "down")]
    worse = [s["name"] for s in series if s["change"] and s["change"]["direction"] == "worse"]
    better = [s["name"] for s in series if s["change"] and s["change"]["direction"] == "better"]
    nexts = sorted(s["forecast"]["next_test"] for s in series if s.get("forecast"))
    alerts = [{"name": s["name"], **s["forecast"]["crosses"]} for s in series if s.get("forecast") and s["forecast"].get("crosses")]
    ages = [s["forecast"]["age"] for s in series if s.get("forecast") and s["forecast"].get("age")]
    from datetime import date as _date
    return {"results": sum(len(s["points"]) for s in series), "tests": len(series),
            "next_test_due_now": bool(nexts) and nexts[0] <= _date.today().isoformat(),
            "in_range": sum(1 for p in latest if p["status"] == "normal"), "out_of_range": sum(1 for p in latest if p["status"] != "normal"),
            "improving": better, "worsening": worse, "trending": len(moving), "next_test": nexts[0] if nexts else None,
            "alerts": alerts, "age": ages[-1] if ages else None}
