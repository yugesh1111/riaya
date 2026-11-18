"""Consent-based sharing across the care pathway.

He decides, per recipient, which parts of his record each one may see:
  - the Riaya review doctor (needs his clinician-review consent at all),
  - the clinic he chooses (through the one-time handover code),
The summary itself (next step, signals, reasons) always travels, because a referral is unsafe without it.
Everything else is opt-in per recipient and can be changed or withdrawn at any time; the change applies at
once to every open case and every handover code. Each change leaves a consent receipt he can download.
"""
import json
import time
import uuid

from . import security

CATEGORIES = ["summary", "answers", "devices", "labs", "plan"]
RECIPIENTS = ["doctor", "clinic"]
DEFAULTS = {"doctor": ["summary", "answers", "devices", "labs", "plan"], "clinic": ["summary", "labs"]}
REQUIRED = {"summary"}

LABELS = {
    "en": {"summary": "Summary: next step, signals and the reasons for them", "answers": "My questionnaire answers",
           "devices": "Watch, phone and glucose-sensor data", "labs": "Lab and test results", "plan": "My 12-week plan and check-ins",
           "doctor": "Riaya review doctor", "clinic": "The clinic I choose", "partner": "My wife (status only)",
           "research": "Anonymous service improvement", "ifhas": "IFHAS screening visit (file I download)"},
    "ar": {"summary": "الملخص: الخطوة التالية والمؤشرات وأسبابها", "answers": "إجاباتي على الاستبيان",
           "devices": "بيانات الساعة والهاتف وجهاز قياس السكر", "labs": "نتائج المختبر والفحوصات", "plan": "خطتي لمدة ١٢ أسبوعاً ومتابعاتها",
           "doctor": "طبيب المراجعة في رعاية", "clinic": "العيادة التي أختارها", "partner": "زوجتي (الحالة فقط)",
           "research": "تحسين الخدمة دون هوية", "ifhas": "زيارة فحص «إفحص» (ملف أحمّله بنفسي)"},
}


def get(c, user_id):
    r = c.execute("SELECT prefs FROM sharing WHERE user_id=?", (user_id,)).fetchone()
    prefs = security.unseal(r["prefs"]) if r else {}
    return {k: sorted(set(prefs.get(k, DEFAULTS[k])) | REQUIRED, key=CATEGORIES.index) for k in RECIPIENTS}


def receipt(c, user_id, recipient, action, scope=None):
    c.execute("INSERT INTO consent_receipts VALUES (?,?,?,?,?,?)",
              (str(uuid.uuid4()), user_id, time.time(), recipient, action, json.dumps(scope) if scope is not None else None))


def set_prefs(c, user_id, new):
    old = get(c, user_id)
    clean = {k: sorted(set(v) & set(CATEGORIES) | REQUIRED, key=CATEGORIES.index) for k, v in new.items() if k in RECIPIENTS}
    merged = {**old, **clean}
    c.execute("INSERT OR REPLACE INTO sharing VALUES (?,?,?)", (user_id, security.seal(merged), time.time()))
    for k in RECIPIENTS:
        if merged[k] != old[k]:
            added, removed = sorted(set(merged[k]) - set(old[k])), sorted(set(old[k]) - set(merged[k]))
            receipt(c, user_id, k, "changed", {"now": merged[k], "added": added, "removed": removed})
    return merged


def access_mode(c, row, clinician):
    """How this clinician reached the case: 'doctor' (his review consent) or 'clinic' (a handover code he gave)."""
    return "doctor" if row["review_consent"] else "clinic"


def filter_case(answers, result, allowed):
    """Removes what he has not shared. Returns (answers, result, withheld)."""
    withheld = [k for k in CATEGORIES if k not in allowed]
    answers = dict(answers or {})
    result = json.loads(json.dumps(result)) if result else result
    if "answers" not in allowed:
        keep = {"age", "background", "reason", "months_trying", "partner_age", "pref_language", "pref_clinician", "pref_contact", "red_flags"}
        answers = {k: v for k, v in answers.items() if k in keep}
    if result:
        drop_sources = set()
        if "devices" not in allowed:
            result["wearable"] = None
            drop_sources |= {"watch", "cgm"}
        if "labs" not in allowed:
            result["labs"], result["semen"] = None, None
            drop_sources |= {"lab", "semen"}
        if "answers" not in allowed:
            drop_sources |= {"questionnaire", "PSS-4", "PHQ-2", "AUDIT-C", "ADAM", "STOP-Bang"}
            result["instruments"] = {k: v for k, v in (result.get("instruments") or {}).items() if k in ("bmi",)}
        if drop_sources:
            hidden = "Not shared by the patient"
            for node, prov in list(result.get("provenance", {}).items()):
                kept = [p for p in prov if p["source"] not in drop_sources]
                result["provenance"][node] = kept or [{"source": "withheld", "reason": hidden}]
    return answers, result, withheld


