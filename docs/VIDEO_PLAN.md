# Riaya demo video: plan, line-up and voiceover scripts

**Goal:** in about 4 minutes, a judge should understand what Riaya is, see it working with real voice, and come away with a clear line-up of features and what they work with.

**Format:** 16:9, 1080p or higher. The app shown in a phone frame on a calm, dark background. Feature cards between scenes.

**Two audio tracks:** English and Arabic voiceovers of the same picture. On YouTube, open **Studio → Languages → Add language → Add audio** and upload the second track. Multi-language audio is not yet enabled on every channel. If it is missing on yours, upload two unlisted videos (EN and AR) and link both.

---

## Before recording: checklist

1. **Deploy** the latest version to Render. Record against the live URL or `localhost:8000`.
2. **Use Microsoft Edge for the Arabic voice demo.** Edge offers natural neural voices (for example "Microsoft Fatima Online (Natural) – Arabic (UAE)" and "Hamdan"), and Riaya picks them automatically.
   - On Safari or iPhone, download a Premium or Enhanced voice first: **Settings → Accessibility → Spoken Content → Voices → Arabic / English**.
   - The **"Hear this voice"** button on the start screen previews the voice.
3. **Run the voice demo once ahead of time** so the on-phone speech model (about 80 MB) is cached. The start screen says "Ready" when it is.
4. **Seed the demo data** so the coordinator board and dashboard have numbers: `python validation/run_validation.py --seed-demo`. Render does this on every deploy.
5. Turn on **Do Not Disturb**. Use the browser at 100% zoom. Use the phone frame size (**390 × 844**) for app scenes.
6. **The privacy screen blurs the app when the window loses focus.** Click inside the app before each take.

---

## How the voice demo works (scenes 3 and 4)

Open `chat.html?demo=en` (English) or `chat.html?demo=ar` (Arabic) and press **Start with voice**.

1. Riaya asks a question out loud.
2. A **recorded answer from a man** plays aloud. The files are `web/demo/en/*.m4a` and `web/demo/ar/*.m4a`, with the script in `lines.json`.
3. **Whisper, running on the phone, recognises the clip.** The understanding is real, and nothing is typed for him.
   - English uses Whisper base (about 80 MB), the same model as private mode.
   - Arabic uses Whisper small (about 250 MB), which is far better at Arabic. Base misheard several Gulf phrases in testing.
   - A recognised answer only counts if it means the same as the scripted line.
4. Riaya confirms and asks the next question, through all 19 steps to the summary.

If a clip is misheard, the app uses that clip's script and **says so on screen**, so the demo never fakes recognition silently. Before the final take, check the run has no such note.

**To use real voices instead of the generated ones:** record the 19 lines yourself, or ask a friend (an Emirati accent is ideal for the Arabic). Save them as `01.m4a` … `19.m4a` in `web/demo/<lang>/`. Keep the wording in `lines.json`, or update it to match.

**For a fully live take with your own voice:** open `chat.html` without `?demo`, choose the language and accent, and talk. In Chrome and Edge, Arabic recognition is done by the browser's speech service and is usually the most accurate option for Gulf Arabic.

**What we measured** (this Mac, generated voices):
- English demo: **19 of 19** clips recognised correctly by Whisper base, with no script used.
- Arabic with Whisper base: most clips misheard (for example "كل يوم" → "كليوم"). This is why Arabic uses Whisper small. Check the Arabic run for "wasn't understood" notes before the final take. If any remain, record those lines with a real voice.

### The man's lines (generated audio: English "Daniel", Arabic "Majed")

| # | Riaya asks | He answers (EN) | He answers (AR) | Understood as |
|---|---|---|---|---|
| 1 | Shall we start? | Yes, let's start. | نعم، يلا نبدأ | yes |
| 2 | May a doctor review your summary? | Yes, that's fine. | نعم، ما عندي مانع | yes |
| 3 | How old are you? | I'm thirty four. | عمري أربعة وثلاثين | 34 |
| 4 | Your height? | One seventy eight. | مية وثمانية وسبعين | 178 cm |
| 5 | Your weight? | About ninety two kilos. | اثنين وتسعين كيلو | 92 kg |
| 6 | What brings you here? | We're trying for a baby. | نحاول ننجب طفل | trying now |
| 7 | How long have you been trying? | About a year and a half. | سنة ونص | 18 months |
| 8 | Do you smoke? | Every day, about a pack. | كل يوم | daily |
| 9 | Shisha, midwakh or dokha? | Only on weekends. | بس في الويكند | weekly |
| 10 | Steroids or SARMs? | Never. | لا أبداً | never |
| 11 | Hours sitting a day? | About ten hours. | حوالي عشر ساعات | 10 |
| 12 | Hours of sleep? | Maybe six hours. | ست ساعات | 6 |
| 13 | Loud snoring? | Yes, my wife says I snore. | نعم، زوجتي تقول إني أشخر | yes |
| 14 | Sleepy in the day? | Yes, quite often. | نعم، كثير | yes |
| 15 | Underwear? | Tight ones, mostly. | ضيقة | tight |
| 16 | Sauna or jacuzzi? | Rarely. | نادراً | rarely |
| 17 | Little interest or pleasure? | Several days. | كم يوم | some days |
| 18 | Feeling down? | Not at all. | لا، أبداً | not at all |
| 19 | Any urgent symptoms? | No. | لا | no |

