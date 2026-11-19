/* Two everyday guards on his summary and plan:
   1. Gym product checker: photo of a supplement / booster / injectable label (read on the phone) or typed ingredients ->
      stop / caution / ok, with why and the evidence. Nothing is stored.
   2. UAE heat guard: today's heat in his emirate (he picks the emirate; no location is used) and one practical tip. */
(function (root) {
  const T = {
    en: { pcT: "Check a gym product", pcSub: "Supplements, 'test boosters', pre-workouts, injectables. Take a photo of the ingredients, or type them. Read on your phone; nothing is saved.",
          photo: "📷 Photo of the label", type: "Or type the ingredients", typePh: "e.g. Ostarine MK-2866, zinc, tribulus", check: "Check", reading: "Reading the label…",
          levels: { stop: "STOP", caution: "CAUTION", ok: "OK" }, source: "Source", heatT: "Today's heat", emirate: "Emirate", feels: "feels like", uv: "UV",
          heatOff: "Today's forecast isn't available right now." },
    ar: { pcT: "افحص منتجاً رياضياً", pcSub: "مكملات، «معززات التستوستيرون»، منشطات ما قبل التمرين، الحقن. صوّر قائمة المكونات أو اكتبها. تُقرأ على هاتفك ولا يُحفظ شيء.",
          photo: "📷 صورة الملصق", type: "أو اكتب المكونات", typePh: "مثال: Ostarine MK-2866، زنك، تريبولوس", check: "افحص", reading: "جارٍ قراءة الملصق…",
          levels: { stop: "توقف", caution: "انتبه", ok: "مقبول" }, source: "المصدر", heatT: "حرارة اليوم", emirate: "الإمارة", feels: "المحسوسة", uv: "الأشعة",
          heatOff: "توقعات اليوم غير متاحة الآن." },
  };
  const Lg = () => (typeof LANG !== "undefined" && LANG === "ar" ? "ar" : "en");
  const x = k => T[Lg()][k];
  const e = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const TESS = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.0/dist/tesseract.min.js";
  const load = src => new Promise((ok, no) => { if ([...document.scripts].some(s => s.src === src)) return ok(); const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = no; document.head.appendChild(s); });

  function productCard() {
    return `<div class="card guard-pc" id="gPc"><h3>🧪 ${e(x("pcT"))}</h3><p class="small muted">${e(x("pcSub"))}</p>
      <p class="row"><label class="btn ghost" for="gPcFile" tabindex="0">${e(x("photo"))}</label><input type="file" id="gPcFile" accept="image/*" capture="environment" class="hidden"></p>
      <label class="small" for="gPcText">${e(x("type"))}</label>
      <div class="row" style="align-items:stretch"><input type="text" id="gPcText" placeholder="${e(x("typePh"))}" autocomplete="off" style="flex:1;min-width:180px"><button class="btn" id="gPcGo" type="button">${e(x("check"))}</button></div>
      <div id="gPcOut" class="small" role="status" aria-live="polite"></div></div>`;
  }
  function showResult(host, r) {
    const tag = l => `<span class="g-tag g-${l}">${e(x("levels")[l])}</span>`;
    host.innerHTML = `<div class="g-verdict g-${r.verdict || "none"}">${r.verdict ? tag(r.verdict) : ""}<b>${e(r.headline)}</b></div>
      ${r.findings.length ? `<ul class="g-list">${r.findings.map(f => `<li>${tag(f.level)} <b>${e(f.match)}</b>: ${e(f.why)} <span class="muted">${e(x("source"))}: ${e(f.source)}</span></li>`).join("")}</ul>` : ""}
      ${r.next.length ? `<ul>${r.next.map(n => `<li>${e(n)}</li>`).join("")}</ul>` : ""}<p class="muted">${e(r.note)}</p>`;
  }
  async function check(text, out) {
    try { showResult(out, await API.post(`/api/products/check?lang=${Lg()}`, { text })); } catch (err) { out.textContent = err.message; }
  }
  function wireProduct(host) {
    const out = host.querySelector("#gPcOut"), txt = host.querySelector("#gPcText");
    host.querySelector("#gPcGo").onclick = () => txt.value.trim() && check(txt.value, out);
    txt.onkeydown = ev => { if (ev.key === "Enter" && txt.value.trim()) check(txt.value, out); };
    host.querySelector("label[for=gPcFile]").onkeydown = ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); host.querySelector("#gPcFile").click(); } };
    host.querySelector("#gPcFile").onchange = async ev => {
      const f = ev.target.files[0]; if (!f) return;
      out.textContent = x("reading");
      try {
        await load(TESS);
        const img = root.Scan && root.Scan.enhance ? await root.Scan.enhance(f) : f;
        const { data } = await Tesseract.recognize(img, "eng+ara");
        txt.value = data.text.replace(/\s+/g, " ").trim().slice(0, 400);
        await check(data.text, out);
      } catch (err) { out.textContent = err.message || String(err); }
      ev.target.value = "";
    };
  }

  async function heatCard(host) {
    const key = (() => { try { return localStorage.getItem("riaya_emirate") || "abu_dhabi"; } catch { return "abu_dhabi"; } })();
    let h;
    try { h = await API.get(`/api/heat?emirate=${encodeURIComponent(key)}&lang=${Lg()}`); } catch { return; }
    const sel = `<label class="small">${e(x("emirate"))} <select id="gEm">${h.emirates.map(m => `<option value="${e(m.key)}" ${m.key === h.emirate ? "selected" : ""}>${e(m.name)}</option>`).join("")}</select></label>`;
    host.innerHTML = h.available ? `<div class="card guard-heat g-heat-${e(h.band)}"><div class="row" style="justify-content:space-between;align-items:flex-start;gap:12px">
        <div><h3 style="margin:0">☀️ ${e(x("heatT"))} · ${e(h.name)}</h3><p class="g-temp"><b>${h.max_c}°</b> <span class="muted">${e(x("feels"))} ${h.feels_c}° · ${e(x("uv"))} ${h.uv}</span></p></div>${sel}</div>
        <p style="margin:6px 0">${e(h.tip)}</p><p class="small muted" style="margin:0">${e(h.why)} <span>(${e(h.source)})</span></p></div>`
      : `<div class="card"><h3>☀️ ${e(x("heatT"))}</h3><p class="small muted">${e(x("heatOff"))}</p>${sel}</div>`;
    host.querySelector("#gEm").onchange = ev => { try { localStorage.setItem("riaya_emirate", ev.target.value); } catch {} heatCard(host); };
  }

  /* host gets: heat card, then the product checker */
  async function mount(host) {
    if (!host) return;
    host.innerHTML = `<div id="gHeat"></div>${productCard()}`;
    wireProduct(host);
    heatCard(host.querySelector("#gHeat"));
  }

  const css = document.createElement("style");
  css.textContent = `
    .g-tag { display: inline-block; font-size: .72em; font-weight: 700; letter-spacing: .06em; padding: 2px 7px; border-radius: 6px; margin-inline-end: 4px; }
    .g-stop { background: color-mix(in srgb, #d9534f 20%, transparent); color: #e0675f; } .g-caution { background: color-mix(in srgb, #e0a030 22%, transparent); color: #d9962a; }
    .g-ok { background: color-mix(in srgb, #3fa66b 20%, transparent); color: #45a872; }
    .g-verdict { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 12px; margin-top: 12px; border: 1px solid var(--line); }
    .g-verdict.g-stop { border-color: #d9534f; } .g-verdict.g-caution { border-color: #e0a030; } .g-verdict.g-ok { border-color: #3fa66b; }
    .g-verdict.g-stop, .g-verdict.g-caution, .g-verdict.g-ok { background: transparent; color: inherit; }
    .g-list { padding-inline-start: 18px; } .g-list li { margin: 6px 0; }
    .g-temp { margin: 6px 0 0; } .g-temp b { font-size: 2.2em; font-weight: 400; }
    .guard-heat { border-inline-start: 4px solid var(--line); } .g-heat-extreme, .g-heat-very_hot { border-inline-start-color: #d9534f; } .g-heat-hot { border-inline-start-color: #e0a030; }
    .g-heat-warm, .g-heat-mild { border-inline-start-color: #3fa66b; }`;
  document.head.appendChild(css);

  root.Guard = { mount, check };
})(window);
