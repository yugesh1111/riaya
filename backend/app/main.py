import json
import os
import secrets
import statistics
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import pgstore
from . import (prescribe, visit, assessment, care, companion, conversation, db, explain, fabric, guide, handover, ifhas, insights, labreport,
               labs, labtimeline, pathway, questionnaire, referral_loop, security, semen, sharing, wearables, wellbeing)
from .knowledge import graph

ROOT = Path(__file__).resolve().parents[2]
CONSENT_VERSION = "1.0"
PURPOSES = {"core": True, "clinician_review": False, "wearables": False, "research": False}
SHARE_HOURS = 72
MAX_UPLOAD = 300 * 1024 * 1024
MAX_REPORT = 15 * 1024 * 1024
MAX_AUDIO = 5 * 1024 * 1024
SESSION_HOURS, IDLE_MINUTES = 8, 30
RECHECK_DAYS = 90
CHANNELS = {"web", "chat", "watch", "sample", "whatsapp"}


def startup():
    db.init()
    try:
        pgstore.init()
    except Exception as e:  # the app still runs; tester feedback falls back to the local database
        print("PostgreSQL unavailable:", e)
        pgstore.URL = None
    problems = graph().validate()
    if problems:
        raise RuntimeError("Knowledge graph invalid: " + "; ".join(problems[:5]))
    user = os.environ.get("RIAYA_CLINICIAN_USER", "clinician")
    pw = os.environ.get("RIAYA_CLINICIAN_PASSWORD", "demo-clinician")
    with db.tx() as c:
        if not c.execute("SELECT 1 FROM clinicians WHERE username=?", (user,)).fetchone():
            salt, h = security.hash_password(pw)
            c.execute("INSERT INTO clinicians VALUES (?,?,?,?)", (user, salt, h, "Duty clinician"))
        care.seed(c)
    purge_expired()
    run_reminders()
    run_jitai()


@asynccontextmanager
async def lifespan(_app):
    startup()
    yield


app = FastAPI(title="Riaya API", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)


@app.middleware("http")
async def headers(request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Permissions-Policy"] = "camera=(self), geolocation=(), microphone=(self), payment=(), usb=()"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = CSP
    return resp


# Only Riaya itself and the two public CDNs the app uses (scripts), plus the on-phone speech and OCR model hosts
# (downloads). No other site can run code in Riaya, frame it, or receive form posts from it.
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' blob: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
    "worker-src 'self' blob: https://cdn.jsdelivr.net",
    "connect-src 'self' blob: data: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://huggingface.co https://*.huggingface.co https://*.hf.co https://tessdata.projectnaptha.com",
    "img-src 'self' data: blob:", "media-src 'self' blob: data:", "font-src 'self' data:",
    "style-src 'self' 'unsafe-inline'", "frame-src 'self' blob:", "object-src 'none'", "base-uri 'self'",
    "form-action 'self'", "frame-ancestors 'none'",
])


# ------------------------------------------------------------------ auth helpers
def current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    with db.tx() as c:
        row = c.execute("SELECT id FROM users WHERE token_hash=?", (security.token_hash(authorization[7:]),)).fetchone()
    if not row:
        raise HTTPException(401, "Unknown token")
    _touch(row["id"])
    return row["id"]


_last_purge = [0.0]


def _touch(user_id):
    """Records that he used the app (at most hourly), so 'delete after N months' counts from his last visit."""
    now = time.time()
    with db.tx() as c:
        c.execute("UPDATE users SET last_active=? WHERE id=? AND (last_active IS NULL OR last_active<?)", (now, user_id, now - 3600))
    if now - _last_purge[0] > 3600:
        _last_purge[0] = now
        purge_expired()
        run_reminders()
        run_jitai()


def purge_expired():
    """Erases everyone whose own retention period has passed since his last visit."""
    with db.tx() as c:
        ids = sharing.expired_users(c, time.time())
    for u in ids:
        erase_user(u)
    if ids:
        db.audit("system", "retention_erased", str(len(ids)))
    return len(ids)


def current_clinician(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    now = time.time()
    th = security.token_hash(authorization[7:])
    with db.tx() as c:
        row = c.execute("SELECT username, last_seen FROM sessions WHERE token_hash=? AND expires_at>?", (th, now)).fetchone()
        if not row or (row["last_seen"] and now - row["last_seen"] > IDLE_MINUTES * 60):
            c.execute("DELETE FROM sessions WHERE token_hash=?", (th,))
            raise HTTPException(401, "Session expired")
        c.execute("UPDATE sessions SET last_seen=? WHERE token_hash=?", (now, th))
    return row["username"]


def consents(user_id):
    with db.tx() as c:
        rows = c.execute("SELECT purpose, granted FROM consents WHERE user_id=? ORDER BY ts", (user_id,)).fetchall()
    state = {p: False for p in PURPOSES}
    for r in rows:
        state[r["purpose"]] = bool(r["granted"])
    return state


def own_assessment(aid, user_id):
    with db.tx() as c:
        row = c.execute("SELECT * FROM assessments WHERE id=? AND user_id=?", (aid, user_id)).fetchone()
    if not row:
        raise HTTPException(404, "Not found")
    return row


def completed(aid, user_id):
    row = own_assessment(aid, user_id)
    result = security.unseal(row["result"])
    if not result:
        raise HTTPException(400, "Not completed")
    return row, result


def lang_of(lang):
    return "ar" if lang == "ar" else "en"


def _referral(c, aid):
    return c.execute("SELECT * FROM referrals WHERE assessment_id=?", (aid,)).fetchone()


def _final_level(row, ref):
    return (ref["final_level"] if ref and ref["final_level"] else None) or row["level"]


def _message(c, aid, sender, body):
    c.execute("INSERT INTO messages (id, assessment_id, sender, body, ts) VALUES (?,?,?,?,?)",
              (str(uuid.uuid4()), aid, sender, security.seal(body), time.time()))


# ------------------------------------------------------------------ he is told every time someone opens his record
NOTIFY_ON = {"view_case", "open_share", "view_labs", "clinic_view", "handover_generated"}
WHO = {"en": {"clinician": "a Riaya doctor", "clinic": "the clinic you chose"}, "ar": {"clinician": "طبيب من رعاية", "clinic": "العيادة التي اخترتها"}}


def _access(actor, action, aid):
    """Audits the access, then tells him in a private message: who opened what, and when. At most once per 30 minutes
    for the same kind of access, so a doctor reading his case does not flood his inbox."""
    db.audit(actor, action, aid)
    if action not in NOTIFY_ON or not aid:
        return
    with db.tx() as c:
        row = c.execute("SELECT a.id, u.lang FROM assessments a JOIN users u ON u.id=a.user_id WHERE a.id=? AND a.simulated=0", (aid,)).fetchone()
        if not row or c.execute("SELECT 1 FROM events WHERE assessment_id=? AND type='access_notice' AND detail=? AND ts>?",
                                (aid, action, time.time() - 1800)).fetchone():
            return
        L = "ar" if (row["lang"] or "ar") == "ar" else "en"
        who = WHO[L]["clinic" if str(actor).startswith("clinic:") else "clinician"]
        what = sharing.ACCESS_TEXT[L].get(action, action)
        when = time.strftime("%H:%M", time.gmtime(time.time() + 4 * 3600))
        body = (f"🔒 {what} ({who}, {when}). إن لم تكن تتوقع ذلك، أوقف كل المشاركة من «الخصوصية» بلمسة واحدة."
                if L == "ar" else f"🔒 {what} ({who}, {when}). Not expecting this? Pause all sharing in Privacy with one switch.")
        _message(c, aid, "riaya", body)
        c.execute("INSERT INTO events VALUES (?,?,?,?)", (time.time(), aid, "access_notice", action))


# ------------------------------------------------------------------ public reference data
@app.get("/api/health")
def health():
    return {"ok": True, "feedback_store": "postgres" if pgstore.enabled() else "local"}


@app.get("/api/config")
def public_config():
    """Non-secret settings the web app needs (e.g. the WhatsApp number to show as a QR code)."""
    return {"whatsapp_number": os.environ.get("RIAYA_WHATSAPP_NUMBER", ""), "whatsapp_join": os.environ.get("RIAYA_WHATSAPP_JOIN", ""),
            "video_enabled": bool(os.environ.get("RIAYA_VIDEO_BASE")), "uae_hosted": os.environ.get("RIAYA_UAE_HOSTED") == "1"}


@app.get("/api/graph")
def get_graph():
    return graph().data


@app.get("/api/questionnaire")
def get_questionnaire():
    return questionnaire.schema(graph())


@app.get("/api/model-card")
def model_card():
    from . import ml, riayanet, synth
    meta = synth.load()["meta"]
    return {"evidence_engine": {"nodes": len(graph().nodes), "edges": len(graph().edges), "references": len(graph().refs)},
            "riaya_net": {k: v for k, v in riayanet.model().items() if k not in ("weights", "biases", "mean", "scale", "fill")},
            "simulated_gbm": meta, "uci_logistic": {"model": "Logistic regression", "data": "UCI Fertility (n=100)",
                                                    "coefficients": dict(zip(ml.model()["features"], ml.model()["coef"]))}}


class FabricIn(BaseModel):
    text: str = Field(max_length=500)
    garment: str = "underwear"
    fit: str = "regular"


@app.post("/api/fabric")
def fabric_check(body: FabricIn):
    return fabric.assess(body.text, body.garment, body.fit)


@app.get("/api/providers")
def list_providers(level: Optional[str] = None, lang: str = "en"):
    with db.tx() as c:
        return {"providers": care.providers_for(c, level, lang_of(lang))}


# ------------------------------------------------------------------ anonymous session + consent
class SessionIn(BaseModel):
    lang: str = "ar"


@app.post("/api/session")
def new_session(body: SessionIn):
    """No name, phone, email or Emirates ID. The token lives only on the man's device."""
    token, uid = security.new_token(), str(uuid.uuid4())
    with db.tx() as c:
        c.execute("INSERT INTO users (id, token_hash, created_at, lang) VALUES (?,?,?,?)", (uid, security.token_hash(token), time.time(), body.lang))
    return {"token": token}


class ConsentIn(BaseModel):
    core: bool
    clinician_review: bool = False
    wearables: bool = False
    research: bool = False


@app.post("/api/consent")
def set_consent(body: ConsentIn, user=Depends(current_user)):
    if not body.core:
        raise HTTPException(400, "Core consent is needed to produce a summary")
    before = consents(user)
    now = time.time()
    with db.tx() as c:
        for p, v in body.model_dump().items():
            c.execute("INSERT INTO consents VALUES (?,?,?,?,?)", (user, p, int(v), CONSENT_VERSION, now))
            rcpt = {"clinician_review": "doctor"}.get(p, p)
            first = not c.execute("SELECT 1 FROM consent_receipts WHERE user_id=? AND recipient=?", (user, rcpt)).fetchone()
            if first or before.get(p) != v:
                sharing.receipt(c, user, rcpt, "granted" if v else ("declined" if first else "withdrawn"))
        if before["clinician_review"] and not body.clinician_review:
            # withdrawal: every doctor loses sight of his checks, including pending reviews and share codes
            ids = [r["id"] for r in c.execute("SELECT id FROM assessments WHERE user_id=?", (user,)).fetchall()]
            for aid in ids:
                c.execute("INSERT INTO consents VALUES (?,?,?,?,?)", (user, f"clinician_review:{aid}", 0, CONSENT_VERSION, now))
                c.execute("UPDATE assessments SET review_consent=0 WHERE id=?", (aid,))
                c.execute("UPDATE referrals SET status='suggested' WHERE assessment_id=? AND status='pending_review'", (aid,))
                c.execute("UPDATE shares SET revoked=1 WHERE assessment_id=?", (aid,))
        elif body.clinician_review and not before["clinician_review"]:
            for r in c.execute("SELECT id FROM assessments WHERE user_id=? AND completed_at IS NOT NULL", (user,)).fetchall():
                c.execute("UPDATE assessments SET review_consent=1 WHERE id=?", (r["id"],))
                c.execute("UPDATE referrals SET status='pending_review' WHERE assessment_id=? AND status='suggested' AND reviewed_at IS NULL", (r["id"],))
    db.audit("user", "consent_changed", user[:8])
    return consents(user)


@app.get("/api/consent")
def get_consent(user=Depends(current_user)):
    return consents(user)


# ------------------------------------------------------------------ assessment
@app.post("/api/assessments")
def start(channel: str = "web", user=Depends(current_user)):
    if not consents(user)["core"]:
        raise HTTPException(403, "Consent required")
    aid = str(uuid.uuid4())
    with db.tx() as c:
        c.execute("INSERT INTO assessments (id, user_id, started_at, channel) VALUES (?,?,?,?)",
                  (aid, user, time.time(), channel if channel in CHANNELS else "web"))
    db.event(aid, "started", channel)
    return {"id": aid}


class AnswersIn(BaseModel):
    answers: dict


@app.put("/api/assessments/{aid}/answers")
def save_answers(aid: str, body: AnswersIn, user=Depends(current_user)):
    own_assessment(aid, user)
    allowed = {q["id"] for q in questionnaire.QUESTIONS}
    clean = {k: v for k, v in body.answers.items() if k in allowed}  # data minimisation: drop anything unexpected
    with db.tx() as c:
        c.execute("UPDATE assessments SET answers=? WHERE id=?", (security.seal(clean), aid))
    db.event(aid, "answers_saved", str(len(clean)))
    return {"saved": len(clean)}


@app.post("/api/assessments/{aid}/wearables")
async def upload_wearables(aid: str, file: UploadFile = File(...), user=Depends(current_user)):
    row = own_assessment(aid, user)
    if not consents(user)["wearables"]:
        raise HTTPException(403, "Device-data consent not given")
    raw = await file.read()
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "File too large")
    try:
        summary = wearables.detect_and_parse(file.filename or "", raw)
    except (ValueError, StopIteration, KeyError) as e:
        raise HTTPException(422, str(e) or "Could not read file")
    finally:
        del raw  # raw export is never stored
    merged = wearables.merge(security.unseal(row["wearable"]), summary)
    with db.tx() as c:
        c.execute("UPDATE assessments SET wearable=? WHERE id=?", (security.seal(merged), aid))
    db.event(aid, "wearable_import", summary.get("source"))
    return merged


@app.post("/api/assessments/{aid}/passive")
def passive(aid: str, lang: str = "en", user=Depends(current_user)):
    """What the devices alone suggest, before any question is asked."""
    row = own_assessment(aid, user)
    return explain.passive(security.unseal(row["wearable"]), lang_of(lang))


class ManualDevice(BaseModel):
    sleep_avg_h: Optional[float] = Field(None, ge=0, le=16)
    steps_avg: Optional[float] = Field(None, ge=0, le=60000)
    screen_daily_h: Optional[float] = Field(None, ge=0, le=24)
    spo2_low_nights: Optional[int] = Field(None, ge=0, le=31)
    social_jetlag_h: Optional[float] = Field(None, ge=0, le=12)


@app.post("/api/assessments/{aid}/device-manual")
def manual_device(aid: str, body: ManualDevice, user=Depends(current_user)):
    row = own_assessment(aid, user)
    merged = wearables.merge(security.unseal(row["wearable"]), {**body.model_dump(exclude_none=True), "source": "manual"})
    with db.tx() as c:
        c.execute("UPDATE assessments SET wearable=? WHERE id=?", (security.seal(merged), aid))
    return merged


class SemenIn(BaseModel):
    source: str = Field(pattern="^(lab|home_quant|home_simple)$")
    kit: Optional[str] = None
    result: Optional[str] = None
    volume_ml: Optional[float] = Field(None, ge=0, le=20)
    concentration_m_per_ml: Optional[float] = Field(None, ge=0, le=500)
    total_count_m: Optional[float] = Field(None, ge=0, le=3000)
    total_motility_pct: Optional[float] = Field(None, ge=0, le=100)
    progressive_motility_pct: Optional[float] = Field(None, ge=0, le=100)
    normal_forms_pct: Optional[float] = Field(None, ge=0, le=100)
    vitality_pct: Optional[float] = Field(None, ge=0, le=100)
    ph: Optional[float] = Field(None, ge=5, le=10)
    abstinence_days: Optional[float] = Field(None, ge=0, le=60)
    motile_conc_m_per_ml: Optional[float] = Field(None, ge=0, le=500)
    prog_motile_conc_m_per_ml: Optional[float] = Field(None, ge=0, le=500)


@app.post("/api/assessments/{aid}/semen")
def add_semen(aid: str, body: SemenIn, user=Depends(current_user)):
    own_assessment(aid, user)
    d = body.model_dump(exclude_none=True)
    if body.source == "lab":
        out = semen.interpret_lab(d)
    elif body.source == "home_quant":
        out = semen.interpret_home_quantitative(d, body.kit or "yo")
    else:
        out = semen.interpret_home(body.kit or "other", body.result)
    with db.tx() as c:
        c.execute("UPDATE assessments SET semen=? WHERE id=?", (security.seal(out), aid))
    db.event(aid, "semen_added", body.source)
    return {"findings": out["findings"], "notes": out["notes"], "normal": out["normal"]}