Every line was checked against the app's own language understanding. Five answers that were misread before have been fixed in the product:
- "thirty four." was read as 30
- "One seventy eight." as 170
- "a year and a half" as 12 months
- "No." was not understood
- "ما عندي مانع" was read as no

---

## How to describe testing in the video

Say what is true: **"We tested Riaya end to end ourselves, in Arabic and English, by voice and by typing."** All the parts are measured: 75 automated tests, scenario checks, an accessibility audit and a full voice run with 19 of 19 answers recognised. Don't call it a beta test with outside users unless outside users have actually tried it.

## Running order (about 4 minutes)

| Time | Scene | On screen | Smart-art / caption |
|---|---|---|---|
| 0:00 | **1. The problem** | Dark title cards | "Men in the UAE wait 12+ months before anyone looks at their side of fertility." · "Most never talk about it." |
| 0:12 | **2. What Riaya is** | Feature map (below) builds on screen | "A private, Arabic-first front door to men's reproductive health." |
| 0:30 | **3. Talk to it (English)** | `chat.html?demo=en`: the voice orb pulses, the man's answer plays, Riaya replies. Show 5–6 exchanges, then cut to the summary. | Caption: "Understood on the phone. No name. No number." |
| 1:05 | **4. Talk to it (Arabic)** | `chat.html?demo=ar`, Emirati accent: 4–5 exchanges, including "سنة ونص" → 18 months | Caption: "Emirati · Saudi · Egyptian · Levantine accents" |
| 1:30 | **5. Feature line-up**, 10–12 s each with a numbered card | | |
| | 5.1 Explained summary | Dial, biggest factor, "Why" tab with evidence grade | "Explains every finding, with the evidence behind it" |
| | 5.2 Prescriptive + predictive | Best 3 changes; toggle changes and watch the 12-week projection redraw | "What to change first, and what it could do in 12 weeks" |
| | 5.3 Watch first | Apple Health sample → findings → **watch preview** (Apple Watch, then the round Wear OS face) | "Apple Watch · Wear OS · Garmin · Fitbit" |
| | 5.4 Scan a lab report | Scan pages → values read → **lab dashboard**: trend, projected next value, early alert | "Scans, reads, files by date, predicts the next result" |
| | 5.5 12-week companion | WHO-5 check, "Why this works" (BCT codes), Ramadan mode card, fresh start | "Built on COM-B and behaviour-change science. Ramadan-aware." |
| | 5.6 Referral loop | Doctor approves in the console → he books → **Call / WhatsApp / Save contact** → clinic portal with handover code → visit summary → journey updates | "From first check to specialist, and back" |
| | 5.7 Closed loop | Coordinator board: early warning, escalations, FHIR Task status | "Time limits by urgency. FHIR R4 Task. Nobody gets lost." |
| | 5.8 Privacy | One switch pauses all sharing; "see exactly what they'll see" letter updating live; access log | "He decides who sees what. One switch stops it all." |
| | 5.8a Locked by default | Set a PIN after the summary → switch apps → come back: the lock screen, nothing readable; a wrong PIN shakes; Face ID opens it | "Picked up his phone by mistake? They see nothing." |
| | 5.8b The calculator | Home screen shows "Calculator" → do 12 + 30 = 42 → type the PIN, = → Riaya opens | "Hidden in plain sight" |
| | 5.8c Encrypted reports | Scanned report in "Reports saved on this phone": encrypted, opens only while unlocked | "Reports never leave his phone. AES-256." |
| | 5.8d Doctors too | "I'm a doctor" on the start screen → console with its own PIN | "One app. Patients and doctors." |
| | 5.9 For the health authority | Programme dashboard: funnel, fairness, **30+ day outcomes** | "k-anonymised. Groups under 5 hidden." |
| 3:30 | **6. Works with** | Logo-free icon row | "iPhone · Android · Apple Watch · Wear OS · Garmin · WhatsApp · FHIR R4 · Arabic + English" |
| 3:45 | **7. Close** | Riaya wordmark | "Riaya. Care that starts in private." |

### Feature map (scene 2)

Build it in Keynote or PowerPoint with SmartArt, using the app's colours: deep navy, saffron accent and off-white text.

