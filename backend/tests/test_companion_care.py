"""End-to-end tests for the recovered features: lab intelligence, the 12-week companion, Care Connect,
the journey, recovery codes, voice notes, WhatsApp and the programme dashboard."""
import os
import tempfile
import time
from pathlib import Path

import pytest

os.environ.setdefault("RIAYA_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASE = {"age": 34, "height_cm": 175, "weight_kg": 98, "smoking": "daily", "cigs_per_day": 15, "sitting_h": 10,
        "sleep_h": 5.5, "underwear": "tight", "snore": "yes", "tired": "yes", "observed": "no", "bp": "no",
        "pss1": 3, "pss2": 1, "pss3": 1, "pss4": 3, "phq1": 0, "phq2": 1, "reason": ["future"], "background": "arab",
        "adam1": "no", "adam2": "yes", "adam5": "yes", "adam9": "yes", "screen_bed": 2, "late_caffeine": 3}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def doc(client):
    tok = client.post("/api/clinician/login", json={"username": "clinician", "password": "demo-clinician"}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def man(client, review=True, answers=BASE):
    tok = client.post("/api/session", json={"lang": "en"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    client.post("/api/consent", json={"core": True, "clinician_review": review, "wearables": True}, headers=h)
    aid = client.post("/api/assessments?channel=web", headers=h).json()["id"]
    client.put(f"/api/assessments/{aid}/answers", json={"answers": answers}, headers=h)
    return h, aid


def test_lab_report_reader_and_timeline(client, doc):
    h, aid = man(client)
    pdf = (ROOT / "web/samples/sample_lab_report.pdf").read_bytes()
    r = client.post(f"/api/assessments/{aid}/lab-report", files={"file": ("r.pdf", pdf, "application/pdf")}, headers=h).json()
    by = {v["field"]: v for v in r["values"]}
    assert r["date"] == "2026-10-28" and r["context"]["abstinence_days"] == 3
    assert by["concentration_m_per_ml"]["value"] == 11.5 and by["concentration_m_per_ml"]["ref"]["low"] == 16
    assert by["hba1c"]["value"] == 5.9 and by["hba1c"]["ref"] is None  # converted from mmol/mol: printed range dropped
    # pasted / OCR text works too, and the man corrects one value before saving
    t = client.post(f"/api/assessments/{aid}/lab-report", data={"text": "Total testosterone 7.2 nmol/L (8.6-29) L"}, headers=h).json()
    assert t["values"][0]["lab_flag"] == "L"
    vals = [{"field": v["field"], "value": v["value"], "extracted_value": v["value"], "ref_low": (v["ref"] or {}).get("low"),
             "ref_high": (v["ref"] or {}).get("high"), "ref_text": v["reference"], "line": v["line"]} for v in r["values"] if v["field"] != "abstinence_days"]
    vals[1]["value"] = 12.0  # he changed concentration from 11.5
    saved = client.post("/api/me/labs", json={"assessment_id": aid, "collected_on": r["date"], "source": "report", "abstinence_days": 1,
                                              "values": vals}, headers=h).json()["saved"]
    client.post("/api/me/labs", json={"collected_on": "2026-12-20", "source": "manual", "values": [{"field": "concentration_m_per_ml", "value": 18}]}, headers=h)
    tl = client.get("/api/me/labs", headers=h).json()
    conc = next(s for s in tl["series"] if s["field"] == "concentration_m_per_ml")
    assert conc["points"][0]["status"] == "low" and conc["latest"]["status"] == "normal" and conc["change"]["direction"] == "better"
    assert any("under 2 days" in n for n in conc["points"][0]["notes"])  # collection check
    assert tl["pending_review"] == len(saved) + 1
    # the doctor sees what he edited and reconciles each value
    q = client.get("/api/clinician/labs/pending", headers=doc).json()["results"]
    mine = [x for x in q if x["id"] in saved]
    assert any(x["edited_by_user"] and x["extracted_value"] == 11.5 for x in mine)
    assert client.post(f"/api/clinician/labs/{mine[0]['id']}", json={"action": "correct", "value": 2.0}, headers=doc).status_code == 400
    client.post(f"/api/clinician/labs/{mine[0]['id']}", json={"action": "correct", "value": 2.0, "note": "Report says 2.0 mL"}, headers=doc)
    client.post(f"/api/clinician/labs/{mine[1]['id']}", json={"action": "reject", "note": "Different patient ID"}, headers=doc)
    pts = {p["id"]: p for s in client.get("/api/me/labs", headers=h).json()["series"] for p in s["points"]}
    assert pts[mine[0]["id"]]["value"] == 2.0 and pts[mine[0]["id"]]["review_status"] == "corrected"
    assert pts[mine[1]["id"]]["review_note"] == "Different patient ID"
    assert client.delete(f"/api/me/labs/{saved[-1]}", headers=h).json()["deleted"]


def test_lab_review_needs_consent(client, doc):
    h, aid = man(client, review=False)
    rid = client.post("/api/me/labs", json={"source": "manual", "values": [{"field": "fsh", "value": 14}]}, headers=h).json()["saved"][0]
    assert rid not in [x["id"] for x in client.get("/api/clinician/labs/pending", headers=doc).json()["results"]]
    assert client.post(f"/api/clinician/labs/{rid}", json={"action": "accept"}, headers=doc).status_code == 404


def test_explain_whatif_and_passive(client):
    h, aid = man(client, answers={**BASE, "sleep_h": 8})
    zipb = (ROOT / "web/samples/apple_health_sample.zip").read_bytes()
    w = client.post(f"/api/assessments/{aid}/wearables", files={"file": ("export.zip", zipb, "application/zip")}, headers=h).json()
    assert w["personal_baseline"]["steps"]["baseline"] == 3640.0
    p = client.post(f"/api/assessments/{aid}/passive", headers=h).json()
    assert [f["node"] for f in p["findings"]][:2] == ["sleep_loss", "sedentary"] and p["findings"][0]["sources"]
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    e = client.get(f"/api/assessments/{aid}/explain", headers=h).json()
    card = next(c for c in e["cards"] if c["node"] == "smoking")
    assert card["grade"] == "A" and card["evidence"] and card["recommendation"] and card["limitations"] == ["Based on your own answers."]
    assert {c["domain"]: c["status"] for c in e["coverage"]}["sleep"] == "measured"
    assert any("watch shows" in x["text"] for x in e["contradictions"])  # says 8 h, watch measured 6.0 h
    base = client.post(f"/api/assessments/{aid}/whatif", json={"improve": []}, headers=h).json()
    better = client.post(f"/api/assessments/{aid}/whatif", json={"improve": ["smoking", "sedentary"]}, headers=h).json()
    assert better["after"] < base["before"] and better["reduction_pct"] > 0 and "not a prediction" in better["note"]
    ar = client.get(f"/api/assessments/{aid}/explain?lang=ar", headers=h).json()
    assert "القدرة على الإنجاب" in ar["cards"][0]["relevance"]


def test_companion_with_doctor_review(client, doc):
    h, aid = man(client)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    o = client.get(f"/api/assessments/{aid}/plan-options", headers=h).json()
    assert o["max"] == 3 and o["doctor_review"] and o["options"][0]["node"] == "smoking"
    nodes = [x["node"] for x in o["options"][:3]]
    p = client.post(f"/api/assessments/{aid}/plan", json={"nodes": nodes}, headers=h).json()
    assert p["status"] == "proposed" and not p["due"]
    assert client.post("/api/me/plan/checkin", json={"items": {}}, headers=h).status_code == 400  # not started yet
    q = client.get("/api/clinician/plans", headers=doc).json()["plans"]
    mine = next(x for x in q if x["id"] == p["id"])
    assert client.post(f"/api/clinician/plans/{mine['id']}", json={"action": "change", "remove": [nodes[2]]}, headers=doc).status_code == 400
    client.post(f"/api/clinician/plans/{mine['id']}", json={"action": "change", "remove": [nodes[2]], "note": "Two goals first."}, headers=doc)
    plan = client.get("/api/me/plan", headers=h).json()["plan"]
    assert plan["status"] == "active" and plan["doctor_note"] == "Two goals first." and len(plan["items"]) == 2 and plan["due"]
    items = {i["node"]: {"adherence": 3, "value": i["measure"]["min"] + 1 if i["measure"] else None} for i in plan["items"]}
    plan = client.post("/api/me/plan/checkin", json={"items": items, "energy": 4}, headers=h).json()
    assert not plan["due"] and plan["items"][0]["summary"]["weeks_logged"] == 1 and plan["energy"][0] == 4
    assert client.post("/api/me/plan/checkin", json={"items": {"smoking": {"adherence": 2, "value": 500}}}, headers=h).status_code == 422
    client.post("/api/me/plan/reminders", json={"enabled": True}, headers=h)
    ics = client.get("/api/me/plan/reminders.ics", headers=h).text
    assert "SUMMARY:Weekly check-in" in ics and "sperm" not in ics.lower() and "RRULE:FREQ=WEEKLY" in ics
    msgs = client.get(f"/api/assessments/{aid}/messages", headers=h).json()
    assert any("12-week plan" in m["body"] for m in msgs)
    client.delete("/api/me/plan", headers=h)
    assert client.get("/api/me/plan", headers=h).json()["plan"]["status"] == "stopped"


def test_companion_self_guided(client):
    h, aid = man(client, review=False)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    nodes = [x["node"] for x in client.get(f"/api/assessments/{aid}/plan-options", headers=h).json()["options"][:1]]
    p = client.post(f"/api/assessments/{aid}/plan", json={"nodes": nodes}, headers=h).json()
    assert p["status"] == "self_guided" and p["due"]


TRYING = {**BASE, "reason": ["trying"], "months_trying": 14}


def test_care_connect_full_loop(client, doc):
    h, aid = man(client, answers=TRYING)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    assert client.get(f"/api/assessments/{aid}/care", headers=h).json()["stage"] == "awaiting_review"
    assert client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "ccad"}, headers=h).status_code == 409
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    s = client.get(f"/api/assessments/{aid}/care", headers=h).json()
    assert s["stage"] == "choose" and {p["id"] for p in s["providers"]} == {"ccad", "skmc", "ssmc", "tawam"}  # urology only
    assert client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "ahs"}, headers=h).status_code == 400
    assert client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "ccad", "contact": "phone"}, headers=h).status_code == 400
    s = client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "ccad", "times": ["morning"], "days": ["weekend"],
                                                                "contact": "phone", "phone": "+971 50 123 4567", "note": "Arabic please"}, headers=h).json()
    assert s["stage"] == "requested" and s["appointment"]["share_code"]
    code = s["appointment"]["share_code"]
    q = client.get("/api/clinician/appointments", headers=doc).json()
    a = next(x for x in q["appointments"] if x["assessment_id"] == aid)
    assert a["phone"] == "+971 50 123 4567" and a["note"] == "Arabic please" and a["times"] == ["morning"] and "insurance" in q["decline_reasons"]
    assert client.post(f"/api/clinician/appointments/{a['id']}", json={"action": "confirm"}, headers=doc).status_code == 400
    slot = time.time() + 3 * 86400
    client.post(f"/api/clinician/appointments/{a['id']}", json={"action": "confirm", "slot_at": slot, "place_note": "Urology, level 2"}, headers=doc)
    s = client.get(f"/api/assessments/{aid}/care", headers=h).json()
    assert s["stage"] == "confirmed" and s["appointment"]["slot_at"] == slot
    ics = client.get(f"/api/assessments/{aid}/appointment.ics", headers=h).text
    assert "SUMMARY:Appointment" in ics and "Cleveland" in ics and "andrology" not in ics.lower()
    # the clinic can open the summary with his one-time handover code
    assert client.post(f"/api/clinician/share/{code}", headers=doc).json()["assessment_id"] == aid
    # missed visit, reason recorded, he can choose again; then attended
    client.post(f"/api/assessments/{aid}/appointment/outcome", json={"outcome": "missed", "reason": "time"}, headers=h)
    s = client.get(f"/api/assessments/{aid}/care", headers=h).json()
    assert s["stage"] == "choose" and s["last"]["reason"] == "time"
    s = client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "skmc"}, headers=h).json()
    a2 = s["appointment"]["id"]
    client.post(f"/api/clinician/appointments/{a2}", json={"action": "confirm", "slot_at": slot}, headers=doc)
    client.post(f"/api/assessments/{aid}/appointment/outcome", json={"outcome": "attended"}, headers=h)
    assert client.get(f"/api/assessments/{aid}/care", headers=h).json()["stage"] == "attended"
    j = client.get("/api/me/journey", headers=h).json()
    steps = [x["step"] for x in j["checks"][0]["steps"]]
    assert steps[:5] == ["completed", "referred", "reviewed", "booked", "attended"]
    cc = client.get("/api/clinician/metrics", headers=doc).json()["care_connect"]
    assert cc["requests"] >= 2 and cc["reasons"].get("time", 0) >= 1


