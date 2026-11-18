"""Closing the loop with the receiving clinic, and the privacy switches he controls.

- The clinic opens the referral with his handover code (no Riaya account), sees only what he shared,
  records attendance and the visit summary, and loses access the moment he withdraws the code.
- Tests the specialist ordered are tracked; saving a matching result ticks them off.
- The companion's next steps and answers follow the specialist's plan after the visit.
- He can pause all sharing at once, and choose how long his data is kept.
"""
import os
import tempfile
import time

import pytest

os.environ.setdefault("RIAYA_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

BASE = {"age": 34, "height_cm": 175, "weight_kg": 98, "smoking": "daily", "cigs_per_day": 15, "sitting_h": 10,
        "sleep_h": 5.5, "underwear": "tight", "snore": "yes", "tired": "yes", "observed": "no", "bp": "no",
        "pss1": 3, "pss2": 1, "pss3": 1, "pss4": 3, "phq1": 0, "phq2": 1, "background": "arab",
        "reason": ["trying"], "months_trying": 14}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def doc(client):
    tok = client.post("/api/clinician/login", json={"username": "clinician", "password": "demo-clinician"}).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def man(client, review=True):
    tok = client.post("/api/session", json={"lang": "en"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    client.post("/api/consent", json={"core": True, "clinician_review": review, "wearables": True}, headers=h)
    aid = client.post("/api/assessments", headers=h).json()["id"]
    client.put(f"/api/assessments/{aid}/answers", json={"answers": BASE}, headers=h)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    return h, aid


def booked(client, doc):
    """Approved, clinic chosen, slot confirmed. Returns (headers, aid, handover code)."""
    h, aid = man(client)
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    appt = client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "ccad"}, headers=h).json()["appointment"]
    client.post(f"/api/clinician/appointments/{appt['id']}", json={"action": "confirm", "slot_at": time.time() + 86400}, headers=doc)
    return h, aid, appt["share_code"]


def clinic(client, code):
    r = client.post("/api/clinic/open", json={"code": code})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_clinic_portal_closes_the_loop(client, doc):
    h, aid, code = booked(client, doc)
    assert client.post("/api/clinic/open", json={"code": "WRONG-CODE"}).status_code == 404
    ch = clinic(client, code)
    case = client.get("/api/clinic/case", headers=ch).json()
    assert case["id"] == aid and case["doctor_reviewed"] and case["appointment"]["clinic"]
    assert case["allowed"] == ["summary", "labs"] and "answers" in case["withheld"] and "devices" in case["withheld"]
    assert case["letter"] and "STOP-Bang" not in str(case["letter"])  # questionnaire scores are withheld by default
    # clinic marks attendance and sends the visit summary back
    assert client.post("/api/clinic/attendance", json={"outcome": "attended"}, headers=ch).json()["ok"]
    r = client.post("/api/clinic/consultation", json={"summary": "Examined. Normal testes, no varicocele.", "tests_ordered": ["Semen analysis", "Hormone panel"],
                                                      "plan": "Stop smoking, repeat tests in 10 weeks.", "next": "followup", "followup_weeks": 10}, headers=ch)
    assert r.status_code == 200
    j = client.get("/api/me/journey", headers=h).json()["checks"][0]
    assert j["current_stage"] == "followup" and j["consultation"]["by"] == "Clinic"
    assert [t["done"] for t in j["consultation"]["tests"]] == [False, False]
    # his access log says the clinic opened it
    log = client.get("/api/me/access-log", headers=h).json()["entries"]
    assert any(e["action"] == "clinic_view" and e["who"] == "clinic" for e in log)
    assert any(e["action"] == "consultation_recorded" for e in log)
    # he withdraws the code: the clinic's access ends at once
    client.delete(f"/api/me/codes/{code}", headers=h)
    assert client.get("/api/clinic/case", headers=ch).status_code == 401
    assert client.post("/api/clinic/open", json={"code": code}).status_code == 404


def test_clinic_sees_only_what_he_shares(client, doc):
    h, aid, code = booked(client, doc)
    ch = clinic(client, code)
    assert client.get("/api/clinic/case", headers=ch).json()["labs"] is not None
    client.post("/api/me/sharing", json={"clinic": ["summary"]}, headers=h)
    case = client.get("/api/clinic/case", headers=ch).json()
    assert case["labs"] is None and "labs" in case["withheld"]


def test_ordered_tests_tick_off_from_results(client, doc):
    h, aid, code = booked(client, doc)
    ch = clinic(client, code)
    client.post("/api/clinic/consultation", json={"summary": "Seen today, examination normal.", "tests_ordered": ["Semen analysis", "Testosterone", "Scrotal ultrasound"],
                                                  "next": "followup", "followup_weeks": 8}, headers=ch)
    client.post("/api/me/labs", json={"assessment_id": aid, "values": [{"field": "concentration_m_per_ml", "value": 22}, {"field": "testosterone", "value": 14}],
                                      "source": "report"}, headers=h)
    con = client.get("/api/me/journey", headers=h).json()["checks"][0]["consultation"]
    tests = {t["name"]: t for t in con["tests"]}
    assert tests["Semen analysis"]["done"] and tests["Semen analysis"]["via"] == "result"
    assert tests["Testosterone"]["done"] and not tests["Scrotal ultrasound"]["done"] and not tests["Scrotal ultrasound"]["uploadable"]
    assert client.post(f"/api/assessments/{aid}/consultation/tests", json={"test": "Something else"}, headers=h).status_code == 400
    v = client.post(f"/api/assessments/{aid}/consultation/tests", json={"test": "Scrotal ultrasound"}, headers=h).json()
    assert v["tests_all_done"]
    steps = [s["step"] for s in client.get("/api/me/journey", headers=h).json()["checks"][0]["steps"]]
    assert "tests_done" in steps


def test_companion_follows_the_specialist(client, doc):
    h, aid, code = booked(client, doc)
    ch = clinic(client, code)
    client.post("/api/clinic/consultation", json={"summary": "Small varicocele, no surgery needed.", "tests_ordered": ["Semen analysis"],
                                                  "plan": "Cooling habits and stop smoking; repeat semen analysis in 10 weeks.",
                                                  "next": "followup", "followup_weeks": 10}, headers=ch)
    n = client.get(f"/api/assessments/{aid}/next-steps", headers=h).json()
    assert n["now"][0]["kind"] == "specialist" and "Cooling habits" in n["now"][0]["text"]
    assert any("Semen analysis" in s["text"] for s in n["now"]) and n["specialist_first"]
    assert not any(s["kind"] == "care" and "Ask about" in s["text"] for s in n["soon"])  # pre-visit advice is gone
    a = client.post(f"/api/assessments/{aid}/ask", json={"question": "What did the specialist find?"}, headers=h).json()
    assert a["intent"] == "visit" and "Small varicocele" in a["answer"] and "Still to do: Semen analysis" in a["answer"]
    assert a["suggestions"][0] == "What did the specialist find?"
    # guardrails still run first
    assert client.post(f"/api/assessments/{aid}/ask", json={"question": "what dose of clomid after my visit?"}, headers=h).json()["safety"] == "redirect"
    ar = client.post(f"/api/assessments/{aid}/ask?lang=ar", json={"question": "ماذا قال المختص في الزيارة؟"}, headers=h).json()
    assert ar["intent"] == "visit" and "ما سجّله المختص" in ar["answer"]


def test_pause_all_sharing(client, doc):
    h, aid, code = booked(client, doc)
    ch = clinic(client, code)
    h2, aid2 = man(client)
    assert any(x["id"] == aid2 for x in client.get("/api/clinician/queue", headers=doc).json()["pending"])
    for hh in (h, h2):
        p = client.post("/api/me/privacy", json={"paused": True}, headers=hh).json()
        assert p["paused"]
    assert not any(x["id"] == aid2 for x in client.get("/api/clinician/queue", headers=doc).json()["pending"])
    assert client.get(f"/api/clinician/cases/{aid2}", headers=doc).status_code == 404
    assert client.get("/api/clinic/case", headers=ch).status_code == 401
    assert client.get("/api/me/journey", headers=h).json()["sharing_paused"]
    assert client.get(f"/api/assessments/{aid}/next-steps", headers=h).json()["now"][0]["kind"] == "privacy"
    # resume: everything is back, and both changes left receipts
    client.post("/api/me/privacy", json={"paused": False}, headers=h2)
    assert client.get(f"/api/clinician/cases/{aid2}", headers=doc).status_code == 200
    acts = [(r["recipient"], r["action"]) for r in client.get("/api/me/receipts", headers=h2).json()["receipts"]]
    assert ("all_sharing", "paused") in acts and ("all_sharing", "resumed") in acts


def test_retention_choice_erases_after_inactivity(client):
    h, aid = man(client)
    assert client.post("/api/me/privacy", json={"retention_months": 5}, headers=h).status_code == 400
    p = client.post("/api/me/privacy", json={"retention_months": 3}, headers=h).json()
    assert p["retention_months"] == 3 and p["delete_after"] > time.time() + 80 * 86400
    assert client.get("/api/me/export", headers=h).json()["privacy"]["retention_months"] == 3
    from app import db, main
    with db.tx() as c:
        uid = c.execute("SELECT user_id FROM assessments WHERE id=?", (aid,)).fetchone()["user_id"]
        c.execute("UPDATE users SET last_active=? WHERE id=?", (time.time() - 100 * 86400, uid))
    assert main.purge_expired() >= 1
    with db.tx() as c:
        assert not c.execute("SELECT 1 FROM assessments WHERE id=?", (aid,)).fetchone()
    assert client.get("/api/me/journey", headers=h).status_code == 401


def test_clinic_letter_lists_results_he_saved(client, doc):
    h, aid, code = booked(client, doc)
    client.post("/api/me/labs", json={"assessment_id": aid, "values": [{"field": "fsh", "value": 6.1}], "source": "report"}, headers=h)
    case = client.get("/api/clinic/case", headers=clinic(client, code)).json()
    have = next(s for s in case["letter"]["sections"] if s["title"] == "Results already available")["lines"]
    assert any(l.startswith("FSH: 6.1") for l in have) and "No prior results." not in have
    log = [e["action"] for e in client.get("/api/me/access-log", headers=h).json()["entries"]]
    assert log.count("clinic_view") == 1  # opening the code and reading the case is one entry, not two