```
                 ┌──────────── PRIVACY AROUND EVERYTHING ────────────┐
   TALK        →     UNDERSTAND     →     ACT        →     REFER       →    FOLLOW UP
 voice · chat      explained summary    best changes      doctor review      12-week plan
 WhatsApp          evidence map         12-week forecast  clinic · call      WHO-5 outcomes
 watch · labs      lab trends           companion         WhatsApp · FHIR    re-check
                 └── one switch pauses all sharing · he chooses who sees what ──┘
```

---

## Voiceover scripts

Read slowly. Each paragraph matches a scene.

### English

1. In the UAE, a man's side of fertility is usually looked at last: often after a year or more of trying. Most men never talk about it at all.
2. Riaya is a private, Arabic-first front door to men's reproductive health. No name, no phone number. It listens, explains, acts and follows through.
3. You can simply talk to it. Riaya asks; he answers in his own words; it understands on the phone and replies.
4. And in Arabic, with an Emirati, Saudi, Egyptian or Levantine accent. "A year and a half" in Gulf Arabic becomes eighteen months.
5. Then, feature by feature.
   - One: every finding is explained, with the strength of the evidence behind it.
   - Two: the three changes that matter most for him, and what they could do over twelve weeks.
   - Three: his watch speaks first: Apple Watch, Wear OS, Garmin or Fitbit.
   - Four: scan a lab report with the camera. Riaya reads it, files it by date, and projects where each result is heading.
   - Five: a twelve-week companion built on behaviour-change science, with a wellbeing check at day zero, thirty and eighty-four, and a Ramadan mode.
   - Six: when a doctor approves a referral, he books, calls or messages the clinic in one tap, and the specialist sends the visit summary back.
   - Seven: every referral has a time limit by urgency, with escalation and a FHIR status the hospital can follow.
   - Eight: he decides who sees what. One switch pauses all sharing.
   - Nine: the health authority sees outcomes and fairness, never individuals.
6. Riaya works on iPhone and Android, with Apple Watch, Wear OS and Garmin, on WhatsApp, in Arabic and English.
7. Riaya. Care that starts in private.

### Arabic (العربية)

١. في الإمارات، يُنظر إلى خصوبة الرجل في العادة آخر الأمر، وغالباً بعد سنة أو أكثر من المحاولة. ومعظم الرجال لا يتحدثون عنها أبداً.

٢. «رعاية» بوابة خاصة لصحة الرجل الإنجابية، بالعربية أولاً. بلا اسم ولا رقم هاتف. تستمع، وتشرح، وتقترح، وتتابع معك حتى النهاية.

٣. يمكنك ببساطة أن تتحدث معها. رعاية تسأل، وهو يجيب بكلماته، فتفهمه على الهاتف نفسه وتردّ عليه.

٤. وبالعربية أيضاً، باللهجة الإماراتية أو السعودية أو المصرية أو الشامية. «سنة ونص» تُفهم ثمانية عشر شهراً.

٥. ثم الميزات، واحدة تلو الأخرى:
   - أولاً: كل نتيجة مشروحة، مع قوة الدليل العلمي خلفها.
   - ثانياً: أهم ثلاثة تغييرات له، وما يمكن أن تحققه خلال اثني عشر أسبوعاً.
   - ثالثاً: ساعته تتحدث أولاً: Apple Watch أو Wear OS أو Garmin أو Fitbit.
   - رابعاً: يصوّر تقرير المختبر بالكاميرا، فتقرؤه رعاية وتحفظه بتاريخه وتتوقع اتجاه كل نتيجة.
   - خامساً: رفيق لاثني عشر أسبوعاً مبني على علم تغيير السلوك، مع فحص للصحة النفسية في اليوم الأول والثلاثين والرابع والثمانين، ووضع خاص لرمضان.
   - سادساً: عندما يوافق الطبيب على الإحالة، يحجز ويتصل بالعيادة أو يراسلها بلمسة واحدة، ويُرسل المختص ملخص الزيارة.
   - سابعاً: لكل إحالة مهلة حسب الأولوية، مع تصعيد وحالة FHIR يتابعها المستشفى.
   - ثامناً: هو من يقرر من يرى ماذا، ومفتاح واحد يوقف كل المشاركة.
   - تاسعاً: ترى الجهة الصحية النتائج والعدالة، ولا ترى الأفراد أبداً.

٦. تعمل رعاية على آيفون وأندرويد، ومع Apple Watch وWear OS وGarmin، وعلى واتساب، بالعربية والإنجليزية.

٧. رعاية. رعاية تبدأ بخصوصية.

### Recording the voiceover

- **Best quality:** a person reads it. A quiet room and a phone held 20 cm away is enough.
- **Generated voices:**
  - On macOS, download a Premium voice (Settings → Accessibility → Spoken Content → System voice → Manage Voices), then run `say -v "<voice>" -f script.txt -o vo.aiff`.
  - For Arabic, the neural voices in Microsoft Edge's Read Aloud (Hamdan or Fatima, Arabic UAE) sound the most natural of the free options.
