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
           "nudge_sent": "Your care team sent a reminder", "clinic_view": "The clinic opened your referral with your handover code",
           "clinic_attendance": "The clinic recorded whether you attended", "clinic_message": "The clinic sent you a message",
           "finding_agree": "A doctor agreed with a finding in your summary", "finding_disagree": "A doctor questioned a finding in your summary"},
    "ar": {"view_case": "فتح طبيب ملخصك", "open_share": "فتحت عيادة ملخصك برمز التسليم",
           "handover_generated": "أُعدّت رسالة إحالة للعيادة", "view_labs": "اطّلع طبيب على نتائج فحوصاتك",
           "review_approve": "وافق طبيب على خطوتك التالية", "review_modify": "غيّر طبيب خطوتك التالية",
           "review_reject": "راجع طبيب ملخصك", "message_sent": "أرسل لك طبيب رسالة", "video_created": "فتح طبيب غرفة مرئية",
           "consultation_recorded": "سجّل المختص زيارتك", "lab_accepted": "تحقق طبيب من قيمة مخبرية",
           "lab_corrected": "صحّح طبيب قيمة مخبرية", "lab_rejected": "استبعد طبيب قيمة مخبرية", "voice_note_sent": "أرسل لك طبيب رسالة صوتية",
           "appointment_confirm": "أكّد المنسّق موعدك", "appointment_decline": "اعتذرت عيادة عن الطلب", "nudge_sent": "أرسل فريق الرعاية تذكيراً",
           "clinic_view": "فتحت العيادة إحالتك برمز التسليم", "clinic_attendance": "سجّلت العيادة حضورك من عدمه", "clinic_message": "أرسلت لك العيادة رسالة",
           "finding_agree": "وافق طبيب على نتيجة في ملخصك", "finding_disagree": "راجع طبيب نتيجة في ملخصك"},
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
    return [{"ts": r["ts"], "who": "you" if r["actor"] == "user" else ("clinic" if r["actor"].startswith("clinic:") else "clinician"), "action": r["action"],
             "text": L.get(r["action"], r["action"].replace("_", " "))} for r in rows if r["action"] in L]


# ------------------------------------------------------------------ one switch to pause all sharing, and how long data is kept
RETENTION = [None, 3, 6, 12, 24]  # months after his last visit to the app; None = until he deletes it


def privacy(c, user_id):
    r = c.execute("SELECT sharing_paused, retention_months, last_active, reminders FROM users WHERE id=?", (user_id,)).fetchone()
    last = r["last_active"] if r else None
    months = r["retention_months"] if r else None
    return {"paused": bool(r and r["sharing_paused"]), "reminders": bool(r is None or r["reminders"] is None or r["reminders"]),
            "retention_months": months, "retention_options": RETENTION,
            "delete_after": (last + months * 30 * 86400) if (last and months) else None}


def set_privacy(c, user_id, paused=None, retention_months=-1, reminders=None):
    old = privacy(c, user_id)
    if reminders is not None and reminders != old["reminders"]:
        c.execute("UPDATE users SET reminders=? WHERE id=?", (1 if reminders else 0, user_id))
        receipt(c, user_id, "reminders", "granted" if reminders else "withdrawn")
    if paused is not None and paused != old["paused"]:
        c.execute("UPDATE users SET sharing_paused=? WHERE id=?", (1 if paused else 0, user_id))
        receipt(c, user_id, "all_sharing", "paused" if paused else "resumed")
    if retention_months != -1 and retention_months != old["retention_months"]:
        if retention_months not in RETENTION:
            raise ValueError("retention")
        c.execute("UPDATE users SET retention_months=? WHERE id=?", (retention_months, user_id))
        receipt(c, user_id, "retention", "changed", {"months": retention_months})
    return privacy(c, user_id)


def is_paused(c, user_id):
    r = c.execute("SELECT sharing_paused FROM users WHERE id=?", (user_id,)).fetchone()
    return bool(r and r["sharing_paused"])


def expired_users(c, now):
    return [r["id"] for r in c.execute("SELECT id FROM users WHERE retention_months IS NOT NULL AND last_active IS NOT NULL "
                                       "AND last_active + retention_months * 30 * 86400 < ?", (now,)).fetchall()]


def scope_of(c, share_row, user_id):
    """What a code shows: the categories he picked for that code, or his clinic choices for a clinic code."""
    if share_row["scope"]:
        return sorted(set(json.loads(share_row["scope"])) & set(CATEGORIES) | REQUIRED, key=CATEGORIES.index)
    return get(c, user_id)["clinic"]
