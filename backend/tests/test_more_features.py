"""Automatic pathway reminders, scoped second-opinion codes, visit preparation and visit feedback."""
import os
import tempfile
import time

import pytest

os.environ.setdefault("RIAYA_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app import db, main  # noqa: E402
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


def man(client, review=True, answers=BASE):
    tok = client.post("/api/session", json={"lang": "en"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    client.post("/api/consent", json={"core": True, "clinician_review": review, "wearables": True}, headers=h)
    aid = client.post("/api/assessments", headers=h).json()["id"]
    client.put(f"/api/assessments/{aid}/answers", json={"answers": answers}, headers=h)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    return h, aid


def age(aid, days):
    """Moves this case's history back in time."""
    with db.tx() as c:
        for t, cols in (("assessments", ("started_at", "completed_at")), ("referrals", ("created_at", "reviewed_at"))):
            for col in cols:
                c.execute(f"UPDATE {t} SET {col}={col}-? WHERE {'id' if t == 'assessments' else 'assessment_id'}=? AND {col} IS NOT NULL",
                          (days * 86400, aid))


def msgs(client, h, aid):
    r = client.get(f"/api/assessments/{aid}/messages", headers=h).json()
    return [m.get("body") or m.get("text") or "" for m in (r["messages"] if isinstance(r, dict) else r)]


def test_automatic_reminders_once_per_stage(client, doc):
    h, aid = man(client)
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    age(aid, 10)  # approved 10 days ago, no clinic chosen
    before = len(msgs(client, h, aid))
    main.run_reminders()
    after = msgs(client, h, aid)
    assert len(after) == before + 1 and "Choose a clinic" in after[-1]
    main.run_reminders()
    assert len(msgs(client, h, aid)) == before + 1  # never twice for the same stage
    board = client.get("/api/clinician/pathway", headers=doc).json()["stalled"]
    assert any(x["id"] == aid and x["reminded"] for x in board)


def test_no_reminders_when_he_says_no(client, doc):
    h, aid = man(client)
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    p = client.post("/api/me/privacy", json={"reminders": False}, headers=h).json()
    assert p["reminders"] is False
    age(aid, 10)
    before = len(msgs(client, h, aid))
    main.run_reminders()
    assert len(msgs(client, h, aid)) == before
    assert ("reminders", "withdrawn") in [(r["recipient"], r["action"]) for r in client.get("/api/me/receipts", headers=h).json()["receipts"]]


def test_recheck_reminder_for_self_care(client):
    light = {**BASE, "smoking": "never", "weight_kg": 72, "sitting_h": 4, "sleep_h": 7.5, "snore": "no", "tired": "no", "underwear": "loose",
             "pss1": 1, "pss4": 1, "reason": ["curious"], "months_trying": None}
    h, aid = man(client, answers=light)
    age(aid, 95)
    main.run_reminders()
    assert any("three months" in m for m in msgs(client, h, aid))


def test_second_opinion_code_is_scoped_and_view_only(client, doc):
    h, aid = man(client)
    client.post("/api/me/labs", json={"assessment_id": aid, "values": [{"field": "fsh", "value": 6.1}], "source": "report"}, headers=h)
    assert client.post(f"/api/assessments/{aid}/share", json={"categories": ["answers"], "hours": 5}, headers=h).status_code == 400
    r = client.post(f"/api/assessments/{aid}/share", json={"categories": ["answers"], "hours": 24, "purpose": "second_opinion"}, headers=h).json()
    assert r["categories"] == ["summary", "answers"] and r["link"].endswith(r["code"])
    tok = client.post("/api/clinic/open", json={"code": r["code"]}).json()["token"]
    ch = {"Authorization": f"Bearer {tok}"}
    case = client.get("/api/clinic/case", headers=ch).json()
    assert case["view_only"] and case["purpose"] == "second_opinion" and case["allowed"] == ["summary", "answers"]
    assert case["labs"] is None and "labs" in case["withheld"] and "STOP-Bang" in str(case["letter"])
    assert client.post("/api/clinic/attendance", json={"outcome": "attended"}, headers=ch).status_code == 403
    assert client.post("/api/clinic/consultation", json={"summary": "Looked at it, fine.", "next": "discharge"}, headers=ch).status_code == 403
    codes = client.get("/api/me/sharing", headers=h).json()["active_codes"]
    mine = next(x for x in codes if x["code"] == r["code"])
    assert mine["scope"] == ["summary", "answers"] and mine["purpose"] == "second_opinion" and mine["used"]
    # the old body-less call still works (clinic choices apply)
    assert client.post(f"/api/assessments/{aid}/share", headers=h).json()["expires_in_hours"] == 72


def test_visit_preparation(client):
    h, aid = man(client)
    p = client.get(f"/api/assessments/{aid}/prepare", headers=h).json()
    titles = [s["title"] for s in p["sections"]]
    assert titles == ["Bring with you", "Before the visit", "Questions worth asking", "Your choices at the visit"]
    before = " ".join(i["text"] for i in p["sections"][1]["items"])
    assert "2 to 7 days" in before and any(i["source"] and "WHO" in i["source"] for i in p["sections"][1]["items"])
    bring = " ".join(i["text"] for i in p["sections"][0]["items"])
    assert "wife" in bring.lower() and "supplement" in bring
    asks = [i["text"] for i in p["sections"][2]["items"]]
    assert any("smoking" in a.lower() for a in asks) and any("wife" in a for a in asks)
    ar = client.get(f"/api/assessments/{aid}/prepare?lang=ar", headers=h).json()
    assert ar["sections"][0]["title"] == "أحضر معك" and "طبيب رجل" in str(ar)


def test_visit_feedback_and_k_anonymous_clinic_quality(client, doc):
    hs = []
    for i in range(5):
        h, aid = man(client)
        client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
        appt = client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "tawam"}, headers=h).json()["appointment"]
        if i == 0:
            assert client.post(f"/api/assessments/{aid}/visit-feedback", json={"respect": 5, "privacy": 5, "explained": 4, "recommend": True},
                               headers=h).status_code == 409  # not attended yet
        client.post(f"/api/clinician/appointments/{appt['id']}", json={"action": "confirm", "slot_at": time.time() + 3600}, headers=doc)
        client.post(f"/api/assessments/{aid}/appointment/outcome", json={"outcome": "attended"}, headers=h)
        assert client.get(f"/api/assessments/{aid}/visit-feedback", headers=h).json()["can_rate"]
        client.post(f"/api/assessments/{aid}/visit-feedback", json={"respect": 4 + (i % 2), "privacy": 5, "explained": 4, "recommend": i != 4,
                                                                    "wait_days": 5}, headers=h)
        hs.append((h, aid))
        if i == 3:  # four ratings: hidden
            q = client.get("/api/insights", headers=doc).json()["clinic_quality"]
            assert any(x.get("suppressed") for x in q if "Tawam" in x["clinic"])
    q = next(x for x in client.get("/api/insights", headers=doc).json()["clinic_quality"] if "Tawam" in x["clinic"])
    assert q["n"] == 5 and q["privacy"] == 5.0 and q["recommend_pct"] == 80 and q["avg_wait_days"] == 5.0
