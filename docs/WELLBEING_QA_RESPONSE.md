# Wellbeing Q&A briefing: how Riaya answers each question

The organisers' Wellbeing Q&A briefing (Future Health Digital Innovation Challenge, 38 slides) addressed ten questions. This note takes each one in turn. For every question it says what the briefing asked for, what Riaya already does, what we added after the briefing, and where to find it in the code and the demo. It ends with what is still open.

**Status:** ✅ in the product and tested · 🟡 partly in place, or ready but not connected · ⬜ not done (with the reason)

---

## Summary

| # | Question | Status | Main evidence in Riaya |
|---|---|---|---|
| 1 | Clinical and behavioural indicators | ✅ | Validated instruments (STOP-Bang, AUDIT-C, PHQ-2, PSS-4, ADAM, WHO-5); device signals; labs judged against each lab's own range |
| 2 | Evidence-based behavioural frameworks | ✅ *(new)* | Each companion part mapped to COM-B, BCT Taxonomy v1 codes and Self-Determination Theory; JITAI nudge engine |
| 3 | Long-term engagement | ✅ *(new)* | 12-week companion, weekly check-ins, relapse recovery ("fresh start"), dropout early warning, discreet reminders |
| 4 | Measurable 30+ day outcomes | ✅ *(new)* | WHO-5 at day 0 / 30 / 84 with a 10-point clinically meaningful threshold; engagement at weeks 4 / 8 / 12; k-anonymised outcomes panel |
| 5 | Cultural appropriateness and accessibility | ✅ *(new: Ramadan mode, accents, WCAG audit)* | Arabic-first RTL, Gulf/Saudi/Egyptian/Levantine voice accents, Ramadan mode, privacy screen, automated WCAG 2.2 AA audit with no violations, UAE PDPL mapping |
| 6 | Evidence of sustained improvement | ✅ *(from published studies)* | Every change Riaya recommends is backed by trials showing improvement that lasts (weight loss: sperm count ×1.4, kept at 52 weeks; quitting smoking: higher concentration after ~3 months), plus DPP, txt2stop and guided iCBT benchmarks. Our own outcome data starts with the pilot |
| 7 | Closed-loop referral tracking | ✅ *(new: time limits by urgency + FHIR Task)* | 8-stage pathway, time limits per urgency, two-step escalation, FHIR R4 Task status. Malaffi / NABIDH / Riayati ready but not connected |
| 8 | Clinician-in-the-loop governance | ✅ | Doctor approves every specialist referral and reviews plans; agree/disagree on each explained finding; full audit log |
| 9 | Local validation and transferability | ✅ *(from published studies)* | Instruments already validated in Arabic and in the Gulf (STOP-Bang in Al Ain and Riyadh; Arabic WHO-5 in Saudi Arabia and Kuwait); UAE prevalence built in (UAE National Health Survey 2017-18; Abu Dhabi semen data, n = 19,482); recalibration plan for the pilot |
| 10 | Explainable and transparent AI | ✅ | Separate explanations for the man, the clinician and the regulator; model card; every number traceable to a source |

---

## 1. Clinical and behavioural indicators

**What the briefing asked for:** objective measures across clinical domains, plus early behavioural markers.

**What Riaya does**
- **Validated instruments** at intake (`backend/app/questionnaire.py`):
  - STOP-Bang (sleep apnoea)
  - AUDIT-C (alcohol)
  - PHQ-2 (mood, with escalation)
  - PSS-4 (stress)
  - ADAM (androgen deficiency)
  - **WHO-5 (wellbeing)**, new and repeated during the plan (`backend/app/wellbeing.py`)
- **Objective device signals** (`backend/app/wearables.py`): sleep, steps, heart-rate variability (HRV), resting heart rate, SpO₂ dips, night glucose, late caffeine, screen time and weekend sleep shift. Sources are Apple Health, Health Connect, Garmin, Fitbit and continuous glucose monitor (CGM) CSV files. His last week is also compared with his own earlier weeks.
- **Clinical domains:**
  - Semen analysis against WHO 2021 limits.
  - Hormones (testosterone, LH, FSH), metabolic (HbA1c, vitamin D), each against the range printed on its own lab report (`backend/app/labtimeline.py`).
  - Genomic flags.
  - Red flags, which override everything.
