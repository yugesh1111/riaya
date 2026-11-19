# Riaya demo video: narration to read

**Length:** the submission form says **keep it under 3 minutes**. Submit the 2:54 cut below. The full read (4:23) covers every feature and can go in the README as the long version.

## The 2:54 cut (for the submission)

The voice track is `voice/riaya-narration-en-short.m4a` (2:46, your own recording, retakes removed, re-recorded words spliced in). It isn't committed, because it is your voice. Put an 8-second silent title card in front of it, which makes 2:54 in total.

| Video time | Voice says | On screen |
|---|---|---|
| 0:00 | (no voice, soft music) | Title card: "In the UAE, a man's side of fertility is usually looked at last. Riaya: a private front door to men's reproductive health." Then slide 1 |
| 0:08 | "Riaya does five things…" | `17-feature-map` |
| 0:17 | "He can simply talk to it…" | `01-voice-check` |
| 0:35 | "And in Arabic…" | `02-arabic-accents` |
| 0:46 | "In about three minutes he gets a summary…" | `03-summary-explained` |
| 1:02 | "Then the part that's usually missing…" | `04-best-changes-projection` |
| 1:14 | "Many young men in the Gulf…" | `21-label-photo-check` |
| 1:29 | "When a doctor approves a referral…" | `13-privacy-controls`, then `14-doctor-and-closed-loop` |
| 1:53 | "Privacy here isn't a policy page…" | `20-first-time-setup` → `11-calculator-cover` → `12-native-locks` → `10-encrypted-vault` |
| 2:16 | "The health authority sees…" | `15-dashboard-and-impact` |
| 2:34 | "We tested Riaya end to end…" | `00-every-device.png`, then slide 14 |

Left out of the short cut: watch and heat, labs, the 12-week plan, and doctors. They appear in the slides and the README GIFs.

**How to read it:** calmly, at about 140 words a minute. Each block is one scene. "On screen" says what to show; most scenes have a ready screenshot in `docs/shots/`, or you can record the live screen.

**Before recording:**
- Use Microsoft Edge for the Arabic voice.
- Set the screen to phone size (390 × 844) for app scenes.
- Click inside the app before each take, because the privacy screen blurs it when the window loses focus.
- Run `validation/run_validation.py --seed-demo` so the dashboards have data.

## What to put on screen: clips and slides

Every scene has a ready clip in `docs/videos/` (full quality, .webm) or `docs/gifs/`, plus slides from `docs/Riaya_Submission.pptx` to cut in between.

| Scene | Clip | Slide to cut in |
|---|---|---|
| 0:00 The problem | `00-every-device.png` | Slide 1 (cover) |
| 0:20 What it is | `17-feature-map` | Slide 4 (architecture) |
| 0:35 Talk to it, English | `01-voice-check` | |
| 1:05 Arabic | `02-arabic-accents`, `18-arabic-first` | |
| 1:25 Summary | `03-summary-explained` | |
| 1:45 Best changes + projection | `04-best-changes-projection` | |
| 2:05 Gym product checker | `21-label-photo-check`, `05-gym-product-checker` | |
| 2:20 Watch + heat | `07-watch-first`, `06-uae-heat-guard` | |
| 2:35 Labs | `08-lab-forecast` | |
| 2:55 12-week companion | `09-twelve-week-plan` | Slide 7 (evidence) |
| 3:15 Referral loop | `13-privacy-controls` (letter preview), `14-doctor-and-closed-loop` | |
| 3:45 Privacy | `20-first-time-setup`, `11-calculator-cover`, `19-minimise-blur-relock`, `12-native-locks`, `10-encrypted-vault`, `16-privacy-map` | Slide 9 (risks and safeguards) |
| 4:15 Doctors | `14-doctor-and-closed-loop` | |
| 4:30 Health authority | `15-dashboard-and-impact` | Slide 6 (success measures), slide 11 (path to pilot) |
| 4:50 Close | `00-every-device.png` | Slide 14 (why Riaya stands out), slide 15 |

