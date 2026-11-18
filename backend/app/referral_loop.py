"""Closed-loop referral tracking: risk-tiered time limits, escalation, and the referral's status as a FHIR R4 Task.

Every referral carries a deadline for each milestone that depends on how urgent it is. When a milestone is late it
escalates: first to the coordinator, then to the clinical lead. The same state is published as a FHIR Task
(status + businessStatus) that points at the ServiceRequest, so a hospital system or a health information exchange
(Malaffi in Abu Dhabi, NABIDH in Dubai, Riayati for the Ministry of Health and Prevention emirates) can follow the referral
until the loop closes. Riaya is not connected to these exchanges; the Task is ready for that integration.
"""
import time
import uuid
from datetime import datetime, timezone

H = 3600
D = 86400
# level -> (priority, {milestone: seconds after the previous milestone})
SLA = {
    "emergency": ("stat", {}),
    "urgent_specialist": ("urgent", {"review": 4 * H, "appointment": 24 * H, "outcome": 2 * D}),
    "same_day_primary": ("urgent", {"review": 4 * H, "appointment": 12 * H, "outcome": 2 * D}),
    "andrology": ("routine", {"review": 48 * H, "appointment": 14 * D, "outcome": 7 * D}),
    "fertility_services": ("routine", {"review": 48 * H, "appointment": 14 * D, "outcome": 7 * D}),
    "primary_care": ("routine", {"review": 48 * H, "appointment": 14 * D, "outcome": 7 * D}),
}
LABEL = {"review": "Doctor review", "appointment": "Appointment confirmed", "outcome": "Visit summary returned"}
ESCALATE = [(1.0, "coordinator"), (2.0, "clinical_lead")]   # late by 1x the limit -> coordinator; 2x -> clinical lead

# pathway stage -> (FHIR Task.status, businessStatus)
TASK_STATUS = {
    "review": ("requested", "awaiting-clinician-review"),
    "clinic": ("accepted", "awaiting-clinic-choice"),
    "appointment": ("accepted", "awaiting-appointment"),
    "visit": ("in-progress", "appointment-booked"),
    "outcome": ("in-progress", "seen-awaiting-summary"),
    "followup": ("completed", "summary-returned-follow-up-planned"),
    "recheck": ("completed", "loop-closed"),
    None: ("completed", "loop-closed"),
}


def milestones(level, stage_list, ref, now=None):
    """Each milestone with its deadline, when it was met, and whether it is late and who it escalates to."""
    now = now or time.time()
    prio, limits = SLA.get(level, ("routine", {}))
    st = {s["key"]: s for s in stage_list}
    out, start = [], (ref["created_at"] if ref else None)
    order = [("review", "review"), ("appointment", "appointment"), ("outcome", "outcome")]
    for key, stage in order:
        if key not in limits or start is None:
            continue
        s = st.get(stage, {})
        if s.get("status") == "skipped":
            continue
        due = start + limits[key]
        done = s.get("at") if s.get("status") == "done" else None
        late_by = ((done or now) - due)
        esc = None
        if not done and late_by > 0:
            esc = "coordinator"
            for mult, who in ESCALATE:
                if late_by >= mult * limits[key]:
                    esc = who
        out.append({"key": key, "label": LABEL[key], "due_at": due, "done_at": done, "limit_hours": round(limits[key] / H),
                    "on_time": None if not done else done <= due, "overdue": bool(not done and now > due), "escalate_to": esc})
        start = done or due if key != "review" else (done or due)
        if key == "appointment" and st.get("visit", {}).get("at"):
            start = st["visit"]["at"]
    return {"priority": prio, "milestones": out,
            "overdue": [m for m in out if m["overdue"]], "met_on_time": sum(1 for m in out if m["on_time"]),
            "closed": bool(st.get("outcome", {}).get("status") == "done")}


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z") if ts else None


def fhir_task(aid, level, stage_list, current, ref, loop):
    """FHIR R4 Task tracking the referral (focus: the ServiceRequest in the pre-screen bundle)."""
    status, business = TASK_STATUS.get(current, TASK_STATUS[None])
    if ref and ref["status"] == "rejected":
        status, business = "rejected", "clinician-declined-referral"
    elif ref and ref["status"] == "declined":
        status, business = "on-hold", "patient-could-not-attend"
    if level in ("self_care", None):
        status, business = "cancelled", "no-referral-needed"
    last = max([s["at"] for s in stage_list if s.get("at") and s["status"] == "done"], default=ref["created_at"] if ref else time.time())
    task = {
        "resourceType": "Task", "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"riaya-task-{aid}")),
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/Task"]},
        "identifier": [{"system": "urn:riaya:referral", "value": aid}],
        "status": status, "businessStatus": {"text": business}, "intent": "order", "priority": loop["priority"],
        "code": {"coding": [{"system": "http://hl7.org/fhir/CodeSystem/task-code", "code": "fulfill"}]},
        "description": "Close the loop on a men's reproductive-health referral",
        "focus": {"reference": f"ServiceRequest/{aid}"},
        "for": {"identifier": {"system": "urn:riaya:pseudonym", "value": aid[:8]}},
        "authoredOn": _iso(ref["created_at"]) if ref else None, "lastModified": _iso(last),
        "restriction": {"period": {"end": _iso(next((m["due_at"] for m in loop["milestones"] if not m["done_at"]), None))}} if loop["milestones"] else None,
        "input": [{"type": {"text": m["label"] + " due"}, "valueDateTime": _iso(m["due_at"])} for m in loop["milestones"]],
        "output": [{"type": {"text": m["label"]}, "valueDateTime": _iso(m["done_at"])} for m in loop["milestones"] if m["done_at"]],
        "note": [{"text": f"Escalated to {m['escalate_to'].replace('_', ' ')}: {m['label']} overdue"} for m in loop["overdue"] if m["escalate_to"]],
    }
    return {k: v for k, v in task.items() if v not in (None, [], {})}