- **Early behavioural markers:**
  - A drop in weekly check-in adherence and missed check-ins (lapse detection).
  - The WHO-5 trend.
  - Dropout-risk predictors on the coordinator board (`backend/app/prescribe.py::dropout_risk`).

---

## 2. Evidence-based behavioural frameworks

**What the briefing asked for:** COM-B, the BCT Taxonomy, Self-Determination Theory, habit formation and JITAI.

**Added after the briefing** (`backend/app/wellbeing.py`, `GET /api/behaviour-design`)

**COM-B and the BCT Taxonomy v1:** every part of the companion is mapped to the COM-B component it targets and the behaviour-change techniques (BCT Taxonomy v1 codes) it delivers.

| Part | COM-B | BCT v1 |
|---|---|---|
| Explained summary with evidence grades | Capability (psychological) | 5.1 Information about health consequences, 9.1 Credible source |
| He picks up to 3 goals from his own drivers | Motivation (reflective) | 1.1 Goal setting (behaviour) |
| First step for each goal | Capability (psychological) | 1.4 Action planning, 4.1 Instruction |
| Weekly check-in with a measure | Motivation (reflective) | 2.3 Self-monitoring of behaviour, 2.4 Self-monitoring of outcome |
| His own trend chart | Motivation (reflective) | 2.2 Feedback on behaviour |
| Just-in-time nudges, discreet calendar cue | Opportunity (physical) | 7.1 Prompts/cues |
| Same time, same cue | Motivation (automatic) | 8.3 Habit formation |
| Change the setting (laptop, phone, clothing) | Opportunity (physical) | 12.1 Restructuring the environment, 12.5 Adding objects |
| Doctor reviews the plan | Motivation (reflective) | 9.1 Credible source, 15.1 Persuasion about capability |
| Partner mode | Opportunity (social) | 3.1 Social support |
| Fresh start after a lapse | Capability (psychological) | 1.2 Problem solving, 1.5 Review behaviour goals |

- **Per goal:** each goal also carries its main barrier and techniques. For example, smoking targets Motivation (automatic) with 1.1, 1.4, 2.3, 8.3 and 1.2. The man sees these under "Why this works" in his plan.
- **Self-Determination Theory:**
  - Autonomy: he chooses his goals, how many, and whether a doctor reviews them, and he can stop at any time.
  - Competence: small first steps, weekly feedback, and a smaller goal after a lapse.
  - Relatedness: the doctor's note, private messages and the optional partner link.
- **Habit formation:** goals are anchored to a daily cue. The 12-week length fits both sperm development (about 74 days) and habit-formation data (median about 66 days; Lally 2010).
- **JITAI** (just-in-time adaptive intervention; Nahum-Shani 2018), run hourly (`run_jitai`):
  - Tailoring variables:
    - week of the plan
    - WHO-5 due or low
    - lapse
    - check-in two or more days late
    - Ramadan
    - quiet hours (11 pm to 7 am)
    - a limit of one nudge every 3 days
    - his reminder switch
    - sharing paused
  - **Every decision records its reasons.** `GET /api/me/plan/nudge-decision` shows him why the app would or would not nudge him right now.

**Tests:** `backend/tests/test_wellbeing_loop.py::test_behaviour_design_is_complete`, `test_jitai_rules_are_explained`.

---

## 3. Long-term engagement, from onboarding to relapse

| Phase | In Riaya |
|---|---|
| Onboarding | 3-minute voice or chat check in Arabic or English, guided tour, no name or number |
| Early weeks | Explained summary, best 3 changes, 12-week projection, plan with first steps, WHO-5 baseline |
| Building | Weekly check-ins, trend charts, doctor's note, discreet calendar reminder, JITAI nudges |
| Maintenance | Re-check at about 3 months, lab trend and next-test date, specialist plan drives next steps after a visit |
| **Relapse and recovery** *(new)* | A lapse is two weak weeks in a row or two missed check-ins. Riaya offers a **fresh start**: keep one goal, name the barrier (time, cravings, friends, work/heat, mood, forgot), and get a written if-then plan. No blame wording. |
| At-risk monitoring | Dropout early warning for coordinators (published predictors, each reason shown); automatic one-time stage reminders |