class LabsIn(BaseModel):
    testosterone: Optional[float] = Field(None, ge=0, le=2000)
    testosterone_unit: str = Field("nmol/L", pattern="^(nmol/L|ng/dL)$")
    fsh: Optional[float] = Field(None, ge=0, le=200)
    lh: Optional[float] = Field(None, ge=0, le=200)
    hba1c: Optional[float] = Field(None, ge=3, le=20)
    vitamin_d: Optional[float] = Field(None, ge=0, le=400)
    vitamin_d_unit: str = Field("ng/mL", pattern="^(ng/mL|nmol/L)$")
    date: Optional[str] = Field(None, max_length=10)


@app.post("/api/assessments/{aid}/labs")
def add_labs(aid: str, body: LabsIn, user=Depends(current_user)):
    own_assessment(aid, user)
    out = labs.interpret(body.model_dump(exclude_none=True))
    with db.tx() as c:
        c.execute("UPDATE assessments SET labs=? WHERE id=?", (security.seal(out), aid))
    db.event(aid, "labs_added")
    return {"findings": [f[:3] for f in out["findings"]]}


@app.post("/api/assessments/{aid}/lab-report")
async def read_lab_report(aid: str, file: Optional[UploadFile] = File(None), text: Optional[str] = Form(None),
                          lang: str = "en", user=Depends(current_user)):
    """Extracts values for him to confirm. Nothing is saved and the file is discarded."""
    own_assessment(aid, user)
    if file is not None:
        raw = await file.read()
        if len(raw) > MAX_REPORT:
            raise HTTPException(413, "File too large")
        try:
            content = labreport.pdf_text(raw) if raw[:5] == b"%PDF-" else raw.decode("utf-8", "ignore")
        except Exception:
            raise HTTPException(422, "Could not read this file. Try a photo of the report, or type the values.")
        finally:
            del raw
    elif text:
        content = text[:20000]
    else:
        raise HTTPException(400, "Send a file or text")
    return labreport.read(content, lang_of(lang))


def _cohort(answers):
    age = answers.get("age")
    try:
        band = f"{int(float(age)) // 10 * 10}s"
    except (TypeError, ValueError):
        band = "unknown"
    return f"{band}|{answers.get('background') or 'unknown'}"


def run_submit(aid, user, lang="en"):
    row = own_assessment(aid, user)
    answers = security.unseal(row["answers"]) or {}
    if not answers.get("age"):
        raise HTTPException(400, "Please answer at least the 'About you' section")
    result = assessment.run(answers, security.unseal(row["wearable"]), security.unseal(row["semen"]), labs=security.unseal(row["labs"]))
    t = result["triage"]
    review_ok = consents(user)["clinician_review"]
    now = time.time()
    with db.tx() as c:
        c.execute("""UPDATE assessments SET result=?, completed_at=?, tier=?, level=?, requires_review=?, review_consent=?, cohort=?
                     WHERE id=?""", (security.seal(result), now, t["tier"], t["level"], int(t["requires_review"]),
                                     int(review_ok), _cohort(answers), aid))
        c.execute("DELETE FROM referrals WHERE assessment_id=? AND status IN ('pending_review','suggested')", (aid,))
        if t["level"] != "self_care":
            status = "pending_review" if t["requires_review"] and review_ok else "suggested"
            due = now + t["sla_hours"] * 3600 if t.get("rapid_review") and t.get("sla_hours") else None
            c.execute("INSERT INTO referrals (id, assessment_id, level, status, created_at, rapid, due_at) VALUES (?,?,?,?,?,?,?)",
                      (str(uuid.uuid4()), aid, t["level"], status, now, int(bool(t.get("rapid_review"))), due))
    db.event(aid, "completed", t["level"])
    view = assessment.user_view(result, lang_of(lang))
    view["clinician_review"] = "queued" if t["requires_review"] and review_ok else ("available" if t["requires_review"] else "not_needed")
    return view


@app.post("/api/assessments/{aid}/submit")
def submit(aid: str, lang: str = "en", user=Depends(current_user)):
    return run_submit(aid, user, lang)


@app.get("/api/assessments/{aid}/result")
def get_result(aid: str, lang: str = "en", user=Depends(current_user)):
    row = own_assessment(aid, user)
    result = security.unseal(row["result"])
    if not result:
        raise HTTPException(404, "Not completed")
    view = assessment.user_view(result, lang_of(lang))
    with db.tx() as c:
        ref = c.execute("SELECT status, final_level, reviewed_at, rapid, due_at, video_url FROM referrals WHERE assessment_id=?", (aid,)).fetchone()
    view["referral"] = dict(ref) if ref else None
    view["review_consent"] = bool(row["review_consent"])
    t = result["triage"]
    view["clinician_review"] = ("queued" if row["review_consent"] else "available") if t["requires_review"] else "not_needed"
    return view


@app.get("/api/assessments/{aid}/explain")
def explain_result(aid: str, lang: str = "en", user=Depends(current_user)):
    row, result = completed(aid, user)
    return explain.explain(security.unseal(row["answers"]) or {}, result, lang_of(lang))


class WhatIfIn(BaseModel):
    improve: list[str] = Field(default_factory=list, max_length=20)


@app.post("/api/assessments/{aid}/whatif")
def whatif(aid: str, body: WhatIfIn, lang: str = "en", user=Depends(current_user)):
    _, result = completed(aid, user)
    return explain.whatif(result, body.improve, lang_of(lang))


@app.get("/api/assessments/{aid}/ifhas")
def ifhas_export(aid: str, user=Depends(current_user)):
    row = own_assessment(aid, user)
    result = security.unseal(row["result"])
    if not result:
        raise HTTPException(404, "Not completed")
    db.event(aid, "ifhas_export")
    return JSONResponse(ifhas.bundle(security.unseal(row["answers"]), result),
                        headers={"Content-Disposition": "attachment; filename=prescreen-summary.fhir.json"})


class ShareIn(BaseModel):
    categories: Optional[list[str]] = None
    hours: int = Field(SHARE_HOURS, ge=1, le=168)
    purpose: str = Field("clinic", pattern="^(clinic|second_opinion)$")


@app.post("/api/assessments/{aid}/share")
def create_share(aid: str, body: Optional[ShareIn] = None, user=Depends(current_user)):
    """A one-time code. He can pick exactly what this code shows and for how long, e.g. a second opinion for 24 hours."""
    own_assessment(aid, user)
    body = body or ShareIn()
    if body.hours not in (24, 72, 168):
        raise HTTPException(400, "Choose 1, 3 or 7 days")
    code = security.share_code()
    now = time.time()
    scope = sorted(set(body.categories) & set(sharing.CATEGORIES) | sharing.REQUIRED, key=sharing.CATEGORIES.index) if body.categories is not None else None
    with db.tx() as c:
        c.execute("INSERT INTO shares (code, assessment_id, created_at, expires_at, revoked, used_by, scope, purpose) VALUES (?,?,?,?,0,NULL,?,?)",
                  (code, aid, now, now + body.hours * 3600, json.dumps(scope) if scope else None, body.purpose))
        sharing.receipt(c, user, "share_code", "granted", {"code": code, "hours": body.hours, "purpose": body.purpose,
                                                          "categories": scope or sharing.get(c, user)["clinic"]})
    db.event(aid, "share_created", body.purpose)
    return {"code": code, "expires_in_hours": body.hours, "categories": scope, "purpose": body.purpose,
            "link": f"/clinic.html#code={code}"}


@app.delete("/api/shares/{code}")
def revoke_share(code: str, user=Depends(current_user)):
    with db.tx() as c:
        n = c.execute("""UPDATE shares SET revoked=1 WHERE code=? AND assessment_id IN
                         (SELECT id FROM assessments WHERE user_id=?)""", (code, user)).rowcount
        if n:
            sharing.receipt(c, user, "share_code", "withdrawn", {"code": code})
    if not n:
        raise HTTPException(404, "Not found")
    return {"revoked": True}


class FeedbackIn(BaseModel):
    trust: int = Field(ge=1, le=5)
    clarity: int = Field(ge=1, le=5)
    comfort: int = Field(ge=1, le=5)


@app.post("/api/assessments/{aid}/feedback")
def feedback(aid: str, body: FeedbackIn, user=Depends(current_user)):
    own_assessment(aid, user)
    with db.tx() as c:
        c.execute("INSERT OR REPLACE INTO feedback VALUES (?,?,?,?,?)", (aid, body.trust, body.clarity, body.comfort, time.time()))
    return {"ok": True}


# ------------------------------------------------------------------ lab intelligence (saved results)
class LabValue(BaseModel):
    field: str
    value: float
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    ref_text: Optional[str] = Field(None, max_length=40)
    extracted_value: Optional[float] = None
    score: Optional[float] = None
    line: Optional[str] = Field(None, max_length=240)
    lab_flag: Optional[str] = Field(None, max_length=10)


class LabSaveIn(BaseModel):
    assessment_id: Optional[str] = None
    collected_on: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    lab_name: Optional[str] = Field(None, max_length=80)
    source: str = Field("report", pattern="^(report|manual)$")
    abstinence_days: Optional[float] = Field(None, ge=0, le=60)
    time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    fasting: Optional[bool] = None
    fever_recent: Optional[bool] = None
    age: Optional[int] = Field(None, ge=16, le=99)
    values: list[LabValue] = Field(min_length=1, max_length=20)


@app.post("/api/me/labs")
def save_labs(body: LabSaveIn, user=Depends(current_user)):
    """He saves values he has checked against his report. A doctor can later accept, correct or set aside each one."""
    if body.assessment_id:
        own_assessment(body.assessment_id, user)
    ctx = {k: v for k, v in {"abstinence_days": body.abstinence_days, "time": body.time, "fasting": body.fasting,
                             "fever_recent": body.fever_recent, "age": body.age}.items() if v is not None}
    ids, now = [], time.time()
    collected = body.collected_on or time.strftime("%Y-%m-%d")
    with db.tx() as c:
        for v in body.values:
            if v.field not in labtimeline.NAMES:
                continue
            ref = {"low": v.ref_low, "high": v.ref_high, "text": v.ref_text} if (v.ref_low is not None or v.ref_high is not None) else None
            detail = {"ref": ref, "context": ctx, "lab_name": body.lab_name, "source": body.source, "lab_flag": v.lab_flag,
                      "line": v.line, "score": v.score,
                      "edited_by_user": v.extracted_value is not None and abs(v.extracted_value - v.value) > 1e-9}
            rid = str(uuid.uuid4())
            c.execute("""INSERT INTO lab_results (id, user_id, assessment_id, field, value, extracted_value, collected_on, created_at, detail)
                         VALUES (?,?,?,?,?,?,?,?,?)""", (rid, user, body.assessment_id, v.field, v.value, v.extracted_value, collected, now,
                                                          security.seal(detail)))
            ids.append(rid)
    if not ids:
        raise HTTPException(400, "No recognised values")
    db.event(body.assessment_id, "lab_results_saved", str(len(ids)))
    return {"saved": ids}


def _lab_points(c, where, args, lang):
    pts = []
    for r in c.execute(f"SELECT * FROM lab_results WHERE {where} ORDER BY collected_on, created_at", args).fetchall():
        pts.append(labtimeline.point(r, security.unseal(r["detail"]) or {}, lang, security.unseal(r["review_note"])))
    return pts


@app.get("/api/me/labs")
def my_labs(lang: str = "en", user=Depends(current_user)):
    L = lang_of(lang)
    with db.tx() as c:
        pts = _lab_points(c, "user_id=?", (user,), L)
    series = labtimeline.series(pts, L)
    return {"series": series, "pending_review": sum(p["review_status"] == "pending" for p in pts),
            "dashboard": labtimeline.dashboard(series, L), "note": labtimeline.TXT[L]["note"]}


@app.delete("/api/me/labs/{rid}")
def delete_lab(rid: str, user=Depends(current_user)):
    with db.tx() as c:
        if not c.execute("DELETE FROM lab_results WHERE id=? AND user_id=?", (rid, user)).rowcount:
            raise HTTPException(404, "Not found")
    return {"deleted": True}


# ------------------------------------------------------------------ 12-week companion
def _doctor_review_on(user, row):
    return bool(row["review_consent"]) or consents(user)["clinician_review"]


@app.get("/api/assessments/{aid}/plan-options")
def plan_options(aid: str, lang: str = "en", user=Depends(current_user)):
    row, result = completed(aid, user)
    return {"options": companion.options(result, graph(), lang_of(lang)), "max": companion.MAX_GOALS,
            "doctor_review": _doctor_review_on(user, row)}


class PlanIn(BaseModel):
    nodes: list[str] = Field(min_length=1, max_length=3)


def _ramadan_setting(c, user):
    u = c.execute("SELECT ramadan FROM users WHERE id=?", (user,)).fetchone()
    return (u["ramadan"] if u and u["ramadan"] else "auto")


def _plan_view(r, lang):
    """The 12-week companion, with its behaviour-change techniques, WHO-5 outcomes, relapse support and Ramadan timing."""
    L = lang_of(lang)
    v = companion.view(r, security.unseal(r["items"]), security.unseal(r["checkins"]) or [], L, security.unseal(r["doctor_note"]))
    with db.tx() as c:
        setting = _ramadan_setting(c, r["user_id"])
    ram = wellbeing.ramadan_view(setting, L)
    for it in v["items"]:
        it["techniques"] = wellbeing.techniques_for(it["node"], L)
        if ram["active"]:
            it["ramadan"] = wellbeing.ramadan_goal(it["node"], L)
    entries = security.unseal(r["wellbeing"]) or []
    restart = security.unseal(r["restart"])
    v["restart"] = ({"barrier": restart["barrier_label_" + L], "if_then": restart["if_then_" + L], "kept": restart["kept"], "at": restart["at"]}
                    if restart else None)
    v["who5"] = {"entries": [{"point": e["point"], "score": e["score"], "week": e["week"]} for e in entries],
                 "due": wellbeing.who5_due(v["week"], entries) if v["status"] in ("active", "self_guided") else None,
                 "change": wellbeing.who5_change(entries), "latest_band": wellbeing.who5_band(entries[-1]["score"], L) if entries else None,
                 "meaningful_points": wellbeing.MEANINGFUL}
    v["lapse"] = None if restart and restart["at"] > time.time() - 14 * 86400 else wellbeing.lapse(v)
    v["ramadan"] = ram
    return v


@app.post("/api/assessments/{aid}/plan")
def start_plan(aid: str, body: PlanIn, lang: str = "en", user=Depends(current_user)):
    row, result = completed(aid, user)
    items = companion.items_for(body.nodes, result, graph())
    if not items:
        raise HTTPException(400, "Choose goals from your summary")
    review = _doctor_review_on(user, row)
    now, pid = time.time(), str(uuid.uuid4())
    with db.tx() as c:
        c.execute("UPDATE plans SET status='stopped', stopped_at=? WHERE user_id=? AND status IN ('proposed','active','self_guided')", (now, user))
        c.execute("INSERT INTO plans (id, user_id, assessment_id, status, created_at, start_at, items) VALUES (?,?,?,?,?,?,?)",
                  (pid, user, aid, "proposed" if review else "self_guided", now, None if review else now, security.seal(items)))
        r = c.execute("SELECT * FROM plans WHERE id=?", (pid,)).fetchone()
    db.event(aid, "plan_started", "proposed" if review else "self_guided")
    return _plan_view(r, lang)