def test_appointment_decline_and_cancel(client, doc):
    h, aid = man(client, answers=TRYING)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    s = client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "tawam"}, headers=h).json()
    a = s["appointment"]["id"]
    assert client.post(f"/api/clinician/appointments/{a}", json={"action": "decline"}, headers=doc).status_code == 400
    client.post(f"/api/clinician/appointments/{a}", json={"action": "decline", "reason": "no_slots"}, headers=doc)
    s = client.get(f"/api/assessments/{aid}/care", headers=h).json()
    assert s["stage"] == "choose" and s["last"]["status"] == "declined"
    assert client.post(f"/api/clinician/share/{s['last']['share_code']}", headers=doc).status_code == 404  # code revoked
    client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "ssmc"}, headers=h)
    assert client.delete(f"/api/assessments/{aid}/appointment", headers=h).json()["cancelled"]
    assert client.get(f"/api/assessments/{aid}/care", headers=h).json()["stage"] == "choose"


def test_reject_needs_reason_and_self_reported_progress(client, doc):
    h, aid = man(client)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    assert client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "reject"}, headers=doc).status_code == 400
    assert client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "modify", "final_level": "primary_care"}, headers=doc).status_code == 400
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "reject", "note": "Lifestyle plan first."}, headers=doc)
    assert client.get(f"/api/clinician/cases/{aid}", headers=doc).json()["review_note"] == "Lifestyle plan first."
    assert client.get(f"/api/assessments/{aid}/care", headers=h).json()["stage"] == "not_needed"
    h2, aid2 = man(client, review=False)
    client.post(f"/api/assessments/{aid2}/submit", headers=h2)
    assert client.post(f"/api/assessments/{aid2}/progress", json={"status": "declined"}, headers=h2).status_code == 400
    client.post(f"/api/assessments/{aid2}/progress", json={"status": "declined", "barrier": "cost"}, headers=h2)
    c = client.get("/api/me/journey", headers=h2).json()["checks"][0]
    assert c["steps"][-1] == {"step": "declined", "at": None, "barrier": "cost"}


