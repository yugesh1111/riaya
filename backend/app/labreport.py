"""Lab report reader. Turns a PDF or pasted / OCR'd text into values for the man to check.

Nothing here is saved: the file is read in memory and discarded. Each value carries the line it was
read from, the lab's own printed reference range (when there is one), a reading confidence and a
plausibility check, so he can compare it with his report before anything is stored.
"""
import io
import re

# field -> (target, canonical unit, plausible range, label patterns)
FIELDS = {
    "volume_ml": ("semen", "mL", (0.1, 15), [r"semen volume", r"\bvolume\b", r"حجم"]),
    "ph": ("semen", "", (6.0, 9.5), [r"\bph\b"]),
    "concentration_m_per_ml": ("semen", "M/mL", (0, 400), [r"sperm concentration", r"\bconcentration\b", r"density", r"تركيز"]),
    "total_count_m": ("semen", "M", (0, 2000), [r"total sperm count", r"total count", r"sperm count", r"العدد الكلي"]),
    "progressive_motility_pct": ("semen", "%", (0, 100), [r"progressive motility", r"\bpr\b motility", r"الحركة التقدمية"]),
    "total_motility_pct": ("semen", "%", (0, 100), [r"total motility", r"\bmotility\b", r"الحركة الكلية"]),
    "normal_forms_pct": ("semen", "%", (0, 100), [r"normal forms", r"morphology", r"normal morph", r"الأشكال الطبيعية"]),
    "vitality_pct": ("semen", "%", (0, 100), [r"vitality", r"viability", r"الحيوية"]),
    "testosterone": ("labs", "nmol/L", (0.5, 60), [r"total testosterone", r"testosterone", r"التستوستيرون"]),
    "fsh": ("labs", "IU/L", (0.1, 150), [r"\bfsh\b", r"follicle"]),
    "lh": ("labs", "IU/L", (0.1, 150), [r"\blh\b", r"luteini"]),
    "hba1c": ("labs", "%", (3.5, 18), [r"hba1c", r"a1c", r"glycated", r"السكر التراكمي"]),
    "vitamin_d": ("labs", "ng/mL", (2, 200), [r"vitamin d", r"25-?oh", r"فيتامين د"]),
}
# check order matters: "total motility" before "motility", "total sperm count" before "concentration"
ORDER = ["total_count_m", "progressive_motility_pct", "total_motility_pct", "normal_forms_pct", "vitality_pct",
         "concentration_m_per_ml", "volume_ml", "testosterone", "fsh", "lh", "hba1c", "vitamin_d", "ph"]

NUM = r"(\d+(?:[.,]\d+)?)"
REF_PATTERNS = [
    (re.compile(r"(?:ref(?:erence)?[:\s]*)?(?:>=|≥|>)\s*" + NUM), "low"),
    (re.compile(r"(?:ref(?:erence)?[:\s]*)?(?:<=|≤|<)\s*" + NUM), "high"),
    (re.compile(NUM + r"\s*[-–]\s*" + NUM), "range"),
]
FLAG = re.compile(r"\b(H|L|HIGH|LOW|ABNORMAL)\b\s*$", re.I)
NOTE = {"en": "Check every value against your report before saving. Values marked 'check' look unusual.",
        "ar": "طابق كل قيمة مع تقريرك قبل الحفظ. القيم المعلّمة «تحقق» تبدو غير معتادة."}


def _f(s):
    return float(s.replace(",", "."))