def _my_plan(c, user):
    return c.execute("SELECT * FROM plans WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user,)).fetchone()


@app.get("/api/me/plan")
def my_plan(lang: str = "en", user=Depends(current_user)):
    with db.tx() as c:
        r = _my_plan(c, user)
    return {"plan": _plan_view(r, lang) if r else None}


@app.delete("/api/me/plan")
def stop_plan(user=Depends(current_user)):
    with db.tx() as c:
        c.execute("UPDATE plans SET status='stopped', stopped_at=? WHERE user_id=? AND status IN ('proposed','active','self_guided')", (time.time(), user))
    return {"stopped": True}


class CheckinIn(BaseModel):
    week: Optional[int] = Field(None, ge=1, le=12)
    items: dict[str, dict[str, Optional[float]]]
    energy: Optional[int] = Field(None, ge=1, le=5)


@app.post("/api/me/plan/checkin")
def checkin(body: CheckinIn, lang: str = "en", user=Depends(current_user)):
    with db.tx() as c:
        r = _my_plan(c, user)
        if not r or r["status"] not in ("active", "self_guided"):
            raise HTTPException(400, "No running plan")
        week = body.week or min(companion.WEEKS, companion.week_of(r["start_at"]))
        items = {it["node"]: it for it in security.unseal(r["items"])}
        clean = {}
        for node, v in body.items.items():
            if node not in items:
                continue
            adh = v.get("adherence")
            if adh is None or not 0 <= adh <= 3:
                raise HTTPException(422, "Adherence must be 0 to 3")
            val, m = v.get("value"), items[node].get("measure")
            if val is not None and m and not m[3] <= val <= m[4]:
                raise HTTPException(422, f"{m[1]} must be between {m[3]} and {m[4]}")
            clean[node] = {"adherence": int(adh), "value": val if m else None}
        cks = [x for x in (security.unseal(r["checkins"]) or []) if x["week"] != week]
        cks.append({"week": week, "items": clean, "energy": body.energy, "ts": time.time()})
        c.execute("UPDATE plans SET checkins=? WHERE id=?", (security.seal(sorted(cks, key=lambda x: x["week"])), r["id"]))
        r = c.execute("SELECT * FROM plans WHERE id=?", (r["id"],)).fetchone()
    return _plan_view(r, lang)


class ReminderIn(BaseModel):
    enabled: bool


@app.post("/api/me/plan/reminders")
def set_reminders(body: ReminderIn, user=Depends(current_user)):
    with db.tx() as c:
        r = _my_plan(c, user)
        if not r:
            raise HTTPException(404, "No plan")
        c.execute("UPDATE plans SET reminders=? WHERE id=?", (int(body.enabled), r["id"]))
    return {"ok": True}


@app.get("/api/me/plan/reminders.ics")
def reminders_ics(user=Depends(current_user)):
    """A weekly entry that says only 'Weekly check-in', at 8 pm Gulf time, for the rest of the 12 weeks."""
    with db.tx() as c:
        r = _my_plan(c, user)
    if not r or not r["start_at"]:
        raise HTTPException(404, "No running plan")
    return Response(companion.reminders_ics(r["id"], r["start_at"]), media_type="text/calendar",
                    headers={"Content-Disposition": "attachment; filename=weekly-check-in.ics"})


# ------------------------------------------------------------------ wellbeing outcomes, relapse recovery, Ramadan, behaviour-change design
SUPPORT_LINE = {"en": "UAE national mental-health support line: 800 4673 (800HOPE)", "ar": "خط الدعم النفسي الوطني في الإمارات: 800 4673 (800HOPE)"}


@app.get("/api/wellbeing/who5")
def who5_form(lang: str = "en"):
    return wellbeing.who5_form(lang_of(lang))


class Who5In(BaseModel):
    answers: list[int] = Field(min_length=5, max_length=5)


@app.post("/api/me/plan/who5")
def who5_submit(body: Who5In, lang: str = "en", user=Depends(current_user)):
    """WHO-5 at day 0, ~30 and ~84. A score of 28 or less offers a private talk with a doctor and the national support line."""
    L = lang_of(lang)
    try:
        score = wellbeing.who5_score(body.answers)
    except ValueError as e:
        raise HTTPException(422, str(e))
    with db.tx() as c:
        r = _my_plan(c, user)
        if not r or r["status"] not in ("active", "self_guided"):
            raise HTTPException(400, "No running plan")
        week = min(companion.WEEKS, companion.week_of(r["start_at"]))
        entries = security.unseal(r["wellbeing"]) or []
        point = wellbeing.who5_due(week, entries)
        if not point:
            raise HTTPException(409, "No wellbeing check is due this week")
        band = wellbeing.who5_band(score, L)
        escalated = False
        if band["action"] == "clinician_review" and consents(user)["clinician_review"] and not sharing.is_paused(c, user):
            _message(c, r["assessment_id"], "riaya", wellbeing.nudge_text("low_wellbeing", L))
            escalated = True
        entries.append({"point": point, "score": score, "week": week, "ts": time.time(), "escalated": escalated})
        c.execute("UPDATE plans SET wellbeing=? WHERE id=?", (security.seal(entries), r["id"]))
        r = c.execute("SELECT * FROM plans WHERE id=?", (r["id"],)).fetchone()
    db.event(r["assessment_id"], "who5", f"{point}:{score}")
    if escalated:
        db.event(r["assessment_id"], "who5_escalated", point)
    return {"score": score, "point": point, "band": band, "escalated": escalated,
            "support_line": SUPPORT_LINE[L] if band["band"] != "good" else None, "plan": _plan_view(r, L)}


@app.get("/api/me/plan/barriers")
def plan_barriers(lang: str = "en"):
    return {"barriers": wellbeing.barriers(lang_of(lang))}


class RestartIn(BaseModel):
    keep: str = Field(min_length=1, max_length=40)
    barrier: str = Field(pattern="^(time|urge|social|work|mood|forgot)$")


@app.post("/api/me/plan/restart")
def plan_restart(body: RestartIn, lang: str = "en", user=Depends(current_user)):
    """Fresh start after a lapse: one goal, a smaller step, and his own if-then plan for what got in the way."""
    with db.tx() as c:
        r = _my_plan(c, user)
        if not r or r["status"] not in ("active", "self_guided"):
            raise HTTPException(400, "No running plan")
        items = security.unseal(r["items"])
        if body.keep not in [i["node"] for i in items]:
            raise HTTPException(422, "Keep one of your current goals")
        kept, info = wellbeing.restart_plan(items, body.keep, body.barrier, lang_of(lang))
        c.execute("UPDATE plans SET items=?, restart=? WHERE id=?", (security.seal([kept]), security.seal(info), r["id"]))
        r = c.execute("SELECT * FROM plans WHERE id=?", (r["id"],)).fetchone()
    db.event(r["assessment_id"], "plan_restart", body.barrier)
    return _plan_view(r, lang)


class RamadanIn(BaseModel):
    setting: str = Field(pattern="^(auto|on|off)$")


@app.get("/api/me/ramadan")
def get_ramadan(lang: str = "en", user=Depends(current_user)):
    with db.tx() as c:
        return wellbeing.ramadan_view(_ramadan_setting(c, user), lang_of(lang))


@app.post("/api/me/ramadan")
def set_ramadan(body: RamadanIn, lang: str = "en", user=Depends(current_user)):
    with db.tx() as c:
        c.execute("UPDATE users SET ramadan=? WHERE id=?", (body.setting, user))
    return wellbeing.ramadan_view(body.setting, lang_of(lang))


@app.get("/api/behaviour-design")
def behaviour_design(lang: str = "en"):
    """How the companion is built: COM-B targets, BCT Taxonomy v1 codes and Self-Determination Theory principles."""
    return wellbeing.design(lang_of(lang))


def run_jitai():
    """Hourly decision point for every running plan: send at most one well-timed nudge, or nothing, and log why."""
    sent = 0
    with db.tx() as c:
        rows = c.execute("""SELECT p.* FROM plans p JOIN users u ON u.id=p.user_id
                            WHERE p.status IN ('active','self_guided') AND COALESCE(u.sharing_paused,0)=0""").fetchall()
        for r in rows:
            u = c.execute("SELECT reminders, ramadan, lang FROM users WHERE id=?", (r["user_id"],)).fetchone()
            v = _plan_view(r, u["lang"] or "ar")
            d = wellbeing.jitai_decide(v, security.unseal(r["wellbeing"]) or [], r["last_nudge_at"],
                                       bool(r["reminders"]) and bool(u["reminders"] if u["reminders"] is not None else 1), v["ramadan"]["active"])
            if not d["send"]:
                continue
            _message(c, r["assessment_id"], "riaya", wellbeing.nudge_text(d["send"], u["lang"] or "ar"))
            c.execute("UPDATE plans SET last_nudge_at=? WHERE id=?", (time.time(), r["id"]))
            c.execute("INSERT INTO events VALUES (?,?,?,?)", (time.time(), r["assessment_id"], "jitai", f"{d['send']}: {'; '.join(d['why'])}"))
            sent += 1
    return sent


@app.get("/api/me/plan/nudge-decision")
def nudge_decision(user=Depends(current_user)):
    """Why the app would, or would not, nudge him right now (every rule is visible to him)."""
    with db.tx() as c:
        r = _my_plan(c, user)
        if not r:
            raise HTTPException(404, "No plan")
        u = c.execute("SELECT reminders FROM users WHERE id=?", (user,)).fetchone()
    v = _plan_view(r, "en")
    return wellbeing.jitai_decide(v, security.unseal(r["wellbeing"]) or [], r["last_nudge_at"],
                                  bool(r["reminders"]) and bool(u["reminders"] if u["reminders"] is not None else 1), v["ramadan"]["active"])


# ------------------------------------------------------------------ closed-loop referral tracking (FHIR Task)
def _loop(c, row):
    ref = _referral(c, row["id"])
    appt = c.execute("SELECT * FROM appointments WHERE assessment_id=? AND status!='cancelled' ORDER BY created_at DESC LIMIT 1",
                     (row["id"],)).fetchone()
    con = _consultation(c, row["id"])
    level = _final_level(row, ref)
    stg, cur = pathway.stages(row, ref, appt, con, level, "en")
    loop = referral_loop.milestones(level, stg, ref)
    return loop, referral_loop.fhir_task(row["id"], level, stg, cur, ref, loop)


@app.get("/api/assessments/{aid}/referral-loop")
def referral_loop_view(aid: str, user=Depends(current_user)):
    row = own_assessment(aid, user)
    with db.tx() as c:
        loop, task = _loop(c, row)
    return {**loop, "task": task}


@app.get("/api/assessments/{aid}/fhir/task")
def referral_task(aid: str, user=Depends(current_user)):
    row = own_assessment(aid, user)
    with db.tx() as c:
        _, task = _loop(c, row)
    return JSONResponse(task, headers={"Content-Disposition": "attachment; filename=referral-task.fhir.json"})


@app.get("/api/clinician/referral-loop")
def referral_loop_board(clin=Depends(current_clinician)):
    """Every open referral against its time limits; late milestones show who it escalates to."""
    out, met, total = [], 0, 0
    with db.tx() as c:
        rows = c.execute("""SELECT a.* FROM assessments a JOIN referrals r ON r.assessment_id=a.id
                            WHERE a.completed_at IS NOT NULL AND a.user_id NOT IN (SELECT id FROM users WHERE sharing_paused=1)
                              AND (a.review_consent=1 OR EXISTS (SELECT 1 FROM appointments x WHERE x.assessment_id=a.id))""").fetchall()
        for row in rows:
            loop, task = _loop(c, row)
            met += loop["met_on_time"]
            total += sum(1 for m in loop["milestones"] if m["done_at"])
            for m in loop["overdue"]:
                out.append({"id": row["id"], "priority": loop["priority"], "milestone": m["label"], "limit_hours": m["limit_hours"],
                            "hours_late": round((time.time() - m["due_at"]) / 3600, 1), "escalate_to": m["escalate_to"],
                            "task_status": task["status"], "simulated": bool(row["simulated"])})
    db.audit(clin, "view_referral_loop")
    prio = {"stat": 0, "urgent": 1, "routine": 2}
    out.sort(key=lambda x: (prio.get(x["priority"], 3), -x["hours_late"]))
    return {"overdue": out[:100], "on_time_pct": round(100 * met / total) if total else None, "milestones_done": total,
            "limits": {k: {"priority": v[0], "hours": {m: round(s / 3600) for m, s in v[1].items()}} for k, v in referral_loop.SLA.items()}}


# ------------------------------------------------------------------ Care Connect
def _care_state(c, row, lang):
    ref = _referral(c, row["id"])
    level = _final_level(row, ref)
    appt = c.execute("SELECT * FROM appointments WHERE assessment_id=? AND status NOT IN ('cancelled') ORDER BY created_at DESC LIMIT 1",
                     (row["id"],)).fetchone()
    stage = care.stage(level, ref, appt)
    con = _consultation(c, row["id"])
    return {"stage": stage, "consultation": _consult_view(con, lang) if con else None, "level": level, "appointment": care.appt_view(c, appt, lang) if appt and appt["status"] in ("requested", "confirmed", "attended") else None,
            "last": care.appt_view(c, appt, lang) if appt and appt["status"] in ("declined", "missed") else None,
            "providers": care.providers_for(c, level, lang) if stage == "choose" else [], "missed_reasons": care.MISSED}


@app.get("/api/assessments/{aid}/care")
def care_state(aid: str, lang: str = "en", user=Depends(current_user)):
    row, _ = completed(aid, user)
    with db.tx() as c:
        return _care_state(c, row, lang_of(lang))


class RequestIn(BaseModel):
    provider_id: str = Field(min_length=1, max_length=40)
    times: list[str] = Field(default_factory=list, max_length=3)
    days: list[str] = Field(default_factory=list, max_length=2)
    contact: str = Field("messages", pattern="^(messages|phone)$")
    phone: Optional[str] = Field(None, max_length=20)
    share_summary: bool = True
    note: Optional[str] = Field(None, max_length=500)


@app.post("/api/assessments/{aid}/appointment")
def request_appointment(aid: str, body: RequestIn, lang: str = "en", user=Depends(current_user)):
    row, _ = completed(aid, user)
    L = lang_of(lang)
    with db.tx() as c:
        st = _care_state(c, row, L)
        if st["stage"] != "choose":
            raise HTTPException(409, "A clinic can't be chosen at this stage")
        if body.provider_id not in {p["id"] for p in st["providers"]}:
            raise HTTPException(400, "This clinic doesn't offer the care your referral needs")
        if body.contact == "phone" and not (body.phone and len([d for d in body.phone if d.isdigit()]) >= 7):
            raise HTTPException(400, "Add a mobile number, or choose Riaya messages")
        code, now = None, time.time()
        if body.share_summary:
            code = security.share_code()
            c.execute("INSERT INTO shares (code, assessment_id, created_at, expires_at, revoked, used_by) VALUES (?,?,?,?,0,NULL)",
                      (code, aid, now, now + care.SHARE_DAYS * 86400))
            sharing.receipt(c, user, "clinic", "granted", {"clinic": body.provider_id, "code": code, "days": care.SHARE_DAYS,
                                                          "categories": sharing.get(c, user)["clinic"]})
        prefs = {"times": [t for t in body.times if t in ("morning", "afternoon", "evening")],
                 "days": [d for d in body.days if d in ("weekday", "weekend")], "contact": body.contact,
                 "phone": body.phone if body.contact == "phone" else None, "note": body.note}
        c.execute("""INSERT INTO appointments (id, assessment_id, provider_id, status, created_at, updated_at, prefs, share_code)
                     VALUES (?,?,?,?,?,?,?,?)""", (str(uuid.uuid4()), aid, body.provider_id, "requested", now, now, security.seal(prefs), code))
        state = _care_state(c, row, L)
    db.event(aid, "appointment_requested", body.provider_id)
    return state


@app.delete("/api/assessments/{aid}/appointment")
def cancel_appointment(aid: str, user=Depends(current_user)):
    own_assessment(aid, user)
    with db.tx() as c:
        a = c.execute("SELECT * FROM appointments WHERE assessment_id=? AND status IN ('requested','confirmed') ORDER BY created_at DESC LIMIT 1",
                      (aid,)).fetchone()
        if not a:
            raise HTTPException(404, "No open request")
        c.execute("UPDATE appointments SET status='cancelled', updated_at=? WHERE id=?", (time.time(), a["id"]))
        if a["share_code"]:
            c.execute("UPDATE shares SET revoked=1 WHERE code=?", (a["share_code"],))
    db.event(aid, "appointment_cancelled")
    return {"cancelled": True}


@app.get("/api/assessments/{aid}/appointment.ics")
def appointment_ics(aid: str, user=Depends(current_user)):
    """A calendar entry that says only 'Appointment' and the place, so nothing private shows on a lock screen."""
    own_assessment(aid, user)
    with db.tx() as c:
        a = c.execute("SELECT a.*, p.name_en FROM appointments a JOIN providers p ON p.id=a.provider_id WHERE a.assessment_id=? AND a.status='confirmed' "
                      "ORDER BY a.created_at DESC LIMIT 1", (aid,)).fetchone()
    if not a or not a["slot_at"]:
        raise HTTPException(404, "No confirmed appointment")
    return Response(care.ics(a["id"], a["slot_at"], a["name_en"]), media_type="text/calendar",
                    headers={"Content-Disposition": "attachment; filename=appointment.ics"})


class OutcomeIn(BaseModel):
    outcome: str = Field(pattern="^(attended|missed)$")
    reason: Optional[str] = None


def _set_referral(c, aid, status, barrier=None, self_reported=False):
    col = {"booked": "booked_at", "attended": "attended_at", "tests_done": "tests_done_at", "followed_up": "followup_at"}.get(status)
    ref = _referral(c, aid)
    if not ref:
        return False
    now = time.time()
    sets, args = ["status=?"], [status]
    implied = {"attended": ["booked_at"], "tests_done": ["booked_at", "attended_at"], "followed_up": ["booked_at", "attended_at"]}
    if col:
        sets.append(f"{col}=?")
        args.append(ref[col] or now)
        for earlier in implied.get(status, []):  # a later step implies the earlier ones happened
            if not ref[earlier]:
                sets.append(f"{earlier}=?")
                args.append(now)
    if barrier is not None or status == "declined":
        sets.append("barrier=?")
        args.append(barrier)
    if self_reported:
        sets.append("self_reported=1")
    c.execute(f"UPDATE referrals SET {', '.join(sets)} WHERE id=?", args + [ref["id"]])
    return True


@app.post("/api/assessments/{aid}/appointment/outcome")
def appointment_outcome(aid: str, body: OutcomeIn, user=Depends(current_user)):
    own_assessment(aid, user)
    if body.outcome == "missed" and body.reason not in care.MISSED:
        raise HTTPException(400, "Choose a reason")
    with db.tx() as c:
        a = c.execute("SELECT * FROM appointments WHERE assessment_id=? AND status='confirmed' ORDER BY created_at DESC LIMIT 1", (aid,)).fetchone()
        if not a:
            raise HTTPException(404, "No confirmed appointment")
        c.execute("UPDATE appointments SET status=?, reason=?, updated_at=? WHERE id=?", (body.outcome, body.reason, time.time(), a["id"]))
        if body.outcome == "attended":
            _set_referral(c, aid, "attended", self_reported=True)
        else:
            ref = _referral(c, aid)
            if ref:
                c.execute("UPDATE referrals SET barrier=? WHERE id=?", (body.reason, ref["id"]))
    db.event(aid, f"appointment_{body.outcome}", body.reason)
    return {"ok": True}


class ProgressIn(BaseModel):
    status: str = Field(pattern="^(booked|attended|tests_done|followed_up|declined)$")
    barrier: Optional[str] = None


@app.post("/api/assessments/{aid}/progress")
def report_progress(aid: str, body: ProgressIn, user=Depends(current_user)):
    """The man closes the loop himself when the clinic is not connected yet."""
    own_assessment(aid, user)
    if body.status == "declined" and body.barrier not in care.BARRIERS:
        raise HTTPException(400, "Choose a reason")
    with db.tx() as c:
        if not _set_referral(c, aid, body.status, body.barrier, self_reported=True):
            raise HTTPException(404, "No referral")
        if body.status == "followed_up":
            c.execute("UPDATE consultations SET followup_done_at=? WHERE assessment_id=? AND followup_done_at IS NULL", (time.time(), aid))
    db.event(aid, f"self_{body.status}", body.barrier)
    return {"ok": True}


# ------------------------------------------------------------------ journey
def _steps(row, ref):
    steps = [{"step": "completed", "at": row["completed_at"]}]
    if ref:
        steps.append({"step": "referred", "at": ref["created_at"]})
        for col, name in (("reviewed_at", "reviewed"), ("booked_at", "booked"), ("attended_at", "attended"),
                          ("tests_done_at", "tests_done"), ("followup_at", "followed_up")):
            if ref[col]:
                steps.append({"step": name, "at": ref[col]})
        if ref["status"] == "declined":
            steps.append({"step": "declined", "at": None, "barrier": ref["barrier"]})
    return steps


def _tests_have(result):
    out = [{"name": n, "value": v, "date": d} for n, v, d in ((result.get("labs") or {}).get("already_done") or [])]
    sem = result.get("semen")
    if sem:
        out.insert(0, {"name": "Semen analysis" if sem.get("source") == "lab" else "Home sperm test", "value": None, "date": None})
    return out


@app.get("/api/me/journey")
def journey(lang: str = "en", user=Depends(current_user)):
    L = lang_of(lang)
    g = graph()
    with db.tx() as c:
        rows = c.execute("SELECT * FROM assessments WHERE user_id=? AND completed_at IS NOT NULL ORDER BY completed_at DESC", (user,)).fetchall()
        refs = {r["id"]: _referral(c, r["id"]) for r in rows}
    checks, prev_inputs = [], None
    for row in reversed(rows):  # oldest first, to describe changes
        result = security.unseal(row["result"])
        answers = security.unseal(row["answers"]) or {}
        v = assessment.user_view(result, L)
        ref = refs[row["id"]]
        lab = lambda n: g.nodes[n].get("label_ar" if L == "ar" else "label", g.nodes[n]["label"])
        changes = None
        if prev_inputs is not None:
            cur = {k: x for k, x in result["inputs"].items() if x >= 0.3}
            changes = {"improved": [lab(k) for k, x in prev_inputs.items() if x >= 0.3 and cur.get(k, 0) < x - 0.15],
                       "new": [lab(k) for k in cur if prev_inputs.get(k, 0) < 0.3]}
        prev_inputs = result["inputs"]
        with db.tx() as c:
            appt = c.execute("SELECT * FROM appointments WHERE assessment_id=? AND status!='cancelled' ORDER BY created_at DESC LIMIT 1",
                             (row["id"],)).fetchone()
            con = _consultation(c, row["id"])
            con_view = _consult_view(con, L, c) if con else None
        stg, cur = pathway.stages(row, ref, appt, con, _final_level(row, ref), L)
        checks.append({"pathway": stg, "current_stage": cur, "consultation": con_view,
                       "id": row["id"], "completed_at": row["completed_at"], "tier": row["tier"], "level": _final_level(row, ref),
                       "next_step": v["next_step"], "summary": v["summary"],
                       "discuss": [lab(k) for k, x in list(result["attribution"].items())[:3] if x > 0],
                       "coverage": explain.coverage(answers, result.get("wearable"), result.get("semen"), result.get("labs"), L),
                       "tests_have": _tests_have(result), "referral_status": ref["status"] if ref else None,
                       "steps": _steps(row, ref), "changes": changes})
    checks.reverse()
    with db.tx() as c:
        paused = sharing.is_paused(c, user)
    return {"sharing_paused": paused, "checks": checks, "recheck_due": rows[0]["completed_at"] + RECHECK_DAYS * 86400 if rows else None, "barriers": care.BARRIERS}


# ------------------------------------------------------------------ recovery code
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_recover_attempts = {}


@app.post("/api/me/recovery")
def make_recovery(user=Depends(current_user)):
    """A code he can write down to restore his checks on a new phone. Shown once; only a hash is stored. A new code replaces the old one."""
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(20))
    code = "-".join(raw[i:i + 5] for i in range(0, 20, 5))
    with db.tx() as c:
        c.execute("INSERT OR REPLACE INTO recovery VALUES (?,?,?)", (user, security.token_hash(raw), time.time()))
    return {"code": code}


