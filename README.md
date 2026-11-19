# Riaya (رعاية): a private front door to men's reproductive health

A privacy-first, Arabic-first pre-screen that helps men in Abu Dhabi understand and act on reproductive-health signals early. It routes each man to the right level of care, with a clinician approving every referral. It is built to plug into the IFHAS reproductive-health screening module.

## All features at a glance

Works in any browser and installs as an app on **iPhone and Android** (PWA). Arabic first, fully in English too. Status: ✅ working and tested · 🟡 ready but not connected to a real-world service.

| # | Feature | What it does | Where | Status |
|---|---|---|---|---|
| **Getting started** |||||
| 1 | Private front door | No name or phone number; a revocable recovery code instead of an account | `/` | ✅ |
| 2 | Guided tour | Two-minute auto-playing walk through a sample check, with narration, spotlight and play/pause | `/` → "Take a guided tour" | ✅ |
| 3 | Talk it through (voice) | The check as a spoken conversation. He talks, Riaya listens, understands and replies out loud | `/chat.html` | ✅ |
| 4 | Language and accent choice | Arabic or English, then accent: Emirati, Saudi, Egyptian, Levantine (or British, American, Indian English). Accent steers recognition and the voice | `/chat.html` start screen | ✅ |
| 5 | Natural voices | Picks the device's most natural voice (neural, premium or enhanced first); speaks sentence by sentence with natural pauses; "hear this voice" preview | `js/voice.js` | ✅ |
| 6 | On-phone speech (private mode) | Whisper runs inside the browser so audio never leaves the phone | `js/voice.js` | ✅ |
| 7 | Spoken-number understanding | "one seventy eight" = 178, "سنة ونص" = 18 months, "ما عندي مانع" = yes; a half-heard duration is asked again, never guessed | `js/nlu.js` | ✅ |
| 7a | Voice demo mode | `chat.html?demo=en` / `?demo=ar`: recorded answers from a man play aloud and are recognised on the phone by Whisper (base for English, small for Arabic); if a clip is misheard, the screen says so | `/chat.html?demo=en` | ✅ |
| 8 | WhatsApp check | The same check over WhatsApp (Twilio), with an in-app demo | `/whatsapp.html` | 🟡 needs a Twilio number |
| 9 | Detailed form | Validated instruments: STOP-Bang, AUDIT-C, PHQ-2, PSS-4, ADAM | `/` | ✅ |
| **Devices and tests** |||||
| 10 | Watch first | Upload an Apple Health export and see what the watch alone suggests, before answering anything | `/` → Watch first | ✅ |
| 11 | On-your-wrist preview | His own data as a watch glance: Apple Watch (square) and Wear OS / Garmin (round) faces, with sleep and step rings, HRV, one tip and a discreet check-in | Watch-first results | ✅ |
| 12 | Other devices | Health Connect, Garmin, Fitbit, Dexcom/Libre CGM, generic CSV; personal baseline | `backend/app/wearables.py` | ✅ |
| 13 | Scan a lab report | Photograph each page; auto-enhanced, read on the phone (English and Arabic OCR), joined into one PDF and filed by date, **kept on the phone only** | Tests step → "Scan pages" | ✅ |
| 14 | Lab report reading | PDF, photo or text; keeps each lab's printed range, reads his age, scores reading confidence, checks how the sample was taken; he corrects before saving | `backend/app/labreport.py` | ✅ |
| 15 | Lab dashboard and forecast | Results saved, in range now, what is moving, next test due; trend line projected to the next test with a likely range; early alert when a value may cross the lab's limit | My lab results | ✅ |
| 16 | Doctor checks lab values | Each saved value is accepted, corrected or set aside by a doctor | Clinician console | ✅ |
| 17 | Semen analysis and blood tests | WHO 2021 limits; testosterone, LH, FSH, HbA1c, vitamin D; genomic flag | Tests step | ✅ |
| 18 | Clothing check | Reads a care label and gives a groin-heat index | `/fabric.html` | ✅ |
| **Explainable insights** |||||
| 19 | Explained summary | Dial, the factor he can change most, what we saw / why it matters / evidence grade / what helps / limits | Summary | ✅ |
| 20 | Evidence map | 69 factors, 148 graded links, 95 references | `/graph.html` | ✅ |
| 21 | Ask about your summary | Answers built only from his summary and the evidence; guardrails for urgent symptoms, medicines and "am I infertile?" | Summary → Ask | ✅ |
| 22 | Safe next steps | Now / next weeks / 3 months / please don't / get help sooner | Summary | ✅ |
| **Prescriptive and predictive** |||||
| 23 | Your best changes | Each change ranked by effect × evidence ÷ effort; the best three together | Summary → Your plan | ✅ |
| 24 | 12-week projection | How his signals could move if he does nothing, half or all of the plan; switch changes on and off | Summary → Your plan | ✅ |
| 25 | Riaya-Net | Our own small neural network, fine-tuned on real data, runs on the phone; clinician second opinion only | `docs/RIAYA_NET.md` | ✅ |
| 26 | Dropout early warning | Coordinators see who may fall off the pathway, with every reason | Coordinator board | ✅ |
| **12-week companion** |||||
| 27 | Goals and weekly check-ins | Up to three goals from his own drivers, doctor-reviewed, weekly adherence and a measure, trend charts | My plan | ✅ |
| 28 | WHO-5 wellbeing outcomes | Day 0, ~30 and ~84; 10-point meaningful change; low score offers a private doctor talk and the 800HOPE line | My plan | ✅ |
| 29 | Behaviour-change design | Each goal shows its COM-B target and BCT Taxonomy v1 techniques ("Why this works") | My plan | ✅ |
| 30 | Just-in-time nudges (JITAI) | Hourly decision: at most one well-timed nudge, never in quiet hours or while fasting; every decision explained | `backend/app/wellbeing.py` | ✅ |
| 31 | Fresh start after a lapse | Two weak or missed weeks → keep one goal, name the barrier, get an if-then plan | My plan | ✅ |
| 32 | Ramadan mode | Fasting-aware goals, check-ins after iftar, no nudges while fasting, test-timing notes; follows the calendar | My plan | ✅ |
| **Connected referral journey** |||||
| 33 | My journey | Check → doctor review → clinic → appointment → visit → visit summary → follow-up → re-check | My journey | ✅ |
| 34 | Doctor review | Every specialist referral approved, changed or rejected (with reason); rapid 24–48 h review with a live timer | Clinician console | ✅ |
| 35 | Care Connect | Verified clinic directory, appointment request with preferred times, coordinator confirms, "Appointment"-only calendar entry | Book your visit | ✅ |
| 36 | Call / WhatsApp / save clinic | One tap to the clinic's official phone or WhatsApp; save to contacts under a discreet name | Book your visit | ✅ |
| 37 | My own doctor | Pick the doctor from phone contacts (Android) or type the number (iPhone); call or send the handover code on WhatsApp; kept on the phone | Book your visit | ✅ |
| 38 | Clinic portal | Specialist opens the referral with his handover code, records attendance, the visit summary and tests ordered, messages him | `/clinic.html` | ✅ |
| 39 | Get ready for your visit | Results to bring, semen-test and morning-testosterone preparation, questions to ask | Book your visit | ✅ |
| 40 | Closed-loop tracking | Time limits by urgency, escalation to coordinator then clinical lead, on-time rate | Coordinator board | ✅ |
| 41 | FHIR R4 exports | Pre-screen bundle, referral letter, and the referral as a FHIR Task (requested → accepted → in-progress → completed) | API | ✅ (Malaffi/NABIDH/Riayati 🟡) |
| 42 | Messages and video | Encrypted messages and voice notes with the doctor; private video room | Journey | ✅ (public Jitsi by default; self-host in the UAE for production) |
| 43 | Automatic reminders | One discreet message per stalled stage; never if he turned reminders off or paused sharing | Automatic | ✅ |
| 44 | Visit ratings | Respect, privacy, explanation, would recommend; clinic averages only at 5+ ratings | After a visit | ✅ |
| 45 | Partner mode | A revocable link that shows his wife only that he completed the check | Summary → Care & sharing | ✅ |
| **Privacy and control** |||||
| 46 | One switch pauses all sharing | Doctor, coordinator and clinic lose access at once; appointments stay | Privacy | ✅ |
| 47 | Choose what each recipient sees | Per recipient: answers, devices, labs, plan; applies at once, even to codes already given | Privacy | ✅ |
| 48 | See exactly what they'll see | The referral letter word for word, updating live as he ticks boxes; his questions go at the top | Care & sharing | ✅ |
| 49 | Second-opinion codes | He picks the parts and 1, 3 or 7 days; view only | Privacy | ✅ |
| 50 | Retention he chooses | Until he deletes, or 3–24 months after his last visit, then erased | Privacy | ✅ |
| 51 | Access log and consent receipts | Who opened his record, and a receipt for every permission given or withdrawn | Privacy | ✅ |
| 52 | Privacy screen | One tap covers the app with a neutral wellness card; blurs when he switches apps | Every page | ✅ |
| 52a | Locked by default | After his first summary Riaya asks for a 4–6 digit PIN (Face ID / fingerprint optional). Every opening, and every return after 15 s away, shows the lock first; the PIN is kept only as a salted PBKDF2 hash; 5 wrong tries pause input | Every page | ✅ |
| 52b | Encrypted documents on the phone | Scanned reports and files are encrypted with AES-256-GCM using a key that cannot be exported from the browser; they open only while unlocked | My lab results | ✅ |
| 52c | Calculator disguise | Install Riaya as "Calculator" with a calculator icon; it is a working calculator, and his PIN then "=" opens Riaya | Privacy → Disguise, `/calc.html` | ✅ |
| 52d | Doctors sign in from the same app | "I'm a doctor" on the start screen opens the clinician console, which has its own PIN lock for shared computers | `/` → I'm a doctor | ✅ |
| 53 | Encryption, export, delete | Encrypted at rest; download everything; delete everything | Privacy | ✅ |
| **For the health authority** |||||
| 54 | Programme dashboard | k-anonymised funnel, time to care, drivers, fairness, clinic ratings, **30+ day outcomes** (engagement, WHO-5 change) | `/insights.html` | ✅ |
| 55 | Doctor feedback on findings | Agree / disagree per finding, aggregated to improve explanations | Clinician console | ✅ |
| 56 | Validation | Triage vignettes, real-data model, calibration, fairness, measured scenario checks | `validation/` | ✅ |
| 57 | Accessibility | Automated WCAG 2.2 AA audit with no violations, keyboard and screen-reader support, reduced motion | All pages | ✅ |

