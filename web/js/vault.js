/* The vault: every document kept on this device, each one encrypted (AES-256-GCM, a key that cannot leave the
   browser), and each one asks for Face ID / fingerprint / PIN again before it opens, even when the app is unlocked.
   The man's vault holds his scanned reports and the documents from his doctors; the doctor's vault (clinician
   console) holds what patients shared. "Add sample documents" fills it with clearly labelled SAMPLE files for demos. */
(function (root) {
  const T = {
    en: { title: "Your vault", sub: "Documents kept only on this device, encrypted. Each one asks for your Face ID, fingerprint or PIN before it opens.",
          docTitle: "Document vault", docSub: "Documents patients shared with you, kept on this computer, encrypted. Each one asks for your PIN before it opens.",
          none: "Nothing here yet. Scanned reports and documents from your doctor appear here.", samples: "Add sample documents", sample: "SAMPLE",
          opening: "Opening…", close: "Close", locked: "Locked", del: "Delete", delQ: "Delete this document from this device?", pages: n => `${n} page${n === 1 ? "" : "s"}`,
          enc: "AES-256 encrypted", from: "From", count: n => `${n} document${n === 1 ? "" : "s"}`, scan: "Scanned report" },
    ar: { title: "خزنتك", sub: "مستندات محفوظة على هذا الجهاز فقط ومشفّرة. يطلب كل مستند بصمة الوجه أو الإصبع أو رمزك قبل أن يُفتح.",
          docTitle: "خزنة المستندات", docSub: "مستندات شاركها المرضى معك، محفوظة على هذا الحاسوب ومشفّرة. يطلب كل مستند رمزك قبل أن يُفتح.",
          none: "لا شيء هنا بعد. تظهر هنا التقارير الممسوحة والمستندات من طبيبك.", samples: "أضف مستندات تجريبية", sample: "تجريبي",
          opening: "جارٍ الفتح…", close: "إغلاق", locked: "مقفل", del: "حذف", delQ: "حذف هذا المستند من هذا الجهاز؟", pages: n => `${n} ${n === 1 ? "صفحة" : "صفحات"}`,
          enc: "مشفّر AES-256", from: "من", count: n => `${n} مستند`, scan: "تقرير ممسوح" },
  };
  const L = () => (typeof LANG !== "undefined" && LANG === "ar" ? "ar" : "en");
  const x = k => T[L()][k];
  const escH = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const JSPDF = "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js";
  const load = src => new Promise((ok, no) => { if ([...document.scripts].some(s => s.src === src)) return ok(); const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = no; document.head.appendChild(s); });
  const dbName = () => (root.Lock && root.Lock.scope === "doc" ? "riaya-docs-doc" : "riaya-docs");

  function db() {
    return new Promise((ok, no) => { const r = indexedDB.open(dbName(), 1); r.onupgradeneeded = () => r.result.createObjectStore("docs", { keyPath: "id" });
      r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  }
  async function op(kind, val) {
    const d = await db();
    return new Promise((ok, no) => { const tx = d.transaction("docs", kind === "list" ? "readonly" : "readwrite"), st = tx.objectStore("docs");
      const r = kind === "list" ? st.getAll() : kind === "del" ? st.delete(val) : st.put(val); r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  }

  // ---------- sample documents (clearly labelled SAMPLE; no real person)
  async function textPdf(title, lines) {
    await load(JSPDF);
    const { jsPDF } = root.jspdf;
    const pdf = new jsPDF({ unit: "pt", format: "a4" });
    pdf.setFontSize(9); pdf.setTextColor(180, 40, 40); pdf.text("SAMPLE DOCUMENT · NOT A REAL PATIENT", 40, 30);
    pdf.setTextColor(15, 42, 58); pdf.setFontSize(18); pdf.text(title, 40, 70);
    pdf.setFontSize(11); pdf.setTextColor(40, 40, 40);
    let y = 100;
    for (const ln of lines) { for (const part of pdf.splitTextToSize(ln, 515)) { pdf.text(part, 40, y); y += 16; } y += 4; }
    return pdf.output("blob");
  }
  const SAMPLES = {
    user: [
      { title: "Semen analysis report", from: "Demo laboratory", date: "2026-08-14", file: "samples/sample_lab_report.pdf" },
      { title: "Hormone panel", from: "Demo laboratory", date: "2026-09-02", lines: ["Total testosterone: 9.1 nmol/L (lab range 8.6–29)", "LH: 4.2 IU/L (1.7–8.6)", "FSH: 5.1 IU/L (1.5–12.4)",
        "Sample taken 08:20, fasting.", "Comment: low-normal testosterone; repeat in 3 months with a morning sample."] },
      { title: "Referral letter", from: "Riaya review doctor", date: "2026-09-05", lines: ["To: Andrology clinic", "Reason: couple trying for 18 months; borderline semen analysis; lifestyle factors (smoking, sleep 6 h).",
        "Results enclosed so tests are not repeated. Patient preferences: male clinician, Arabic, messages only.", "Questions he wants to discuss: Does smoking affect sperm count? Should my wife be tested at the same time?"] },
      { title: "Specialist visit summary", from: "Andrology clinic", date: "2026-09-20", lines: ["Seen with his wife. Examination normal; no varicocele found.", "Plan: stop smoking (support offered), sleep 7 h, loose underwear, repeat semen analysis in 12 weeks.",
        "Tests ordered: repeat semen analysis, morning testosterone.", "Follow-up: 2026-12-15."] },
    ],
    doc: [
      { title: "Referral · patient 7F2A", from: "Riaya pre-screen", date: "2026-11-10", lines: ["Level: andrology. Tier: high signals. Reviewed and approved.", "Drivers: smoking, short sleep, BMI 30.", "Shared parts: summary, lab results. Withheld by the patient: device data."] },
      { title: "Semen analysis · patient 7F2A", from: "Shared by the patient", date: "2026-11-08", file: "samples/sample_lab_report.pdf" },
      { title: "Visit summary draft · patient 7F2A", from: "You", date: "2026-11-18", lines: ["Findings:", "Plan:", "Tests ordered:", "Follow-up date:"] },
    ],
  };
  async function addSamples() {
    const list = SAMPLES[root.Lock && root.Lock.scope === "doc" ? "doc" : "user"];
    for (const d of list) {
      const blob = d.file ? await (await fetch(d.file)).blob() : await textPdf(d.title, d.lines);
      const pdf = root.Lock ? await root.Lock.encryptBlob(blob) : blob;
      await op("put", { id: "sample-" + d.title.replace(/\W+/g, "-").toLowerCase(), created: Date.now(), date: d.date, pages: 1, title: d.title, from: d.from, sample: true, pdf });
    }
  }

  // ---------- viewer: opens only after confirming it's him, closes back to locked
  async function openDoc(d) {
    if (root.Lock && !(await root.Lock.verify())) return;
    const blob = root.Lock ? await root.Lock.decryptBlob(d.pdf) : d.pdf;
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const v = document.createElement("div");
    v.className = "vt-viewer"; v.setAttribute("role", "dialog"); v.setAttribute("aria-modal", "true"); v.setAttribute("aria-label", d.title || x("scan"));
    v.innerHTML = `<div class="vt-bar"><b>${escH(d.title || x("scan"))}</b>${d.sample ? ` <span class="vt-sample">${escH(x("sample"))}</span>` : ""}<span style="flex:1"></span>
      <a class="chip" href="${url}" target="_blank" rel="noopener">↗</a><button class="chip" type="button" id="vtClose">${escH(x("close"))}</button></div>
      <iframe src="${url}" title="${escH(d.title || x("scan"))}"></iframe>`;
    document.body.appendChild(v);
    const close = () => { v.remove(); URL.revokeObjectURL(url); document.removeEventListener("visibilitychange", hide); };
    const hide = () => { if (document.hidden) close(); };   // leaving the app closes the document
    document.addEventListener("visibilitychange", hide);
    v.querySelector("#vtClose").onclick = close;
    v.querySelector("#vtClose").focus();
  }

  async function render(host) {
    const docs = (await op("list").catch(() => [])).sort((a, b) => (b.date || "").localeCompare(a.date || "") || b.created - a.created);
    const doc = root.Lock && root.Lock.scope === "doc";
    const fmt = d => d.date ? new Date(d.date + "T00:00:00").toLocaleDateString(L() === "ar" ? "ar-AE" : "en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";
    host.innerHTML = `<div class="vt-head"><div><h1 style="margin:0">🔐 ${escH(doc ? x("docTitle") : x("title"))}</h1><p class="lead" style="margin:6px 0 0">${escH(doc ? x("docSub") : x("sub"))}</p></div></div>
      <p class="small muted">${escH(x("count")(docs.length))} · ${escH(x("enc"))}${root.Lock && root.Lock.BIO_NAME ? ` · ${escH(root.Lock.BIO_NAME[L() === "ar" ? 1 : 0])}` : ""}</p>
      ${docs.length ? `<div class="vt-grid">${docs.map(d => `<button type="button" class="vt-doc" data-id="${escH(d.id)}">
          <span class="vt-ic" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg></span>
          <span class="vt-t">${escH(d.title || x("scan"))}</span>
          <span class="vt-m">${d.from ? `${escH(x("from"))} ${escH(d.from)} · ` : ""}${escH(fmt(d))}</span>
          <span class="vt-tags">${d.sample ? `<span class="vt-sample">${escH(x("sample"))}</span>` : ""}<span class="vt-enc">${escH(x("locked"))}</span></span></button>`).join("")}</div>`
        : `<div class="card"><p>${escH(x("none"))}</p></div>`}
      <p class="row" style="margin-top:14px"><button type="button" class="btn ghost" id="vtSamples">${escH(x("samples"))}</button></p>`;
    host.querySelectorAll(".vt-doc").forEach(b => b.onclick = () => { const d = docs.find(v => v.id === b.dataset.id); if (d) openDoc(d); });
    host.querySelector("#vtSamples").onclick = async e => { e.target.disabled = true; e.target.textContent = x("opening"); await addSamples(); render(host); };
  }

  const css = document.createElement("style");
  css.textContent = `
    .vt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
    .vt-doc { text-align: start; display: flex; flex-direction: column; gap: 6px; padding: 16px; border-radius: 18px; border: 1px solid var(--line); background: var(--surface);
      color: var(--ink); font: inherit; cursor: pointer; min-height: 132px; transition: transform .15s, border-color .15s; }
    .vt-doc:hover { transform: translateY(-2px); border-color: var(--brand); } .vt-doc:focus-visible { outline: 3px solid var(--brand); outline-offset: 2px; }
    .vt-ic { width: 38px; height: 38px; border-radius: 12px; display: grid; place-items: center; background: color-mix(in srgb, var(--saffron, #c9a86a) 18%, transparent); color: var(--saffron, #c9a86a); }
    .vt-t { font-weight: 600; } .vt-m { font-size: .82em; color: var(--muted); } .vt-tags { display: flex; gap: 6px; margin-top: auto; }
    .vt-sample { font-size: .7em; letter-spacing: .08em; font-weight: 700; padding: 3px 7px; border-radius: 6px; background: color-mix(in srgb, #d9534f 18%, transparent); color: #d9534f; }
    .vt-enc { font-size: .7em; padding: 3px 7px; border-radius: 6px; border: 1px solid var(--line); color: var(--muted); }
    .vt-viewer { position: fixed; inset: 0; z-index: 900; background: var(--bg); display: flex; flex-direction: column; }
    .vt-bar { display: flex; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--line); }
    .vt-viewer iframe { flex: 1; border: 0; width: 100%; background: #fff; }`;
  document.head.appendChild(css);

  root.Vault = { render, addSamples };
})(window);