---

### 0:00 ★ The problem
**On screen:** dark title card, then `01-landing-en`
> In the UAE, a man's side of fertility is usually looked at last, often after a year or more of trying. Most men never talk about it, because it feels private, and it is. This is Riaya: a private front door to men's reproductive health, built for Abu Dhabi.

### 0:20 ★ What it is
**On screen:** `27-feature-map` (live `features.html`, it animates)
> Riaya does five things. He talks to it. It explains what it found. It shows what to change first. It connects him to the right specialist. And it follows up. Privacy wraps every step.

### 0:35 ★ Talk to it, in English
**On screen:** live `chat.html?demo=en` (or `04-voice-start-en` → `05-voice-understood-en`)
> He can simply talk to it. He chooses a language and an accent, and Riaya speaks with the most natural voice his phone has. He answers in his own words: "one seventy eight", "about a year and a half". Riaya understands, shows what it understood under each answer, and he can undo with one tap. No name, no phone number.

### 1:05 ★ And in Arabic
**On screen:** live `chat.html?demo=ar` (or `06-voice-start-ar`)
> And in Arabic, with an Emirati, Saudi, Egyptian or Levantine accent. "سنة ونص" becomes eighteen months. Speech can even be understood on the phone itself, so his voice never leaves it.

### 1:25 ★ A summary he can understand
**On screen:** `07-summary`, then `08-why-explained`
> In about three minutes he gets a summary, not a diagnosis. Every finding says what we saw, why it matters, how strong the evidence is, from A to D across 95 published sources, what helps, and its limits. If he types something urgent, like sudden pain, Riaya sends him straight to emergency care.

### 1:45 ★ What to change first, and what it could do
**On screen:** `09-best-changes-forecast` (live: switch changes on and off; the chart redraws)
> Then the part that's usually missing: what to do. Riaya ranks his best three changes by effect, evidence and effort, and projects how his signals could move over twelve weeks if he does nothing, half, or all of the plan.

### 2:05 Gym product checker
**On screen:** `10-gym-product-checker` (live: type "Ostarine")
> Many young men in the Gulf train hard, and some take boosters. He photographs the label. Riaya flags testosterone, steroids and SARMs, which can switch off sperm production, and explains why, with the evidence. The photo is read on his phone, and nothing is saved.

### 2:20 Watch first and the UAE heat guard
**On screen:** `13-watch-preview`, then `11-heat-guard`
> His watch can speak first: Apple Watch, Wear OS, Garmin or Fitbit. And because this is the UAE, Riaya checks today's heat in his emirate (his emirate, never his location) and turns it into one practical tip.

### 2:35 Lab reports that predict
**On screen:** `14-lab-dashboard-forecast`
> He scans a lab report page by page. Riaya reads it on the phone, keeps each lab's own reference range, reads his age, and files it by date. Then it projects where each result is heading at his next test, and warns before a value crosses the limit.

### 2:55 A twelve-week companion
**On screen:** `15-plan-who5-ramadan`
> Change takes about three months, because that is how long sperm take to develop. So Riaya stays with him for twelve weeks: weekly check-ins, a wellbeing score at day zero, thirty and eighty-four, a fresh start after a bad week, and a Ramadan mode that fits the fast.

### 3:15 ★ The referral loop
**On screen:** `12-care-sharing-preview`, then `30-clinic-portal`, then `23-coordinator-closed-loop`
> When a doctor approves a referral, he chooses a clinic and can call it or message it on WhatsApp in one tap. Before anything is shared, he sees the exact letter the clinic will read. The specialist opens it with a one-time code, records the visit, and sends the summary back. Every referral has a deadline set by its urgency; late ones escalate, and the status is published in FHIR, the standard hospital systems read.