See `docs/WELLBEING_QA_RESPONSE.md` for how these answer the organisers' Wellbeing Q&A briefing, and `docs/FEEDBACK_RESPONSE.md` for the review feedback.

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
- **Clinic portal** (`/clinic.html`): the receiving specialist opens the referral with his handover code (no account), sees only what he shared, records attendance and the visit summary, and messages him. Tests the specialist ordered become a checklist in his journey that ticks itself off when he saves the results. After the visit, his companion's next steps follow the specialist's plan.
- **Privacy switches**: one switch pauses all sharing (doctor, coordinator and clinic lose access at once; appointments stay booked), and he chooses how long his data is kept (until he deletes it, or 3–24 months after his last visit, then everything is erased).
- **Get ready for your visit**: once he has a clinic, a checklist built from his own summary: results to bring, how to prepare for a semen analysis (WHO 2021) or a morning testosterone test (Endocrine Society 2018), questions worth asking about his own top drivers, and his choices at the visit.
- **Automatic, discreet reminders**: one private message per stalled stage (and when his re-check is due), checked hourly. Never sent if he turned reminders off or paused sharing; the coordinator board shows who has been reminded.
- **Second-opinion codes**: he picks exactly which parts of his record a code shows and for how long (1, 3 or 7 days). The doctor opens it on the clinic page, view only.
- **Visit experience ratings**: three quick ratings after a visit (respect, privacy, explanation) plus "would you recommend". The programme dashboard shows averages per clinic only when 5 or more men have rated it.
- **See exactly what they'll see**: before sharing, he previews the referral letter word for word as the doctor or clinic receives it (built by the same code that builds their view), and the preview updates live as he ticks boxes. He can add the questions he wants to ask; they go at the top of the letter.
- **Your best changes (prescriptive)**: each change ranked by expected effect on his signals × strength of evidence ÷ effort, with a first step and when it shows; the best set of three is chosen together. **12-week projection (predictive)**: how his signals could move if he does nothing, follows the plan half the time, or fully; he switches changes on and off and the chart redraws. Signals only, never a chance of pregnancy.
- **Dropout early warning**: coordinators see who may fall off the pathway before they stall, scored from published predictors of missed care, with every reason shown.
- **Doctor feedback on findings**: clinicians agree or disagree with each explained finding (a reason is required to disagree); it is audited, shown to him in his access log, and aggregated to improve the explanations.
- **Riaya-Net** (`docs/RIAYA_NET.md`): our own small neural network, pre-trained on our simulated cohort and fine-tuned on real data, exported to run on the phone. Evaluated honestly; clinician second opinion only.
- **Guided tour**: a two-minute, auto-playing walk through a sample check with narration, spotlight and play/pause/skip, in Arabic and English.
- **Measured scenario checks** (`validation/SCENARIOS.md`): red flags, unsupported companion claims, adversarial questions, consent and revocation, referral packages, all counted by running them.
- **User-controlled sharing across the pathway**: he chooses, per recipient (Riaya review doctor, the clinic he picks), which parts of his record travel: answers, device data, lab results, plan. The summary always travels with a referral. Changes apply at once, including to handover codes already given. He sees every active share code, who opened his record (access log), and downloads consent receipts for every permission he gave or withdrew.