---

## 4. Measurable outcomes at 30+ days

**What the briefing asked for:** clinically meaningful thresholds (WHO-5, PHQ-9, GAD-7, ISI, steps) and a study design.

**Added**
- **WHO-5** at **day 0** (plan start), **about day 30** (week 5) and **about day 84** (week 12).
  - Raw score × 4 gives 0–100.
  - **≤50** = poor wellbeing.
  - **≤28** = likely depression: a private talk with a doctor is offered (only with review consent and sharing on), and the UAE support line 800 4673 (800HOPE) is always shown.
  - **±10 points** = a clinically meaningful change (Topp 2015).
- **Programme dashboard: "Outcomes at 30 days and beyond"** (`/insights.html`, k-anonymised, groups under 5 hidden):
  - engagement at weeks 4, 8 and 12
  - average WHO-5 change
  - % meaningfully better, % meaningfully worse
  - % with low wellbeing at the start
- **Objective outcomes already tracked:**
  - steps and sleep from devices, before and after
  - plan measures (cigarettes a day, weight, active days)
  - lab trends with a forecast
  - re-check at about 3 months
  - pathway outcomes (time to evaluation, completion)
- **Study design** (`docs/IFHAS_AND_ROADMAP.md`): pragmatic pilot.
  - Primary outcome: referral completion. Secondary outcomes: WHO-5 change at day 30 and day 84, engagement, time to evaluation.
  - Comparison with the usual pathway (12+ months before men are assessed).

**Not added:** PHQ-9, GAD-7 and ISI. PHQ-2 already screens mood and escalates. A full PHQ-9 includes a self-harm item that needs a staffed crisis protocol, which should be agreed with the pilot clinic before it is turned on. Sleep is measured objectively from the watch rather than with ISI.

---

## 5. Cultural appropriateness and accessibility

- **Deep-structure localisation** (`docs/CULTURAL_DESIGN.md`):
  - A men-only private front door; no names; a privacy cover screen.
  - Male/female clinician preference.
  - Partner mode that shows only that he acted.
  - Shisha, midwakh and dokha asked about by name.
  - Sirwal and wizar in the clothing questions.
  - Religiously sensitive wording reviewed.
- **Arabic RTL:** Arabic is the default language, with full RTL layout and Arabic numerals where they help.
- **Voice accents** *(new)*: in "Talk it through" he chooses Arabic or English, then the accent: **Emirati, Saudi, Egyptian or Levantine** (or British, American or Indian English). The accent steers both speech recognition and the voice that reads to him. Riaya picks the most natural voice on the device (neural, premium or enhanced voices first) and speaks sentence by sentence with natural pauses.
- **Ramadan mode** *(new)*:
  - Follows the calendar automatically (Umm al-Qura estimates; the UAE confirms by moon sighting), or he turns it on or off.
  - Goals are reworded for fasting: a quit window for smoking, split sleep, walking after iftar, a light suhoor.
  - Check-ins move to after iftar (9:30 pm), and **no nudges while he fasts**.
  - Lab and semen-test timing notes for fasting.
- **WCAG 2.2 AA** *(new audit)*: axe-core 4.10 automated audit (rules wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa).
  - Pages checked: landing, voice chat, summary, plan, lab results, care booking, journey, clinic portal and coordinator board.
  - Result: **no violations** after two fixes, a contrast fix on the landing mockup and a role fix for radio-style choices.
  - Already in place: keyboard support for every option chip, visible focus, reduced-motion support, a bigger-text switch, and screen-reader labels on charts. Touch targets pass the WCAG 2.2 target-size check.
  - Automated checks cannot find every barrier; a manual screen-reader pass with VoiceOver and TalkBack is planned for the pilot.
- **UAE PDPL** (`docs/PRIVACY_AND_REGULATION.md`):
  - Federal Decree-Law 45/2021, the ICT in Health Law 2/2019 (data stays in the UAE in production), and DoH Abu Dhabi standards.
  - Controls: consent per purpose, a one-switch pause on all sharing, retention periods he chooses, consent receipts, an access log, and export or deletion of his data.