### 3:45 ★ Privacy he can feel
*(Extra line for the minimise clip: "Switch apps and the screen blurs; come back and it's locked again.")*
**On screen:** `20-cover-choice` → `21-calculator-cover` → `18-lock-iphone` / `19-lock-android` → `16-vault` → `28-privacy-map`
> Privacy here isn't a policy page. At setup he chooses: a normal lock, or a cover. With the cover, anyone who opens Riaya sees a working calculator. His PIN and the equals sign open it. The lock looks native on iPhone and on Samsung. Reports live in an encrypted vault on his phone, and each one asks for Face ID again. Every time a doctor opens his record, he gets a message. And one switch pauses all sharing.

### 4:15 Doctors in the same app
**On screen:** `22-clinician-queue`, `24-doctor-vault`
> Doctors sign in from the same app, to their own locked console. They review every referral, agree or disagree with each finding, and keep shared documents in their own vault.

### 4:30 ★ For the health authority
**On screen:** `25-programme-dashboard`, then `26-impact-simulator` (live: move the slider)
> The health authority sees outcomes and fairness, never an individual; any group smaller than five is hidden. And this simulator shows what a rollout could change. Offered to twenty thousand men, about fourteen hundred more would reach a specialist each year, with every assumption visible and adjustable.

### 4:50 ★ Proof and close
**On screen:** README "Proof it works" table, then the Riaya icon
> We tested Riaya end to end ourselves, in Arabic and English, by voice and by typing: 79 automated tests, every red flag caught, every adversarial question stopped, and accessibility checked. It runs on iPhone, Android, Mac and WhatsApp. Riaya. Care that starts in private.

---

## Arabic narration (for the second audio track)

**0:00** في الإمارات، يُنظر إلى خصوبة الرجل في العادة آخر الأمر، وغالباً بعد سنة أو أكثر من المحاولة. ومعظم الرجال لا يتحدثون عنها لأنها أمر خاص. هذه «رعاية»: بوابة خاصة لصحة الرجل الإنجابية، صُمّمت لأبوظبي.

**0:20** تقوم رعاية بخمسة أشياء: يتحدث إليها، فتشرح ما وجدت، وتبيّن ما يُغيَّر أولاً، وتوصله بالمختص المناسب، وتتابع معه. والخصوصية تحيط بكل خطوة.

**0:35** يمكنه ببساطة أن يتحدث معها. يختار اللغة واللهجة، فتتحدث رعاية بأكثر صوت طبيعي على هاتفه. يجيب بكلماته، فتفهمه وتعرض ما فهمته تحت كل إجابة، ويمكنه التراجع بلمسة واحدة. بلا اسم ولا رقم هاتف.

**1:05** وبالعربية أيضاً، باللهجة الإماراتية أو السعودية أو المصرية أو الشامية. «سنة ونص» تُفهم ثمانية عشر شهراً، ويمكن فهم الكلام على الهاتف نفسه فلا يغادره صوته.

**1:25** في نحو ثلاث دقائق يحصل على ملخص، لا تشخيص. كل نتيجة تشرح ما رأيناه، ولماذا يهم، وقوة الدليل من 95 مصدراً منشوراً، وما يساعد، وحدود النتيجة. وإن كتب شيئاً عاجلاً كألم مفاجئ، توجهه رعاية فوراً إلى الطوارئ.

**1:45** ثم ما يغيب عادة: ماذا يفعل. ترتّب رعاية أفضل ثلاثة تغييرات له حسب الأثر والدليل والجهد، وتتوقع كيف قد تتغير مؤشراته خلال اثني عشر أسبوعاً.

**2:05** كثير من الشباب في الخليج يتمرنون بجد، وبعضهم يتناول «المعززات». يصوّر الملصق، فتنبّه رعاية إلى التستوستيرون والستيرويدات وSARMs التي قد توقف إنتاج الحيوانات المنوية، مع السبب والدليل. تُقرأ الصورة على هاتفه ولا يُحفظ شيء.