## Run it
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
```
- User app: http://localhost:8000 · Clinician console: http://localhost:8000/clinician.html (demo login `clinician` / `demo-clinician`; set `RIAYA_CLINICIAN_PASSWORD` for anything real) · Evidence map: /graph.html · Clothing check: /fabric.html · WhatsApp demo: /whatsapp.html · Programme dashboard: /insights.html · Clinic portal (handover code): /clinic.html · API docs: /api/docs

Settings (environment variables): `RIAYA_DATA_KEY` (Fernet key for encryption at rest; otherwise a key file is created in `data/`), `RIAYA_DB` (SQLite path), `RIAYA_CLINICIAN_PASSWORD`, `RIAYA_PUBLIC_URL` (used in WhatsApp links), `RIAYA_WHATSAPP_NUMBER` and `RIAYA_WHATSAPP_JOIN` (shown as a QR code), `RIAYA_TWILIO_AUTH_TOKEN` (checks Twilio webhook signatures), `RIAYA_VIDEO_BASE` (enables video rooms, e.g. a self-hosted Jitsi in the UAE), `RIAYA_UAE_HOSTED=1` (hides the demo banner).

```bash
.venv/bin/python -m pytest -q backend/tests          # end-to-end API tests
.venv/bin/python validation/run_validation.py         # writes validation/REPORT.md
.venv/bin/python validation/scenario_checks.py        # writes validation/SCENARIOS.md (measured end-to-end checks)
.venv/bin/python validation/run_validation.py --seed-demo   # also loads simulated cases into the console
```

## Docs
- `docs/FEEDBACK_RESPONSE.md`: each point of the review feedback and where it is answered in the product
- `docs/WELLBEING_QA_RESPONSE.md`: the organisers' 10 Wellbeing Q&A questions, what is covered, what was added and what is still open
- `docs/VIDEO_PLAN.md`: the demo video plan, feature line-up and voiceover scripts (English and Arabic)
- `docs/recovery/`: the API description captured from the live deployment, used to rebuild the backend after the repository was lost
- `validation/REPORT.md`: triage vignettes, real-data model, simulated cohort, calibration, fairness, pathway simulation, limitations
- `docs/RESEARCH_VERIFICATION.md`: every claim checked against the literature, including corrections
- `docs/CULTURAL_DESIGN.md`: each cultural/religious barrier and how the product handles it
- `docs/PRIVACY_AND_REGULATION.md`: applicable UAE rules and the controls in the code
- `docs/SYSTEM_LAYERS.md`: each gap Abu Dhabi has named, mapped to a working feature
- `docs/IFHAS_AND_ROADMAP.md`: integration, referral levels, pilot roadmap and value measures