class RecoverIn(BaseModel):
    code: str = Field(min_length=10, max_length=40)


@app.post("/api/recover")
def recover(body: RecoverIn, request: Request):
    """Restores access on a new device. The old device's link stops working, in case the phone was lost."""
    ip = request.client.host if request.client else "?"
    now = time.time()
    tries = [t for t in _recover_attempts.get(ip, []) if now - t < 3600]
    if len(tries) >= 10:
        raise HTTPException(429, "Too many attempts. Try again in an hour.")
    _recover_attempts[ip] = tries + [now]
    raw = "".join(ch for ch in body.code.upper() if ch.isalnum())
    with db.tx() as c:
        r = c.execute("SELECT user_id FROM recovery WHERE code_hash=?", (security.token_hash(raw),)).fetchone()
        if not r:
            raise HTTPException(404, "That code didn't match. Check it and try again.")
        token = security.new_token()
        c.execute("UPDATE users SET token_hash=? WHERE id=?", (security.token_hash(token), r["user_id"]))
        c.execute("DELETE FROM recovery WHERE user_id=?", (r["user_id"],))
        a = c.execute("SELECT id FROM assessments WHERE user_id=? AND completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 1",
                      (r["user_id"],)).fetchone()
    db.audit("user", "recovered_access", r["user_id"][:8])
    return {"token": token, "aid": a["id"] if a else None}


# ------------------------------------------------------------------ export + erase
@app.get("/api/me/export")
def export_me(user=Depends(current_user)):
    with db.tx() as c:
        rows = c.execute("SELECT * FROM assessments WHERE user_id=?", (user,)).fetchall()
        shares = c.execute("SELECT code, created_at, expires_at, revoked, used_by FROM shares WHERE assessment_id IN "
                           "(SELECT id FROM assessments WHERE user_id=?)", (user,)).fetchall()
        pts = _lab_points(c, "user_id=?", (user,), "en")
        plans = c.execute("SELECT * FROM plans WHERE user_id=?", (user,)).fetchall()
        appts = c.execute("SELECT * FROM appointments WHERE assessment_id IN (SELECT id FROM assessments WHERE user_id=?)", (user,)).fetchall()
        msgs = {r["id"]: _messages(c, r["id"]) for r in rows}
        appt_views = [care.appt_view(c, a) for a in appts]
        share_prefs, receipts = sharing.get(c, user), sharing.receipts(c, user)
        consults = [_consult_view(x, "en", c) for r in rows if (x := _consultation(c, r["id"]))]
        priv = sharing.privacy(c, user)
    all_consents = {}
    with db.tx() as c:
        for r in c.execute("SELECT purpose, granted FROM consents WHERE user_id=? ORDER BY ts", (user,)).fetchall():
            all_consents[r["purpose"]] = bool(r["granted"])
    return {"consents": all_consents, "shares": [dict(s) for s in shares],
            "assessments": [{"id": r["id"], "started_at": r["started_at"], "completed_at": r["completed_at"],
                             "answers": security.unseal(r["answers"]), "device_summary": security.unseal(r["wearable"]),
                             "test_result": security.unseal(r["semen"]), "blood_tests": security.unseal(r["labs"]),
                             "result": security.unseal(r["result"]), "messages": msgs[r["id"]]} for r in rows],
            "lab_results": labtimeline.series(pts, "en"), "plans": [_plan_view(p, "en") for p in plans], "appointments": appt_views,
            "sharing": share_prefs, "privacy": {"sharing_paused": priv["paused"], "retention_months": priv["retention_months"]},
            "consent_receipts": receipts, "consultations": consults}


def erase_user(user):
    """Erases everything about this person. Aggregate counters in `events` lose the link (assessment id removed)."""
    with db.tx() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM assessments WHERE user_id=?", (user,)).fetchall()]
        for aid in ids:
            for t in ("referrals", "shares", "feedback", "messages", "partner_links", "appointments", "consultations"):
                c.execute(f"DELETE FROM {t} WHERE assessment_id=?", (aid,))
            c.execute("DELETE FROM clinic_access WHERE assessment_id=?", (aid,))
            c.execute("DELETE FROM visit_feedback WHERE assessment_id=?", (aid,))
            c.execute("DELETE FROM visit_questions WHERE assessment_id=?", (aid,))
            c.execute("DELETE FROM finding_reviews WHERE assessment_id=?", (aid,))
            c.execute("UPDATE events SET assessment_id=NULL WHERE assessment_id=?", (aid,))
        for t in ("assessments", "consents", "lab_results", "plans", "recovery", "sharing", "consent_receipts"):
            c.execute(f"DELETE FROM {t} WHERE user_id=?", (user,))
        c.execute("DELETE FROM users WHERE id=?", (user,))
    db.audit("user", "erased_all_data")
    return len(ids)


@app.delete("/api/me")
def delete_me(user=Depends(current_user)):
    return {"deleted": True, "assessments": erase_user(user)}


# ------------------------------------------------------------------ rapid review: request, messages, voice notes
@app.post("/api/assessments/{aid}/request-review")
def request_review(aid: str, user=Depends(current_user)):
    """Explicit, case-level consent for a clinician to see this assessment (when global review consent was not given)."""
    row = own_assessment(aid, user)
    if not row["completed_at"]:
        raise HTTPException(400, "Not completed")
    with db.tx() as c:
        c.execute("INSERT INTO consents VALUES (?,?,?,?,?)", (user, f"clinician_review:{aid}", 1, CONSENT_VERSION, time.time()))
        sharing.receipt(c, user, "doctor", "granted", {"check": aid[:8], "categories": sharing.get(c, user)["doctor"]})
        c.execute("UPDATE assessments SET review_consent=1 WHERE id=?", (aid,))
        c.execute("UPDATE referrals SET status='pending_review' WHERE assessment_id=? AND status='suggested'", (aid,))
        if not c.execute("SELECT 1 FROM referrals WHERE assessment_id=?", (aid,)).fetchone():
            c.execute("INSERT INTO referrals (id, assessment_id, level, status, created_at) VALUES (?,?,?,?,?)",
                      (str(uuid.uuid4()), aid, row["level"], "pending_review", time.time()))
    db.event(aid, "review_requested")
    return {"queued": True}


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


def _messages(c, aid):
    return [{"id": r["id"], "sender": r["sender"], "body": security.unseal(r["body"]) if not r["audio"] else "", "ts": r["ts"],
             "voice": bool(r["audio"]), "seconds": r["seconds"]}
            for r in c.execute("SELECT * FROM messages WHERE assessment_id=? ORDER BY ts", (aid,)).fetchall()]


@app.get("/api/assessments/{aid}/messages")
def user_messages(aid: str, user=Depends(current_user)):
    own_assessment(aid, user)
    with db.tx() as c:
        c.execute("UPDATE messages SET read_at=? WHERE assessment_id=? AND sender='clinician' AND read_at IS NULL", (time.time(), aid))
        return _messages(c, aid)


@app.post("/api/assessments/{aid}/messages")
def user_send(aid: str, body: MessageIn, user=Depends(current_user)):
    row = own_assessment(aid, user)
    if not row["review_consent"]:
        raise HTTPException(403, "Request a clinician review first")
    with db.tx() as c:
        _message(c, aid, "user", body.body)
    return {"ok": True}


async def _store_note(aid, sender, file, seconds):
    raw = await file.read()
    if len(raw) > MAX_AUDIO:
        raise HTTPException(413, "Voice note too long")
    mime = (file.content_type or "audio/webm").split(";")[0]
    if not mime.startswith("audio/"):
        raise HTTPException(415, "Audio only")
    with db.tx() as c:
        c.execute("INSERT INTO messages (id, assessment_id, sender, body, ts, audio, mime, seconds) VALUES (?,?,?,?,?,?,?,?)",
                  (str(uuid.uuid4()), aid, sender, security.seal(""), time.time(), security.fernet().encrypt(raw), mime, min(seconds, 120)))


def _note(aid, mid):
    with db.tx() as c:
        r = c.execute("SELECT audio, mime FROM messages WHERE id=? AND assessment_id=?", (mid, aid)).fetchone()
    if not r or not r["audio"]:
        raise HTTPException(404, "Not found")
    return Response(security.fernet().decrypt(r["audio"]), media_type=r["mime"] or "audio/webm")


@app.post("/api/assessments/{aid}/voice-notes")
async def user_note(aid: str, file: UploadFile = File(...), seconds: float = Form(0), user=Depends(current_user)):
    row = own_assessment(aid, user)
    if not row["review_consent"]:
        raise HTTPException(403, "Request a clinician review first")
    await _store_note(aid, "user", file, seconds)
    return {"ok": True}


@app.get("/api/assessments/{aid}/voice-notes/{mid}")
def user_note_get(aid: str, mid: str, user=Depends(current_user)):
    own_assessment(aid, user)
    return _note(aid, mid)


# ------------------------------------------------------------------ partner mode (status only)
PARTNER_DAYS = 30
PARTNER_TEXT = {
    "none": {"en": "He has completed his men's health check. No follow-up visit is needed right now.",
             "ar": "أكمل فحص صحة الرجل. لا حاجة لزيارة متابعة في الوقت الحالي."},
    "routine": {"en": "He has completed his men's health check. A routine follow-up visit is recommended.",
                "ar": "أكمل فحص صحة الرجل. يُنصح بزيارة متابعة روتينية."},
    "specialist": {"en": "He has completed his men's health check. A specialist visit is recommended — he is taking the next step.",
                   "ar": "أكمل فحص صحة الرجل. يُنصح بزيارة مختص — وهو يتخذ الخطوة التالية."},
    "together": {"en": "He has completed his men's health check. A joint visit to a fertility clinic is recommended, so you can both be seen at the same time.",
                 "ar": "أكمل فحص صحة الرجل. يُنصح بزيارة مشتركة لعيادة الخصوبة، ليتم فحصكما معاً في الوقت نفسه."},
}


def _partner_status(level):
    if level == "fertility_services":
        return "together"
    if level in ("andrology", "urgent_specialist", "emergency", "same_day_primary"):
        return "specialist"
    return "routine" if level == "primary_care" else "none"


@app.post("/api/assessments/{aid}/partner-link")
def partner_link(aid: str, user=Depends(current_user)):
    row = own_assessment(aid, user)
    if not row["completed_at"]:
        raise HTTPException(400, "Not completed")
    token = security.new_token()
    with db.tx() as c:
        c.execute("DELETE FROM partner_links WHERE assessment_id=?", (aid,))
        c.execute("INSERT INTO partner_links VALUES (?,?,?,?,0,0)", (security.token_hash(token), aid, time.time(), time.time() + PARTNER_DAYS * 86400))
        sharing.receipt(c, user, "partner", "granted", {"days": PARTNER_DAYS, "categories": ["completion", "kind_of_next_step"]})
    db.event(aid, "partner_link_created")
    return {"token": token, "path": f"/partner.html#{token}", "expires_in_days": PARTNER_DAYS}


@app.delete("/api/assessments/{aid}/partner-link")
def partner_revoke(aid: str, user=Depends(current_user)):
    own_assessment(aid, user)
    with db.tx() as c:
        c.execute("UPDATE partner_links SET revoked=1 WHERE assessment_id=?", (aid,))
        sharing.receipt(c, user, "partner", "withdrawn")
    return {"revoked": True}


