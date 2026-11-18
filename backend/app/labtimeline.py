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
                    "change": change, "advice": advice, "higher_is_better": field in HIGHER_BETTER, "lower_is_better": field in LOWER_BETTER})
    return out