def pdf_text(raw: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join((p.extract_text() or "") for p in reader.pages[:10])


def _convert(field, value, line):
    """Returns (value in canonical unit, converted?)."""
    low = line.lower()
    if field == "testosterone" and "ng/dl" in low:
        return round(value / 28.84, 1), True
    if field == "testosterone" and "ng/ml" in low:
        return round(value * 3.467, 1), True
    if field == "hba1c" and "mmol/mol" in low:
        return round(value / 10.929 + 2.15, 1), True
    if field == "vitamin_d" and "nmol/l" in low:
        return round(value / 2.496, 1), True
    return value, False


def _unit_seen(field, line):
    low = line.lower()
    want = {"volume_ml": ["ml"], "concentration_m_per_ml": ["/ml", "10^6", "million"], "total_count_m": ["million", "10^6", " m"],
            "progressive_motility_pct": ["%"], "total_motility_pct": ["%"], "normal_forms_pct": ["%"], "vitality_pct": ["%"],
            "testosterone": ["nmol", "ng/dl", "ng/ml"], "fsh": ["iu/l", "miu/ml", "u/l"], "lh": ["iu/l", "miu/ml", "u/l"],
            "hba1c": ["%", "mmol/mol"], "vitamin_d": ["ng/ml", "nmol/l"]}.get(field, [])
    return any(w in low for w in want)


def _reference(rest):
    for rx, kind in REF_PATTERNS:
        m = rx.search(rest)
        if not m:
            continue
        if kind == "range":
            lo, hi = _f(m.group(1)), _f(m.group(2))
            if lo < hi:
                return {"low": lo, "high": hi, "text": f"{m.group(1)}-{m.group(2)}"}
        elif kind == "low":
            return {"low": _f(m.group(1)), "high": None, "text": m.group(0).replace("ref", "").replace("Ref", "").strip(" :")}
        else:
            return {"low": None, "high": _f(m.group(1)), "text": m.group(0).replace("ref", "").strip(" :")}
    return None


def _match_field(line):
    low = line.lower()
    for f in ORDER:
        for pat in FIELDS[f][3]:
            m = re.search(pat, low)
            if m:
                return f, m.end()
    return None, None


def _date(text):
    m = re.search(r"(?:collect\w*|sample|date)[^\d]{0,20}(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", text, re.I)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    return m.group(0) if m else None


def _age(text):
    """His age as printed on the report ("Age: 34 Y", "Age/Sex: 34Y/M", "العمر: 34"), if it is plausible."""
    m = re.search(r"(?:\bage\b(?:\s*/\s*(?:sex|gender))?|العمر)\s*[:\-]?\s*(\d{2})\s*(?:y|yr|yrs|years?|سنة)?\b", text, re.I)
    if m and 16 <= int(m.group(1)) <= 99:
        return int(m.group(1))
    return None


def read(text, lang="en"):
    values, seen, context = [], set(), {}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        m = re.search(r"abstinen\w*[^\d]{0,15}" + NUM + r"\s*(?:d|day)", ln, re.I)
        if m:
            context["abstinence_days"] = _f(m.group(1))
            values.append({"field": "abstinence_days", "value": _f(m.group(1)), "unit": "days", "target": "semen", "line": ln[:240],
                           "confidence": "high", "score": 0.75, "plausible": True, "reference": None, "ref": None, "lab_flag": None})
        tm = re.search(r"(?:collection|sample)\s*time[^\d]{0,10}(\d{1,2}):(\d{2})", ln, re.I)
        if tm:
            context["time"] = f"{int(tm.group(1)):02d}:{tm.group(2)}"
        if re.search(r"\bfasting\b", ln, re.I):
            context["fasting"] = not re.search(r"non[- ]?fasting|not fasting", ln, re.I)
    for ln in lines:
        field, end = _match_field(ln)
        if not field or field in seen:
            continue
        rest = ln[end:]
        nm = re.search(NUM, rest)
        if not nm:
            continue
        raw_value = _f(nm.group(1))
        target, unit, (lo, hi), _ = FIELDS[field]
        value, converted = _convert(field, raw_value, ln)
        after = rest[nm.end():]
        ref = _reference(after)
        if ref and converted:
            ref = None  # a printed range in another unit would be misleading
        flag = FLAG.search(ln)
        plausible = lo <= value <= hi
        unit_ok = _unit_seen(field, ln) or not unit
        score = 0.5 + (0.25 if unit_ok and unit else 0) + (0.15 if ref and unit else 0) - (0.1 if converted else 0)
        score = round(max(0.1, min(0.95, score)), 2)
        conf = "check" if not plausible else "high" if score >= 0.75 else "medium" if score >= 0.5 else "low"
        seen.add(field)
        values.append({"field": field, "value": value, "unit": unit, "target": target, "line": ln[:240], "confidence": conf,
                       "score": score, "plausible": plausible, "reference": ref["text"] if ref else None, "ref": ref,
                       "lab_flag": flag.group(1).upper() if flag else None})
    rank = ["volume_ml", "concentration_m_per_ml", "total_count_m", "progressive_motility_pct", "total_motility_pct", "normal_forms_pct",
            "vitality_pct", "ph", "abstinence_days", "testosterone", "fsh", "lh", "hba1c", "vitamin_d"]
    values.sort(key=lambda v: rank.index(v["field"]))
    kind = "semen" if any(v["target"] == "semen" and v["field"] != "abstinence_days" for v in values) else "blood"
    table = sum(1 for ln in lines if ("|" in ln or "\t" in ln)) >= 3
    return {"values": values, "date": _date(text), "age": _age(text), "context": context, "table": table, "kind": kind,
            "note": NOTE["ar" if lang == "ar" else "en"]}