@app.get("/api/partner/{token}")
def partner_view(token: str):
    """Shows only completion and the broad kind of next step. No answers, scores, results or reasons."""
    with db.tx() as c:
        link = c.execute("SELECT * FROM partner_links WHERE token_hash=? AND revoked=0 AND expires_at>?",
                         (security.token_hash(token), time.time())).fetchone()
        if not link:
            raise HTTPException(404, "This link has expired or was withdrawn")
        a = c.execute("SELECT completed_at, level FROM assessments WHERE id=?", (link["assessment_id"],)).fetchone()
        ref = c.execute("SELECT final_level FROM referrals WHERE assessment_id=?", (link["assessment_id"],)).fetchone()
        c.execute("UPDATE partner_links SET views=views+1 WHERE token_hash=?", (link["token_hash"],))
    level = (ref and ref["final_level"]) or a["level"]
    status = _partner_status(level)
    return {"completed_on": time.strftime("%Y-%m-%d", time.gmtime(a["completed_at"])), "status": status, "message": PARTNER_TEXT[status]}


# ------------------------------------------------------------------ WhatsApp
def _wa_submit(aid, user, lang):
    return run_submit(aid, user, lang)


class DemoIn(BaseModel):
    session: str = Field(min_length=16, max_length=64)
    text: str = Field("", max_length=500)


@app.post("/api/conversation/demo")
def conversation_demo(body: DemoIn, request: Request):
    """Same engine as WhatsApp, for the in-app WhatsApp-style demo."""
    base = os.environ.get("RIAYA_PUBLIC_URL") or str(request.base_url)
    return {"replies": conversation.handle("demo:" + body.session, body.text, base, _wa_submit, erase_user)}


@app.post("/api/whatsapp/twilio")
async def whatsapp(request: Request):
    """Twilio WhatsApp webhook (sandbox or production sender). The phone number is never stored: only a salted hash keys the session."""
    form = dict(await request.form())
    url = os.environ.get("RIAYA_PUBLIC_URL", str(request.base_url)).rstrip("/") + "/api/whatsapp/twilio"
    if not conversation.twilio_valid(url, {k: str(v) for k, v in form.items()}, request.headers.get("X-Twilio-Signature")):
        raise HTTPException(403, "Bad signature")
    sender = str(form.get("From", ""))
    if not sender:
        raise HTTPException(400, "No sender")
    base = os.environ.get("RIAYA_PUBLIC_URL") or str(request.base_url)
    replies = conversation.handle(conversation.key_for(sender), str(form.get("Body", "")), base, _wa_submit, erase_user)
    return Response(conversation.twiml(replies), media_type="application/xml")


# ------------------------------------------------------------------ clinician side
class LoginIn(BaseModel):
    username: str
    password: str


_login_fails = {}


@app.post("/api/clinician/login")
def login(body: LoginIn, request: Request):
    """Five wrong passwords from one address, or for one username, within 15 minutes pause sign-in for 15 minutes."""
    now = time.time()
    keys = [f"ip:{request.client.host if request.client else '?'}", f"user:{body.username.lower()}"]
    for k in keys:
        _login_fails[k] = [t for t in _login_fails.get(k, []) if now - t < 900]
        if len(_login_fails[k]) >= 5:
            db.audit(body.username, "login_blocked")
            raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    with db.tx() as c:
        row = c.execute("SELECT * FROM clinicians WHERE username=?", (body.username,)).fetchone()
        if not row or not security.check_password(body.password, row["salt"], row["pw_hash"]):
            db.audit(body.username, "login_failed")
            for k in keys:
                _login_fails.setdefault(k, []).append(now)
            raise HTTPException(401, "Invalid credentials")
        token = security.new_token()
        now = time.time()
        c.execute("DELETE FROM sessions WHERE expires_at<?", (now,))
        c.execute("INSERT INTO sessions (token_hash, username, expires_at, last_seen) VALUES (?,?,?,?)",
                  (security.token_hash(token), body.username, now + SESSION_HOURS * 3600, now))
    db.audit(body.username, "login")
    return {"token": token, "name": row["display_name"]}


@app.post("/api/clinician/logout")
def logout(authorization: str = Header(None), clin=Depends(current_clinician)):
    with db.tx() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (security.token_hash(authorization[7:]),))
    db.audit(clin, "logout")
    return {"ok": True}


class PasswordIn(BaseModel):
    current: str
    new: str = Field(min_length=12, max_length=200)


@app.post("/api/clinician/password")
def change_password(body: PasswordIn, authorization: str = Header(None), clin=Depends(current_clinician)):
    with db.tx() as c:
        row = c.execute("SELECT * FROM clinicians WHERE username=?", (clin,)).fetchone()
        if not security.check_password(body.current, row["salt"], row["pw_hash"]):
            raise HTTPException(400, "Current password is wrong")
        salt, h = security.hash_password(body.new)
        c.execute("UPDATE clinicians SET salt=?, pw_hash=? WHERE username=?", (salt, h, clin))
        c.execute("DELETE FROM sessions WHERE username=? AND token_hash!=?", (clin, security.token_hash(authorization[7:])))
    db.audit(clin, "password_changed")
    return {"ok": True}


@app.get("/api/clinician/queue")
def queue(clin=Depends(current_clinician)):
    """Only cases where the man consented to clinician review (or shared a code) are visible."""
    with db.tx() as c:
        rows = c.execute("""SELECT a.*, r.status, r.final_level, r.rapid, r.due_at FROM assessments a JOIN referrals r ON r.assessment_id=a.id
                            WHERE a.review_consent=1 AND r.status='pending_review' AND a.user_id NOT IN (SELECT id FROM users WHERE sharing_paused=1)
                            ORDER BY r.rapid DESC, COALESCE(r.due_at, 9e18), CASE a.level WHEN 'emergency' THEN 0 WHEN 'urgent_specialist' THEN 1
                                     WHEN 'same_day_primary' THEN 2 WHEN 'andrology' THEN 3 ELSE 4 END, a.completed_at""").fetchall()
        recent = c.execute("""SELECT a.*, r.status, r.final_level, r.rapid, r.due_at FROM assessments a
                              JOIN referrals r ON r.assessment_id=a.id WHERE a.review_consent=1 AND r.status NOT IN ('pending_review','suggested')
                              AND a.user_id NOT IN (SELECT id FROM users WHERE sharing_paused=1)
                              ORDER BY r.reviewed_at DESC LIMIT 30""").fetchall()
        unread = {r[0]: r[1] for r in c.execute("SELECT assessment_id, COUNT(*) FROM messages WHERE sender='user' AND read_at IS NULL GROUP BY assessment_id")}
    db.audit(clin, "view_queue")
    pick = lambda r: {"rapid": bool(r["rapid"]), "due_at": r["due_at"], "unread": unread.get(r["id"], 0), "id": r["id"], "tier": r["tier"],
                      "level": r["level"], "cohort": r["cohort"], "completed_at": r["completed_at"], "simulated": bool(r["simulated"]),
                      "status": r["status"], "final_level": r["final_level"]}
    return {"pending": [pick(r) for r in rows], "recent": [pick(r) for r in recent]}


def _clinician_can_see(c, aid):
    row = c.execute("SELECT * FROM assessments WHERE id=?", (aid,)).fetchone()
    if not row or sharing.is_paused(c, row["user_id"]):
        return None
    if row["review_consent"]:
        return row
    shared = c.execute("SELECT 1 FROM shares WHERE assessment_id=? AND revoked=0 AND expires_at>? AND used_by IS NOT NULL",
                       (aid, time.time())).fetchone()
    return row if shared else None


def _visible(c, aid):
    row = _clinician_can_see(c, aid)
    if not row:
        raise HTTPException(404, "Not found or not shared")
    return row


def _with_models(result, answers):
    if result and ("models" not in result or "riaya_net" not in result["models"]):
        from . import ml, synth
        from . import riayanet
        result["models"] = {"uci_logistic": ml.predict(answers), "simulated_gbm": synth.explain(answers, result["instruments"], result.get("wearable")),
                            "riaya_net": riayanet.predict(answers, result["instruments"], result.get("wearable"))}
    return result


@app.get("/api/clinician/cases/{aid}")
def case(aid: str, clin=Depends(current_clinician)):
    with db.tx() as c:
        row = _visible(c, aid)
        ref = _referral(c, aid)
        msgs = _messages(c, aid)
    _access(clin, "view_case", aid)
    answers = security.unseal(row["answers"]) or {}
    result = _with_models(security.unseal(row["result"]), answers)
    with db.tx() as c:
        mode = sharing.access_mode(c, row, clin)
        allowed = sharing.get(c, row["user_id"])[mode]
        con = _consultation(c, aid)
        con_view = _consult_view(con, "en", c) if con else None
    answers, result, withheld = sharing.filter_case(answers, result, allowed)
    g = graph()
    return {"id": aid, "answers": answers, "result": result, "access": mode, "withheld": withheld,
            "consultation": con_view,
            "referral": {k: ref[k] for k in ref.keys() if k != "note"} if ref else None,
            "review_note": security.unseal(ref["note"]) if ref and ref["note"] else None,
            "paths": {n: g.paths(n)[:3] for n in list((result or {}).get("attribution", {}))[:5]},
            "references": {r: g.refs[r] for r in {r for e in g.edges for r in e["refs"]}},
            "simulated": bool(row["simulated"]), "messages": msgs}


@app.get("/api/clinician/cases/{aid}/explain")
def clin_explain(aid: str, clin=Depends(current_clinician)):
    with db.tx() as c:
        row = _visible(c, aid)
    result = security.unseal(row["result"])
    if not result:
        raise HTTPException(404, "Not completed")
    with db.tx() as c:
        allowed = sharing.get(c, row["user_id"])[sharing.access_mode(c, row, clin)]
    answers, result, _ = sharing.filter_case(security.unseal(row["answers"]) or {}, result, allowed)
    return explain.explain(answers, result, "en")


@app.post("/api/clinician/share/{code}")
def open_share(code: str, clin=Depends(current_clinician)):
    with db.tx() as c:
        s = c.execute("SELECT * FROM shares WHERE code=? AND revoked=0 AND expires_at>?", (code.upper(), time.time())).fetchone()
        if not s:
            raise HTTPException(404, "Code invalid, expired or revoked")
        c.execute("UPDATE shares SET used_by=? WHERE code=?", (clin, code.upper()))
    _access(clin, "open_share", s["assessment_id"])
    return {"assessment_id": s["assessment_id"]}


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(approve|modify|reject)$")
    final_level: Optional[str] = None
    note: Optional[str] = Field(None, max_length=2000)


@app.post("/api/clinician/cases/{aid}/review")
def review(aid: str, body: ReviewIn, clin=Depends(current_clinician)):
    from .triage import LEVELS
    if body.decision in ("modify", "reject") and not (body.note or "").strip():
        raise HTTPException(400, "A reason is required to change or reject a referral")
    with db.tx() as c:
        ref = _referral(c, aid)
        if not ref:
            raise HTTPException(404, "No referral")
        if body.decision == "reject":
            final, status = None, "rejected"
        else:
            final = ref["level"] if body.decision == "approve" else body.final_level
            status = "approved"
            if final not in LEVELS:
                raise HTTPException(400, "Invalid level")
        c.execute("UPDATE referrals SET status=?, reviewed_at=?, reviewer=?, final_level=?, note=? WHERE id=?",
                  (status, time.time(), clin, final, security.seal(body.note), ref["id"]))
        if body.decision == "reject":
            _message(c, aid, "clinician", "راجع الطبيب ملخصك ولا يرى حاجة لإحالة الآن. / A doctor reviewed your summary and doesn't think a referral is needed now."
                     + (f"\n{body.note}" if body.note else ""))
        else:
            _message(c, aid, "clinician", "راجع الطبيب ملخصك ووافق على خطوتك التالية. يمكنك الآن اختيار عيادة من «مساري». / "
                     "A doctor has reviewed your summary and approved your next step. You can now choose a clinic from My journey.")
    db.audit(clin, f"review_{body.decision}", aid)
    db.event(aid, "reviewed", final or "rejected")
    return {"status": status, "final_level": final}


class StatusIn(BaseModel):
    status: str = Field(pattern="^(booked|attended|tests_done|followed_up|declined)$")
    barrier: Optional[str] = None


@app.post("/api/clinician/cases/{aid}/status")
def referral_status(aid: str, body: StatusIn, clin=Depends(current_clinician)):
    with db.tx() as c:
        _visible(c, aid)
        if not _set_referral(c, aid, body.status, body.barrier):
            raise HTTPException(404, "No referral")
    db.audit(clin, f"referral_{body.status}", aid)
    db.event(aid, f"referral_{body.status}")
    return {"ok": True}


@app.get("/api/clinician/cases/{aid}/messages")
def clin_messages(aid: str, clin=Depends(current_clinician)):
    with db.tx() as c:
        _visible(c, aid)
        c.execute("UPDATE messages SET read_at=? WHERE assessment_id=? AND sender='user' AND read_at IS NULL", (time.time(), aid))
        return _messages(c, aid)


@app.post("/api/clinician/cases/{aid}/messages")
def clin_send(aid: str, body: MessageIn, clin=Depends(current_clinician)):
    with db.tx() as c:
        _visible(c, aid)
        _message(c, aid, "clinician", body.body)
    db.audit(clin, "message_sent", aid)
    return {"ok": True}


@app.post("/api/clinician/cases/{aid}/voice-notes")
async def clin_note(aid: str, file: UploadFile = File(...), seconds: float = Form(0), clin=Depends(current_clinician)):
    with db.tx() as c:
        _visible(c, aid)
    await _store_note(aid, "clinician", file, seconds)
    db.audit(clin, "voice_note_sent", aid)
    return {"ok": True}


@app.get("/api/clinician/cases/{aid}/voice-notes/{mid}")
def clin_note_get(aid: str, mid: str, clin=Depends(current_clinician)):
    with db.tx() as c:
        _visible(c, aid)
    return _note(aid, mid)


VIDEO_BASE = os.environ.get("RIAYA_VIDEO_BASE", "https://meet.jit.si")


@app.post("/api/clinician/cases/{aid}/video")
def start_video(aid: str, clin=Depends(current_clinician)):
    """Creates an unguessable video room. For production, point RIAYA_VIDEO_BASE at a self-hosted Jitsi inside the UAE."""
    url = f"{VIDEO_BASE}/riaya-{security.new_token()[:24]}"
    with db.tx() as c:
        _visible(c, aid)
        c.execute("UPDATE referrals SET video_url=? WHERE assessment_id=?", (url, aid))
        _message(c, aid, "clinician", "استشارتك المرئية الخاصة جاهزة. افتح الرابط من صفحة نتيجتك متى كنت مستعداً. / "
                                      "A private video consultation is ready. Open the link on your result page when you are ready.")
    db.audit(clin, "video_created", aid)
    return {"url": url}


def _questions(c, aid):
    r = c.execute("SELECT body FROM visit_questions WHERE assessment_id=?", (aid,)).fetchone()
    return (security.unseal(r["body"]) or []) if r else []


def _package(c, row, allowed, reviewer=None):
    """The referral package exactly as a recipient with `allowed` categories sees it: his summary, the parts he chose to share,
    results he saved later (so tests aren't repeated) and the questions he wants to discuss."""
    ref = _referral(c, row["id"])
    answers, result, withheld = sharing.filter_case(security.unseal(row["answers"]) or {}, security.unseal(row["result"]), allowed)
    out = handover.build(answers, result, {k: ref[k] for k in ref.keys() if k != "note"} if ref else None, reviewer)
    labs = labtimeline.series(_lab_points(c, "user_id=?", (row["user_id"],), "en"), "en") if "labs" in allowed else None
    if labs:
        extra = [f"{x['name']}: {x['latest']['value']} {x['unit'] or ''}".strip() + (f" ({x['latest']['date']})" if x["latest"]["date"] else "")
                 + " (from his lab report)" for x in labs if x["latest"]]
        for sec in out["letter"]["sections"]:
            if sec["title"] == "Results already available":
                sec["lines"] = [l for l in sec["lines"] if l != "No prior results."] + extra
    qs = _questions(c, row["id"])
    if qs:
        out["letter"]["sections"].insert(1, {"title": "Questions he wants to discuss", "lines": qs})
    out["withheld"], out["allowed"], out["labs"], out["questions"] = withheld, allowed, labs, qs
    return out, result, ref


@app.get("/api/clinician/cases/{aid}/handover")
def get_handover(aid: str, clin=Depends(current_clinician)):
    with db.tx() as c:
        row = _visible(c, aid)
        ref = _referral(c, aid)
        if ref:
            c.execute("UPDATE referrals SET handover_at=? WHERE id=?", (time.time(), ref["id"]))
        allowed = sharing.get(c, row["user_id"])[sharing.access_mode(c, row, clin)]
        out, _, _ = _package(c, row, allowed, clin)
    _access(clin, "handover_generated", aid)
    return {"bundle": out["bundle"], "letter": out["letter"], "withheld": out["withheld"]}


@app.get("/api/clinician/cases/{aid}/labs")
def case_labs(aid: str, clin=Depends(current_clinician)):
    with db.tx() as c:
        row = _visible(c, aid)
        if "labs" not in sharing.get(c, row["user_id"])[sharing.access_mode(c, row, clin)]:
            raise HTTPException(403, "He has not shared his lab results")
        pts = _lab_points(c, "user_id=?", (row["user_id"],), "en")
    _access(clin, "view_labs", aid)
    return {"series": labtimeline.series(pts, "en")}


