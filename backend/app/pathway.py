"""The connected referral journey: from first check to specialist visit and follow-up.

One pathway per check, with the same eight stages for the man, his doctor and the coordinator:
  check -> doctor review -> clinic chosen -> appointment confirmed -> specialist visit -> visit outcome
  -> follow-up -> re-check at about 3 months.
Each stage is 'done', 'current', 'upcoming', 'skipped' (not needed for his level) or 'stopped' (he could not go).
The coordinator board lists cases that have stalled at a stage, so someone reaches out before he drops out.
"""
import time

RECHECK_DAYS = 90
STAGES = ["check", "review", "clinic", "appointment", "visit", "outcome", "followup", "recheck"]
LABELS = {
    "en": {"check": "Check completed", "review": "Doctor review", "clinic": "Clinic chosen", "appointment": "Appointment confirmed",
           "visit": "Specialist visit", "outcome": "Visit summary and plan", "followup": "Follow-up", "recheck": "Re-check in about 3 months"},
    "ar": {"check": "اكتمل الفحص", "review": "مراجعة الطبيب", "clinic": "اختيار العيادة", "appointment": "تأكيد الموعد",
           "visit": "زيارة المختص", "outcome": "ملخص الزيارة والخطة", "followup": "المتابعة", "recheck": "فحص متابعة بعد نحو ٣ أشهر"},
}
NEXT_ACTION = {
    "en": {"review": "A doctor is looking at your summary.", "clinic": "Choose a clinic for your visit.",
           "appointment": "The coordinator is agreeing a time with the clinic.", "visit": "Go to your appointment, then tell us how it went.",
           "outcome": "Waiting for the specialist's visit summary.", "followup": "Your follow-up is booked in your plan.",
           "recheck": "Repeat your check to see what changed."},
    "ar": {"review": "يراجع طبيب ملخصك الآن.", "clinic": "اختر عيادة لزيارتك.", "appointment": "يتفق المنسّق مع العيادة على موعد.",
           "visit": "اذهب إلى موعدك، ثم أخبرنا كيف كان.", "outcome": "بانتظار ملخص زيارة المختص.", "followup": "متابعتك مدرجة في خطتك.",
           "recheck": "أعد الفحص لترى ما تغيّر."},
}
# coordinator thresholds (days at a stage before someone reaches out)
STALL = {"review": 2, "clinic": 7, "appointment": 3, "visit": 1, "outcome": 7, "followup": 0}
STALL_TEXT = {"review": "Waiting for doctor review", "clinic": "Approved but no clinic chosen", "appointment": "Clinic request not confirmed",
              "visit": "Appointment date passed, no outcome", "outcome": "Seen, but no visit summary recorded", "followup": "Follow-up overdue"}
NUDGE = {
    "clinic": ("تمت الموافقة على خطوتك التالية. يمكنك اختيار عيادة من «مساري» متى كنت مستعداً، أو مراسلتنا إن كان هناك ما يمنعك. / "
               "Your next step is approved. Choose a clinic from My journey when you're ready, or message us if something is in the way."),
    "visit": ("كيف كان موعدك؟ أخبرنا من «مساري» إن ذهبت، أو اختر وقتاً آخر إن لم تتمكن. / "
              "How did your appointment go? Tell us in My journey, or pick another time if you couldn't go."),
    "followup": ("حان وقت متابعتك. افتح «مساري» لترى ما اتفقت عليه مع المختص. / "
                 "It's time for your follow-up. Open My journey to see what you agreed with the specialist."),
    "recheck": ("مرّت ثلاثة أشهر تقريباً. فحص متابعة قصير يُظهر ما تغيّر. / "
                "About three months have passed. A short follow-up check shows what has changed."),
}


def stages(row, ref, appt, consult, level, lang="en"):
    """Returns the ordered stages with status, time and a one-line next action for the current one."""
    L = "ar" if lang == "ar" else "en"
    now = time.time()
    st = {s: {"key": s, "label": LABELS[L][s], "status": "upcoming", "at": None} for s in STAGES}
    st["check"].update(status="done", at=row["completed_at"])
    needs_visit = level not in ("self_care", "emergency") and ref is not None and (ref["status"] != "rejected")
    if not needs_visit:
        for s in ("review", "clinic", "appointment", "visit", "outcome", "followup"):
            st[s]["status"] = "skipped"
        if ref and ref["reviewed_at"]:
            st["review"].update(status="done", at=ref["reviewed_at"])
    else:
        if ref["reviewed_at"]:
            st["review"].update(status="done", at=ref["reviewed_at"])
        elif ref["status"] == "suggested":
            st["review"]["status"] = "skipped"  # no review consent: he goes straight to choosing a clinic
        if appt:
            st["clinic"].update(status="done", at=appt["created_at"])
        elif ref["booked_at"]:
            st["clinic"].update(status="done", at=ref["booked_at"])
        if (appt and appt["status"] in ("confirmed", "attended")) or ref["booked_at"]:
            st["appointment"].update(status="done", at=ref["booked_at"] or (appt and appt["updated_at"]), slot_at=appt["slot_at"] if appt else None)
        if ref["attended_at"]:
            st["visit"].update(status="done", at=ref["attended_at"])
        if consult:
            st["outcome"].update(status="done", at=consult["created_at"])
            if consult["followup_at"]:
                st["followup"].update(status="done" if consult["followup_done_at"] else "upcoming",
                                      at=consult["followup_done_at"] or consult["followup_at"], due=consult["followup_at"])
            else:
                st["followup"]["status"] = "skipped"
        elif ref["tests_done_at"] or ref["followup_at"]:
            st["outcome"].update(status="done", at=ref["tests_done_at"] or ref["followup_at"])
        if ref["followup_at"]:
            st["followup"].update(status="done", at=ref["followup_at"])
        if ref["status"] == "declined":
            nxt = next((s for s in STAGES if st[s]["status"] == "upcoming"), None)
            if nxt:
                st[nxt].update(status="stopped", barrier=ref["barrier"])
    due = row["completed_at"] + RECHECK_DAYS * 86400
    st["recheck"].update(due=due)
    current = next((s for s in STAGES if st[s]["status"] == "upcoming"), None)
    if current:
        st[current]["status"] = "current"
        st[current]["next_action"] = NEXT_ACTION[L].get(current)
        if current == "recheck" and now < due:
            st[current]["status"] = "upcoming"
            current = None
    return [st[s] for s in STAGES], current


def stalled(stage_list, current, appt=None, consult=None):
    """(stage, days stalled) when the man has been at the current stage longer than the threshold."""
    if not current or current not in STALL:
        return None
    now = time.time()
    done_before = [s for s in stage_list if s["status"] == "done" and s["at"]]
    since = max((s["at"] for s in done_before), default=now)
    if current == "visit" and appt and appt["slot_at"]:
        since = appt["slot_at"]
    if current == "followup" and consult and consult["followup_at"]:
        since = consult["followup_at"]
    days = (now - since) / 86400
    return (current, round(days, 1)) if days >= STALL[current] else None