**2:20** يمكن لساعته أن تتحدث أولاً. ولأننا في الإمارات، تقرأ رعاية حرارة اليوم في إمارته، لا موقعه، وتحوّلها إلى نصيحة عملية واحدة.

**2:35** يمسح تقرير المختبر صفحة صفحة، فتقرؤه رعاية على الهاتف وتحفظه بتاريخه، ثم تتوقع اتجاه كل نتيجة في فحصه القادم وتنبّه قبل أن تتجاوز الحد.

**2:55** التغيير يحتاج نحو ثلاثة أشهر، لذا ترافقه رعاية اثني عشر أسبوعاً: متابعة أسبوعية، ومقياس للصحة النفسية في اليوم الأول والثلاثين والرابع والثمانين، وبداية جديدة بعد أسبوع صعب، ووضع خاص لرمضان.

**3:15** عندما يوافق الطبيب على الإحالة، يختار العيادة ويتصل بها أو يراسلها على واتساب بلمسة. وقبل المشاركة يرى الرسالة كما ستقرؤها العيادة حرفياً. يفتحها المختص برمز لمرة واحدة ويرسل ملخص الزيارة. ولكل إحالة مهلة حسب أولويتها، ويُصعَّد المتأخر منها.

**3:45** الخصوصية هنا ليست صفحة سياسات. عند الإعداد يختار: قفلاً عادياً أو غطاءً. مع الغطاء، من يفتح رعاية يرى آلة حاسبة تعمل، ورمزه مع علامة «=» يفتحها. القفل يبدو أصلياً على آيفون وسامسونج، والتقارير في خزنة مشفّرة على هاتفه، وكل مستند يطلب بصمة الوجه مجدداً. وكلما فتح طبيب سجله تصله رسالة، ومفتاح واحد يوقف كل المشاركة.

**4:15** يدخل الأطباء من التطبيق نفسه إلى بوابتهم المقفلة: يراجعون كل إحالة، ويوافقون أو يعترضون على كل نتيجة، ويحفظون المستندات في خزنتهم.

**4:30** ترى الجهة الصحية النتائج والعدالة، ولا ترى فرداً أبداً، وتُخفى كل مجموعة أصغر من خمسة. ويُظهر هذا المحاكي أثر التطبيق: لعشرين ألف رجل، يصل نحو ألف وأربعمئة رجل إضافي إلى المختص كل عام، مع كل افتراض ظاهر وقابل للتعديل.

**4:50** اختبرنا رعاية بأنفسنا من البداية إلى النهاية، بالعربية والإنجليزية، بالصوت والكتابة. تعمل على آيفون وأندرويد وماك وواتساب. «رعاية»: رعاية تبدأ بخصوصية.

---

## Napkin AI (if you prefer its graphics)

Napkin needs your own login. Paste each block into Napkin and pick a "columns" or "process" visual.

**Privacy, side by side**
```
On his phone: locked by default; calculator cover; encrypted vault with Face ID per document; privacy screen; on-phone speech and photo reading.
What may leave it: no identity; only values he confirms; WhatsApp carries codes only; calendar says "Appointment"; heat by emirate, not GPS.
Who sees what: choose per recipient; see the exact letter; one switch pauses all sharing; expiring codes; authority sees groups of 5+ only.
He is always told: access alerts; access log; consent receipts; every doctor action logged.
On the server: encrypted at rest; CSP and HSTS; brute-force limits; retention he chooses; export or delete everything.
```
**How Riaya works**
```
Talk (voice in Arabic or English, WhatsApp, watch, lab scan) → Understand (explained summary, evidence A–D, lab forecast) → Act (best 3 changes, 12-week plan, Ramadan mode) → Refer (doctor approves, call or WhatsApp the clinic, FHIR) → Follow up (visit summary back, WHO-5, re-check at 3 months)
```
