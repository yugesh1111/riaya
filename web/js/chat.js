/* "Talk it through": the quick check as a conversation. Same answer schema and backend as the detailed form. */
const C = {
  en: { voice: "Voice", send: "Send", typeHere: "Type or tap the mic…", listening: "Listening…", notUnderstood: "Sorry, I didn't catch that. You can also tap an option.",
        micNote: "Your browser's speech service turns speech into text; only the text answer is saved.", noMic: "Voice input isn't available in this browser — type or tap instead.",
        working: "Preparing your summary…", full: "See my full summary", more: "Add more detail (devices, tests)", voices: { auto: "Default voice" },
        start: "Start with voice", startText: "Start without voice", handsFree: "Hands-free", private: "Private mode (speech stays on this phone)",
        loading: p => `Preparing on-phone speech model ${p}%…`, heardNothing: "I didn't hear anything. Tap the mic and speak, or type your answer.", switching: "This browser's speech service isn't available, so Riaya is using on-phone speech instead. The first time takes a moment to prepare.", editHint: "Not quite right? Correct the words in the box and press Send.", thinking: "Understanding…", micDenied: "Microphone access was blocked. Allow it in your browser settings, or type instead.",
        noVoiceLang: "This phone has no Arabic voice installed, so questions are shown as text.",
        pickLang: "Which language would you like to talk in?", accent: "Accent", hear: "Hear this voice", natural: "natural",
        lead: "Talk it through. About three minutes, no name, no number.", q: (i, n) => `Question ${i} of ${n}`,
        orb: { idle: "", speaking: "Riaya is speaking", listening: "Listening", thinking: "Understanding" },
        sample: "Hello. I'm Riaya. I'll ask a few quick questions, and you can answer by talking.",
        bestVoice: v => `Voice: ${v}`, installTip: "For the most natural voice on iPhone or Mac: Settings › Accessibility › Spoken Content › Voices, and download a Premium voice." },
  ar: { voice: "الصوت", send: "إرسال", typeHere: "اكتب أو اضغط على الميكروفون…", listening: "أستمع إليك…", notUnderstood: "عذراً، لم أفهم. يمكنك أيضاً اختيار أحد الخيارات.",
        micNote: "تحوّل خدمة المتصفح الكلام إلى نص؛ ويُحفظ نص الإجابة فقط.", noMic: "الإدخال الصوتي غير متاح في هذا المتصفح — اكتب أو اختر بدلاً من ذلك.",
        working: "جارٍ إعداد ملخصك…", full: "اعرض ملخصي الكامل", more: "أضف تفاصيل أكثر (الأجهزة، الفحوصات)", voices: { auto: "الصوت الافتراضي" },
        start: "ابدأ بالصوت", startText: "ابدأ بدون صوت", handsFree: "بدون استخدام اليدين", private: "الوضع الخاص (يبقى الكلام على هذا الهاتف)",
        loading: p => `جارٍ تجهيز نموذج الكلام على الهاتف ${p}٪…`, heardNothing: "لم أسمع شيئاً. اضغط على الميكروفون وتحدّث، أو اكتب إجابتك.", switching: "خدمة الكلام في هذا المتصفح غير متاحة، لذا تستخدم رعاية التعرّف على الكلام داخل الهاتف. يستغرق التجهيز لحظة في المرة الأولى.", editHint: "ليس صحيحاً تماماً؟ صحّح الكلمات في المربع واضغط إرسال.", thinking: "جارٍ الفهم…", micDenied: "تم حظر الميكروفون. اسمح به من إعدادات المتصفح، أو اكتب بدلاً من ذلك.",
        noVoiceLang: "لا يوجد صوت عربي مثبت على هذا الهاتف، لذا تظهر الأسئلة كنص.",
        pickLang: "بأي لغة تحب أن نتحدث؟", accent: "اللهجة", hear: "اسمع هذا الصوت", natural: "طبيعي",
        lead: "تحدّث معنا. نحو ثلاث دقائق، بلا اسم ولا رقم.", q: (i, n) => `السؤال ${i} من ${n}`,
        orb: { idle: "", speaking: "رعاية تتحدث", listening: "أستمع إليك", thinking: "جارٍ الفهم" },
        sample: "مرحباً، أنا رعاية. سأطرح عليك أسئلة سريعة، ويمكنك الإجابة بصوتك.",
        bestVoice: v => `الصوت: ${v}`, installTip: "لأكثر صوت طبيعي على آيفون أو ماك: الإعدادات › تسهيلات الاستخدام › المحتوى المنطوق › الأصوات، ونزّل صوتاً مميزاً (Premium)." },
};
const o = (value, en, ar, keys = []) => ({ value, en, ar, keys: [en, ar, ...keys] });
const YN = [o("yes", "Yes", "نعم"), o("no", "No", "لا")];
const YNU = [...YN, o("unsure", "Not sure", "لست متأكداً")];
const SKIPO = o("skip", "Prefer not to say", "أفضّل عدم الإجابة");

