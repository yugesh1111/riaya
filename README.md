# Riaya (رعاية): a private front door to men's reproductive health

A privacy-first, Arabic-first pre-screen that helps men in Abu Dhabi understand and act on reproductive-health signals early. It routes each man to the right level of care, with a clinician approving every referral. It is built to plug into the IFHAS reproductive-health screening module.

## What's in it
- **Evidence graph** (`knowledge/graph.json`): 69 factors and 148 cause→effect links, each with an evidence grade (A–D) and a source (95 references). It also holds 23 measurable signals (watch, phone, CGM, questionnaire, lab) with thresholds, and 8 red flags. The graph drives scoring and explanations, and is validated at server start.
- **Intake** in Arabic and English, using validated instruments: STOP-Bang, AUDIT-C, PHQ-2, PSS-4 and ADAM.
- **Device data**: Apple Health export (sleep, steps, HRV, SpO2, glucose, caffeine, alcohol), Dexcom/Libre CGM CSV, a generic daily CSV (Fitbit/Garmin/Health Connect/screen time), or manual entry. Raw files are never stored.
- **Test results**: interpreted against WHO 2021 reference limits, from a lab report, a quantitative smartphone device (YO-type) or a simple home test.
- **Explainability**: Shapley attribution over the evidence graph, a gradient-boosting model with a SHAP waterfall (simulated cohort with literature effect sizes), and a logistic model trained on real data (UCI Fertility, n=100) as a second opinion.
- **Triage**: deterministic, ordered rules, each citing its guideline. Red flags override everything. Clinician approval is required for specialist referrals.
- **Clinician console**: review queue, case explanation, approve/modify, booking and attendance tracking, outcome and fairness metrics, access log.
- **IFHAS hand-off**: FHIR R4 Bundle export.
- **Privacy**: no identity data, granular consent, encryption at rest, revocable share codes, delete/export, audit log.
- **Care navigation**: after approval, a handover package (FHIR referral document plus a readable letter) for the receiving clinic. It includes results already available (so tests are not repeated) and the man's preferences.
- **Genomic flag**: automatic karyotype / AZF / CFTR and genetic-counselling flags for severe results, high FSH or a family pattern.
- **Rapid clinical review**: 24–48 h target with a live timer, encrypted patient–clinician messages, and a private video room.
- **Partner mode**: a revocable link that shows his wife only that he completed the check and the kind of next step.
- **Blood results and environment**: optional testosterone/LH/FSH/HbA1c/vitamin D entry, plus occupation and traffic/industry proximity.
- **Clothing check**: reads a care label (typed, or photographed with on-device OCR) and gives a groin-heat index with evidence-graded notes.
- **Voice and chat intake**: "Talk it through" in Gulf Arabic or English, with on-device understanding of spoken answers (`web/chat.html`, `js/nlu.js`, `js/voice.js`), and the same check over **WhatsApp** (Twilio webhook, with an in-app demo at `/whatsapp.html`). The phone number is never stored.
- **Watch first**: upload an Apple Health export and see what the devices alone suggest before answering anything, including a personal baseline (his last week against his own earlier weeks).
- **Lab Intelligence**: reads a lab report (PDF, photo via on-device OCR, or pasted text), keeps each lab's own printed range, scores reading confidence, checks how the sample was taken, and lets him correct values before saving. A results timeline shows each test against its own lab's range; a doctor accepts, corrects or sets aside each value.
- **12-week companion**: up to three goals from his own drivers, doctor-reviewed when he agreed to review, weekly check-ins with adherence and a measure, trends, and a discreet calendar reminder that says only "Weekly check-in".
- **Care Connect**: a verified clinic directory (official websites, who confirmed each clinic and when), appointment requests with preferred times, a coordinator who confirms the slot, a calendar entry that says only "Appointment", attendance and missed-visit reasons, and a one-time handover code for the clinic.
- **Programme dashboard** (`/insights.html`): k-anonymised funnel, time to care, drivers, prevalence, channels and fairness for ADPHC / DoH. Groups under 5 are hidden.
- **Recovery code**: restores his checks on a new phone with no name or number; the old device is signed out.

### Added after the review feedback (see `docs/FEEDBACK_RESPONSE.md`)
- **Private health companion**: a ladder of *safe next steps* (now, next weeks, 3 months, what not to do, when to get help sooner) and an *Ask about your summary* box. Answers are built only from his own summary and the evidence map, cite their evidence grade, and run three guardrails first (urgent symptoms, medicines and doses, "am I infertile?"). Nothing he types is stored or sent to an outside AI service.
- **Connected referral journey**: one pathway per check with eight stages (check, doctor review, clinic, appointment, specialist visit, visit summary, follow-up, re-check). The specialist records the visit outcome, tests ordered and the follow-up date; he sees it in his journey with a discreet follow-up calendar entry. A coordinator board shows where every man is and who has stalled, with a one-click private nudge.
- **User-controlled sharing across the pathway**: he chooses, per recipient (Riaya review doctor, the clinic he picks), which parts of his record travel: answers, device data, lab results, plan. The summary always travels with a referral. Changes apply at once, including to handover codes already given. He sees every active share code, who opened his record (access log), and downloads consent receipts for every permission he gave or withdrew.

## Run it
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
```
- User app: http://localhost:8000 · Clinician console: http://localhost:8000/clinician.html (demo login `clinician` / `demo-clinician`; set `RIAYA_CLINICIAN_PASSWORD` for anything real) · Evidence map: /graph.html · Clothing check: /fabric.html · WhatsApp demo: /whatsapp.html · Programme dashboard: /insights.html · API docs: /api/docs

Settings (environment variables): `RIAYA_DATA_KEY` (Fernet key for encryption at rest; otherwise a key file is created in `data/`), `RIAYA_DB` (SQLite path), `RIAYA_CLINICIAN_PASSWORD`, `RIAYA_PUBLIC_URL` (used in WhatsApp links), `RIAYA_WHATSAPP_NUMBER` and `RIAYA_WHATSAPP_JOIN` (shown as a QR code), `RIAYA_TWILIO_AUTH_TOKEN` (checks Twilio webhook signatures), `RIAYA_VIDEO_BASE` (enables video rooms, e.g. a self-hosted Jitsi in the UAE), `RIAYA_UAE_HOSTED=1` (hides the demo banner).

```bash
.venv/bin/python -m pytest -q backend/tests          # end-to-end API tests
.venv/bin/python validation/run_validation.py         # writes validation/REPORT.md
.venv/bin/python validation/run_validation.py --seed-demo   # also loads simulated cases into the console
```

## Docs
- `docs/FEEDBACK_RESPONSE.md`: each point of the review feedback and where it is answered in the product
- `docs/recovery/`: the API description captured from the live deployment, used to rebuild the backend after the repository was lost
- `validation/REPORT.md`: triage vignettes, real-data model, simulated cohort, calibration, fairness, pathway simulation, limitations
- `docs/RESEARCH_VERIFICATION.md`: every claim checked against the literature, including corrections
- `docs/CULTURAL_DESIGN.md`: each cultural/religious barrier and how the product handles it
- `docs/PRIVACY_AND_REGULATION.md`: applicable UAE rules and the controls in the code
- `docs/SYSTEM_LAYERS.md`: each gap Abu Dhabi has named, mapped to a working feature
- `docs/IFHAS_AND_ROADMAP.md`: integration, referral levels, pilot roadmap and value measures
