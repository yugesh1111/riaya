# Response to the review feedback

The review team asked us to take Riaya from "AI summaries and insights after a questionnaire and report upload" to:

1. a **private health companion** that turns findings into **explainable risk insights** and **safe next-step recommendations**;
2. a **connected referral journey** that guides men from the first risk assessment to **specialist consultation and follow-up**;
3. with **clear explanations**, **user-controlled privacy settings** and **consent-based data sharing across the care pathway**.

This note maps each point to what is now in the product, where it lives in the code, and how it is tested.

---

## 1. Private health companion

### Explainable risk insights
Every finding is shown as a card with five parts, in Arabic or English:

| Part | What he sees | Source |
|---|---|---|
| What we saw | "Watch: 6.0 h average sleep", "Smokes daily", "Lab: FSH 9.2 IU/L" | his answers, devices, labs (`provenance`) |
| Why it matters | the strongest cause-and-effect path to fertility potential, e.g. *Sedentary → Obesity → Lower sperm count → fertility potential* | evidence graph, 148 graded links |
| Strength of evidence | grade A–D, with the studies linked | 95 references |
| What helps | one concrete action | clinician-written plan library |
| Limits | "Based on your own answers", "Consumer wearables estimate this", "The research behind this link is limited (grade C)…" | per source and per grade |

He also sees **what the summary is based on** (measured, screened, reported, not yet measured), **contradictions** between sources (e.g. he says 8 h of sleep, the watch measured 6 h), his **personal baseline** from the watch, and an **educational what-if** ("if you changed these, the signals from habits would fall by about 5%"), always labelled as not a prediction.

### Safe next steps (`GET /api/assessments/{id}/next-steps`, `backend/app/guide.py`)
A ladder instead of a score:
- **Now**: anything time-critical (emergency, mental-health line), and the doctor review he is waiting for.
- **In the next few weeks**: the level of care and why, the tests to ask about so the first visit answers the question, results to bring so nothing is repeated, sharing with the clinic, and his top habit changes, each with its evidence grade and path.
- **Over 3 months**: the 12-week plan and a re-check (sperm take about 74 days to develop).
- **Please don't**: stop a prescribed medicine on his own; start testosterone, steroids, SARMs or "fertility boosters" (they lower his own sperm production); act on one home test or one result.
- **Get help sooner if**: the red flags from the evidence graph (sudden pain or swelling, a new lump, blood in semen, painful swelling with fever, thoughts of self-harm), each with where to go.

### Ask about your summary (`POST /api/assessments/{id}/ask`)
A private question box on the result page. It is **deterministic and grounded**: answers are assembled only from his own summary, the evidence graph and fixed clinician-written safety text, with the evidence grade and studies shown. Nothing he types is stored (only the type of question is counted) or sent to an outside AI service, so it cannot invent a diagnosis, a dose or a probability.

Three guardrails run before anything else:
1. **Urgent symptoms** (pain, swelling, lump, blood, self-harm, hopelessness): urgent help only (998, 800-HOPE).
2. **Medicines, doses, supplements, steroid cycles**: no advice; the one safe fact (testosterone lowers sperm production); a button that moves his question into a private message to a doctor.
3. **"Am I infertile? What are my chances?"**: screening is not a prediction, no percentages, what the summary does show, and which test actually answers the question.

### The companion follows his specialist after the visit
Once the specialist records the visit, the companion stops giving pre-visit advice. **Now** leads with the specialist's own plan, the tests still to do and the follow-up date, with a note that the specialist's advice comes first. "What did the specialist find?" (in Arabic or English) answers from the visit summary, including which ordered tests are still outstanding. The guardrails still run first, so "what dose of clomid after my visit?" is still redirected to his doctor.

Tests: `backend/tests/test_feedback_features.py::test_companion_guardrails`, `test_companion_grounded_answers`, `test_safe_next_steps`, `backend/tests/test_connected_care.py::test_companion_follows_the_specialist`.

---

## 2. Connected referral journey

One pathway per check, the same for the man, his doctor and the coordinator (`backend/app/pathway.py`):

**check → doctor review → clinic chosen → appointment confirmed → specialist visit → visit summary and plan → follow-up → re-check (about 3 months)**

Each stage is *done*, *current* (with the one thing that happens next), *upcoming*, *not needed* (e.g. no clinic for a self-care plan) or *stopped* (with the barrier he gave).