const STEPS = [
  { id: "consent_core", type: "yesno", en: "Hi, I'm Riaya. I'll ask about 14 quick questions about everyday habits that affect energy, hormones and your future family.\nNo name or phone number, and nothing is shared unless you choose.\nShall we start?",
    ar: "مرحباً، أنا رعاية. سأطرح عليك نحو ١٤ سؤالاً سريعاً عن عادات يومية تؤثر في طاقتك وهرموناتك ومستقبل عائلتك.\nبلا اسم ولا رقم هاتف، ولا يُشارك شيء إلا باختيارك.\nهل نبدأ؟", opts: YN },
  { id: "consent_review", type: "yesno", en: "If something needs a doctor, may a licensed doctor review your summary? You can say no and still get it.",
    ar: "إذا احتاج الأمر إلى طبيب، هل تسمح لطبيب مرخّص بمراجعة ملخصك؟ يمكنك الرفض وستحصل على ملخصك أيضاً.", opts: YN },
  { id: "age", type: "number", min: 18, max: 80, en: "How old are you?", ar: "كم عمرك؟" },
  { id: "height_cm", type: "number", min: 130, max: 220, skippable: true, en: "Your height in centimetres? (say skip if you don't know)", ar: "طولك بالسنتيمتر؟ (قل تخطي إن كنت لا تعرف)" },
  { id: "weight_kg", type: "number", min: 40, max: 250, skippable: true, en: "And your weight in kilograms?", ar: "ووزنك بالكيلوغرام؟" },
  { id: "reason", type: "choice", en: "What brings you here?", ar: "ما الذي جاء بك؟", multi: true,
    opts: [o("general", "General check", "فحص عام", ["health", "صحة", "عام"]), o("future", "Planning ahead", "تخطيط للمستقبل", ["future", "later", "مستقبل", "زواج", "marriage"]),
           o("trying", "Trying for a child now", "نحاول الإنجاب الآن", ["trying", "baby", "child", "pregnan", "نحاول", "حمل", "طفل", "انجاب"]),
           o("fitness", "Energy / fitness", "الطاقة / اللياقة", ["gym", "energy", "fitness", "نادي", "طاقة", "رياضة"])] },
  { id: "months_trying", type: "number", months: true, min: 0, max: 240, when: a => (a.reason || []).includes("trying"),
    en: "How long have you been trying? Months or years are both fine.", ar: "منذ متى وأنتم تحاولون؟ بالأشهر أو بالسنوات." },
  { id: "smoking", type: "choice", en: "Do you smoke cigarettes or vape?", ar: "هل تدخن السجائر أو السجائر الإلكترونية؟",
    opts: [o("never", "Never", "لا", ["no", "never", "ابدا", "ما ادخن", "لا ادخن"]), o("former", "I stopped", "أقلعت", ["quit", "stopped", "used to", "تركت", "اقلعت", "كنت"]),
           o("occasional", "Sometimes", "أحياناً", ["sometimes", "occasionally", "social", "احيانا", "مرات"]), o("daily", "Daily", "يومياً", ["daily", "every day", "yes", "يوميا", "كل يوم", "نعم", "اي"])] },
  { id: "waterpipe", type: "choice", en: "Shisha, midwakh or dokha?", ar: "الشيشة أو المدواخ أو الدوخة؟",
    opts: [o("never", "Never", "أبداً", ["no", "never", "لا", "ابدا"]), o("monthly", "Now and then", "أحياناً", ["sometimes", "month", "احيانا", "شهر"]),
           o("weekly", "Weekly", "أسبوعياً", ["week", "weekend", "اسبوع", "ويكند"]), o("daily", "Daily", "يومياً", ["daily", "every day", "يوميا", "كل يوم"])] },
  { id: "aas", type: "choice", sensitive: true,
    en: "Gym question, no judgement: have you used testosterone, steroids or SARMs? It's one of the most common, and most reversible, reasons for low sperm production.",
    ar: "سؤال عن النادي بلا أحكام: هل استخدمت التستوستيرون أو المنشطات أو SARMs؟ هذا من أكثر الأسباب شيوعاً لانخفاض إنتاج الحيوانات المنوية، وغالباً ما يكون قابلاً للعكس.",
    opts: [o("never", "Never", "أبداً", ["no", "never", "لا", "ابدا"]), o("past_old", "Over a year ago", "قبل أكثر من سنة", ["years ago", "long ago", "سنين", "زمان"]),
           o("past_recent", "In the last year", "خلال السنة الماضية", ["last year", "recently", "months ago", "مؤخرا", "السنة"]),
           o("current", "Currently", "حالياً", ["now", "currently", "cycle", "on a", "الحين", "حاليا", "الان", "كورس"]), SKIPO] },
  { id: "sitting_h", type: "number", min: 0, max: 20, en: "On a normal day, how many hours do you sit — desk, car and sofa together?", ar: "في يوم عادي، كم ساعة تجلس — المكتب والسيارة والأريكة معاً؟" },
  { id: "sleep_h", type: "number", min: 2, max: 14, en: "How many hours do you actually sleep on a typical night?", ar: "كم ساعة تنام فعلياً في ليلة عادية؟" },
  { id: "snore", type: "yesno", en: "Do you snore loudly, or has anyone noticed you stop breathing in your sleep?", ar: "هل تشخر بصوت عالٍ، أو لاحظ أحد أنك تتوقف عن التنفس أثناء النوم؟", opts: YNU,
    set: (a, v) => { a.snore = v; if (v === "yes") a.observed = "unsure"; } },
  { id: "tired", type: "yesno", en: "Do you often feel sleepy during the day?", ar: "هل تشعر غالباً بالنعاس خلال النهار؟", opts: YN },
  { id: "underwear", type: "choice", en: "Usual underwear: loose like boxers or sirwal, or tight like briefs?", ar: "ملابسك الداخلية عادةً: فضفاضة مثل البوكسر أو السروال، أم ضيقة؟",
    opts: [o("loose", "Loose", "فضفاضة", ["boxer", "sirwal", "wizar", "بوكسر", "سروال", "وزار", "واسع"]), o("mixed", "Mix", "مختلطة", ["both", "mix", "الاثنين", "مختلف"]),
           o("tight", "Tight", "ضيقة", ["brief", "tight", "compression", "سليب", "ضيق"])] },
  { id: "hot_bath", type: "choice", en: "Sauna, jacuzzi or very hot baths?", ar: "الساونا أو الجاكوزي أو الحمامات الساخنة جداً؟",
    opts: [o(0, "Rarely", "نادراً", ["no", "never", "rarely", "لا", "نادرا", "ابدا"]), o(1, "About weekly", "أسبوعياً", ["week", "اسبوع"]),
           o(2, "Several times a week", "عدة مرات أسبوعياً", ["often", "several", "daily", "every day", "كثير", "يوميا"])] },
  { id: "phq1", type: "choice", en: "In the last two weeks, how often have you had little interest or pleasure in things?", ar: "خلال الأسبوعين الماضيين، كم مرة شعرت بقلة الاهتمام أو المتعة؟",
    opts: [o(0, "Not at all", "إطلاقاً", ["no", "never", "not at all", "none", "لا", "ابدا", "ولا مره", "ماشي"]),
           o(1, "Some days", "بعض الأيام", ["some", "sometimes", "several days", "a few days", "few days", "احيانا", "بعض الايام", "كم يوم", "يومين"]),
           o(2, "More than half the days", "أكثر من نصف الأيام", ["often", "most", "half", "more than half", "كثير", "واجد", "اغلب", "نص", "اكثر من النص"]),
           o(3, "Nearly every day", "تقريباً كل يوم", ["every day", "nearly every day", "always", "all the time", "daily", "يوميا", "كل يوم", "طول الوقت", "دايم", "دائما"])] },
  { id: "phq2", type: "choice", en: "And feeling down or hopeless?", ar: "والشعور بالإحباط أو اليأس؟",
    opts: [o(0, "Not at all", "إطلاقاً", ["no", "never", "not at all", "none", "لا", "ابدا", "ولا مره", "ماشي"]),
           o(1, "Some days", "بعض الأيام", ["some", "sometimes", "several days", "a few days", "few days", "احيانا", "بعض الايام", "كم يوم", "يومين"]),
           o(2, "More than half the days", "أكثر من نصف الأيام", ["often", "most", "half", "more than half", "كثير", "واجد", "اغلب", "نص", "اكثر من النص"]),
           o(3, "Nearly every day", "تقريباً كل يوم", ["every day", "nearly every day", "always", "all the time", "daily", "يوميا", "كل يوم", "طول الوقت", "دايم", "دائما"])] },
  { id: "rf_any", type: "yesno", en: "Last one. Right now, do you have sudden testicle pain or swelling, a new lump, blood in your semen, or thoughts of harming yourself?",
    ar: "آخر سؤال. هل لديك الآن ألم أو تورم مفاجئ في الخصية، أو كتلة جديدة، أو دم في السائل المنوي، أو أفكار لإيذاء نفسك؟", opts: YN },
  { id: "red_flags", type: "choice", multi: true, when: a => a.rf_any === "yes", en: "Which one? Tap all that apply.", ar: "أيّها؟ اختر كل ما ينطبق.",
    opts: [o("rf_torsion", "Sudden pain or swelling", "ألم أو تورم مفاجئ", ["pain", "swelling", "الم", "ورم"]), o("rf_lump", "A new lump", "كتلة جديدة", ["lump", "كتلة", "حبة"]),
           o("rf_hematospermia", "Blood in semen", "دم في السائل المنوي", ["blood", "دم"]), o("rf_mood", "Thoughts of self-harm", "أفكار لإيذاء النفس", ["harm", "hopeless", "ايذاء", "انتحار"])] },
];

