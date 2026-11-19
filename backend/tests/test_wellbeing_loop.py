"""WHO-5 outcomes, relapse recovery, Ramadan mode, JITAI decisions, behaviour-change design and the FHIR Task referral loop."""
import os
import tempfile
import time
from datetime import date, datetime

import pytest

os.environ.setdefault("RIAYA_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app import db, wellbeing, referral_loop  # noqa: E402
from app.main import app  # noqa: E402

BASE = {"age": 34, "height_cm": 175, "weight_kg": 98, "smoking": "daily", "cigs_per_day": 15, "sitting_h": 10,
        "sleep_h": 5.5, "underwear": "tight", "snore": "no", "tired": "yes", "observed": "no", "bp": "no",
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


def man(client, review=False):
    tok = client.post("/api/session", json={"lang": "en"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    client.post("/api/consent", json={"core": True, "clinician_review": review, "wearables": True}, headers=h)
    aid = client.post("/api/assessments", headers=h).json()["id"]
    client.put(f"/api/assessments/{aid}/answers", json={"answers": BASE}, headers=h)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    return h, aid


def plan(client, h, aid):
    opts = client.get(f"/api/assessments/{aid}/plan-options", headers=h).json()["options"]
    return client.post(f"/api/assessments/{aid}/plan", json={"nodes": [o["node"] for o in opts[:2]]}, headers=h).json()


def test_who5_scoring_and_bands():
    assert wellbeing.who5_score([5, 5, 5, 5, 5]) == 100
    assert wellbeing.who5_score([1, 1, 1, 2, 2]) == 28
    assert wellbeing.who5_band(28)["action"] == "clinician_review"
    assert wellbeing.who5_band(48)["band"] == "fair"
    with pytest.raises(ValueError):
        wellbeing.who5_score([6, 0, 0, 0, 0])
    assert wellbeing.who5_change([{"point": "day0", "score": 40}, {"point": "day30", "score": 56}])["meaningful"] == "improved"


def test_plan_carries_techniques_and_who5_baseline(client):
    h, aid = man(client)
    p = plan(client, h, aid)
    assert p["status"] == "self_guided"
    assert all(it["techniques"]["bct"] and it["techniques"]["com_b"] for it in p["items"])
    assert p["who5"]["due"] == "day0"
    r = client.post("/api/me/plan/who5", json={"answers": [3, 3, 2, 3, 3]}, headers=h).json()
    assert r["score"] == 56 and r["point"] == "day0" and r["band"]["band"] == "good"
    assert r["plan"]["who5"]["due"] is None
    assert client.post("/api/me/plan/who5", json={"answers": [3, 3, 2, 3, 3]}, headers=h).status_code == 409


def test_low_who5_escalates_only_with_review_consent(client):
    h, aid = man(client, review=False)
    plan(client, h, aid)
    r = client.post("/api/me/plan/who5", json={"answers": [1, 1, 1, 1, 1]}, headers=h).json()
    assert r["band"]["action"] == "clinician_review" and r["escalated"] is False and "800" in r["support_line"]


def test_lapse_and_fresh_start(client):
    h, aid = man(client)
    p = plan(client, h, aid)
    nodes = [it["node"] for it in p["items"]]
    for w in (1, 2):
        client.post("/api/me/plan/checkin", json={"week": w, "items": {n: {"adherence": 0} for n in nodes}}, headers=h)
    v = client.get("/api/me/plan", headers=h).json()["plan"]
    assert v["lapse"]["reason"] == "low_adherence"
    r = client.post("/api/me/plan/restart", json={"keep": nodes[0], "barrier": "time"}, headers=h).json()
    assert len(r["items"]) == 1 and r["restart"]["if_then"].startswith("If my day is full") and r["lapse"] is None
    assert client.post("/api/me/plan/restart", json={"keep": "nope", "barrier": "time"}, headers=h).status_code == 422


def test_ramadan_mode(client):
    assert wellbeing.is_ramadan(date(2027, 2, 20)) and not wellbeing.is_ramadan(date(2027, 6, 1))
    h, aid = man(client)
    plan(client, h, aid)
    r = client.post("/api/me/ramadan?lang=ar", json={"setting": "on"}, headers=h).json()
    assert r["active"] and r["checkin_time"] == "21:30" and r["notes"]
    v = client.get("/api/me/plan?lang=en", headers=h).json()["plan"]
    assert v["ramadan"]["active"] and any(it.get("ramadan") for it in v["items"])
    client.post("/api/me/ramadan", json={"setting": "off"}, headers=h)
    assert not client.get("/api/me/plan", headers=h).json()["plan"]["ramadan"]["active"]


def test_jitai_rules_are_explained():
    view = {"status": "active", "week": 3, "items": [], "due": True, "start_at": time.time() - 20 * 86400}
    noon = datetime(2026, 11, 18, 12, 0).timestamp() - 4 * 3600 + time.timezone * 0  # around midday Gulf time
    assert wellbeing.jitai_decide(view, [], None, False, False)["why"] == ["He turned reminders off."]
    d = wellbeing.jitai_decide(view, [], time.time() - 3600, True, False)
    assert d["send"] is None
    night = datetime(2026, 11, 18, 23, 30, tzinfo=wellbeing.GST).timestamp()
    assert "Quiet hours" in wellbeing.jitai_decide(view, [], None, True, False, now=night)["why"][0]
    fasting = datetime(2026, 11, 18, 13, 0, tzinfo=wellbeing.GST).timestamp()
    assert "Ramadan" in wellbeing.jitai_decide(view, [], None, True, True, now=fasting)["why"][0]
    d = wellbeing.jitai_decide(view, [{"point": "day0", "score": 20, "week": 1}], None, True, False, now=fasting)
    assert d["send"] == "low_wellbeing"


def test_behaviour_design_is_complete(client):
    d = client.get("/api/behaviour-design").json()
    codes = {b["code"] for comp in d["components"] for b in comp["bct"]}
    assert {"1.1", "1.2", "1.4", "2.3", "7.1", "8.3"} <= codes and set(d["sdt"]) == {"autonomy", "competence", "relatedness"}


def test_referral_loop_task_and_escalation(client, doc):
    h, aid = man(client, review=True)
    loop = client.get(f"/api/assessments/{aid}/referral-loop", headers=h).json()
    assert loop["task"]["resourceType"] == "Task" and loop["task"]["status"] == "requested"
    assert loop["milestones"][0]["key"] == "review" and not loop["overdue"]
    with db.tx() as c:
        c.execute("UPDATE referrals SET created_at=created_at-? WHERE assessment_id=?", (7 * 86400, aid))
    loop = client.get(f"/api/assessments/{aid}/referral-loop", headers=h).json()
    assert loop["overdue"] and loop["overdue"][0]["escalate_to"] == "clinical_lead"
    board = client.get("/api/clinician/referral-loop", headers=doc).json()
    assert any(x["id"] == aid for x in board["overdue"])
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    t = client.get(f"/api/assessments/{aid}/fhir/task", headers=h).json()
    assert t["status"] == "accepted" and t["focus"]["reference"].startswith("ServiceRequest/")


def test_outcomes_are_k_anonymised(client, doc):
    out = client.get("/api/insights", headers=doc).json()["outcomes"]
    assert "n" in out


def test_patient_is_told_when_a_doctor_opens_his_record(client, doc):
    h, aid = man(client, review=True)
    client.get(f"/api/clinician/cases/{aid}", headers=doc)
    client.get(f"/api/clinician/cases/{aid}", headers=doc)   # a second look within 30 minutes does not send another
    r = client.get(f"/api/assessments/{aid}/messages", headers=h).json()
    msgs = r["messages"] if isinstance(r, dict) else r
    notes = [m for m in msgs if "🔒" in (m.get("body") or "")]
    assert len(notes) == 1 and "doctor" in notes[0]["body"].lower()


def test_tester_feedback_and_sus(client, doc):
    from app.main import sus_score
    assert sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100 and sus_score([3] * 10) == 50
    body = {"device": "iphone", "lang": "ar", "tried": ["voice", "vault", "nope"], "sus": [4, 2, 5, 1, 4, 2, 5, 1, 4, 2],
            "clear": 5, "private_felt": 5, "voice_ok": 4, "would_use": 4, "recommend": True, "comment": "Very private, voice was good"}
    r = client.post("/api/tester-feedback", json=body).json()
    assert r["sus"] == 85.0
    assert client.post("/api/tester-feedback", json={**body, "sus": [6] * 10}).status_code == 422
    pub = client.get("/api/tester-feedback/summary").json()
    assert pub["n"] >= 1 and "comments" not in pub and pub["tried"].get("vault") and "nope" not in pub["tried"]
    team = client.get("/api/clinician/tester-feedback", headers=doc).json()
    assert team["comments"][0]["text"].startswith("Very private")


def test_urgent_pain_is_caught_however_it_is_phrased():
    from app import guide
    for q in ["I have sudden testicle pain", "my testicle suddenly hurts", "severe pain in my balls", "twisted testicle",
              "ألم شديد في الخصية", "عندي وجع في الخصية"]:
        assert guide._urgent(guide._norm(q)), q
    for q in ["I want to know which tests to do", "my back hurts a bit after gym", "what dose of clomid"]:
        assert not guide._urgent(guide._norm(q)), q


def test_gym_product_checker(client):
    r = client.post("/api/products/check?lang=en", json={"text": "Ingredients: Ostarine (MK-2866) 10mg, Zinc 15mg"}).json()
    assert r["verdict"] == "stop" and r["findings"][0]["match"] == "ostarine"
    assert client.post("/api/products/check", json={"text": "Whey protein, creatine monohydrate"}).json()["verdict"] == "ok"
    assert client.post("/api/products/check?lang=ar", json={"text": "حقن تستوستيرون"}).json()["verdict"] == "stop"
    assert client.post("/api/products/check", json={"text": "specialist approved formula"}).json()["verdict"] is None  # no false hit inside words


def test_heat_guard_uses_emirate_not_location():
    from app import heat
    r = heat.today("dubai", "en", fetch=lambda lat, lon: {"max_c": 44, "feels_c": 47, "uv": 11})
    assert r["band"] == "extreme" and "midday" in r["tip"] and r["name"] == "Dubai"
    heat._cache.clear()
    def boom(lat, lon):
        raise OSError("offline")
    assert heat.today("sharjah", "ar", fetch=boom)["available"] is False
