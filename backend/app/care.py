"""Care Connect: from an approved referral to a confirmed, attended visit.

No availability is shown or invented. He picks a clinic and his preferred times; a coordinator agrees a
slot with the clinic and confirms it; he gets a message and a calendar entry that says only 'Appointment'.
"""
import json
from datetime import datetime, timedelta, timezone

from . import security

SEED = [
    ("ccad", "Cleveland Clinic Abu Dhabi", "كليفلاند كلينك أبوظبي", "Al Maryah Island, Abu Dhabi", "جزيرة الماريه، أبوظبي",
     "private", ["urology"], "https://www.clevelandclinicabudhabi.ae"),
    ("ahs", "SEHA primary healthcare centres", "مراكز الرعاية الصحية الأولية التابعة لصحة", "Abu Dhabi, Al Ain and Al Dhafra",
     "أبوظبي والعين والظفرة", "public", ["primary"], "https://www.seha.ae"),
    ("skmc", "Sheikh Khalifa Medical City", "مدينة الشيخ خليفة الطبية", "Abu Dhabi city", "مدينة أبوظبي", "public",
     ["urology", "emergency"], "https://www.seha.ae"),
    ("ssmc", "Sheikh Shakhbout Medical City", "مدينة الشيخ شخبوط الطبية", "Abu Dhabi city", "مدينة أبوظبي", "public",
     ["urology", "emergency"], "https://www.ssmc.ae"),
    ("tawam", "Tawam Hospital", "مستشفى توام", "Al Ain", "العين", "public", ["urology", "emergency"], "https://www.seha.ae"),
]
LEVEL_KINDS = {"primary_care": "primary", "same_day_primary": "primary", "andrology": "urology",
               "fertility_services": "urology", "urgent_specialist": "urology", "emergency": "emergency"}
MISSED = ["cost", "time", "embarrassment", "distance", "waiting_list", "partner", "not_needed", "other",
          "forgot", "clinic_cancelled", "felt_better"]
BARRIERS = ["cost", "time", "embarrassment", "distance", "waiting_list", "partner", "not_needed", "other"]
DECLINE = ["not_accepting", "wrong_service", "no_slots", "insurance", "other"]
SHARE_DAYS = 14


# Public appointment lines, from each organisation's own website (checked November 2026).
# Cleveland Clinic Abu Dhabi: 800 8 2223 (Contact Center). SEHA facilities: 80050 (call centre) and WhatsApp 02 410 2200.
CONTACT = {"ccad": ("800 8 2223", None), "ahs": ("80050", "+97124102200"), "skmc": ("80050", "+97124102200"),
           "ssmc": ("80050", "+97124102200"), "tawam": ("80050", "+97124102200")}


def seed(c):
    for p in SEED:
        if not c.execute("SELECT 1 FROM providers WHERE id=?", (p[0],)).fetchone():
            c.execute("INSERT INTO providers (id,name_en,name_ar,area,area_ar,sector,kinds,website) VALUES (?,?,?,?,?,?,?,?)",
                      (*p[:6], json.dumps(p[6]), p[7]))
    for pid, (phone, wa) in CONTACT.items():
        c.execute("UPDATE providers SET phone=COALESCE(phone, ?), whatsapp=COALESCE(whatsapp, ?) WHERE id=?", (phone, wa, pid))


def provider_view(r, lang="en", staff=False):
    out = {"id": r["id"], "name": r["name_ar"] if lang == "ar" else r["name_en"], "name_en": r["name_en"], "name_ar": r["name_ar"],
           "area": r["area_ar"] if lang == "ar" else r["area"], "sector": r["sector"], "kinds": json.loads(r["kinds"]),
           "website": r["website"], "confirmed_at": r["confirmed_at"], "confirm_note": r["confirm_note"],
           "phone": r["phone"] if "phone" in r.keys() else None, "whatsapp": r["whatsapp"] if "whatsapp" in r.keys() else None}
    if staff:
        out.update(active=bool(r["active"]), confirmed_by=r["confirmed_by"], area_ar=r["area_ar"])
    return out


def providers_for(c, level, lang):
    rows = c.execute("SELECT * FROM providers WHERE active=1 ORDER BY rowid").fetchall()
    kind = LEVEL_KINDS.get(level) if level else None
    if level and not kind:
        return []
    return [provider_view(r, lang) for r in rows if not kind or kind in json.loads(r["kinds"])]


def appt_view(c, a, lang="en"):
    if not a:
        return None
    p = c.execute("SELECT * FROM providers WHERE id=?", (a["provider_id"],)).fetchone()
    prefs = security.unseal(a["prefs"]) or {}
    return {"id": a["id"], "status": a["status"], "provider": provider_view(p, lang) if p else None, "created_at": a["created_at"],
            "updated_at": a["updated_at"], "slot_at": a["slot_at"], "place_note": a["place_note"], "reason": a["reason"],
            "share_code": a["share_code"], "times": prefs.get("times", []), "days": prefs.get("days", []), "contact": prefs.get("contact", "messages")}


def stage(level, referral, appt):
    if level == "emergency":
        return "emergency"
    if level == "self_care":
        return "not_needed"
    if not referral:
        return "no_referral"
    if referral["status"] == "pending_review":
        return "awaiting_review"
    if referral["status"] == "rejected":
        return "not_needed"
    if appt and appt["status"] in ("requested", "confirmed", "attended"):
        return appt["status"]
    return "choose"


def ics(appt_id, slot_at, place):
    """'Appointment' and the place: nothing private on a lock screen."""
    start = datetime.fromtimestamp(slot_at, timezone.utc)
    fmt = lambda d: d.strftime("%Y%m%dT%H%M%SZ")
    return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Riaya//Care Connect//EN", "BEGIN:VEVENT",
                        f"UID:{appt_id}@riaya", f"DTSTAMP:{fmt(datetime.now(timezone.utc))}", f"DTSTART:{fmt(start)}",
                        f"DTEND:{fmt(start + timedelta(minutes=45))}", "SUMMARY:Appointment", f"LOCATION:{place}",
                        "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Appointment", "TRIGGER:-PT2H", "END:VALARM",
                        "END:VEVENT", "END:VCALENDAR", ""])