let L = LANG, S = { answers: {}, step: 0, aid: null, multi: [] }, voices = [], rec = null;
const log = () => $("#log");
const CT = k => C[L][k];
const accentKey = () => store.get("accent_" + L) || Voice.ACCENTS[L][0].key;
const locale = () => (Voice.ACCENTS[L].find(a => a.key === accentKey()) || Voice.ACCENTS[L][0]).locale;

/* The voice orb shows what Riaya is doing: speaking, listening or understanding. */
function orb(state) {
  const o = $("#orb");
  if (!o) return;
  o.dataset.state = state;
  $("#orbLabel").textContent = CT("orb")[state] || "";
}

function speak(text, then) {
  if (!$("#voiceOn").checked) { then && then(); return; }
  Voice.speak(text, { lang: L, locale: locale(), voiceName: $("#voice").value, onstart: () => orb("speaking"),
                      onend: () => { orb("idle"); then && then(); } });
}

function loadVoices() {
  voices = Voice.voicesFor(L, locale());
  const saved = store.get("voice_" + L);
  $("#voice").innerHTML = `<option value="">${CT("voices").auto}${voices[0] ? ` (${esc(voices[0].name)})` : ""}</option>` +
    voices.map(v => `<option value="${esc(v.name)}" ${v.name === saved ? "selected" : ""}>${esc(v.name)}${v._natural ? ` · ${CT("natural")}` : ""}</option>`).join("");
  $("#voiceNote").textContent = window.speechSynthesis && speechSynthesis.getVoices().length && !voices.length && L === "ar" ? CT("noVoiceLang")
    : voices.length && !voices[0]._natural ? CT("installTip") : "";
}