---

## 6. Evidence of sustained improvement

The briefing asked for benchmarks from digital CBT, smoking cessation and diabetes prevention trials. Riaya is designed against these:

| Benchmark | Effect | What Riaya borrows |
|---|---|---|
| Diabetes Prevention Program (Knowler 2002, NEJM) | 58% fewer new diabetes cases with lifestyle change | Weight and activity goals, weekly self-monitoring, coach (doctor) feedback |
| Text-message smoking cessation (txt2stop; Free 2011, Lancet) | Verified quitting at 6 months roughly doubled (10.7% vs 4.9%) | Brief, well-timed prompts; a fresh start after a slip |
| Guided internet CBT for depression (Karyotaki 2021, JAMA Psychiatry) | Guided programmes do better than unguided ones | Human guidance: the doctor's note on the plan, messages, low-WHO-5 escalation |
| Mental-health app retention (Baumel 2019, JMIR) | Median 30-day retention about 3% | Why engagement is measured at weeks 4, 8 and 12, and why we have dropout early warning |

**Honest status:** the outcomes on the demo dashboard come from **simulated** plans, labelled as such. They show that the measurement pipeline works, not that Riaya works. Sustained improvement will come from the pilot.

---

## 7. Closed-loop referral tracking

**Added** (`backend/app/referral_loop.py`)

**Time limits by urgency:**

| Level | Priority | Doctor review | Appointment | Visit summary back |
|---|---|---|---|---|
| Emergency | stat | not routed: told to go to the emergency department or call 998 now | | |
| Urgent specialist | urgent | 4 h | 24 h | 2 days |
| Same-day primary care | urgent | 4 h | 12 h | 2 days |
| Andrology, fertility services, primary care | routine | 48 h | 14 days | 7 days |

- **Escalation:** a late milestone goes to the **coordinator**. At twice the limit it goes to the **clinical lead**. Shown on the coordinator board under "Closed-loop referral tracking", with the on-time rate.
- **HL7 FHIR status flow:** every referral is published as a **FHIR R4 Task** (`GET /api/assessments/{id}/fhir/task`) whose `focus` is the ServiceRequest. Its status moves through:
  - `requested` → `accepted` → `in-progress` (appointment booked, seen) → `completed` (summary returned)
  - or `rejected` (doctor declined) / `on-hold` (he could not attend) / `cancelled` (no referral needed)

  Deadlines go in `restriction.period` and `input`, met milestones in `output`, and escalations in `note`.
- **Malaffi / NABIDH / Riayati:** the Task and the pre-screen bundle are standard FHIR R4, the format these exchanges take. **Riaya is not connected to them.** Connecting needs onboarding as a DoH/DHA/MOHAP-approved participant, which is a pilot step.
- **Already in place:**
  - Clinic portal with a handover code, attendance, the specialist's visit summary and tests ordered.
  - Follow-up date.
  - Re-check at about 3 months.
  - Discreet reminders.
- **New in the loop:**
  - One-tap **call** and **WhatsApp** to the clinic's official lines (Cleveland Clinic Abu Dhabi 800 8 2223; SEHA 80050, WhatsApp 02 410 2200).
  - **Save to contacts** under a discreet name.
  - **My own doctor**: picked from phone contacts on Android, or typed on iPhone. Kept on the phone only.

**Tests:** `test_wellbeing_loop.py::test_referral_loop_task_and_escalation`.

---

## 8. Clinician-in-the-loop governance

- Riaya is **decision support only**. Every specialist referral is approved, changed (reason required) or rejected (reason required) by a licensed doctor. Plans are doctor-reviewed when he agreed to review.
- **Doctor feedback on findings:** the doctor agrees or disagrees with each explained finding (a reason is required to disagree). This is audited, shown to him in his access log, and aggregated to improve the explanations.
- **Red flags** override everything and never wait for review.
- The **companion has guardrails:** no doses, no diagnosis, no chances.
- **Audit:** every clinician and clinic action is recorded, and he sees who opened his record.
- **Accountability:** the pilot clinic's licensed clinicians own clinical decisions under DoH Abu Dhabi standards. Riaya's role, its limits and how incidents are reported are set out in `docs/PRIVACY_AND_REGULATION.md` and `docs/IFHAS_AND_ROADMAP.md`.
- **EHR integration:** FHIR R4 pre-screen bundle (Observation, Condition, ServiceRequest), the FHIR Task above, and the IFHAS hand-off.

