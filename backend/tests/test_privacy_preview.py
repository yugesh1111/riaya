"""Privacy he can see: the preview is exactly what the recipient gets; his questions travel with the referral;
doctors agree or disagree with each finding, with reasons, and he sees that in his access log."""
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


def booked(client, doc):
    tok = client.post("/api/session", json={"lang": "en"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    client.post("/api/consent", json={"core": True, "clinician_review": True}, headers=h)
    aid = client.post("/api/assessments", headers=h).json()["id"]
    client.put(f"/api/assessments/{aid}/answers", json={"answers": BASE}, headers=h)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    client.post("/api/me/labs", json={"assessment_id": aid, "values": [{"field": "fsh", "value": 6.1}], "source": "report"}, headers=h)
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    appt = client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "ccad"}, headers=h).json()["appointment"]
    client.post(f"/api/clinician/appointments/{appt['id']}", json={"action": "confirm", "slot_at": time.time() + 86400}, headers=doc)
    return h, aid, appt["share_code"]


def test_preview_is_exactly_what_the_clinic_sees(client, doc):
    h, aid, code = booked(client, doc)
    q = client.put(f"/api/assessments/{aid}/questions", json={"questions": ["Could my sleep be part of this?", "  ", "Should my wife come too?"]}, headers=h).json()
    assert q["questions"] == ["Could my sleep be part of this?", "Should my wife come too?"]
    preview = client.get(f"/api/assessments/{aid}/share-preview?recipient=clinic", headers=h).json()
    tok = client.post("/api/clinic/open", json={"code": code}).json()["token"]
    seen = client.get("/api/clinic/case", headers={"Authorization": f"Bearer {tok}"}).json()
    assert preview["letter"]["sections"] == seen["letter"]["sections"] and preview["withheld"] == seen["withheld"]
    titles = [s["title"] for s in seen["letter"]["sections"]]
    assert titles[1] == "Questions he wants to discuss" and "Should my wife come too?" in str(seen["letter"])
    assert any("FSH: 6.1" in l for s in seen["letter"]["sections"] for l in s["lines"])
    # previewing a different choice changes the preview but shares nothing
    narrow = client.get(f"/api/assessments/{aid}/share-preview?recipient=clinic&categories=summary", headers=h).json()
    assert "labs" in narrow["withheld"] and not any("FSH" in l for s in narrow["letter"]["sections"] for l in s["lines"])
    assert client.get("/api/me/sharing", headers=h).json()["prefs"]["clinic"] == ["summary", "labs"]
    doctor = client.get(f"/api/assessments/{aid}/share-preview?recipient=doctor", headers=h).json()
    assert doctor["withheld"] == [] and "STOP-Bang" in str(doctor["letter"])
    assert client.get(f"/api/assessments/{aid}/share-preview?recipient=everyone", headers=h).status_code == 400


def test_questions_are_his_only(client, doc):
    h, aid, _ = booked(client, doc)
    other = {"Authorization": "Bearer " + client.post("/api/session", json={"lang": "en"}).json()["token"]}
    assert client.get(f"/api/assessments/{aid}/questions", headers=other).status_code == 404
    assert client.get(f"/api/assessments/{aid}/share-preview", headers=other).status_code == 404
    client.put(f"/api/assessments/{aid}/questions", json={"questions": []}, headers=h)
    assert client.get(f"/api/assessments/{aid}/questions", headers=h).json()["questions"] == []


def test_doctor_agrees_or_disagrees_with_findings(client, doc):
    h, aid, _ = booked(client, doc)
    assert client.post(f"/api/clinician/cases/{aid}/findings", json={"node": "smoking", "verdict": "disagree"}, headers=doc).status_code == 400
    assert client.post(f"/api/clinician/cases/{aid}/findings", json={"node": "not_a_node", "verdict": "agree"}, headers=doc).status_code == 400
    client.post(f"/api/clinician/cases/{aid}/findings", json={"node": "smoking", "verdict": "agree"}, headers=doc)
    client.post(f"/api/clinician/cases/{aid}/findings", json={"node": "sleep_loss", "verdict": "disagree", "reason": "Works night shifts; sleep is long by day."}, headers=doc)
    r = client.get(f"/api/clinician/cases/{aid}/findings", headers=doc).json()["reviews"]
    assert r["smoking"]["verdict"] == "agree" and r["sleep_loss"]["reason"].startswith("Works night")
    agg = {x["node"]: x for x in client.get("/api/clinician/findings/agreement", headers=doc).json()["by_finding"]}
    assert agg["smoking"]["agree_pct"] == 100 and agg["sleep_loss"]["agree_pct"] == 0
    log = [e["action"] for e in client.get("/api/me/access-log", headers=h).json()["entries"]]
    assert "finding_agree" in log and "finding_disagree" in log