function bubble(text, who) {
  const d = document.createElement("div");
  d.className = "bubble " + who;
  d.textContent = text;
  log().appendChild(d);
  requestAnimationFrame(() => d.classList.add("in"));
  d.scrollIntoView({ behavior: "smooth", block: "end" });
  return d;
}

/* Riaya "types" for a moment before each message, like a person would. */
function botSay(text) {
  return new Promise(res => {
    const d = bubble("", "bot typing");
    d.innerHTML = `<span class="dots" aria-label="…"><i></i><i></i><i></i></span>`;
    setTimeout(() => { d.classList.remove("typing"); d.textContent = text; d.scrollIntoView({ behavior: "smooth", block: "end" }); res(d); },
               Math.min(900, 280 + text.length * 4));
  });
}

function progress() {
  const live = STEPS.filter(q => !q.when || q.when(S.answers));
  const idx = live.indexOf(STEPS[S.step]);
  const n = live.length, i = Math.max(0, idx) + 1;
  $("#prog").style.width = `${Math.round(100 * (i - 1) / n)}%`;
  $("#progLabel").textContent = S.step < STEPS.length ? CT("q")(i, n) : "";
}

function current() {
  while (S.step < STEPS.length && STEPS[S.step].when && !STEPS[S.step].when(S.answers)) S.step++;
  return STEPS[S.step];
}