def _review_allowed(c, user_id):
    """Doctor review of his saved results needs his general review consent, or a check he sent for review."""
    last = c.execute("SELECT granted FROM consents WHERE user_id=? AND purpose='clinician_review' ORDER BY ts DESC LIMIT 1", (user_id,)).fetchone()
    if last and last["granted"]:
        return True
    return bool(c.execute("SELECT 1 FROM assessments WHERE user_id=? AND review_consent=1", (user_id,)).fetchone())


@app.get("/api/clinician/labs/pending")
def pending_labs(clin=Depends(current_clinician)):
    with db.tx() as c:
        rows = [r for r in c.execute("SELECT * FROM lab_results WHERE review_status='pending' ORDER BY created_at").fetchall()
                if _review_allowed(c, r["user_id"]) and "labs" in sharing.get(c, r["user_id"])["doctor"]]
        latest = {}
        out = []
        for r in rows:
            d = security.unseal(r["detail"]) or {}
            p = labtimeline.point(r, d, "en")
            aid = r["assessment_id"]
            if not aid:
                if r["user_id"] not in latest:
                    a = c.execute("SELECT id FROM assessments WHERE user_id=? ORDER BY review_consent DESC, started_at DESC LIMIT 1", (r["user_id"],)).fetchone()
                    latest[r["user_id"]] = a["id"] if a else None
                aid = latest[r["user_id"]]
            out.append({**p, "assessment_id": aid, "extracted_value": r["extracted_value"], "score": d.get("score"), "line": d.get("line")})
    db.audit(clin, "view_lab_queue")
    return {"results": out}


class ReconcileIn(BaseModel):
    action: str = Field(pattern="^(accept|correct|reject)$")
    value: Optional[float] = None
    note: Optional[str] = Field(None, max_length=300)


@app.post("/api/clinician/labs/{rid}")
def reconcile(rid: str, body: ReconcileIn, clin=Depends(current_clinician)):
    if body.action in ("correct", "reject") and not (body.note or "").strip():
        raise HTTPException(400, "Add a reason he will see")
    if body.action == "correct" and body.value is None:
        raise HTTPException(400, "Enter the value from the report")
    with db.tx() as c:
        r = c.execute("SELECT * FROM lab_results WHERE id=?", (rid,)).fetchone()
        if not r or not _review_allowed(c, r["user_id"]):
            raise HTTPException(404, "Not found")
        status = {"accept": "accepted", "correct": "corrected", "reject": "rejected"}[body.action]
        value = body.value if body.action == "correct" else r["value"]
        c.execute("""UPDATE lab_results SET review_status=?, review_note=?, reviewed_by=?, reviewed_at=?, value=?, original_value=?
                     WHERE id=?""", (status, security.seal(body.note) if body.note else None, clin, time.time(), value,
                                    r["value"] if body.action == "correct" else r["original_value"], rid))
    db.audit(clin, f"lab_{status}", rid)
    return {"ok": True, "review_status": status}


@app.get("/api/clinician/plans")
def plan_queue(clin=Depends(current_clinician)):
    with db.tx() as c:
        rows = c.execute("""SELECT p.* FROM plans p JOIN assessments a ON a.id=p.assessment_id
                            WHERE a.review_consent=1 AND p.status IN ('proposed','active','self_guided') ORDER BY p.created_at DESC""").fetchall()
        rows = [r for r in rows if "plan" in sharing.get(c, r["user_id"])["doctor"]]
    return {"plans": [_plan_view(r, "en") for r in rows]}


class PlanReviewIn(BaseModel):
    action: str = Field(pattern="^(approve|change)$")
    remove: list[str] = Field(default_factory=list)
    note: Optional[str] = Field(None, max_length=500)


@app.post("/api/clinician/plans/{pid}")
def review_plan(pid: str, body: PlanReviewIn, clin=Depends(current_clinician)):
    if body.action == "change" and not (body.note or "").strip():
        raise HTTPException(400, "Add a note he will see when you remove a goal")
    now = time.time()
    with db.tx() as c:
        r = c.execute("SELECT * FROM plans WHERE id=? AND status='proposed'", (pid,)).fetchone()
        if not r:
            raise HTTPException(404, "Not found")
        _visible(c, r["assessment_id"])
        items = [i for i in security.unseal(r["items"]) if i["node"] not in set(body.remove)]
        if not items:
            raise HTTPException(400, "Keep at least one goal")
        c.execute("UPDATE plans SET status='active', start_at=?, reviewed_at=?, reviewer=?, items=?, doctor_note=? WHERE id=?",
                  (now, now, clin, security.seal(items), security.seal(body.note) if body.note else None, pid))
        _message(c, r["assessment_id"], "clinician", "وافق طبيبك على خطتك لمدة ١٢ أسبوعاً وبدأت الآن. / Your doctor approved your 12-week plan. It starts today."
                 + (f"\n{body.note}" if body.note else ""))
    db.audit(clin, f"plan_{body.action}", pid)
    return {"ok": True}


@app.get("/api/clinician/appointments")
def appointment_queue(clin=Depends(current_clinician)):
    with db.tx() as c:
        rows = c.execute("SELECT * FROM appointments WHERE status IN ('requested','confirmed') ORDER BY created_at").fetchall()
        out = []
        for a in rows:
            v = care.appt_view(c, a)
            prefs = security.unseal(a["prefs"]) or {}
            row = c.execute("SELECT level FROM assessments WHERE id=?", (a["assessment_id"],)).fetchone()
            ref = _referral(c, a["assessment_id"])
            out.append({**v, "assessment_id": a["assessment_id"], "level": (ref and ref["final_level"]) or (row and row["level"]),
                        "phone": prefs.get("phone"), "note": prefs.get("note")})
    db.audit(clin, "view_appointments")
    return {"appointments": out, "decline_reasons": care.DECLINE, "missed_reasons": care.MISSED}


class DecisionIn(BaseModel):
    action: str = Field(pattern="^(confirm|decline|attended|missed)$")
    slot_at: Optional[float] = None
    place_note: Optional[str] = Field(None, max_length=200)
    reason: Optional[str] = None


@app.post("/api/clinician/appointments/{appt_id}")
def decide_appointment(appt_id: str, body: DecisionIn, clin=Depends(current_clinician)):
    now = time.time()
    with db.tx() as c:
        a = c.execute("SELECT a.*, p.name_en, p.name_ar FROM appointments a JOIN providers p ON p.id=a.provider_id WHERE a.id=?", (appt_id,)).fetchone()
        if not a:
            raise HTTPException(404, "Not found")
        aid = a["assessment_id"]
        if body.action == "confirm":
            if a["status"] != "requested":
                raise HTTPException(409, "Already handled")
            if not body.slot_at or body.slot_at < now - 3600:
                raise HTTPException(400, "Choose the date and time the clinic agreed")
            c.execute("UPDATE appointments SET status='confirmed', slot_at=?, place_note=?, decided_by=?, updated_at=? WHERE id=?",
                      (body.slot_at, body.place_note, clin, now, appt_id))
            _set_referral(c, aid, "booked")
            _message(c, aid, "clinician", f"تم تأكيد موعدك في {a['name_ar']}. التفاصيل في «مساري». / "
                                          f"Your appointment at {a['name_en']} is confirmed. Details are in My journey.")
        elif body.action == "decline":
            if body.reason not in care.DECLINE:
                raise HTTPException(400, "Choose a reason")
            c.execute("UPDATE appointments SET status='declined', reason=?, decided_by=?, updated_at=? WHERE id=?", (body.reason, clin, now, appt_id))
            if a["share_code"]:
                c.execute("UPDATE shares SET revoked=1 WHERE code=?", (a["share_code"],))
            _message(c, aid, "clinician", f"لم تتمكن {a['name_ar']} من قبول الطلب. يمكنك اختيار عيادة أخرى من «مساري». / "
                                          f"{a['name_en']} couldn't take this request. You can choose another clinic from My journey.")
        elif body.action == "attended":
            c.execute("UPDATE appointments SET status='attended', decided_by=?, updated_at=? WHERE id=?", (clin, now, appt_id))
            _set_referral(c, aid, "attended")
        else:
            c.execute("UPDATE appointments SET status='missed', reason=?, decided_by=?, updated_at=? WHERE id=?",
                      (body.reason if body.reason in care.MISSED else "other", clin, now, appt_id))
    db.audit(clin, f"appointment_{body.action}", aid)
    db.event(aid, f"appointment_{body.action}", body.reason)
    return {"ok": True}


@app.get("/api/clinician/providers")
def all_providers(clin=Depends(current_clinician)):
    with db.tx() as c:
        return {"providers": [care.provider_view(r, "en", staff=True) for r in c.execute("SELECT * FROM providers ORDER BY name_en").fetchall()]}


class ProviderIn(BaseModel):
    name_en: str = Field(min_length=3, max_length=120)
    name_ar: str = Field(min_length=2, max_length=120)
    area: str = Field(min_length=2, max_length=120)
    area_ar: str = Field(min_length=2, max_length=120)
    sector: str = Field(pattern="^(public|private)$")
    kinds: list[str] = Field(min_length=1, max_length=3)
    website: str = Field(max_length=200, pattern=r"^https://[^\s]+$")


@app.post("/api/clinician/providers")
def add_provider(body: ProviderIn, clin=Depends(current_clinician)):
    kinds = [k for k in body.kinds if k in ("urology", "primary", "emergency")]
    if not kinds:
        raise HTTPException(400, "Choose at least one kind of care")
    pid = "p" + secrets.token_hex(4)
    with db.tx() as c:
        c.execute("INSERT INTO providers (id,name_en,name_ar,area,area_ar,sector,kinds,website) VALUES (?,?,?,?,?,?,?,?)",
                  (pid, body.name_en, body.name_ar, body.area, body.area_ar, body.sector, json.dumps(kinds), body.website))
    db.audit(clin, "provider_added", pid)
    return {"id": pid}


@app.post("/api/clinician/providers/{pid}/active")
def set_provider_active(pid: str, active: bool, clin=Depends(current_clinician)):
    with db.tx() as c:
        if not c.execute("UPDATE providers SET active=? WHERE id=?", (int(active), pid)).rowcount:
            raise HTTPException(404, "Not found")
    db.audit(clin, "provider_shown" if active else "provider_hidden", pid)
    return {"ok": True}


class ConfirmIn(BaseModel):
    note: str = Field(min_length=10, max_length=300)


@app.post("/api/clinician/providers/{pid}/confirm")
def confirm_provider(pid: str, body: ConfirmIn, clin=Depends(current_clinician)):
    """Records who checked the clinic, when and how. Patients see the date and the note."""
    with db.tx() as c:
        if not c.execute("UPDATE providers SET confirmed_at=?, confirmed_by=?, confirm_note=? WHERE id=?", (time.time(), clin, body.note, pid)).rowcount:
            raise HTTPException(404, "Not found")
    db.audit(clin, "provider_confirmed", pid)
    return {"ok": True}


@app.get("/api/clinician/metrics")
def metrics(include_simulated: bool = True, clin=Depends(current_clinician)):
    sim = "" if include_simulated else " AND simulated=0"
    with db.tx() as c:
        a = c.execute(f"SELECT * FROM assessments WHERE 1=1{sim}").fetchall()
        r = c.execute(f"SELECT * FROM referrals WHERE 1=1{sim}").fetchall()
        ap = c.execute(f"SELECT * FROM appointments WHERE 1=1{sim}").fetchall()
        fb = c.execute("SELECT AVG(trust) t, AVG(clarity) cl, AVG(comfort) co, COUNT(*) n FROM feedback").fetchone()
    done = [x for x in a if x["completed_at"]]
    minutes = [(x["completed_at"] - x["started_at"]) / 60 for x in done]
    review_h = [(x["reviewed_at"] - x["created_at"]) / 3600 for x in r if x["reviewed_at"]]
    to_eval_d = [(x["attended_at"] - x["created_at"]) / 86400 for x in r if x["attended_at"]]
    approved = [x for x in r if x["status"] in ("approved", "booked", "attended", "tests_done", "followed_up", "declined")]
    by = lambda key: _group([x for x in done], key)
    conf = [x for x in ap if x["status"] in ("confirmed", "attended", "missed")]
    reasons = _count([x["reason"] for x in ap if x["status"] in ("missed", "declined") and x["reason"]] +
                     [x["barrier"] for x in r if x["barrier"]])
    return {
        "started": len(a), "completed": len(done), "completion_rate": round(len(done) / len(a), 3) if a else None,
        "median_minutes_to_complete": _median(minutes),
        "referrals": len(r), "pending_review": sum(x["status"] == "pending_review" for x in r),
        "median_hours_to_review": _median(review_h),
        "median_days_to_evaluation": _median(to_eval_d),
        "referral_completion_rate": round(sum(x["status"] in ("attended", "tests_done", "followed_up") for x in approved) / len(approved), 3) if approved else None,
        "clinician_changed_level": sum(1 for x in r if x["final_level"] and x["final_level"] != x["level"]),
        "levels": _count(x["level"] for x in done),
        "by_age": by(lambda x: (x["cohort"] or "unknown|").split("|")[0]),
        "by_background": by(lambda x: (x["cohort"] or "|unknown").split("|")[1]),
        "user_feedback": dict(fb) if fb and fb["n"] else None,
        "care_connect": {"requests": len(ap), "booking_rate": round(len(conf) / len(ap), 3) if ap else None,
                         "median_hours_to_confirm": _median([(x["updated_at"] - x["created_at"]) / 3600 for x in conf if x["slot_at"]]),
                         "attendance_rate": round(sum(x["status"] == "attended" for x in conf) / len(conf), 3) if conf else None,
                         "declined_by_clinic": sum(x["status"] == "declined" for x in ap), "reasons": reasons},
    }


def _median(v):
    return round(statistics.median(v), 2) if v else None


def _count(it):
    out = {}
    for k in it:
        out[k] = out.get(k, 0) + 1
    return out


def _group(rows, key):
    groups = {}
    for x in rows:
        groups.setdefault(key(x), []).append(x)
    return {k: {"n": len(v), "tiers": _count(y["tier"] for y in v),
                "referred_pct": round(100 * sum(y["level"] != "self_care" for y in v) / len(v), 1)} for k, v in sorted(groups.items())}


@app.get("/api/clinician/audit")
def audit_log(clin=Depends(current_clinician)):
    with db.tx() as c:
        rows = c.execute("SELECT * FROM audit ORDER BY ts DESC LIMIT 200").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/insights")
def programme_insights(include_simulated: bool = False, clin=Depends(current_clinician)):
    """Aggregated, k-anonymised programme dashboard for the health authority."""
    with db.tx() as c:
        out = insights.build(c, include_simulated)
    db.audit(clin, "view_insights")
    return out


# ------------------------------------------------------------------ companion: safe next steps and questions about his summary
@app.get("/api/assessments/{aid}/next-steps")
def next_steps(aid: str, lang: str = "en", user=Depends(current_user)):
    row, result = completed(aid, user)
    with db.tx() as c:
        ref = _referral(c, aid)
        con = _consultation(c, aid)
        con_view = _consult_view(con, lang_of(lang), c) if con else None
        paused = sharing.is_paused(c, user)
    return guide.next_steps(result, assessment.user_view(result, lang_of(lang)), ref["status"] if ref else None, lang_of(lang),
                            consult=con_view, paused=paused)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.post("/api/assessments/{aid}/ask")
def ask(aid: str, body: AskIn, lang: str = "en", user=Depends(current_user)):
    """Answers from his own summary and the evidence map only. The question is not stored or sent anywhere."""
    row, result = completed(aid, user)
    with db.tx() as c:
        prefs = sharing.get(c, user)
        con = _consultation(c, aid)
        con_view = _consult_view(con, lang_of(lang), c) if con else None
    out = guide.ask(body.question, security.unseal(row["answers"]) or {}, result, assessment.user_view(result, lang_of(lang)),
                    prefs, consents(user)["clinician_review"] or bool(row["review_consent"]), lang_of(lang), consult=con_view)
    db.event(aid, "companion_question", out["intent"])  # the intent only, never the words
    return out


# ------------------------------------------------------------------ privacy centre: who sees what, receipts, access log
@app.get("/api/me/sharing")
def get_sharing(lang: str = "en", user=Depends(current_user)):
    L = lang_of(lang)
    with db.tx() as c:
        prefs = sharing.get(c, user)
        partner = c.execute("SELECT COUNT(*) FROM partner_links p JOIN assessments a ON a.id=p.assessment_id "
                            "WHERE a.user_id=? AND p.revoked=0 AND p.expires_at>?", (user, time.time())).fetchone()[0]
        codes = [dict(r) for r in c.execute("SELECT s.code, s.created_at, s.expires_at, s.used_by IS NOT NULL used, s.scope, s.purpose FROM shares s JOIN assessments a "
                                            "ON a.id=s.assessment_id WHERE a.user_id=? AND s.revoked=0 AND s.expires_at>? ORDER BY s.created_at DESC",
                                            (user, time.time())).fetchall()]
    for x in codes:
        x["scope"] = json.loads(x["scope"]) if x["scope"] else prefs["clinic"]
    return {"prefs": prefs, "categories": [{"key": k, "label": sharing.LABELS[L][k], "required": k in sharing.REQUIRED} for k in sharing.CATEGORIES],
            "recipients": [{"key": k, "label": sharing.LABELS[L][k]} for k in sharing.RECIPIENTS],
            "consents": consents(user), "partner_links": partner, "active_codes": codes}