def test_journey_changes_between_checks(client):
    h, aid = man(client, review=False)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    aid2 = client.post("/api/assessments?channel=web", headers=h).json()["id"]
    client.put(f"/api/assessments/{aid2}/answers", json={"answers": {**BASE, "smoking": "never", "sleep_h": 7.5}}, headers=h)
    client.post(f"/api/assessments/{aid2}/submit", headers=h)
    j = client.get("/api/me/journey", headers=h).json()
    assert len(j["checks"]) == 2 and j["checks"][0]["id"] == aid2 and "Cigarette smoking" in j["checks"][0]["changes"]["improved"]
    assert j["recheck_due"] > time.time() + 80 * 86400


def test_recovery_code(client):
    h, aid = man(client, review=False)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    code = client.post("/api/me/recovery", headers=h).json()["code"]
    assert len(code) == 23 and code.count("-") == 3
    r = client.post("/api/recover", json={"code": code.lower().replace("-", " ")}).json()
    assert r["aid"] == aid
    assert client.get("/api/consent", headers=h).status_code == 401  # the lost phone is signed out
    assert client.get("/api/consent", headers={"Authorization": f"Bearer {r['token']}"}).status_code == 200
    assert client.post("/api/recover", json={"code": code}).status_code == 404  # works once


def test_consent_withdrawal_removes_doctor_access(client, doc):
    h, aid = man(client)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    code = client.post(f"/api/assessments/{aid}/share", headers=h).json()["code"]
    assert aid in [x["id"] for x in client.get("/api/clinician/queue", headers=doc).json()["pending"]]
    client.post("/api/consent", json={"core": True, "clinician_review": False}, headers=h)
    assert aid not in [x["id"] for x in client.get("/api/clinician/queue", headers=doc).json()["pending"]]
    assert client.get(f"/api/clinician/cases/{aid}", headers=doc).status_code == 404
    assert client.post(f"/api/clinician/share/{code}", headers=doc).status_code == 404