async function ask() {
  const q = current();
  if (!q) return finish();
  progress();
  await botSay(q[L]);
  speak(q[L], () => { if (handsFree() && !S.finished) startListening(); });
  S.multi = [];
  const opts = q.opts || (q.skippable ? [SKIPO] : []);
  $("#chips").innerHTML = opts.map((x, i) => `<span class="opt" role="button" tabindex="0" style="--d:${i * 40}ms" data-i="${i}">${esc(x[L])}</span>`).join("") +
    (q.multi ? `<span class="opt" id="done" style="border-color:var(--brand)">✓</span>` : "");
  $$("#chips .opt[data-i]").forEach(el => el.onclick = () => {
    const x = opts[+el.dataset.i];
    if (q.multi && x.value !== "skip") { el.classList.toggle("on"); S.multi = $$("#chips .opt.on").map(e => opts[+e.dataset.i].value); return; }
    answer(x.value, x[L]);
  });
  if ($("#done")) $("#done").onclick = () => S.multi.length && answer(S.multi, S.multi.map(v => opts.find(x => x.value === v)[L]).join("، "));
  $("#text").focus();
}

function interpret(q, text) {
  if (window.NLU) NLU.lastFuzzy = false;
  if (q.type === "number") {
    if (NLU.yesNo(text, false) === "skip") return "skip";
    const n = q.months ? NLU.months(text) : NLU.number(text);
    return n != null && n >= q.min && n <= q.max ? n : null;
  }
  if (q.type === "yesno") return NLU.yesNo(text, (q.opts || []).some(x => x.value === "unsure"));
  if (q.multi) {
    const hits = q.opts.filter(x => NLU.choice(text, [x]) != null).map(x => x.value);
    return hits.length ? hits : null;
  }
  return NLU.choice(text, q.opts);
}

function onText(text, spoken) {
  const q = current();
  if (!q || !text.trim()) return;
  const v = interpret(q, text);
  if (v == null) {
    bubble(text, "me"); botSay(CT("notUnderstood"));
    if (spoken) { $("#text").value = text; $("#micNote").textContent = CT("editHint"); }
    speak(CT("notUnderstood"), () => handsFree() && startListening());
    return;
  }
  answer(v, text);
}

/* What Riaya understood, shown under his words, so a misheard answer is easy to spot and undo. */
function understood(q, v) {
  if (v === "skip") return L === "ar" ? "تخطٍّ" : "skipped";
  if (q.opts) {
    const vals = Array.isArray(v) ? v : [v];
    const labels = vals.map(x => (q.opts.find(o => o.value === x) || {})[L]).filter(Boolean);
    if (labels.length) return labels.join(L === "ar" ? "، " : ", ");
  }
  if (q.type === "number") return q.months ? (L === "ar" ? `${v} شهراً` : `${v} months`) : String(v);
  return null;
}

let lastAnswer = null;
async function undo() {
  if (!lastAnswer || S.finished) return;
  const { step, answers } = lastAnswer;
  lastAnswer = null; $("#undo").hidden = true;
  S.answers = answers; S.step = step;
  if (S.aid) { const clean = { ...S.answers }; delete clean.rf_any; API.put(`/api/assessments/${S.aid}/answers`, { answers: clean }).catch(() => {}); }
  Voice.stopSpeaking();
  await botSay(L === "ar" ? "لا بأس، لنُعد هذا السؤال." : "No problem, let's redo that one.");
  ask();
}

