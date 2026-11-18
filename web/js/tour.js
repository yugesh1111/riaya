/* Guided tour of a sample check, plus gentle screen transitions everywhere.

   The tour plays the sample man's check like a short film: it taps his answers, adds his watch data, reveals
   his summary, asks the companion two questions (one of them a medicine question, to show the guardrail),
   then walks through his care pathway and privacy controls. Every step can be paused, skipped or replayed,
   with buttons, arrow keys or the space bar. Nothing here is real data; the sample is clearly labelled.
   With "reduce motion" switched on in the phone's settings, it still works, without the animation. */
(function () {
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const TT = {
    en: {
      play: "Play", pause: "Pause", next: "Next", back: "Back", exit: "Exit tour", of: (a, b) => `${a} of ${b}`,
      steps: {
        answers: ["His answers", "A 34-year-old man who smokes, sleeps about 6 hours and sits most of the day. Short questions, validated scales, and he can skip anything. No name, no number."],
        more: ["Every part of his life that matters", "Sleep, stress, heat, history and his preferences, like a male doctor and contact only through the app. Watch the answers fill in."],
        watch: ["His watch, if he wants", "He adds an Apple Health export. Riaya reads sleep, steps and heart data on the server, keeps only the summary and throws the file away."],
        result: ["One clear next step", "Not a score or a diagnosis: the right level of care, and that a licensed doctor checks any referral before it is final. The dial shows signals in words, never a number."],
        best: ["His best changes, ranked", "Each change scored by expected effect, strength of evidence and effort. Switch one on and the 12-week projection redraws. Together they do more than the sum of their parts."],
        explain: ["Why, in plain words", "Each finding shows what was seen, the cause-and-effect path, the strength of the research (A to D) and its limits."],
        steps: ["Safe next steps", "What to do now, in the next weeks and over 3 months, what not to do, and when to get help sooner."],
        ask: ["Ask about his summary", "Answers come only from his own summary and the evidence map. Watch what happens with a medicine question."],
        journey: ["From check to specialist and back", "Eight stages: doctor review, clinic, appointment, visit, the specialist's summary, follow-up and a re-check at 3 months."],
        privacy: ["He decides who sees what", "Pause all sharing with one switch, choose what the doctor and clinic see, see who opened his record, and set when it is deleted."],
        end: ["That's Riaya", "A private front door to men's reproductive health, in Arabic and English, by voice, chat, form or WhatsApp."],
      },
      q1: "Why do I need to see a doctor?", q2: "What dose of clomid should I take?",
      own: "Start my own check", replay: "Replay", explore: "Explore the sample",
    },
    ar: {
      play: "تشغيل", pause: "إيقاف مؤقت", next: "التالي", back: "السابق", exit: "إنهاء الجولة", of: (a, b) => `${a} من ${b}`,
      steps: {
        answers: ["إجاباته", "رجل عمره ٣٤ عاماً يدخّن وينام نحو ٦ ساعات ويجلس معظم اليوم. أسئلة قصيرة ومقاييس معتمدة، ويمكنه تخطي أي شيء. بلا اسم ولا رقم."],
        more: ["كل ما يهم في حياته", "النوم والتوتر والحرارة والتاريخ الصحي وتفضيلاته، مثل طبيب رجل والتواصل عبر التطبيق فقط. شاهد الإجابات تمتلئ."],
        watch: ["ساعته، إن أراد", "يضيف ملف Apple Health. تقرأ رعاية النوم والخطوات وبيانات القلب، وتحتفظ بالملخص فقط وتحذف الملف."],
        result: ["خطوة تالية واضحة", "ليست درجة ولا تشخيصاً: مستوى الرعاية المناسب، ويراجع طبيب مرخّص أي إحالة قبل اعتمادها. المؤشر يُعرض بالكلمات لا بالأرقام."],
        best: ["أفضل تغييراته، مرتبة", "كل تغيير مقيّم بأثره المتوقع وقوة الدليل والجهد. فعّل أحدها فيُعاد رسم توقع الأسابيع الاثني عشر. معاً تفعل أكثر من مجموعها."],
        explain: ["لماذا، بكلمات بسيطة", "كل نتيجة تُظهر ما رأيناه، ومسار السبب والنتيجة، وقوة الدليل (A إلى D)، وحدوده."],
        steps: ["خطوات تالية آمنة", "ما يفعله الآن وخلال الأسابيع والأشهر الثلاثة، وما لا يفعله، ومتى يطلب المساعدة أسرع."],
        ask: ["اسأل عن ملخصه", "الإجابات من ملخصه وخريطة الأدلة فقط. لاحظ ما يحدث مع سؤال عن دواء."],
        journey: ["من الفحص إلى المختص والعودة", "ثماني مراحل: مراجعة الطبيب، العيادة، الموعد، الزيارة، ملخص المختص، المتابعة، وفحص بعد ٣ أشهر."],
        privacy: ["هو من يقرر من يرى ماذا", "يوقف كل المشاركة بمفتاح واحد، ويختار ما يراه الطبيب والعيادة، ويرى من فتح سجله، ويحدد متى يُحذف."],
        end: ["هذه رعاية", "باب خاص لصحة الرجل الإنجابية، بالعربية والإنجليزية، بالصوت أو المحادثة أو النموذج أو واتساب."],
      },
      q1: "لماذا أحتاج إلى طبيب؟", q2: "ما جرعة الكلوميد التي آخذها؟",
      own: "ابدأ فحصي", replay: "أعد الجولة", explore: "استكشف المثال",
    },
  };
  const tt = () => TT[LANG === "ar" ? "ar" : "en"];

  /* ---------------------------------------------------------------- styles */
  const css = document.createElement("style");
  css.textContent = `
    @media (prefers-reduced-motion: no-preference) {
      #view.v-in > * { animation: v-rise .5s cubic-bezier(.2,.75,.25,1) both; }
      ${[2, 3, 4, 5, 6, 7, 8].map(n => `#view.v-in > *:nth-child(${n}) { animation-delay: ${(n - 1) * 55}ms; }`).join("\n")}
      #companion > .card, #explain > *, #sharing > .card, #prep > .card, #vfb > .card { animation: v-rise .5s cubic-bezier(.2,.75,.25,1) both; }
      #sharing > .card:nth-child(2) { animation-delay: 60ms; } #sharing > .card:nth-child(3) { animation-delay: 120ms; }
      .pathway li { animation: v-pop .4s cubic-bezier(.2,.75,.25,1) both; }
      ${[2, 3, 4, 5, 6, 7, 8].map(n => `.pathway li:nth-child(${n}) { animation-delay: ${(n - 1) * 70}ms; }`).join("\n")}
      .ask-q, .ask-a { animation: v-rise .35s ease both; }
      .progress div { transition: width .6s cubic-bezier(.2,.75,.25,1); }
    }
    @keyframes v-rise { from { opacity: .35; transform: translateY(12px); } to { opacity: 1; transform: none; } }
    @keyframes v-pop { from { opacity: 0; transform: translateX(-6px); } to { opacity: 1; transform: none; } }
    [dir=rtl] .pathway li { animation-name: v-rise; }
    .tour-spot { position: fixed; z-index: 90; border-radius: 16px; pointer-events: none; box-shadow: 0 0 0 9999px rgba(8, 20, 28, .52);
      outline: 2px solid var(--saffron); outline-offset: 3px; transition: top .45s cubic-bezier(.2,.75,.25,1), left .45s cubic-bezier(.2,.75,.25,1), width .45s cubic-bezier(.2,.75,.25,1), height .45s cubic-bezier(.2,.75,.25,1), opacity .3s; }
    .tour-spot.off { opacity: 0; }
    .tour-sheet { position: fixed; z-index: 95; inset-inline: 16px; bottom: 16px; margin: 0 auto; max-width: 560px; background: var(--surface, #fff); color: var(--ink);
      border-radius: 20px; padding: 18px 20px 14px; box-shadow: 0 18px 60px rgba(0,0,0,.28); transition: transform .35s cubic-bezier(.2,.75,.25,1), opacity .35s; }
    .tour-sheet.hide { transform: translateY(24px); opacity: 0; }
    .tour-sheet .k { color: var(--muted); font-size: 13px; display: flex; gap: 8px; align-items: center; }
    .tour-sheet h3 { margin: 6px 0 4px; font-size: 19px; }
    .tour-sheet p { margin: 0 0 12px; line-height: 1.55; }
    .tour-bar { height: 3px; background: var(--line); border-radius: 3px; overflow: hidden; margin: 0 0 12px; }
    .tour-bar i { display: block; height: 100%; width: 0; background: var(--saffron); }
    .tour-dots { display: flex; gap: 5px; flex-wrap: wrap; }
    .tour-dots b { width: 7px; height: 7px; border-radius: 50%; background: var(--line); cursor: pointer; transition: background .2s, transform .2s; }
    .tour-dots b.on { background: var(--saffron); transform: scale(1.35); }
    .tour-dots b.done { background: var(--good); }
    .tour-ctl { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .tour-ctl .spacer { flex: 1; }
    .tour-tap { position: relative; }
    @media (prefers-reduced-motion: no-preference) {
      .tour-tap::after { content: ""; position: absolute; inset: -4px; border-radius: inherit; border: 2px solid var(--saffron); animation: tap-ring .6s ease-out both; pointer-events: none; }
      @keyframes tap-ring { from { opacity: 1; transform: scale(.92); } to { opacity: 0; transform: scale(1.12); } }
    }
    .tour-end { text-align: center; padding: 28px 18px; }
    .tour-end .row { justify-content: center; }
    body.touring .demo-banner { display: none; }
    @media (max-width: 680px) { .tour-sheet { inset-inline: 8px; bottom: 8px; padding: 14px 16px 12px; } .tour-sheet h3 { font-size: 17px; } }`;
  document.head.appendChild(css);

  /* ---------------------------------------------------------------- screen transitions everywhere */
  const viewEl = document.getElementById("view");
  if (viewEl && !REDUCED) {
    new MutationObserver(() => {
      viewEl.classList.remove("v-in");
      void viewEl.offsetWidth;  // restart the animation
      viewEl.classList.add("v-in");
    }).observe(viewEl, { childList: true });
  }

  /* ---------------------------------------------------------------- tour engine */
  class Cancelled extends Error {}
  const T = { on: false, i: 0, paused: false, run: 0, dwell: 0, auto: true };
  let spot, sheet, raf;

  const sleep = ms => new Promise((resolve, reject) => {
    const my = T.run;
    let left = REDUCED ? Math.min(ms, 250) : ms, last = performance.now();
    const tick = () => {
      const now = performance.now();
      if (my !== T.run) return reject(new Cancelled());
      if (!T.paused) left -= now - last;
      last = now;
      left <= 0 ? resolve() : setTimeout(tick, Math.min(60, Math.max(10, left)));
    };
    setTimeout(tick, Math.min(60, left));
  });
  const until = async (fn, ms = 8000) => { const t0 = Date.now(); while (!fn()) { if (Date.now() - t0 > ms) return null; await sleep(120); } return fn(); };

  function focus(el) {
    if (!spot) return;
    T.target = el || null;
    if (!el) { spot.classList.add("off"); return; }
    spot.classList.remove("off");
    const place = smooth => {
      if (T.target !== el || !document.contains(el)) return;
      const r = el.getBoundingClientRect();
      const sheetH = sheet ? sheet.getBoundingClientRect().height + 24 : 0;
      if (r.top < 70 || r.top > innerHeight - sheetH - 60) {
        scrollTo({ top: scrollY + r.top - Math.max(80, (innerHeight - sheetH - Math.min(r.height, innerHeight * .5)) / 2), behavior: smooth && !REDUCED ? "smooth" : "auto" });
      }
    };
    place(true);
    setTimeout(() => place(false), 900);  // if anything interrupted the smooth scroll, land on it anyway
  }
  function track() {
    if (spot && T.target && document.contains(T.target)) {
      const r = T.target.getBoundingClientRect();
      Object.assign(spot.style, { top: r.top - 6 + "px", left: r.left - 6 + "px", width: r.width + 12 + "px", height: Math.min(r.height + 12, innerHeight * .62) + "px" });
    }
    raf = requestAnimationFrame(track);
  }
  async function tap(el, wait = 520) {
    if (!el) return;
    el.classList.remove("tour-tap"); void el.offsetWidth; el.classList.add("tour-tap");
    await sleep(wait);
  }
  /* Types into a field on screen only. It never fires input events, so the sample's saved answers can't be
     left half-typed if the tour is skipped or stopped mid-word. */
  async function type(input, text, per = 55) {
    input.focus({ preventScroll: true });
    try {
      input.value = "";
      for (const ch of text) { input.value += ch; await sleep(REDUCED ? 0 : per); }
    } finally { input.value = text; }
  }
  async function playAnswers(speed) {
    const box = document.getElementById("qs");
    if (!box) return;
    for (const el of box.querySelectorAll('.opt.on, input[data-q]')) {
      if (el.tagName === "INPUT") {
        if (el.value === "") continue;
        const v = el.value; el.scrollIntoView({ block: "nearest" }); await type(el, v, speed / 6);
      } else await tap(el, speed);
    }
  }
  const sample = () => (T.sampling = T.sampling || startSample());
  const ARABIC_DIGITS = s => LANG === "ar" ? String(s).replace(/\d/g, d => "٠١٢٣٤٥٦٧٨٩"[d]) : s;

  const STEPS = [
    { key: "answers", async go() { await sample(); }, target: () => document.getElementById("qs"),
      async play() { await sleep(700); await playAnswers(380); } },
    { key: "more", async go() { }, target: () => document.getElementById("qs"),
      async play() {
        const n = S.schema.sections.length;
        for (let k = 1; k < n; k++) {
          S.section = k; intake(); S.sample = true;
          focus(document.getElementById("qs"));
          await sleep(350); await playAnswers(150); await sleep(250);
        }
      } },
    { key: "watch", async go() { await devices(); }, target: () => document.querySelector("#f")?.closest(".card") || document.querySelector("#view .card"),
      async play() {
        const f = document.getElementById("f");
        if (!f) return;
        await sleep(900);
        const blob = await (await fetch("samples/apple_health_sample.zip")).blob();
        const dt = new DataTransfer(); dt.items.add(new File([blob], "export.zip", { type: "application/zip" }));
        f.files = dt.files; f.dispatchEvent(new Event("change"));
        await until(() => (document.getElementById("fs")?.innerText || "").length > 3, 15000);
        focus(document.getElementById("fs")?.closest(".card")); await sleep(2200);
      } },
    { key: "result", async go() { await submit(); await until(() => document.querySelector("#view .sum-hero")); }, target: () => document.querySelector("#view .sum-hero"),
      async play() { await sleep(2600); focus(document.getElementById("facts")); await sleep(2400); } },
    { key: "best", async go() { window.showPanel && showPanel("plan"); await until(() => document.querySelector("#forecast .card")); }, target: () => document.querySelector("#forecast .card"),
      async play() {
        await sleep(2400);
        const rows = [...document.querySelectorAll("#forecast input[data-node]")];
        const off = rows.find(i => !i.checked);
        if (off) { await tap(off.closest(".fc-row"), 400); off.click(); await sleep(2200); }
        focus(document.querySelector("#forecast .fc-chart")); await sleep(3600);
      } },
    { key: "explain", async go() { window.showPanel && showPanel("why"); }, target: () => document.getElementById("explain"),
      async play() { await until(() => document.getElementById("explain")?.children.length); focus(document.getElementById("explain").firstElementChild); await sleep(4200); } },
    { key: "steps", async go() { window.showPanel && showPanel("overview"); }, target: () => document.querySelector("#companion .card"),
      async play() { await until(() => document.querySelector("#companion .ladder")); focus(document.querySelector("#companion .card")); await sleep(4400); } },
    { key: "ask", async go() { window.showPanel && showPanel("ask"); }, target: () => document.getElementById("askCard"),
      async play() {
        const card = await until(() => document.getElementById("askIn"));
        if (!card) return;
        focus(document.getElementById("askCard"));
        for (const q of [tt().q1, tt().q2]) {
          await type(document.getElementById("askIn"), q, 45);
          await sleep(300);
          const before = document.querySelectorAll("#askLog .ask-a").length;
          document.getElementById("askForm").requestSubmit();
          await until(() => document.querySelectorAll("#askLog .ask-a").length > before);
          focus(document.getElementById("askCard"));
          await sleep(3800);
        }
      } },
    { key: "journey", async go() { await renderJourney(); await until(() => document.querySelector(".pathway")); }, target: () => document.querySelector(".pathway")?.closest(".card"),
      async play() { await sleep(4600); } },
    { key: "privacy", async go() { await renderPrivacy(); await until(() => document.querySelector("#sharing .card")); }, target: () => document.querySelector("#sharing .card"),
      async play() {
        await sleep(3000);
        const grid = document.querySelector("#sharing .share-grid")?.closest(".card");
        if (grid) { focus(grid); await sleep(3400); }
      } },
    { key: "end", async go() {
        view().innerHTML = `<div class="card tour-end"><h1>${tt().steps.end[0]}</h1><p class="lead">${tt().steps.end[1]}</p>
          <div class="row"><button class="btn" id="tOwn">${tt().own}</button><button class="btn ghost" id="tReplay">${tt().replay}</button><button class="btn ghost" id="tExplore">${tt().explore}</button></div></div>`;
        document.getElementById("tOwn").onclick = () => { stop(); ["aid", "draft", "done"].forEach(store.del); S.answers = {}; S.aid = null; consent(); };
        document.getElementById("tReplay").onclick = () => { stop(); start(); };
        document.getElementById("tExplore").onclick = () => { stop(); showResult(); };
      }, target: () => null, async play() { } },
  ];

  function drawSheet() {
    const s = STEPS[T.i], [title, text] = tt().steps[s.key];
    sheet.innerHTML = `<div class="tour-bar"><i id="tBar"></i></div>
      <div class="k"><span>${tt().of(ARABIC_DIGITS(T.i + 1), ARABIC_DIGITS(STEPS.length))}</span><span class="tour-dots">${STEPS.map((_, k) =>
        `<b class="${k === T.i ? "on" : k < T.i ? "done" : ""}" data-k="${k}" title="${esc(tt().steps[STEPS[k].key][0])}"></b>`).join("")}</span></div>
      <h3>${esc(title)}</h3><p>${esc(text)}</p>
      <div class="tour-ctl"><button class="chip" id="tBack" ${T.i ? "" : "disabled"}>${tt().back}</button>
        <button class="chip" id="tPlay" aria-pressed="${!T.paused}">${T.paused ? "▶ " + tt().play : "❚❚ " + tt().pause}</button>
        <button class="btn" id="tNext" style="min-height:40px;padding:8px 20px">${tt().next}</button><span class="spacer"></span>
        <button class="chip" id="tExit">${tt().exit}</button></div>`;
    sheet.querySelector("#tBack").onclick = () => goto(T.i - 1);
    sheet.querySelector("#tNext").onclick = () => goto(T.i + 1);
    sheet.querySelector("#tPlay").onclick = () => { T.paused = !T.paused; drawSheet(); };
    sheet.querySelector("#tExit").onclick = () => { stop(); };
    sheet.querySelectorAll(".tour-dots b").forEach(b => b.onclick = () => goto(Number(b.dataset.k)));
  }

  async function goto(k) {
    if (k < 0 || k >= STEPS.length) return;
    const my = ++T.run;
    T.i = k;
    const s = STEPS[k];
    sheet.classList.add("hide");
    drawSheet();
    try {
      if (k >= 1) await sample();  // jumping ahead: always the sample, never his own check
      if (k >= 4 && !S.result && s.key !== "result") { await submit(); await until(() => document.querySelector("#view .sum-hero")); }
      await s.go();
      if (my !== T.run) return;
      focus(s.target());
      sheet.classList.remove("hide");
      const bar = sheet.querySelector("#tBar"), t0 = performance.now();
      const fill = () => { if (my === T.run && bar) { bar.style.width = Math.min(100, (performance.now() - t0) / 120) + "%"; if (STEPS[T.i].key !== "end") requestAnimationFrame(fill); } };
      if (!REDUCED) requestAnimationFrame(fill);
      await s.play();
      if (bar) bar.style.width = "100%";
      if (s.key === "end") { focus(null); return; }
      await sleep(900);
      if (my === T.run) goto(k + 1);
    } catch (e) {
      if (!(e instanceof Cancelled)) { console.error(e); sheet.classList.remove("hide"); }
    }
  }

  function keys(e) {
    if (!T.on || /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) return;
    const fwd = LANG === "ar" ? "ArrowLeft" : "ArrowRight", bwd = LANG === "ar" ? "ArrowRight" : "ArrowLeft";
    if (e.key === fwd) goto(T.i + 1);
    else if (e.key === bwd) goto(T.i - 1);
    else if (e.key === " ") { e.preventDefault(); T.paused = !T.paused; drawSheet(); }
    else if (e.key === "Escape") stop();
  }

  function start() {
    if (T.on) stop();
    T.on = true; T.paused = false; T.sampling = null; S.result = null;
    document.body.classList.remove("landing");
    document.body.classList.add("touring");
    spot = Object.assign(document.createElement("div"), { className: "tour-spot off" });
    sheet = Object.assign(document.createElement("div"), { className: "tour-sheet hide" });
    sheet.setAttribute("role", "dialog"); sheet.setAttribute("aria-live", "polite"); sheet.setAttribute("aria-label", "Guided tour");
    document.body.append(spot, sheet);
    raf = requestAnimationFrame(track);
    addEventListener("keydown", keys);
    goto(0);
  }

  function stop() {
    T.on = false; T.run++;
    cancelAnimationFrame(raf);
    spot?.remove(); sheet?.remove(); spot = sheet = null;
    document.body.classList.remove("touring");
    removeEventListener("keydown", keys);
  }

  window.Tour = { start, stop, get state() { return { on: T.on, step: STEPS[T.i]?.key, i: T.i, paused: T.paused }; } };
})();
