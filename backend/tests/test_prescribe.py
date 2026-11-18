"""Prescriptive (best changes) and predictive (12-week projection, dropout early warning) layers."""
import os
import tempfile

import pytest

os.environ.setdefault("RIAYA_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app import assessment, prescribe  # noqa: E402
from app.main import app  # noqa: E402

BASE = {"age": 34, "height_cm": 175, "weight_kg": 98, "smoking": "daily", "cigs_per_day": 15, "sitting_h": 10,
        "sleep_h": 5.5, "underwear": "tight", "snore": "yes", "tired": "yes", "observed": "no", "bp": "no",
        "pss1": 3, "pss2": 1, "pss3": 1, "pss4": 3, "phq1": 0, "phq2": 1, "background": "arab",
        "reason": ["trying"], "months_trying": 14}


def test_best_changes_are_ranked_and_grounded():
    r = assessment.run(BASE, with_models=False)
    b = prescribe.best_changes(r)
    scores = [x["score"] for x in b["ranked"]]
    assert scores == sorted(scores, reverse=True) and b["ranked"][0]["node"] == "smoking"
    assert all(x["grade"] in "ABCD" and x["first_step"] and x["effort"] in (1, 2, 3) for x in b["ranked"])
    assert len(b["bundle"]["nodes"]) == 3 and b["bundle"]["impact_pct"] > b["ranked"][0]["impact_pct"]
    assert "not a prediction" in b["note"]


def test_projection_moves_the_right_way():
    r = assessment.run(BASE, with_models=False)
    p = prescribe.projection(r)
    none, half, full = (p["scenarios"][k]["values"] for k in ("none", "half", "full"))
    assert none == [100.0] * 13 and full[0] == half[0] == 100.0
    assert all(a >= b for a, b in zip(full, full[1:])) and full[-1] < half[-1] < 100
    assert [m["week"] for m in p["milestones"]] == [3, 11, 12]


def test_forecast_endpoint_and_his_own_choice():
    with TestClient(app) as c:
        tok = c.post("/api/session", json={"lang": "en"}).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        c.post("/api/consent", json={"core": True}, headers=h)
        aid = c.post("/api/assessments", headers=h).json()["id"]
        c.put(f"/api/assessments/{aid}/answers", json={"answers": BASE}, headers=h)
        c.post(f"/api/assessments/{aid}/submit", headers=h)
        f = c.get(f"/api/assessments/{aid}/forecast", headers=h).json()
        assert f["selected"] == f["best"]["bundle"]["nodes"]
        only = c.get(f"/api/assessments/{aid}/forecast?nodes=sleep_loss", headers=h).json()
        assert only["selected"] == ["sleep_loss"] and only["projection"]["scenarios"]["full"]["values"][-1] > f["projection"]["scenarios"]["full"]["values"][-1]
        ar = c.get(f"/api/assessments/{aid}/forecast?lang=ar", headers=h).json()
        assert "ليس توقعاً" in ar["best"]["note"]


def test_dropout_early_warning_explains_itself():
    row = {"review_consent": 0}
    appt = {"status": "missed", "slot_at": None, "created_at": 0}
    ref = {"barrier": "time", "status": "attended"}
    r = prescribe.dropout_risk(row, ref, appt, {"phq1": 2, "phq2": 2}, stalled=True)
    assert r["band"] == "high" and {x["factor"] for x in r["reasons"]} == {"prior_missed", "barrier", "low_mood", "stalled", "no_review"}
    assert all(x["source"] for x in r["reasons"])
    low = prescribe.dropout_risk({"review_consent": 1}, None, None, {})
    assert low["band"] == "low" and low["points"] == 0