async function answer(v, shown) {
  const q = current();
  const me = bubble(shown, "me");
  const u = understood(q, v);
  if (u && String(u).trim() !== String(shown).trim()) {
    const tag = document.createElement("small");
    tag.className = "und"; tag.textContent = `✓ ${u}${window.NLU && NLU.lastFuzzy ? (L === "ar" ? " (تقريباً)" : " (best guess)") : ""}`;
    me.appendChild(tag);
  }
  if (window.NLU) NLU.lastFuzzy = false;
  if (!q.id.startsWith("consent")) { lastAnswer = { step: S.step, answers: JSON.parse(JSON.stringify(S.answers)) }; $("#undo").hidden = false; }
  $("#chips").innerHTML = "";
  if (q.id === "consent_core") {
    if (v !== "yes") { bubble(L === "ar" ? "لا بأس. يمكنك العودة في أي وقت." : "No problem. You can come back any time.", "bot"); return; }
  } else if (q.id === "consent_review") {
    if (!API.token) { API.token = (await API.post("/api/session", { lang: L })).token; store.set("token", API.token); }
    const carried = store.get("passive_aid");
    await API.post("/api/consent", { core: true, clinician_review: v === "yes", wearables: !!carried, research: false });
    if (carried) { S.aid = carried; store.del("passive_aid"); }
    else S.aid = (await API.post("/api/assessments?channel=chat")).id;
    store.set("aid", S.aid); store.del("done");
  } else if (q.set) q.set(S.answers, v);
  else if (q.id === "rf_any") S.answers.rf_any = v;
  else if (v !== "skip") S.answers[q.id] = v;
  if (S.aid && !q.id.startsWith("consent")) {
    const clean = { ...S.answers }; delete clean.rf_any;
    store.set("draft", JSON.stringify(clean));
    API.put(`/api/assessments/${S.aid}/answers`, { answers: clean }).catch(() => {});
  }
  S.step++;
  setTimeout(ask, 350);
}

async function finish() {
  S.finished = true;
  $("#undo").hidden = true;
  $("#chips").innerHTML = "";
  $("#prog").style.width = "100%"; $("#progLabel").textContent = "";
  await botSay(CT("working"));
  const clean = { ...S.answers }; delete clean.rf_any;
  await API.put(`/api/assessments/${S.aid}/answers`, { answers: clean });
  await API.post(`/api/assessments/${S.aid}/submit?lang=${L}`);
  const r = await API.get(`/api/assessments/${S.aid}/result?lang=${L}`);
  store.set("done", "1");
  const lines = [r.disclaimer, "", r.summary, r.next_step];
  if (r.plan.length) lines.push("", (L === "ar" ? "أهم فرصك:" : "Your top opportunities:"), ...r.plan.map((p, i) => `${i + 1}. ${p.action}`));
  await botSay(lines.join("\n"));
  speak([r.summary, r.next_step, ...r.plan.map(p => p.action)].join(". "));
  $("#chips").innerHTML = `<a class="btn" href="index.html">${CT("full")}</a> <a class="btn ghost" href="index.html#more">${CT("more")}</a>`;
}

const handsFree = () => $("#handsFree").checked;

/* Demo mode (chat.html?demo=en or ?demo=ar), for recording the product video and for judges without a microphone.
   Each answer is a recorded clip of a man speaking. It is played aloud and recognised by the same on-phone Whisper
   model that serves private mode, so the understanding shown is real; nothing is typed for him.
   If the speech model cannot load (offline), the clip's script is used and the bubble says so. */
const DEMO = (() => { const d = new URLSearchParams(location.search).get("demo"); return d === "ar" || d === "en" ? d : null; })();
const demo = { i: 0, lines: null, ready: null };
const demoSize = () => (new URLSearchParams(location.search).get("model") || (L === "ar" ? "small" : "base"));
async function demoListen() {
  const q = current();
  if (!q || S.finished) return;
  if (!demo.lines) demo.lines = await (await fetch(`demo/${DEMO}/lines.json`)).json();
  const n = String(++demo.i).padStart(2, "0");
  const blob = await (await fetch(`demo/${DEMO}/${n}.m4a`)).blob();
  const audio = new Audio(URL.createObjectURL(blob));
  micState("listening"); $("#mic").classList.add("live");
  const heard = Promise.race([Voice.transcribe(blob, L, null, demoSize()).catch(() => null), new Promise(r => setTimeout(() => r(null), 30000))]);
  await new Promise(res => { audio.onended = res; audio.onerror = res; audio.play().catch(res); });
  micState("thinking");
  let text = await heard;
  let scripted = false;
  // if the model mishears a clip, use its script rather than derail the demo, and say so on screen
  const want = JSON.stringify(interpret(q, demo.lines[demo.i - 1]));
  if (!text || JSON.stringify(interpret(q, text)) !== want) { demo.misheard = text; text = demo.lines[demo.i - 1]; scripted = true; }
  else demo.misheard = null;
  $("#text").value = "";
  micState("idle");
  onText(text, true);
  $("#micNote").textContent = scripted ? (L === "ar" ? `وضع العرض: لم يُفهم المقطع${demo.misheard ? ` («${demo.misheard}»)` : ""}، فاستُخدم نص الإجابة.` : `Demo mode: the clip wasn't understood${demo.misheard ? ` ("${demo.misheard}")` : ""}, so its script was used.`) : "";
}
let listening = null, quietTries = 0, browserASRDown = false;