---

## 9. Local validation and transferability

- **Measured now:**
  - Triage vignettes based on guidelines (WHO 2021, AUA/ASRM 2021, EAU 2024, ASRM 2020).
  - A model on real data (UCI Fertility, n=100, repeated cross-validation).
  - A simulated local cohort built from published effect sizes, with calibration and fairness by age band and background.
  - All in `validation/REPORT.md`.
  - Scenario checks: red flags 5/5, unsupported claims 0/78, adversarial questions 30/30, consent checks 15/15, referral packages 6/6 (`validation/SCENARIOS.md`).
- **Riaya-Net** (`docs/RIAYA_NET.md`): our own small model, pre-trained on the simulated cohort and fine-tuned on real data. It did not beat the simple baselines and is reported honestly. It is used as a clinician second opinion only.
- **Local recalibration plan:**
  - Thresholds and model weights are refitted on pilot data.
  - The fairness table is monitored by group.
  - A blind panel of UAE andrologists and family physicians sets the expected vignette answers.
- **Transferability:** the evidence graph, the time limits and the clinic directory are data, not code. Another emirate or country changes its clinics, limits and language without changing the engine.

---

## 10. Explainable and transparent AI, tailored by audience

| Audience | What they get |
|---|---|
| The man | Plain-language findings with "what we saw / why it matters / evidence grade / what helps / limits", best changes ranked by effect × evidence ÷ effort, 12-week projection, lab trend forecast with its caveat, "see exactly what the doctor will see" before sharing |
| Clinicians | Shapley attribution over the evidence graph, SHAP waterfall, real-data second opinion, Riaya-Net contributions, provenance of every input, agree/disagree per finding |
| Regulators / health authority | Model card, validation report, scenario checks, k-anonymised programme dashboard (funnel, fairness, outcomes), access log, FHIR exports |

Nothing he types into "Ask" is sent to an outside AI service. Answers are built from his own summary and the evidence graph, so they cannot invent a diagnosis or a dose.

---

## Open items

1. **Connect to a health information exchange:** Malaffi (Abu Dhabi), then NABIDH or Riayati, as an approved participant.
2. **Full PHQ-9 and GAD-7**, once a staffed crisis protocol is agreed with the pilot clinic.
3. **Manual accessibility testing** with VoiceOver and TalkBack users, and a bilingual usability round in Abu Dhabi.
4. **Riaya's own outcome data** from the pilot. Published evidence for each recommended change is above; the dashboard's demo values stay labelled simulated.
5. **More intake languages**, starting with Urdu, Hindi, Malayalam and Tagalog, after clinical translation review. Voice already works in four Arabic accents and three English accents.

---

## Evidence for questions 6 and 9, from published studies

Riaya's own pilot hasn't happened yet, so we don't present any results of our own. What we show instead is that **each part of Riaya rests on published evidence, including from the UAE and the Gulf.**

### Q6. Improvements from the changes Riaya recommends that last

