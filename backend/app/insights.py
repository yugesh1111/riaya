"""Programme dashboard for the health authority (ADPHC / DoH): aggregated and k-anonymised.

Any group with fewer than K men is suppressed. No row-level data leaves this function.
"""
import statistics
import time
from datetime import datetime, timezone

from . import security, visit
from .knowledge import graph

K = 5
USUAL_PATHWAY_DAYS = 365  # men are typically assessed after 12+ months of trying (ASRM 2020)
REACHED = ("attended", "tests_done", "followed_up")


def _median(v):
    return round(statistics.median(v), 1) if v else None


def _pct(a, b):
    return round(100 * a / b) if b else None


def build(c, include_simulated=False):
    g = graph()
    sim = "" if include_simulated else " WHERE simulated=0"
    rows = c.execute("SELECT * FROM assessments" + sim).fetchall()
    refs = {r["assessment_id"]: r for r in c.execute("SELECT * FROM referrals").fetchall()}
    appts = {}
    for a in c.execute("SELECT * FROM appointments ORDER BY created_at").fetchall():
        appts[a["assessment_id"]] = a
    simulated = c.execute("SELECT COUNT(*) FROM assessments WHERE simulated=1").fetchone()[0]
    done = [r for r in rows if r["completed_at"]]
    now = time.time()

    referred = [r for r in done if r["level"] and r["level"] != "self_care"]
    approved = [r for r in referred if r["id"] in refs and refs[r["id"]]["reviewed_at"]]
    booked = [r for r in referred if (r["id"] in refs and refs[r["id"]]["booked_at"]) or (r["id"] in appts and appts[r["id"]]["status"] in ("confirmed", "attended"))]
    chosen = [r for r in referred if r["id"] in appts or r in booked]  # booking outside Care Connect still means a clinic was chosen
    reached = [r for r in referred if r["id"] in refs and (refs[r["id"]]["status"] in REACHED or refs[r["id"]]["attended_at"])]
    funnel = [{"step": "Started a check", "n": len(rows)}, {"step": "Completed it", "n": len(done)},
              {"step": "Advised to see a clinician", "n": len(referred)}, {"step": "Doctor reviewed", "n": len(approved)},
              {"step": "Chose a clinic", "n": len(chosen)}, {"step": "Booked", "n": len(booked)}, {"step": "Seen by a clinician", "n": len(reached)}]

    to_eval = [(refs[r["id"]]["attended_at"] - r["completed_at"]) / 86400 for r in reached if refs[r["id"]]["attended_at"]]
    to_review = [(refs[r["id"]]["reviewed_at"] - refs[r["id"]]["created_at"]) / 3600 for r in approved]
    rapid = [refs[r["id"]] for r in done if r["id"] in refs and refs[r["id"]]["rapid"] and refs[r["id"]]["due_at"]]
    on_time = [x for x in rapid if x["reviewed_at"] and x["reviewed_at"] <= x["due_at"]]
    overdue = [x for x in rapid if not x["reviewed_at"] and now > x["due_at"]]
    minutes = [(r["completed_at"] - r["started_at"]) / 60 for r in done]

    drivers, prevalence, n_res = {}, {}, 0
    for r in done:
        res = security.unseal(r["result"])
        if not res:
            continue
        n_res += 1
        attr = {k: v for k, v in res["attribution"].items() if v > 0 and g.nodes[k].get("modifiable")}
        total = sum(attr.values()) or 1
        for k, v in attr.items():
            drivers[k] = drivers.get(k, 0) + v / total
        for k, v in res["inputs"].items():
            if v >= 0.5 and g.nodes[k].get("type") != "outcome":
                prevalence[k] = prevalence.get(k, 0) + 1
    top = sorted(drivers.items(), key=lambda kv: -kv[1])[:10]
    weekly = {}
    for r in done:
        w = datetime.fromtimestamp(r["completed_at"], timezone.utc).strftime("%G-%V")
        weekly[w] = weekly.get(w, 0) + 1

    def groups(idx):
        out = {}
        for r in done:
            key = ((r["cohort"] or "unknown|unknown").split("|") + ["unknown"])[idx] or "unknown"
            out.setdefault(key, []).append(r)
        res = []
        for k, v in sorted(out.items()):
            if len(v) < K:
                res.append({"group": k, "suppressed": True})
                continue
            ref = [x for x in v if x["level"] != "self_care"]
            res.append({"group": k, "n": len(v), "referred_pct": _pct(len(ref), len(v)),
                        "high_pct": _pct(sum(x["tier"] == "high" for x in v), len(v)),
                        "attended_pct": _pct(sum(1 for x in ref if x["id"] in refs and refs[x["id"]]["status"] in REACHED), len(ref))})
        return res

    count = lambda key: {k: v for k, v in _count(key(r) for r in done).items() if v >= K}
    return {
        "k_anonymity": K, "includes_simulated": include_simulated, "simulated": simulated, "generated_at": now,
        "tiles": {"completed": len(done), "completion_rate": _pct(len(done), len(rows)), "median_days_to_evaluation": _median(to_eval),
                  "usual_pathway_days": USUAL_PATHWAY_DAYS, "referral_completion": _pct(len(reached), len(referred)),
                  "rapid_on_time": _pct(len(on_time), len([x for x in rapid if x["reviewed_at"]])), "rapid_overdue": len(overdue),
                  "median_minutes": _median(minutes), "median_hours_to_review": _median(to_review)},
        "funnel": funnel if len(rows) >= K else [{"step": f["step"], "n": 0} for f in funnel],
        "reviewed": {"reviewed_by_doctor": len(approved)},
        "drivers": [{"node": k, "label": g.nodes[k]["label"], "share": round(100 * v / max(1, n_res), 1)} for k, v in top] if n_res >= K else [],
        "prevalence": [{"node": k, "label": g.nodes[k]["label"], "pct": _pct(v, n_res)} for k, v in sorted(prevalence.items(), key=lambda kv: -kv[1])[:12]
                       if v >= K] if n_res >= K else [],
        "weekly": [{"week": k, "n": v} for k, v in sorted(weekly.items()) if v >= K or include_simulated],
        "levels": count(lambda r: refs[r["id"]]["final_level"] if r["id"] in refs and refs[r["id"]]["final_level"] else r["level"]),
        "channels": count(lambda r: (r["channel"] or "web") if (r["channel"] or "web") != "sample" else "web"),
        "by_age": groups(0), "by_background": groups(1), "clinic_quality": visit.clinic_quality(c, K),
    }


def _count(it):
    out = {}
    for k in it:
        out[k] = out.get(k, 0) + 1
    return out