def receipts(c, user_id, lang="en"):
    L = LABELS["ar" if lang == "ar" else "en"]
    out = []
    for r in c.execute("SELECT * FROM consent_receipts WHERE user_id=? ORDER BY ts DESC LIMIT 100", (user_id,)).fetchall():
        scope = json.loads(r["scope"]) if r["scope"] else None
        out.append({"id": r["id"], "ts": r["ts"], "recipient": r["recipient"], "recipient_label": L.get(r["recipient"], r["recipient"]),
                    "action": r["action"], "scope": scope})
    return out


ACCESS_TEXT = {
    "en": {"view_case": "A doctor opened your summary", "open_share": "A clinic opened your summary with your handover code",
           "handover_generated": "A referral letter was prepared for the clinic", "view_labs": "A doctor looked at your lab results",
           "review_approve": "A doctor approved your next step", "review_modify": "A doctor changed your next step",
           "review_reject": "A doctor reviewed your summary", "message_sent": "A doctor sent you a message",
           "video_created": "A doctor opened a video room", "consultation_recorded": "The specialist recorded your visit",
           "lab_accepted": "A doctor checked a lab value", "lab_corrected": "A doctor corrected a lab value",
           "lab_rejected": "A doctor set aside a lab value", "voice_note_sent": "A doctor sent you a voice note",
           "appointment_confirm": "The coordinator confirmed your appointment", "appointment_decline": "A clinic declined the request",
           "nudge_sent": "Your care team sent a reminder"},
    "ar": {"view_case": "فتح طبيب ملخصك", "open_share": "فتحت عيادة ملخصك برمز التسليم",
           "handover_generated": "أُعدّت رسالة إحالة للعيادة", "view_labs": "اطّلع طبيب على نتائج فحوصاتك",
           "review_approve": "وافق طبيب على خطوتك التالية", "review_modify": "غيّر طبيب خطوتك التالية",
           "review_reject": "راجع طبيب ملخصك", "message_sent": "أرسل لك طبيب رسالة", "video_created": "فتح طبيب غرفة مرئية",
           "consultation_recorded": "سجّل المختص زيارتك", "lab_accepted": "تحقق طبيب من قيمة مخبرية",
           "lab_corrected": "صحّح طبيب قيمة مخبرية", "lab_rejected": "استبعد طبيب قيمة مخبرية", "voice_note_sent": "أرسل لك طبيب رسالة صوتية",
           "appointment_confirm": "أكّد المنسّق موعدك", "appointment_decline": "اعتذرت عيادة عن الطلب", "nudge_sent": "أرسل فريق الرعاية تذكيراً"},
}


def access_log(c, user_id, lang="en"):
    """Every time someone on the care side touched his record: who (role), what, when."""
    L = ACCESS_TEXT["ar" if lang == "ar" else "en"]
    aids = [r["id"] for r in c.execute("SELECT id FROM assessments WHERE user_id=?", (user_id,)).fetchall()]
    lab_ids = [r["id"] for r in c.execute("SELECT id FROM lab_results WHERE user_id=?", (user_id,)).fetchall()]
    targets = aids + lab_ids
    if not targets:
        return []
    q = ",".join("?" * len(targets))
    rows = c.execute(f"SELECT * FROM audit WHERE target IN ({q}) ORDER BY ts DESC LIMIT 200", targets).fetchall()
    return [{"ts": r["ts"], "who": "clinician" if r["actor"] != "user" else "you", "action": r["action"],
             "text": L.get(r["action"], r["action"].replace("_", " "))} for r in rows if r["action"] in L]