| Change Riaya recommends | Published evidence | Lasting? |
|---|---|---|
| Lose 5–10% of body weight | RCT, 56 men with obesity: an 8-week diet (~16.5 kg lost) raised sperm concentration **1.49×** and sperm count **1.41×**; the gain was **kept at 52 weeks** in men who kept the weight off, helped by exercise (Andersen et al., *Human Reproduction* 2022) | ✅ 1 year |
| Quit smoking | Prospective controlled study: about 3 months after quitting, **sperm concentration, semen volume and total count rose** (2022, PubMed 35963898) | ✅ 3 months (one sperm cycle) |
| Lifestyle programme with an app (Riaya's model) | Nordic Sperm DNA Study: an 800-man RCT of a 3-month lifestyle programme plus app, versus standard care (NCT07779954); results pending | ⏳ |
| Weekly self-monitoring and feedback | Diabetes Prevention Program: 58% fewer new diabetes cases (Knowler 2002) | ✅ years |
| Brief, well-timed prompts | txt2stop: verified quitting at 6 months roughly doubled (Free 2011) | ✅ 6 months |
| Human guidance alongside digital support | Guided internet CBT does better than unguided (Karyotaki 2021) | ✅ |

Why Riaya's plan is 12 weeks and the re-check is at about 3 months: sperm take about 74 days to develop, and both trials above measured the gain at or after that point.

### Q9. Local validation and transferability

| What | Published local evidence | How Riaya uses it |
|---|---|---|
| STOP-Bang (sleep apnoea) | Validated in Arabic at an **Al Ain, UAE** sleep clinic (high sensitivity, test-retest ICC 0.931, UAEU) and in **Riyadh** against polysomnography (98% sensitivity; BaHammam 2015) | Asked as validated; its result feeds the sleep-apnoea path |
| WHO-5 (wellbeing) | Arabic WHO-5 validated in **Saudi Arabia** (α = 0.91; Alshayea 2023) and in six Arab countries including **Kuwait** (α .92–.96, n = 3,247; *Cambridge Prisms* 2025) | Used at day 0, 30 and 84 |
| Who the men are | UAE National Health Survey 2017-18: among Emirati men, **38.5% overweight and 32.2% obese**; daily smoking 13.9% of men; 2024-25 survey: smoking 13.7% of men | Explains why weight, smoking and shisha are first-line goals |
| Semen quality here | Abu Dhabi fertility centre, **19,482 men from 113 countries over 11 years**: Emirati men had lower motility and normal morphology, and teratozoospermia was **12%**, higher than in other nationalities (Heliyon 2024) | Supports screening Emirati men early and the clinic pathway |
| Genetics | Al Ain Fertility Center, 4,672 infertile patients: **6.5%** had chromosomal abnormalities | Supports the genomic flag (karyotype / AZF / CFTR) |
| Male factor is common | Clinics in the UAE report men as the causative factor in around half of couples' cases (small clinic sample; Bourn Hall) | Supports a men-first front door |

**Transferability:** clinics, time limits, language, thresholds and the evidence graph are data, not code. Recalibration on pilot data is planned: refit the model weights and thresholds, watch fairness by nationality and age, and have a blind panel of UAE andrologists set the expected vignette answers.

### Sources
- Andersen E. et al. Sperm count is increased by diet-induced weight loss and maintained by exercise or GLP-1 analogue treatment: a randomized controlled trial. *Hum Reprod* 2022. https://pmc.ncbi.nlm.nih.gov/articles/PMC9247415
- Sperm concentration and semen volume increase after smoking cessation in infertile men (2022). https://pubmed.ncbi.nlm.nih.gov/35963898/
- Nordic Sperm DNA Study (NCT07779954). https://clinicaltrials.gov/study/NCT07779954
- Evaluation of the Arabic version of STOP-Bang questionnaire (Al Ain, UAEU). https://research.uaeu.ac.ae/en/publications/evaluation-of-the-arabic-version-of-stop-bang-questionnaire-as-a-/
- BaHammam A. et al. Arabic STOP-Bang validation (2015). https://pmc.ncbi.nlm.nih.gov/articles/PMC4378065
- Cross-country validation of the Arabic WHO-5 in six Arab countries (2025). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12394027/
- Alshayea A. Arabic WHO-5 (Saudi Arabia), *J Psychopathol Behav Assess* 2023. https://link.springer.com/10.1007/s10862-023-10027-x
- UAE National Health Survey 2017-2018 (MOHAP). https://u.ae/-/media/Documents-2nd-half-2023/uae-national-health-survey-report-2017-2018.pdf
- Tobacco profile, United Arab Emirates (from STEPS 2018). https://gsthr.org/countries/profile/are/1
- Semen parameter profiles by nationality at a UAE fertility centre (Heliyon 2024). https://doaj.org/article/8561ebfd01ba4fe39b2b9007d8ae7285
- Male infertility in the UAE (clinic data). https://pmc.ncbi.nlm.nih.gov/articles/PMC11609639
- Male infertility a reality in UAE (Gulf News, Bourn Hall). https://gulfnews.com/uae/health/male-infertility-a-reality-in-uae-1.2105864