class SharingIn(BaseModel):
    doctor: Optional[list[str]] = None
    clinic: Optional[list[str]] = None


@app.post("/api/me/sharing")
def set_sharing(body: SharingIn, user=Depends(current_user)):
    with db.tx() as c:
        prefs = sharing.set_prefs(c, user, body.model_dump(exclude_none=True))
    db.audit("user", "sharing_changed", user[:8])
    return {"prefs": prefs}


@app.get("/api/me/receipts")
def my_receipts(lang: str = "en", user=Depends(current_user)):
    with db.tx() as c:
        return {"receipts": sharing.receipts(c, user, lang_of(lang))}


@app.get("/api/me/access-log")
def my_access_log(lang: str = "en", user=Depends(current_user)):
    """Every time someone on the care side opened or acted on his record."""
    with db.tx() as c:
        return {"entries": sharing.access_log(c, user, lang_of(lang))}


@app.delete("/api/me/codes/{code}")
def revoke_any_code(code: str, user=Depends(current_user)):
    return revoke_share(code, user)


# ------------------------------------------------------------------ specialist visit outcome and follow-up
NEXT_KINDS = {"followup": ("Follow-up visit", "زيارة متابعة"), "treatment": ("Treatment started", "بدء العلاج"),
              "fertility": ("Couple's fertility assessment", "تقييم الخصوبة للزوجين"), "discharge": ("Back to self-care and re-check", "العودة للرعاية الذاتية وفحص متابعة")}


def _consultation(c, aid):
    return c.execute("SELECT * FROM consultations WHERE assessment_id=? ORDER BY created_at DESC LIMIT 1", (aid,)).fetchone()


# words in an ordered test -> the lab fields that show it is done, when he saves results after the visit
TEST_FIELDS = [(("semen", "sperm", "سائل", "منوي", "حيوانات"), {"concentration_m_per_ml", "total_count_m", "progressive_motility_pct", "volume_ml"}),
               (("testosterone", "تستوستيرون", "التستوستيرون"), {"testosterone"}), (("fsh",), {"fsh"}), (("lh",), {"lh"}),
               (("hba1c", "a1c", "سكر", "التراكمي"), {"hba1c"}), (("vitamin d", "vit d", "فيتامين"), {"vitamin_d"}),
               (("hormone", "هرمون"), {"testosterone", "fsh", "lh"})]


def _test_fields(name):
    n = name.lower()
    out = set()
    for words, fields in TEST_FIELDS:
        if any(w in n for w in words):
            out |= fields
    return out


def _consult_view(r, lang="en", c=None):
    o = security.unseal(r["outcome"]) or {}
    nk = NEXT_KINDS.get(o.get("next"), (o.get("next"), o.get("next")))
    done = set(o.get("tests_done", []))
    labs = set()
    if c is not None:
        a = c.execute("SELECT user_id FROM assessments WHERE id=?", (r["assessment_id"],)).fetchone()
        if a:
            labs = {x["field"] for x in c.execute("SELECT field FROM lab_results WHERE user_id=? AND created_at>=? AND review_status!='rejected'",
                                                  (a["user_id"], r["created_at"])).fetchall()}
    tests = []
    for t in o.get("tests_ordered", []):
        f = _test_fields(t)
        via_lab = bool(f & labs)
        tests.append({"name": t, "done": t in done or via_lab, "via": "result" if via_lab else ("you" if t in done else None), "uploadable": bool(f)})
    return {"id": r["id"], "created_at": r["created_at"], "summary": o.get("summary"), "tests_ordered": o.get("tests_ordered", []),
            "tests": tests, "tests_all_done": bool(tests) and all(t["done"] for t in tests),
            "plan": o.get("plan"), "next": o.get("next"), "next_label": nk[1] if lang == "ar" else nk[0],
            "followup_at": r["followup_at"], "followup_done_at": r["followup_done_at"],
            "by": "Clinic" if (r["clinician"] or "").startswith("clinic:") else "Specialist"}


def _record_consultation(c, aid, actor, body):
    if body.next in ("followup", "treatment", "fertility") and not body.followup_weeks:
        raise HTTPException(400, "Set when he should be followed up")
    if not _referral(c, aid):
        raise HTTPException(404, "No referral")
    now = time.time()
    fu = now + body.followup_weeks * 7 * 86400 if body.followup_weeks else None
    _set_referral(c, aid, "attended")
    c.execute("UPDATE appointments SET status='attended', updated_at=? WHERE assessment_id=? AND status='confirmed'", (now, aid))
    c.execute("INSERT INTO consultations VALUES (?,?,?,?,?,?,NULL)",
              (str(uuid.uuid4()), aid, actor, now, security.seal({**body.model_dump(), "tests_done": []}), fu))
    when = time.strftime("%Y-%m-%d", time.gmtime(fu)) if fu else None
    _message(c, aid, "clinician", "سجّل المختص ملخص زيارتك وخطتك. افتح «مساري» لتراها." + (f" موعد المتابعة: {when}." if when else "")
             + " / The specialist recorded your visit summary and plan. Open My journey to see it." + (f" Follow-up due: {when}." if when else ""))
    return fu


class ConsultationIn(BaseModel):
    summary: str = Field(min_length=10, max_length=1500)
    tests_ordered: list[str] = Field(default_factory=list, max_length=10)
    plan: Optional[str] = Field(None, max_length=1500)
    next: str = Field(pattern="^(followup|treatment|fertility|discharge)$")
    followup_weeks: Optional[int] = Field(None, ge=1, le=52)


@app.post("/api/clinician/cases/{aid}/consultation")
def record_consultation(aid: str, body: ConsultationIn, clin=Depends(current_clinician)):
    """The specialist closes the loop: what was found, what was ordered, and when he should come back."""
    with db.tx() as c:
        _visible(c, aid)
        fu = _record_consultation(c, aid, clin, body)
    db.audit(clin, "consultation_recorded", aid)
    db.event(aid, "consultation_recorded", body.next)
    return {"ok": True, "followup_at": fu}


@app.get("/api/assessments/{aid}/followup.ics")
def followup_ics(aid: str, user=Depends(current_user)):
    """Says only 'Follow-up', nothing about what for."""
    own_assessment(aid, user)
    with db.tx() as c:
        con = _consultation(c, aid)
    if not con or not con["followup_at"]:
        raise HTTPException(404, "No follow-up planned")
    return Response(care.ics(con["id"] + "-fu", con["followup_at"], "").replace("SUMMARY:Appointment", "SUMMARY:Follow-up"),
                    media_type="text/calendar", headers={"Content-Disposition": "attachment; filename=follow-up.ics"})


@app.get("/api/clinician/pathway")
def pathway_board(clin=Depends(current_clinician)):
    """Coordinator view: how many men are at each stage, and who has stalled long enough to need a nudge."""
    counts = {s: 0 for s in pathway.STAGES}
    stalled, at_risk = [], []
    with db.tx() as c:
        rows = c.execute("""SELECT a.* FROM assessments a JOIN referrals r ON r.assessment_id=a.id
                            WHERE a.completed_at IS NOT NULL AND a.user_id NOT IN (SELECT id FROM users WHERE sharing_paused=1)
                              AND (a.review_consent=1 OR EXISTS
                              (SELECT 1 FROM appointments x WHERE x.assessment_id=a.id))""").fetchall()
        for row in rows:
            ref = _referral(c, row["id"])
            appt = c.execute("SELECT * FROM appointments WHERE assessment_id=? AND status!='cancelled' ORDER BY created_at DESC LIMIT 1",
                             (row["id"],)).fetchone()
            con = _consultation(c, row["id"])
            stg, cur = pathway.stages(row, ref, appt, con, _final_level(row, ref), "en")
            if cur:
                counts[cur] += 1
            s = pathway.stalled(stg, cur, appt, con)
            if cur and cur not in ("recheck",):
                risk = prescribe.dropout_risk(row, ref, appt, security.unseal(row["answers"]) or {}, bool(s))
                if risk["band"] != "low":
                    at_risk.append({"id": row["id"], "stage": cur, "stage_label": pathway.LABELS["en"][cur], "level": _final_level(row, ref),
                                    "cohort": row["cohort"], "simulated": bool(row["simulated"]), **risk})
            if s:
                stalled.append({"id": row["id"], "stage": s[0], "days": s[1], "reason": pathway.STALL_TEXT[s[0]], "level": _final_level(row, ref),
                                "cohort": row["cohort"], "simulated": bool(row["simulated"]), "barrier": ref["barrier"] if ref else None,
                                "can_nudge": s[0] in pathway.NUDGE,
                                "reminded": bool(c.execute("SELECT 1 FROM events WHERE assessment_id=? AND type IN ('nudge','auto_nudge') AND detail=?",
                                                           (row["id"], s[0])).fetchone())})
    stalled.sort(key=lambda x: -x["days"])
    db.audit(clin, "view_pathway")
    at_risk.sort(key=lambda x: -x["points"])
    return {"stages": [{"key": k, "label": pathway.LABELS["en"][k], "n": counts[k]} for k in pathway.STAGES], "stalled": stalled,
            "at_risk": at_risk[:50], "risk_factors": {k: {"points": v[0], "text": v[1], "source": v[2]} for k, v in prescribe.DROPOUT_FACTORS.items()},
            "thresholds_days": pathway.STALL}


class NudgeIn(BaseModel):
    stage: str = Field(pattern="^(clinic|visit|followup|recheck)$")


@app.post("/api/clinician/cases/{aid}/nudge")
def nudge(aid: str, body: NudgeIn, clin=Depends(current_clinician)):
    """A short, discreet reminder in his private messages. Never by SMS or phone unless he chose that."""
    with db.tx() as c:
        _visible(c, aid)
        _message(c, aid, "clinician", pathway.NUDGE[body.stage])
    db.audit(clin, "nudge_sent", aid)
    db.event(aid, "nudge", body.stage)
    return {"ok": True}


class TestDoneIn(BaseModel):
    test: str = Field(min_length=1, max_length=200)
    done: bool = True


@app.post("/api/assessments/{aid}/consultation/tests")
def mark_test(aid: str, body: TestDoneIn, lang: str = "en", user=Depends(current_user)):
    """He ticks off a test the specialist ordered. Saving the result itself ticks it automatically."""
    own_assessment(aid, user)
    with db.tx() as c:
        con = _consultation(c, aid)
        if not con:
            raise HTTPException(404, "No visit recorded")
        o = security.unseal(con["outcome"]) or {}
        if body.test not in o.get("tests_ordered", []):
            raise HTTPException(400, "Not one of the ordered tests")
        done = set(o.get("tests_done", []))
        done = done | {body.test} if body.done else done - {body.test}
        o["tests_done"] = sorted(done)
        c.execute("UPDATE consultations SET outcome=? WHERE id=?", (security.seal(o), con["id"]))
        view = _consult_view(c.execute("SELECT * FROM consultations WHERE id=?", (con["id"],)).fetchone(), lang_of(lang), c)
        if view["tests_all_done"]:
            ref = _referral(c, aid)
            if ref and not ref["tests_done_at"]:
                _set_referral(c, aid, "tests_done", self_reported=True)
    db.event(aid, "ordered_test_marked", "done" if body.done else "undone")
    return view


# ------------------------------------------------------------------ privacy: pause all sharing, and how long data is kept
@app.get("/api/me/privacy")
def get_privacy(user=Depends(current_user)):
    with db.tx() as c:
        return sharing.privacy(c, user)


class PrivacyIn(BaseModel):
    paused: Optional[bool] = None
    retention_months: Optional[int] = -1
    reminders: Optional[bool] = None


@app.post("/api/me/privacy")
def set_privacy(body: PrivacyIn, user=Depends(current_user)):
    try:
        with db.tx() as c:
            out = sharing.set_privacy(c, user, body.paused, body.retention_months, body.reminders)
    except ValueError:
        raise HTTPException(400, "Choose 3, 6, 12 or 24 months, or keep until you delete")
    db.audit("user", "privacy_changed", user[:8])
    return out


# ------------------------------------------------------------------ clinic portal: the receiving specialist, with his handover code
CLINIC_HOURS = 12
_clinic_attempts = {}


class ClinicOpenIn(BaseModel):
    code: str = Field(min_length=4, max_length=20)


def _clinic_share(c, code):
    s = c.execute("SELECT s.*, a.user_id FROM shares s JOIN assessments a ON a.id=s.assessment_id WHERE s.code=? AND s.revoked=0 AND s.expires_at>?",
                  (code, time.time())).fetchone()
    if not s or sharing.is_paused(c, s["user_id"]):
        return None
    return s


@app.post("/api/clinic/open")
def clinic_open(body: ClinicOpenIn, request: Request):
    """The clinic types the code he gave them. No Riaya account is needed; access ends when the code expires or he withdraws it."""
    ip = request.client.host if request.client else "?"
    now = time.time()
    tries = [t for t in _clinic_attempts.get(ip, []) if now - t < 3600]
    if len(tries) >= 20:
        raise HTTPException(429, "Too many attempts. Try again in an hour.")
    _clinic_attempts[ip] = tries + [now]
    code = "".join(ch for ch in body.code.upper() if ch.isalnum() or ch == "-")
    with db.tx() as c:
        s = _clinic_share(c, code)
        if not s:
            raise HTTPException(404, "Code invalid, expired or withdrawn")
        appt = c.execute("SELECT provider_id FROM appointments WHERE share_code=?", (code,)).fetchone()
        actor = "clinic:" + (appt["provider_id"] if appt else "code")
        token = security.new_token()
        c.execute("INSERT INTO clinic_access VALUES (?,?,?,?,?)",
                  (security.token_hash(token), code, s["assessment_id"], now, min(s["expires_at"], now + CLINIC_HOURS * 3600)))
        c.execute("UPDATE shares SET used_by=COALESCE(used_by, ?) WHERE code=?", (actor, code))
    return {"token": token, "expires_in_hours": CLINIC_HOURS}