def test_voice_notes(client, doc):
    h, aid = man(client)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    audio = b"\x1aE\xdf\xa3" + b"0" * 500
    client.post(f"/api/assessments/{aid}/voice-notes", files={"file": ("n.webm", audio, "audio/webm")}, data={"seconds": "2.5"}, headers=h)
    assert client.post(f"/api/assessments/{aid}/voice-notes", files={"file": ("n.txt", b"x", "text/plain")}, headers=h).status_code == 415
    m = next(x for x in client.get(f"/api/clinician/cases/{aid}/messages", headers=doc).json() if x["voice"])
    assert m["seconds"] == 2.5 and m["body"] == ""
    got = client.get(f"/api/clinician/cases/{aid}/voice-notes/{m['id']}", headers=doc)
    assert got.content == audio and got.headers["content-type"].startswith("audio/webm")


def test_whatsapp_demo_conversation(client):
    s = "demo-session-0123456789"
    say = lambda t: client.post("/api/conversation/demo", json={"session": s, "text": t}).json()["replies"]
    assert "English" in say("")[0]
    assert "Welcome" in say("2")[0]
    for t in ["2", "34", "175", "98", "1 2", "4", "1", "1", "10", "5.5", "1", "1", "3", "0"]:
        r = say(t)
    assert "number" in say("abc")[0]  # phq1 asks for a menu number
    say("1")
    say("1")
    out = say("1")[0]  # red flags: none
    assert "Your top opportunities" in out and "#t=" in out and "&a=" in out
    tok, aid = out.split("#t=")[1].split()[0].split("&a=")
    r = client.get(f"/api/assessments/{aid}/result", headers={"Authorization": f"Bearer {tok}"}).json()
    assert r["level"] and r["plan"]
    assert "summary is above" in say("hello")[0]
    assert "erased" in say("delete")[0]
    assert client.get(f"/api/assessments/{aid}/result", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_twilio_webhook(client):
    r = client.post("/api/whatsapp/twilio", data={"From": "whatsapp:+971500000001", "Body": "hi"})
    assert r.status_code == 200 and r.text.startswith("<?xml") and "<Message>" in r.text and "English" in r.text


def test_clinician_session_and_password(client):
    tok = client.post("/api/clinician/login", json={"username": "clinician", "password": "demo-clinician"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.post("/api/clinician/password", json={"current": "wrong", "new": "x" * 12}, headers=h).status_code == 400
    assert client.post("/api/clinician/password", json={"current": "demo-clinician", "new": "short"}, headers=h).status_code == 422
    client.post("/api/clinician/logout", headers=h)
    assert client.get("/api/clinician/queue", headers=h).status_code == 401


def test_providers_directory(client, doc):
    assert [p["id"] for p in client.get("/api/providers?level=primary_care").json()["providers"]] == ["ahs"]
    assert client.get("/api/providers?level=self_care").json()["providers"] == []
    pid = client.post("/api/clinician/providers", json={"name_en": "Test Andrology Centre", "name_ar": "مركز تجريبي", "area": "Khalifa City",
                                                         "area_ar": "مدينة خليفة", "sector": "private", "kinds": ["urology"],
                                                         "website": "https://example.org"}, headers=doc).json()["id"]
    assert client.post(f"/api/clinician/providers/{pid}/confirm", json={"note": "short"}, headers=doc).status_code == 422
    client.post(f"/api/clinician/providers/{pid}/confirm", json={"note": "Called reception on 18 Nov"}, headers=doc)
    p = next(x for x in client.get("/api/providers?level=andrology").json()["providers"] if x["id"] == pid)
    assert p["confirm_note"] == "Called reception on 18 Nov" and p["confirmed_at"]
    client.post(f"/api/clinician/providers/{pid}/active?active=false", headers=doc)
    assert pid not in [x["id"] for x in client.get("/api/providers").json()["providers"]]


def test_insights_k_anonymity(client, doc):
    for _ in range(6):
        h, aid = man(client, review=False)
        client.post(f"/api/assessments/{aid}/submit", headers=h)
    d = client.get("/api/insights", headers=doc).json()
    assert d["k_anonymity"] == 5 and d["tiles"]["completed"] >= 6 and d["funnel"][0]["step"] == "Started a check"
    assert all(r.get("suppressed") or r["n"] >= 5 for r in d["by_age"] + d["by_background"])
    assert d["drivers"] and d["drivers"][0]["share"] > 0
    assert client.get("/api/insights").status_code == 401


def test_export_and_erase_cover_new_data(client):
    h, aid = man(client, review=False)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    client.post("/api/me/labs", json={"source": "manual", "values": [{"field": "fsh", "value": 5}]}, headers=h)
    node = client.get(f"/api/assessments/{aid}/plan-options", headers=h).json()["options"][0]["node"]
    client.post(f"/api/assessments/{aid}/plan", json={"nodes": [node]}, headers=h)
    client.post("/api/me/recovery", headers=h)
    e = client.get("/api/me/export", headers=h).json()
    assert e["lab_results"] and e["plans"] and e["assessments"][0]["id"] == aid
    client.delete("/api/me", headers=h)
    from app import db
    with db.tx() as c:
        for t in ("lab_results", "plans", "recovery"):
            assert c.execute(f"SELECT COUNT(*) FROM {t} WHERE user_id NOT IN (SELECT id FROM users)").fetchone()[0] == 0