function micState(st, pct) {
  $("#mic").classList.toggle("live", st === "listening");
  orb(st === "loading" ? "thinking" : st);
  $("#text").placeholder = st === "listening" ? CT("listening") : st === "thinking" ? CT("thinking") : st === "loading" ? CT("loading")(pct || 0) : CT("typeHere");
}

async function startListening() {
  if (DEMO) return demoListen();
  if (listening || !(Voice.hasBrowserASR || Voice.canRecord)) return;
  Voice.stopSpeaking();
  const box = $("#text");
  const usePrivate = $("#private").checked || browserASRDown || !Voice.hasBrowserASR;
  const h = Voice.listen({ lang: L, locale: locale(), privateMode: usePrivate, onState: micState, onPartial: t => { box.value = t; } });
  listening = h;
  try {
    const alts = await h.result;
    const q = current();
    box.value = "";
    if (alts.length && q) { quietTries = 0; onText(alts.find(a => interpret(q, a) != null) || alts[0], true); }
    else if (q) {
      // heard nothing: say so, and in hands-free mode try once more before waiting for a tap
      $("#micNote").textContent = CT("heardNothing");
      if (handsFree() && ++quietTries < 2) setTimeout(startListening, 600);
    }
  } catch (e) {
    const m = String(e.message || e);
    if (/not-allowed|denied|permission/i.test(m) && !/service-not-allowed/i.test(m)) { $("#micNote").textContent = CT("micDenied"); $("#handsFree").checked = false; }
    else if (Voice.SERVICE_DOWN.test(m) && !browserASRDown && Voice.canRecord) {
      // the browser's speech service doesn't work here (Brave, some Android browsers): switch to on-phone speech and try again
      browserASRDown = true; $("#private").checked = true;
      $("#micNote").textContent = CT("switching");
      listening = null; micState("idle");
      return startListening();
    }
    else if (!/no-speech|aborted/i.test(m)) $("#micNote").textContent = m;
  } finally { listening = null; micState("idle"); }
}

function setupMic() {
  const ok = Voice.hasBrowserASR || Voice.canRecord;
  $("#micNote").textContent = ok ? CT("micNote") : CT("noMic");
  $("#mic").disabled = !ok; $("#mic").style.opacity = ok ? 1 : .4;
  $("#private").disabled = !Voice.canRecord;
  $("#mic").onclick = () => listening ? listening.stop() : startListening();
}

function chrome() {
  applyLang();
  $("#brand").textContent = t("app"); $("#langBtn").textContent = t("lang");
  $("#lblVoice").textContent = CT("voice"); $("#send").textContent = CT("send"); $("#text").placeholder = CT("typeHere");
  $("#lblHands").textContent = CT("handsFree"); $("#lblPrivate").textContent = CT("private");
  $("#undo").textContent = L === "ar" ? "↶ تراجع" : "↶ Undo";
  loadVoices(); setupMic();
}

$("#langBtn").onclick = () => { L = LANG = L === "ar" ? "en" : "ar"; store.set("lang", L); chrome(); log().innerHTML = ""; S = { answers: {}, step: 0, aid: null, multi: [] };
  if (S.started) ask(); else startPad(); };
