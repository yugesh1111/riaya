"""Tests for the reviewers' requests: a private companion with explainable insights and safe next steps,
a connected referral journey through specialist visit and follow-up, and user-controlled, consent-based sharing."""
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


def man(client, review=True, answers=BASE, submit=True):
    tok = client.post("/api/session", json={"lang": "en"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    client.post("/api/consent", json={"core": True, "clinician_review": review, "wearables": True}, headers=h)
    aid = client.post("/api/assessments", headers=h).json()["id"]
    client.put(f"/api/assessments/{aid}/answers", json={"answers": answers}, headers=h)
    if submit:
        client.post(f"/api/assessments/{aid}/submit", headers=h)
    return h, aid


# ---------------------------------------------------------------- companion
def test_companion_guardrails(client):
    h, aid = man(client)
    ask = lambda q, lang="en": client.post(f"/api/assessments/{aid}/ask?lang={lang}", json={"question": q}, headers=h).json()
    a = ask("I have sudden pain and swelling in my testicle")
    assert a["safety"] == "urgent" and "998" in a["answer"]
    a = ask("I've been thinking about ending it, I feel hopeless")
    assert a["safety"] == "urgent" and "800" in a["answer"]
    a = ask("What dose of clomid should I take?")
    assert a["safety"] == "redirect" and "can't advise" in a["answer"] and "testosterone" in a["answer"].lower()
    a = ask("Am I infertile? What are my chances?")
    assert a["intent"] == "chance" and "not a prediction" in a["answer"] and "%" not in a["answer"]
    a = ask("هل أنا عقيم؟", "ar")
    assert a["intent"] == "chance" and "ليست توقعاً" in a["answer"]


def test_companion_grounded_answers(client):
    h, aid = man(client)
    ask = lambda q: client.post(f"/api/assessments/{aid}/ask", json={"question": q}, headers=h).json()
    a = ask("Why do I need to see a doctor?")
    assert a["intent"] == "why_next" and "fertility clinic" in a["answer"].lower()
    a = ask("What should I change first?")
    assert a["intent"] == "first" and "1." in a["answer"] and "educational estimate" in a["answer"] and a["sources"][0]["grade"]
    a = ask("Tell me about smoking")
    assert a["intent"] == "about" and "evidence grade A" in a["answer"] and a["sources"]
    assert ask("How long until things get better?")["intent"] == "time"
    assert ask("What about my wife?")["intent"] == "wife"
    assert "doctor may review" in ask("Who can see my data?")["answer"]
    f = ask("asdfgh")
    assert f["intent"] == "fallback" and len(f["suggestions"]) >= 4
    # the question text is never stored: only the intent goes into the event log
    from app import db
    with db.tx() as c:
        rows = c.execute("SELECT detail FROM events WHERE assessment_id=? AND type='companion_question'", (aid,)).fetchall()
    assert {r["detail"] for r in rows} <= {"why_next", "first", "about", "time", "wife", "privacy", "fallback"}


def test_safe_next_steps(client):
    h, aid = man(client)
    n = client.get(f"/api/assessments/{aid}/next-steps", headers=h).json()
    assert any("doctor will review" in s["text"] for s in n["now"])
    kinds = [s["kind"] for s in n["soon"]]
    assert "care" in kinds and "habit" in kinds and any(s["grade"] for s in n["soon"] if s["kind"] == "habit")
    assert any("testosterone" in d.lower() for d in n["dont"]) and any("medicine" in d for d in n["dont"])
    assert n["safety_net"]["items"] and any("emergency" in x for x in n["safety_net"]["items"])
    assert n["later"][-1]["kind"] == "recheck"
    h2, aid2 = man(client, answers={**BASE, "red_flags": ["rf_torsion"]})
    n2 = client.get(f"/api/assessments/{aid2}/next-steps", headers=h2).json()
    assert n2["now"][0]["kind"] == "urgent" and "998" in n2["now"][0]["text"]


# ---------------------------------------------------------------- connected referral journey
def test_full_pathway_to_follow_up(client, doc):
    h, aid = man(client)
    stage = lambda: client.get("/api/me/journey", headers=h).json()["checks"][0]
    c = stage()
    assert [s["key"] for s in c["pathway"]] == ["check", "review", "clinic", "appointment", "visit", "outcome", "followup", "recheck"]
    assert c["current_stage"] == "review"
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    assert stage()["current_stage"] == "clinic"
    appt = client.post(f"/api/assessments/{aid}/appointment", json={"provider_id": "ccad"}, headers=h).json()["appointment"]
    assert stage()["current_stage"] == "appointment"
    client.post(f"/api/clinician/appointments/{appt['id']}", json={"action": "confirm", "slot_at": time.time() + 86400}, headers=doc)
    assert stage()["current_stage"] == "visit"
    client.post(f"/api/assessments/{aid}/appointment/outcome", json={"outcome": "attended"}, headers=h)
    assert stage()["current_stage"] == "outcome"
    assert client.post(f"/api/clinician/cases/{aid}/consultation", json={"summary": "Examined; varicocele grade 1.", "next": "followup"},
                       headers=doc).status_code == 400  # follow-up needs a date
    client.post(f"/api/clinician/cases/{aid}/consultation", json={"summary": "Examined; small varicocele, no treatment needed now.",
                                                                  "tests_ordered": ["Repeat semen analysis", "FSH, LH, testosterone"],
                                                                  "plan": "Lifestyle plan, repeat tests in 10 weeks.", "next": "followup",
                                                                  "followup_weeks": 10}, headers=doc)
    c = stage()
    assert c["current_stage"] == "followup" and c["consultation"]["tests_ordered"][0] == "Repeat semen analysis"
    assert c["consultation"]["followup_at"] > time.time() + 9 * 7 * 86400
    care = client.get(f"/api/assessments/{aid}/care", headers=h).json()
    assert care["consultation"]["summary"].startswith("Examined")
    ics = client.get(f"/api/assessments/{aid}/followup.ics", headers=h).text
    assert "SUMMARY:Follow-up" in ics and "varicocele" not in ics.lower()
    client.post(f"/api/assessments/{aid}/progress", json={"status": "followed_up"}, headers=h)
    c = stage()
    assert next(s for s in c["pathway"] if s["key"] == "followup")["status"] == "done"
    assert any("recorded your visit" in m["body"] for m in client.get(f"/api/assessments/{aid}/messages", headers=h).json())


def test_self_care_pathway_skips_clinic(client):
    h, aid = man(client, review=False, answers={"age": 25, "smoking": "never", "sleep_h": 8, "sitting_h": 3, "reason": ["general"]})
    c = client.get("/api/me/journey", headers=h).json()["checks"][0]
    st = {s["key"]: s["status"] for s in c["pathway"]}
    assert st["clinic"] == "skipped" and st["visit"] == "skipped" and st["recheck"] == "upcoming"


def test_coordinator_board_and_nudge(client, doc):
    h, aid = man(client)
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    from app import db
    with db.tx() as c:  # pretend the approval was 9 days ago
        c.execute("UPDATE referrals SET reviewed_at=reviewed_at-9*86400, created_at=created_at-9*86400 WHERE assessment_id=?", (aid,))
        c.execute("UPDATE assessments SET completed_at=completed_at-9*86400 WHERE id=?", (aid,))
    b = client.get("/api/clinician/pathway", headers=doc).json()
    mine = next(x for x in b["stalled"] if x["id"] == aid)
    assert mine["stage"] == "clinic" and mine["days"] >= 8 and mine["can_nudge"]
    assert {s["key"] for s in b["stages"]} >= {"review", "clinic", "followup"}
    client.post(f"/api/clinician/cases/{aid}/nudge", json={"stage": "clinic"}, headers=doc)
    assert any("Choose a clinic" in m["body"] for m in client.get(f"/api/assessments/{aid}/messages", headers=h).json())


# ---------------------------------------------------------------- user-controlled, consent-based sharing
def test_sharing_controls_what_the_clinic_sees(client, doc):
    zipb = open(os.path.join(os.path.dirname(__file__), "../../web/samples/apple_health_sample.zip"), "rb").read()
    h, aid = man(client, review=False, submit=False)
    client.post(f"/api/assessments/{aid}/wearables", files={"file": ("export.zip", zipb, "application/zip")}, headers=h)
    client.post(f"/api/assessments/{aid}/labs", json={"testosterone": 9.0}, headers=h)
    client.post(f"/api/assessments/{aid}/submit", headers=h)
    s = client.get("/api/me/sharing", headers=h).json()
    assert s["prefs"]["clinic"] == ["summary", "labs"] and any(c["required"] for c in s["categories"])
    code = client.post(f"/api/assessments/{aid}/share", headers=h).json()["code"]
    client.post(f"/api/clinician/share/{code}", headers=doc)
    case = client.get(f"/api/clinician/cases/{aid}", headers=doc).json()
    assert case["access"] == "clinic" and set(case["withheld"]) == {"answers", "devices", "plan"}
    assert case["result"]["wearable"] is None and case["result"]["labs"] is not None
    assert "smoking" not in case["answers"] and case["answers"]["age"] == 34
    assert all(p["source"] not in ("watch", "cgm", "questionnaire") for ps in case["result"]["provenance"].values() for p in ps)
    ex = client.get(f"/api/clinician/cases/{aid}/explain", headers=doc).json()
    assert ex["baseline"] is None
    # he withdraws lab sharing: the clinic loses it at once, and he cannot remove the summary itself
    client.post("/api/me/sharing", json={"clinic": []}, headers=h)
    assert client.get("/api/me/sharing", headers=h).json()["prefs"]["clinic"] == ["summary"]
    case = client.get(f"/api/clinician/cases/{aid}", headers=doc).json()
    assert case["result"]["labs"] is None and "labs" in case["withheld"]
    assert client.get(f"/api/clinician/cases/{aid}/labs", headers=doc).status_code == 403
    # he widens it again: devices now travel
    client.post("/api/me/sharing", json={"clinic": ["summary", "devices"]}, headers=h)
    assert client.get(f"/api/clinician/cases/{aid}", headers=doc).json()["result"]["wearable"]["sleep_avg_h"]


def test_doctor_scope_and_receipts_and_access_log(client, doc):
    h, aid = man(client)
    client.post("/api/me/sharing", json={"doctor": ["summary", "answers", "plan"]}, headers=h)
    client.post("/api/me/labs", json={"source": "manual", "values": [{"field": "fsh", "value": 15}]}, headers=h)
    assert not [x for x in client.get("/api/clinician/labs/pending", headers=doc).json()["results"] if x["assessment_id"] == aid]
    client.get(f"/api/clinician/cases/{aid}", headers=doc)
    client.post(f"/api/clinician/cases/{aid}/review", json={"decision": "approve"}, headers=doc)
    log = client.get("/api/me/access-log", headers=h).json()["entries"]
    assert {"view_case", "review_approve"} <= {e["action"] for e in log} and all(e["who"] == "clinician" for e in log)
    client.post(f"/api/assessments/{aid}/partner-link", headers=h)
    rec = client.get("/api/me/receipts", headers=h).json()["receipts"]
    kinds = {(r["recipient"], r["action"]) for r in rec}
    assert ("doctor", "changed") in kinds and ("partner", "granted") in kinds and ("doctor", "granted") in kinds
    changed = next(r for r in rec if r["recipient"] == "doctor" and r["action"] == "changed")
    assert set(changed["scope"]["removed"]) == {"devices", "labs"}
    e = client.get("/api/me/export", headers=h).json()
    assert e["sharing"]["doctor"] == ["summary", "answers", "plan"] and e["consent_receipts"]
    client.delete("/api/me", headers=h)
    from app import db
    with db.tx() as c:
        assert c.execute("SELECT COUNT(*) FROM consent_receipts WHERE user_id NOT IN (SELECT id FROM users)").fetchone()[0] == 0