def current_clinic(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    with db.tx() as c:
        a = c.execute("SELECT * FROM clinic_access WHERE token_hash=? AND expires_at>?", (security.token_hash(authorization[7:]), time.time())).fetchone()
        s = _clinic_share(c, a["code"]) if a else None
        if not s:  # he withdrew the code or paused sharing: access ends at once
            raise HTTPException(401, "Access ended: the code expired or he withdrew it")
        appt = c.execute("SELECT provider_id FROM appointments WHERE share_code=?", (a["code"],)).fetchone()
    return {"aid": a["assessment_id"], "code": a["code"], "actor": "clinic:" + (appt["provider_id"] if appt else "code")}


@app.get("/api/clinic/case")
def clinic_case(clinic=Depends(current_clinic)):
    aid = clinic["aid"]
    with db.tx() as c:
        row = c.execute("SELECT * FROM assessments WHERE id=?", (aid,)).fetchone()
        ref = _referral(c, aid)
        share = c.execute("SELECT * FROM shares WHERE code=?", (clinic["code"],)).fetchone()
        allowed = sharing.scope_of(c, share, row["user_id"])
        appt = c.execute("SELECT a.*, p.name_en FROM appointments a JOIN providers p ON p.id=a.provider_id WHERE a.share_code=?",
                         (clinic["code"],)).fetchone()
        con = _consultation(c, aid)
        con_view = _consult_view(con, "en", c) if con else None
        prefs = security.unseal(appt["prefs"]) if appt else None
        letter, result, _ = _package(c, row, allowed)
    labs, withheld = letter["labs"], letter["withheld"]
    answers = security.unseal(row["answers"]) or {}
    view = assessment.user_view(result, "en")
    _access(clinic["actor"], "clinic_view", aid)
    return {"id": aid, "letter": letter["letter"], "fhir": letter["bundle"], "withheld": withheld, "allowed": allowed,
            "level": _final_level(row, ref), "doctor_reviewed": bool(ref and ref["reviewed_at"]), "next_step": view["next_step"],
            "tests_suggested": view["tests"], "tests_have": _tests_have(result), "labs": labs,
            "appointment": {"clinic": appt["name_en"], "status": appt["status"], "slot_at": appt["slot_at"],
                            "times": (prefs or {}).get("times"), "days": (prefs or {}).get("days"),
                            "contact": (prefs or {}).get("contact")} if appt else None,
            "preferences": {k: answers.get(k) for k in ("pref_language", "pref_clinician") if answers.get(k)},
            "consultation": con_view, "next_kinds": {k: v[0] for k, v in NEXT_KINDS.items()},
            "view_only": appt is None, "purpose": share["purpose"] or "clinic", "expires_at": share["expires_at"]}


def _needs_appointment(c, clinic):
    if not c.execute("SELECT 1 FROM appointments WHERE share_code=?", (clinic["code"],)).fetchone():
        raise HTTPException(403, "This code is for viewing only. Visits are recorded by the clinic he booked through Riaya.")


class ClinicAttendIn(BaseModel):
    outcome: str = Field(pattern="^(attended|missed)$")


@app.post("/api/clinic/attendance")
def clinic_attendance(body: ClinicAttendIn, clinic=Depends(current_clinic)):
    aid = clinic["aid"]
    with db.tx() as c:
        _needs_appointment(c, clinic)
        a = c.execute("SELECT * FROM appointments WHERE share_code=?", (clinic["code"],)).fetchone()
        if a:
            c.execute("UPDATE appointments SET status=?, updated_at=? WHERE id=?", (body.outcome, time.time(), a["id"]))
        if body.outcome == "attended":
            _set_referral(c, aid, "attended")
        else:
            _message(c, aid, "clinician", "لم نرك في موعدك. يمكنك اختيار وقت آخر من «مساري» متى ناسبك. / "
                                          "We missed you at your appointment. You can choose another time in My journey whenever suits you.")
    db.audit(clinic["actor"], "clinic_attendance", aid)
    db.event(aid, f"clinic_{body.outcome}")
    return {"ok": True}


@app.post("/api/clinic/consultation")
def clinic_consultation(body: ConsultationIn, clinic=Depends(current_clinic)):
    """The receiving specialist sends the visit summary back, so his journey and his companion know what happens next."""
    with db.tx() as c:
        _needs_appointment(c, clinic)
        fu = _record_consultation(c, clinic["aid"], clinic["actor"], body)
    db.audit(clinic["actor"], "consultation_recorded", clinic["aid"])
    db.event(clinic["aid"], "consultation_recorded", body.next)
    return {"ok": True, "followup_at": fu}


class ClinicMsgIn(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


@app.post("/api/clinic/message")
def clinic_message(body: ClinicMsgIn, clinic=Depends(current_clinic)):
    with db.tx() as c:
        _message(c, clinic["aid"], "clinician", "From the clinic / من العيادة: " + body.body)
    db.audit(clinic["actor"], "clinic_message", clinic["aid"])
    return {"ok": True}


# ------------------------------------------------------------------ prescriptive and predictive: best changes and a 12-week projection
@app.get("/api/assessments/{aid}/forecast")
def forecast(aid: str, lang: str = "en", nodes: Optional[str] = None, user=Depends(current_user)):
    """His best changes ranked (expected effect x evidence / effort) and how his signals could move over 12 weeks.
    `nodes` (comma-separated) lets him try his own choice of changes."""
    _, result = completed(aid, user)
    L = lang_of(lang)
    best = prescribe.best_changes(result, L)
    pick = [n for n in (nodes or "").split(",") if n] or (best["bundle"]["nodes"] if best["bundle"] else [])
    return {"best": best, "projection": prescribe.projection(result, pick, lang=L), "selected": pick}


# ------------------------------------------------------------------ privacy: see exactly what they will see, and add his questions
class QuestionsIn(BaseModel):
    questions: list[str] = Field(default_factory=list, max_length=8)


@app.put("/api/assessments/{aid}/questions")
def save_questions(aid: str, body: QuestionsIn, user=Depends(current_user)):
    """Questions he wants to discuss at the visit. They travel with the referral, in his words."""
    own_assessment(aid, user)
    qs = [q.strip()[:300] for q in body.questions if q and q.strip()][:8]
    with db.tx() as c:
        if qs:
            c.execute("INSERT OR REPLACE INTO visit_questions VALUES (?,?,?)", (aid, security.seal(qs), time.time()))
        else:
            c.execute("DELETE FROM visit_questions WHERE assessment_id=?", (aid,))
    return {"questions": qs}


@app.get("/api/assessments/{aid}/questions")
def get_questions(aid: str, user=Depends(current_user)):
    own_assessment(aid, user)
    with db.tx() as c:
        return {"questions": _questions(c, aid)}


@app.get("/api/assessments/{aid}/share-preview")
def share_preview(aid: str, recipient: str = "clinic", categories: Optional[str] = None, user=Depends(current_user)):
    """Exactly what the doctor or clinic would see, built by the same code that builds their view. Nothing is shared by previewing.
    `categories` previews a choice before he saves it."""
    if recipient not in sharing.RECIPIENTS:
        raise HTTPException(400, "Unknown recipient")
    row, _ = completed(aid, user)
    with db.tx() as c:
        prefs = sharing.get(c, user)
        allowed = prefs[recipient] if categories is None else \
            sorted(set(categories.split(",")) & set(sharing.CATEGORIES) | sharing.REQUIRED, key=sharing.CATEGORIES.index)
        out, _, _ = _package(c, row, allowed)
        paused = sharing.is_paused(c, user)
    return {"recipient": recipient, "allowed": out["allowed"], "withheld": out["withheld"], "letter": out["letter"],
            "questions": out["questions"], "paused": paused, "lab_count": len(out["labs"] or [])}


# ------------------------------------------------------------------ human in the loop: doctors agree or disagree with each finding
class FindingReviewIn(BaseModel):
    node: str = Field(min_length=1, max_length=60)
    verdict: str = Field(pattern="^(agree|disagree)$")
    reason: Optional[str] = Field(None, max_length=500)


@app.post("/api/clinician/cases/{aid}/findings")
def review_finding(aid: str, body: FindingReviewIn, clin=Depends(current_clinician)):
    """A doctor agrees or disagrees with one explained finding. Disagreeing needs a reason; every review is kept and audited."""
    if body.verdict == "disagree" and not (body.reason and body.reason.strip()):
        raise HTTPException(400, "Say why you disagree")
    if body.node not in graph().nodes:
        raise HTTPException(400, "Unknown finding")
    with db.tx() as c:
        _visible(c, aid)
        c.execute("INSERT INTO finding_reviews VALUES (?,?,?,?,?,?,?)",
                  (str(uuid.uuid4()), aid, body.node, clin, body.verdict, (body.reason or "").strip() or None, time.time()))
    db.audit(clin, "finding_" + body.verdict, aid)
    return {"ok": True}


@app.get("/api/clinician/cases/{aid}/findings")
def case_findings(aid: str, clin=Depends(current_clinician)):
    with db.tx() as c:
        _visible(c, aid)
        rows = c.execute("SELECT node, verdict, reason, clinician, ts FROM finding_reviews WHERE assessment_id=? ORDER BY ts", (aid,)).fetchall()
    latest = {}
    for r in rows:
        latest[r["node"]] = dict(r)
    return {"reviews": latest}


@app.get("/api/clinician/findings/agreement")
def finding_agreement(clin=Depends(current_clinician)):
    """How often doctors agree with each kind of finding, to show where the explanations need work."""
    g = graph()
    with db.tx() as c:
        rows = c.execute("SELECT node, SUM(verdict='agree') a, COUNT(*) n FROM finding_reviews GROUP BY node ORDER BY n DESC").fetchall()
        reasons = c.execute("SELECT node, reason FROM finding_reviews WHERE verdict='disagree' AND reason IS NOT NULL ORDER BY ts DESC LIMIT 20").fetchall()
    return {"by_finding": [{"node": r["node"], "label": g.nodes[r["node"]]["label"], "reviews": r["n"], "agree_pct": round(100 * r["a"] / r["n"])} for r in rows],
            "recent_disagreements": [{"label": g.nodes[r["node"]]["label"], "reason": r["reason"]} for r in reasons]}


# ------------------------------------------------------------------ automatic, discreet pathway reminders
def run_reminders():
    """Once per stage, a short private message when he has been stuck longer than the threshold, and one when his
    re-check is due. Never when he paused sharing or turned reminders off; never by SMS or phone."""
    sent = 0
    with db.tx() as c:
        rows = c.execute("""SELECT a.* FROM assessments a JOIN users u ON u.id=a.user_id
                            WHERE a.completed_at IS NOT NULL AND a.simulated=0 AND COALESCE(u.reminders,1)=1 AND COALESCE(u.sharing_paused,0)=0
                              AND a.completed_at=(SELECT MAX(b.completed_at) FROM assessments b WHERE b.user_id=a.user_id)""").fetchall()
        for row in rows:
            ref = _referral(c, row["id"])
            appt = c.execute("SELECT * FROM appointments WHERE assessment_id=? AND status!='cancelled' ORDER BY created_at DESC LIMIT 1",
                             (row["id"],)).fetchone()
            con = _consultation(c, row["id"])
            stg, cur = pathway.stages(row, ref, appt, con, _final_level(row, ref), "en")
            due = None
            if cur == "recheck":
                due = "recheck"
            else:
                st = pathway.stalled(stg, cur, appt, con)
                if st and st[0] in pathway.NUDGE:
                    due = st[0]
            if not due or c.execute("SELECT 1 FROM events WHERE assessment_id=? AND type IN ('nudge','auto_nudge') AND detail=?",
                                    (row["id"], due)).fetchone():
                continue
            _message(c, row["id"], "clinician", pathway.NUDGE[due])
            c.execute("INSERT INTO events VALUES (?,?,?,?)", (time.time(), row["id"], "auto_nudge", due))
            sent += 1
    if sent:
        db.audit("system", "reminders_sent", str(sent))
    return sent


@app.post("/api/clinician/reminders/run")
def reminders_now(clin=Depends(current_clinician)):
    """Runs the hourly reminder check now (for the coordinator)."""
    return {"sent": run_reminders()}


# ------------------------------------------------------------------ preparing for the visit, and how it went
@app.get("/api/assessments/{aid}/prepare")
def prepare_visit(aid: str, lang: str = "en", user=Depends(current_user)):
    row, result = completed(aid, user)
    L = lang_of(lang)
    with db.tx() as c:
        ref = _referral(c, aid)
        con = _consultation(c, aid)
        con_view = _consult_view(con, L, c) if con else None
        labs = labtimeline.series(_lab_points(c, "user_id=?", (user,), L), L)
    have = [f"{x['name']} {x['value']}".strip() for x in _tests_have(result) if x.get("value")] + \
           [f"{x['name']} {x['latest']['value']} {x['unit'] or ''}".strip() for x in labs if x["latest"]]
    return visit.prepare(result, assessment.user_view(result, L), security.unseal(row["answers"]) or {}, _final_level(row, ref),
                         have, con_view, L)


class VisitFeedbackIn(BaseModel):
    respect: int = Field(ge=1, le=5)
    privacy: int = Field(ge=1, le=5)
    explained: int = Field(ge=1, le=5)
    recommend: bool
    wait_days: Optional[float] = Field(None, ge=0, le=365)


@app.post("/api/assessments/{aid}/visit-feedback")
def visit_feedback(aid: str, body: VisitFeedbackIn, user=Depends(current_user)):
    """Three quick ratings after the visit. Clinics and the health authority only ever see averages over 5 or more men."""
    own_assessment(aid, user)
    with db.tx() as c:
        a = c.execute("SELECT * FROM appointments WHERE assessment_id=? AND status='attended' ORDER BY created_at DESC LIMIT 1", (aid,)).fetchone()
        if not a:
            raise HTTPException(409, "Rate the visit after you have attended it")
        c.execute("INSERT OR REPLACE INTO visit_feedback VALUES (?,?,?,?,?,?,?,?)",
                  (aid, a["provider_id"], body.respect, body.privacy, body.explained, int(body.recommend), body.wait_days, time.time()))
    db.event(aid, "visit_feedback")
    return {"ok": True}


@app.get("/api/assessments/{aid}/visit-feedback")
def get_visit_feedback(aid: str, user=Depends(current_user)):
    own_assessment(aid, user)
    with db.tx() as c:
        r = c.execute("SELECT * FROM visit_feedback WHERE assessment_id=?", (aid,)).fetchone()
        can = bool(c.execute("SELECT 1 FROM appointments WHERE assessment_id=? AND status='attended'", (aid,)).fetchone())
    return {"given": dict(r) if r else None, "can_rate": can}


# ------------------------------------------------------------------ usability testing with real testers
# The System Usability Scale (Brooke 1996): 10 items, 1-5. Odd items score (x-1), even items (5-x); the sum x 2.5 gives 0-100.
# 68 is the published average; 80+ is in the top 10% of products (Sauro & Lewis).
TESTER_DEVICES = {"iphone", "android", "mac", "windows", "other"}
TESTER_PARTS = {"voice", "form", "watch", "labs", "plan", "vault", "lock", "calculator", "booking", "privacy", "doctor"}
_tester_hits = {}


class TesterIn(BaseModel):
    device: str = Field(pattern="^(iphone|android|mac|windows|other)$")
    lang: str = Field(pattern="^(ar|en)$")
    tried: list[str] = Field(default_factory=list, max_length=11)
    sus: list[int] = Field(min_length=10, max_length=10)
    clear: int = Field(ge=1, le=5)
    private_felt: int = Field(ge=1, le=5)
    voice_ok: Optional[int] = Field(None, ge=1, le=5)
    would_use: int = Field(ge=1, le=5)
    recommend: bool
    comment: Optional[str] = Field(None, max_length=1000)


def sus_score(items):
    if any(not 1 <= v <= 5 for v in items):
        raise ValueError("SUS answers must be 1 to 5")
    return sum((v - 1) if i % 2 == 0 else (5 - v) for i, v in enumerate(items)) * 2.5


@app.post("/api/tester-feedback")
def tester_feedback(body: TesterIn, request: Request):
    """Anonymous feedback from people who tried Riaya. No name, email or phone; the comment is encrypted at rest."""
    ip = request.client.host if request.client else "?"
    now = time.time()
    _tester_hits[ip] = [t for t in _tester_hits.get(ip, []) if now - t < 3600]
    if len(_tester_hits[ip]) >= 10:
        raise HTTPException(429, "Too many responses from this connection. Try again later.")
    try:
        score = sus_score(body.sus)
    except ValueError as e:
        raise HTTPException(422, str(e))
    tried = [t for t in body.tried if t in TESTER_PARTS]
    row = (str(uuid.uuid4()), now, body.device, body.lang, json.dumps(tried), json.dumps(body.sus), score, body.clear, body.private_felt,
           body.voice_ok, body.would_use, int(body.recommend), security.seal(body.comment) if body.comment else None)
    if pgstore.enabled():
        pgstore.insert(row)
    else:
        with db.tx() as c:
            c.execute("INSERT INTO tester_feedback VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
    _tester_hits[ip].append(now)
    return {"ok": True, "sus": score}


def _tester_summary(c, with_comments):
    rows = pgstore.rows() if pgstore.enabled() else c.execute("SELECT * FROM tester_feedback ORDER BY ts").fetchall()
    n = len(rows)
    avg = lambda k: round(statistics.mean([r[k] for r in rows if r[k] is not None]), 2) if any(r[k] is not None for r in rows) else None
    parts, devices = {}, {}
    for r in rows:
        devices[r["device"]] = devices.get(r["device"], 0) + 1
        for t in json.loads(r["tried"] or "[]"):
            parts[t] = parts.get(t, 0) + 1
    scores = [r["sus_score"] for r in rows]
    out = {"n": n, "sus_mean": round(statistics.mean(scores), 1) if scores else None,
           "sus_median": round(statistics.median(scores), 1) if scores else None,
           "sus_benchmark": 68, "grade": None, "clear": avg("clear"), "private_felt": avg("private_felt"), "voice_ok": avg("voice_ok"),
           "would_use": avg("would_use"), "recommend_pct": round(100 * sum(r["recommend"] for r in rows) / n) if n else None,
           "devices": devices, "tried": dict(sorted(parts.items(), key=lambda kv: -kv[1])), "first": rows[0]["ts"] if rows else None,
           "last": rows[-1]["ts"] if rows else None}
    if scores:
        m = out["sus_mean"]
        out["grade"] = "A (excellent)" if m >= 80.3 else "B (good)" if m >= 74 else "C (OK, about average)" if m >= 68 else "D (below average)" if m >= 51 else "F (poor)"
    if with_comments:
        out["comments"] = [{"ts": r["ts"], "device": r["device"], "text": security.unseal(bytes(r["comment"]))} for r in reversed(rows) if r["comment"]][:100]
    return out


@app.get("/api/tester-feedback/summary")
def tester_summary_public():
    """Aggregates only, so the team can show how many people tested Riaya and what they thought."""
    with db.tx() as c:
        return _tester_summary(c, False)


@app.get("/api/clinician/tester-feedback")
def tester_summary_team(clin=Depends(current_clinician)):
    with db.tx() as c:
        out = _tester_summary(c, True)
    db.audit(clin, "view_tester_feedback")
    return out


# ------------------------------------------------------------------ Android apps: lets Riaya.apk and Calculator.apk open full screen
# The fingerprint is the SHA-256 of the signing certificate in android/signing (override with RIAYA_APK_SHA256).
APK_SHA256 = os.environ.get("RIAYA_APK_SHA256", "20:68:DA:BE:5C:0A:81:F7:FA:AC:9E:34:08:31:66:43:84:46:D4:09:28:CD:43:41:64:85:A2:85:2E:CA:20:4B")


@app.get("/.well-known/assetlinks.json")
def assetlinks():
    return [{"relation": ["delegate_permission/common.handle_all_urls"],
             "target": {"namespace": "android_app", "package_name": pkg, "sha256_cert_fingerprints": [APK_SHA256]}}
            for pkg in ("ae.riaya.app",)]


# ------------------------------------------------------------------ static web app
app.mount("/knowledge", StaticFiles(directory=ROOT / "knowledge"), name="knowledge")
app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