$("#voice").onchange = e => store.set("voice_" + L, e.target.value);
$("#undo").onclick = undo;
$("#send").onclick = () => { onText($("#text").value); $("#text").value = ""; };
$("#text").onkeydown = e => { if (e.key === "Enter") { onText(e.target.value); e.target.value = ""; } };
if (window.speechSynthesis) speechSynthesis.onvoiceschanged = loadVoices;
API.token = store.get("token");
$("#private").checked = store.get("private_voice") === "1";
$("#private").onchange = e => store.set("private_voice", e.target.checked ? "1" : "0");
chrome();
/* Start: he picks the language and accent, can hear the voice first, then starts by voice or by typing.
   One tap is needed before phones allow audio; it also decides voice on/off. */
function startPad() {
  if (DEMO && L !== DEMO) { L = LANG = DEMO; store.set("lang", L); chrome(); }
  if (DEMO && !demo.ready) demo.ready = Voice.loadWhisper(p => { if (p && p.status === "progress" && $("#demoNote")) $("#demoNote").textContent = CT("loading")(Math.round(p.progress || 0)); }, demoSize())
    .then(() => { if ($("#demoNote")) $("#demoNote").textContent = L === "ar" ? "جاهز: إجابات مسجلة تُفهم على الهاتف" : "Ready: recorded answers, understood on the phone"; }).catch(() => {});
  const accents = Voice.ACCENTS[L];
  $("#log").innerHTML = `<div class="startpad">
    <div class="orb big" id="orbStart" data-state="idle" aria-hidden="true"><i></i><i></i><i></i></div>
    <p class="lead" style="text-align:center;margin:0">${esc(CT("lead"))}</p>
    <p class="small muted" style="text-align:center;margin:8px 0 0">${esc(CT("pickLang"))}</p>
    <div class="langpick" role="radiogroup" aria-label="${esc(CT("pickLang"))}">
      <button class="langcard ${L === "ar" ? "on" : ""}" role="radio" aria-checked="${L === "ar"}" data-l="ar"><b lang="ar">العربية</b><span>Arabic</span></button>
      <button class="langcard ${L === "en" ? "on" : ""}" role="radio" aria-checked="${L === "en"}" data-l="en"><b>English</b><span lang="ar">الإنجليزية</span></button>
    </div>
    <p class="small muted" style="margin:4px 0 0">${esc(CT("accent"))}</p>
    <div class="opts accents" role="radiogroup" aria-label="${esc(CT("accent"))}">${accents.map(a => `<span class="opt ${a.key === accentKey() ? "on" : ""}" role="radio" tabindex="0" aria-checked="${a.key === accentKey()}" data-a="${a.key}">${esc(a[L])}</span>`).join("")}</div>
    <button class="chip" id="hear">▶ ${esc(CT("hear"))}</button>
    <p class="small muted" id="voiceName" style="text-align:center;margin:0"></p>
    <button class="btn" id="startVoice">${esc(CT("start"))}</button><button class="btn ghost" id="startText">${esc(CT("startText"))}</button>
    ${DEMO ? `<p class="small muted" style="text-align:center" id="demoNote">${L === "ar" ? "وضع العرض" : "Demo mode"}</p>` : ""}</div>`;
  const showVoice = () => { const v = Voice.voicesFor(L, locale())[0]; $("#voiceName").textContent = v ? CT("bestVoice")(v.name) : ""; };
  showVoice();
  $$(".langcard").forEach(b => b.onclick = () => { if (b.dataset.l !== L) { L = LANG = b.dataset.l; store.set("lang", L); chrome(); startPad(); } });
  $$(".accents .opt").forEach(o => {
    const pickIt = () => { store.set("accent_" + L, o.dataset.a); store.del("voice_" + L); loadVoices(); startPad(); };
    o.onclick = pickIt;
  });
  $("#hear").onclick = () => {
    const so = $("#orbStart");
    $("#voiceOn").checked = true;
    Voice.speak(CT("sample"), { lang: L, locale: locale(), voiceName: $("#voice").value, onstart: () => so.dataset.state = "speaking", onend: () => so.dataset.state = "idle" });
  };
  const begin = voice => { S.started = true; $("#voiceOn").checked = voice; $("#handsFree").checked = voice && (DEMO || Voice.hasBrowserASR || Voice.canRecord);
    $("#log").innerHTML = ""; $("#dock").hidden = false; ask(); };
  $("#startVoice").onclick = () => begin(true);
  $("#startText").onclick = () => begin(false);
  $("#dock").hidden = true;
}
startPad();