What closes each gap:
- **Doctor review**: every specialist referral is approved, changed (reason required) or rejected (reason required) by a licensed doctor; he gets a private message either way.
- **Clinic and appointment (Care Connect)**: he picks a verified clinic that offers the care his referral needs and his preferred times; a coordinator confirms the slot with the clinic; he gets a calendar entry that says only "Appointment". If the clinic declines, he is told why and chooses again; the handover code is withdrawn.
- **Specialist visit**: he or the clinic marks it attended; if he couldn't go, the reason is recorded and he can choose another time immediately.
- **Visit summary and plan** (new): the specialist records, in plain words, what was found, the tests ordered, the plan and when to come back (`POST /api/clinician/cases/{id}/consultation`). He sees it in his journey; the follow-up gets its own discreet calendar entry ("Follow-up").
- **The receiving clinic is connected too** (new, `/clinic.html`): the specialist opens the referral with the handover code he gave them, with no Riaya account. They see the referral letter, the results he chose to share (so tests aren't repeated), his appointment and his preferences, with a banner listing what he chose not to share. From the same page they mark attendance, send the visit summary back and message him privately. Access lasts up to 12 hours and ends at once if he withdraws the code or pauses sharing. Every opening appears in his access log as "The clinic opened your referral".
- **Tests the specialist ordered are tracked**: each one becomes a checklist item in his journey. Saving a matching result (semen analysis, testosterone, FSH, LH, HbA1c, vitamin D) ticks it off automatically; anything else (e.g. an ultrasound) he ticks himself. When all are done, the referral moves to "tests done" without anyone chasing.
- **Getting ready for the visit**: once a clinic is chosen, a checklist built from his own summary: the results to bring so nothing is repeated, every medicine and gym product he takes, how to prepare for a semen analysis (2–7 days' abstinence, tell the lab about a recent fever; WHO 2021) or a morning testosterone test (Endocrine Society 2018), questions about his own top drivers, and his choices at the visit (a male doctor, Arabic, what the clinic sees).
- **Automatic reminders**: every hour, Riaya sends one short private message for any stage that has waited longer than its threshold, and one when the re-check is due. It is never repeated for the same stage, never sent if he turned reminders off or paused sharing, and never by SMS or phone. The coordinator board marks who has already been reminded and can run the check on demand.
- **Visit experience**: after a visit he can rate respect, privacy and how clearly things were explained, and whether he would recommend the clinic. The programme dashboard shows these per clinic only once 5 or more men have rated it, so clinics improve on what matters to men without any single rating being identifiable.
- **Follow-up and re-check**: he marks the follow-up done; a re-check is suggested at about 3 months, and the journey shows what changed between checks.
- **Coordinator board** (new, clinician console → *Pathway*): how many men are at each stage, and who has **stalled** longer than a threshold (e.g. approved but no clinic after 7 days, appointment passed with no outcome), with a one-click **private nudge** in his messages, never an SMS or a call.
- **Programme view**: the k-anonymised dashboard shows the funnel from first tap to a clinician, time to care against the usual 12+ months, and fairness by group.

Tests: `test_full_pathway_to_follow_up`, `test_self_care_pathway_skips_clinic`, `test_coordinator_board_and_nudge`, the Care Connect tests in `test_companion_care.py`, and `test_connected_care.py::test_clinic_portal_closes_the_loop`, `test_ordered_tests_tick_off_from_results`, `test_clinic_letter_lists_results_he_saved`.

---

## 3. User-controlled privacy and consent-based sharing

Already in place: no name, phone or ID; per-purpose consent he can withdraw; encryption at rest; a hide button and blur in the app switcher; one-time share codes; export and delete everything; a recovery code instead of an account.

New in the **Privacy & sharing** screen (`backend/app/sharing.py`):
- **Who sees what**: a grid of recipients (the Riaya review doctor, the clinic he chooses) against parts of his record (summary, questionnaire answers, device data, lab results, 12-week plan). The summary always travels with a referral, because a referral is unsafe without it; everything else is his choice. The default for a clinic is summary and lab results only.
- **Applied everywhere, at once**: the clinician case view, explanations, lab review and plan review are filtered on every request, so withdrawing applies even to a handover code he has already given. The clinician sees a banner listing what he chose not to share.
- **Active share codes**: every live code, whether it has been opened, when it expires, and a button to withdraw it.
- **Who opened my record**: an access log of every time someone on the care side opened his summary, his lab results or acted on his case.
- **Consent receipts**: a record of every permission given, declined, changed or withdrawn (doctor review, device data, research, each share code, the clinic, his wife's link), downloadable as a file and included in "Download my data".
- Withdrawing doctor review removes his checks from every doctor's view, including pending reviews and share codes.
- **Pause all sharing** (one switch): no doctor, coordinator board or clinic can open his record, and codes he has given stop working, until he turns it back on. His appointments stay booked. Pausing and resuming each leave a receipt.
- **Second-opinion codes**: besides the clinic handover, he can make a code for any other doctor, choosing exactly which parts it shows (e.g. summary and answers, no lab results) and for how long (1, 3 or 7 days). It opens view-only on the clinic page; that doctor cannot record a visit. Each code is listed with who it is for and what it shows, and can be withdrawn at once.
- **Reminders are his choice**: one switch turns the automatic reminders off; the change leaves a consent receipt.
- **How long his data is kept**: until he deletes it, or 3, 6, 12 or 24 months after his last visit to the app. When the time passes, everything is erased exactly as if he had pressed Delete. The screen shows the date it will happen.
- The handover letter in the console and in the clinic portal is built from the filtered record, so withheld answers (e.g. questionnaire scores) don't leak through the letter.

Tests: `test_sharing_controls_what_the_clinic_sees`, `test_doctor_scope_and_receipts_and_access_log`, `test_consent_withdrawal_removes_doctor_access`, `test_connected_care.py::test_clinic_sees_only_what_he_shares`, `test_pause_all_sharing`, `test_retention_choice_erases_after_inactivity`.

---

## Going further: prescriptive, predictive, human in the loop, measured

- **Prescriptive: your best changes.** Every change he could make is ranked by its expected effect on his signals (a counterfactual through the evidence graph) × strength of evidence ÷ effort, with a concrete first step and how long it takes to show. The best three are chosen together, because in the graph they reinforce each other (in the sample, 34% together against 12% added separately). Only things he can do himself are listed; medical conditions go to a doctor (`backend/app/prescribe.py`).
- **Predictive: 12-week projection.** Week by week, how his signals could move with no change, half adherence or full adherence, with milestones (week 3 energy and sleep, week 11 new sperm at about 74 days, week 12 re-check). Interactive, and labelled as signals, never a chance of pregnancy.
- **Predictive, for the care team: dropout early warning.** Points from published predictors of missed care (prior missed visit, reported barrier, low mood, long wait, stalled stage, no personal follow-up), each shown with its source. It becomes a fitted model once the pilot has real outcomes; we didn't train one on simulated attendance, which would only learn our assumptions.
- **Human in the loop.** Doctors agree or disagree with each explained finding; disagreeing needs a reason. Verdicts are audited, appear in his access log, and are aggregated per finding.
- **Our own model, honestly evaluated.** Riaya-Net is pre-trained on our simulated cohort and fine-tuned on real data (`docs/RIAYA_NET.md`). On 100 real men it is not better than simpler models (AUC 0.59 against 0.65 and 0.68, wide overlapping intervals), and we say so. It is the pipeline for pilot data and a clinician-only second opinion.
- **Privacy you can see.** "See exactly what they'll see" previews the referral letter word for word for the doctor or clinic, updates live as he changes what to share, and carries his own questions. Tested to be identical to what the clinic receives.
- **Measured, not claimed.** `validation/SCENARIOS.md`: red flags escalated 5/5; unsupported companion claims 0/78; adversarial questions caught 30/30; consent and revocation checks 15/15; referral packages valid 6/6. Internal tests, with their limits stated.

## How to see it

1. Start the app (README → *Run it*), open http://localhost:8000 and choose **See a sample check, filled in**, then **See his summary now**.
2. On the summary: **Your safe next steps** and **Ask about your summary** (try "What dose of clomid should I take?" or "Am I infertile?").
3. **My journey** shows the pathway; **Privacy** shows who sees what, codes, access log and receipts.
4. In the clinician console (`/clinician.html`, demo login), approve the case; back in the app choose a clinic; confirm it under **Appointments**; mark it attended; record the **Specialist visit outcome** in the case; open the **Pathway** tab.
5. Or play the receiving clinic: open `/clinic.html`, enter the handover code shown in his **Book your visit** screen, mark him attended and send a visit summary with tests ordered. Back in the app, **My journey** shows the summary and the test checklist, and the summary page's next steps now follow the specialist's plan.
6. In **Privacy**, press **Pause all sharing**, then reload the clinic page: access has ended.
