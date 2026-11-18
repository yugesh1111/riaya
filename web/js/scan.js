/* Scan a lab report with the phone camera, page by page, like a document scanner.
   Each photo is straightened for contrast (greyscale, auto-levels), read on the phone (Tesseract OCR, English + Arabic),
   and the pages are joined into one PDF. The PDF is kept on this phone only (IndexedDB), filed by the report's date,
   so he can open it at his visit. Only the recognised text is sent to Riaya to find the values; the images never leave the phone. */
(function (root) {
  const T = {
    en: { title: "Scan your report", sub: "Take a photo of each page. Hold the phone flat over the page in good light.",
          add: "Add a page", camera: "Take photo", done: n => `Read ${n} page${n === 1 ? "" : "s"}`, cancel: "Cancel", remove: "Remove page",
          page: i => `Page ${i}`, ocr: (i, n, p) => `Reading page ${i} of ${n}… ${p}%`, saving: "Saving the document on this phone…",
          docs: "Reports saved on this phone", none: "No scanned reports yet.", open: "Open", del: "Delete", pages: n => `${n} page${n === 1 ? "" : "s"}`,
          onPhone: "Kept only on this phone. Never uploaded.", enhance: "Auto-enhanced for reading" },
    ar: { title: "امسح تقريرك", sub: "التقط صورة لكل صفحة. أمسك الهاتف مستوياً فوق الصفحة في إضاءة جيدة.",
          add: "أضف صفحة", camera: "التقط صورة", done: n => `اقرأ ${n} ${n === 1 ? "صفحة" : "صفحات"}`, cancel: "إلغاء", remove: "احذف الصفحة",
          page: i => `صفحة ${i}`, ocr: (i, n, p) => `جارٍ قراءة الصفحة ${i} من ${n}… ${p}٪`, saving: "جارٍ حفظ المستند على هذا الهاتف…",
          docs: "تقارير محفوظة على هذا الهاتف", none: "لا توجد تقارير ممسوحة بعد.", open: "افتح", del: "احذف", pages: n => `${n} ${n === 1 ? "صفحة" : "صفحات"}`,
          onPhone: "محفوظة على هذا الهاتف فقط. لا تُرفع أبداً.", enhance: "حُسّنت تلقائياً للقراءة" },
  };
  const L = () => (typeof LANG !== "undefined" && LANG === "ar" ? "ar" : "en");
  const x = k => T[L()][k];
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const load = src => new Promise((ok, no) => { if ([...document.scripts].some(s => s.src === src)) return ok(); const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = no; document.head.appendChild(s); });
  const TESS = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.0/dist/tesseract.min.js";
  const JSPDF = "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js";

  // ---------- on-phone document store
  function db() {
    return new Promise((ok, no) => {
      const r = indexedDB.open("riaya-docs", 1);
      r.onupgradeneeded = () => r.result.createObjectStore("docs", { keyPath: "id" });
      r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error);
    });
  }
  async function store(op, val) {
    const d = await db();
    return new Promise((ok, no) => {
      const tx = d.transaction("docs", op === "list" || op === "get" ? "readonly" : "readwrite"), st = tx.objectStore("docs");
      const r = op === "list" ? st.getAll() : op === "get" ? st.get(val) : op === "del" ? st.delete(val) : st.put(val);
      r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error);
    });
  }
  const listDocs = () => store("list").catch(() => []);
  const saveDoc = doc => store("put", doc);
  const delDoc = id => store("del", id);
  async function setDate(id, date) { const d = await store("get", id).catch(() => null); if (d) { d.date = date; await saveDoc(d); } }

  // ---------- image clean-up: greyscale + auto-levels, max 1700 px on the long side
  async function enhance(file) {
    const bmp = await createImageBitmap(file);
    const k = Math.min(1, 1700 / Math.max(bmp.width, bmp.height));
    const c = document.createElement("canvas"); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
    const g = c.getContext("2d"); g.drawImage(bmp, 0, 0, c.width, c.height);
    const img = g.getImageData(0, 0, c.width, c.height), d = img.data, hist = new Uint32Array(256);
    for (let i = 0; i < d.length; i += 4) { const y = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000 | 0; d[i] = y; hist[y]++; }
    const n = d.length / 4; let lo = 0, hi = 255, acc = 0;
    while (lo < 255 && (acc += hist[lo]) < n * 0.02) lo++;
    acc = 0; while (hi > 0 && (acc += hist[hi]) < n * 0.02) hi--;
    const span = Math.max(30, hi - lo);
    for (let i = 0; i < d.length; i += 4) { const v = Math.max(0, Math.min(255, ((d[i] - lo) * 255 / span))); d[i] = d[i + 1] = d[i + 2] = v; }
    g.putImageData(img, 0, 0);
    return c;
  }

  // ---------- the scanner sheet
  function open(onText) {
    const pages = [];
    const sheet = document.createElement("div");
    sheet.className = "scan-sheet"; sheet.setAttribute("role", "dialog"); sheet.setAttribute("aria-modal", "true"); sheet.setAttribute("aria-label", x("title"));
    sheet.innerHTML = `<div class="scan-card"><h2>${esc(x("title"))}</h2><p class="small muted">${esc(x("sub"))}</p>
      <div class="scan-pages" id="scPages"></div>
      <input type="file" id="scIn" accept="image/*" capture="environment" multiple class="hidden">
      <p class="row"><label class="btn ghost" for="scIn" tabindex="0" id="scAdd">📷 ${esc(x("camera"))}</label><button class="btn" id="scDone" disabled>${esc(x("done")(0))}</button>
        <button class="chip" id="scCancel">${esc(x("cancel"))}</button></p><p class="small" id="scMsg" role="status"></p>
      <p class="small muted">🔒 ${esc(x("onPhone"))}</p></div>`;
    document.body.appendChild(sheet);
    requestAnimationFrame(() => sheet.classList.add("in"));
    const close = () => { sheet.classList.remove("in"); setTimeout(() => sheet.remove(), 250); };
    const draw = () => {
      sheet.querySelector("#scPages").innerHTML = pages.map((c, i) => `<figure class="scan-page"><img alt="${esc(x("page")(i + 1))}" src="${c.toDataURL("image/jpeg", .6)}">
        <figcaption class="small">${esc(x("page")(i + 1))} · <span class="muted">${esc(x("enhance"))}</span></figcaption>
        <button class="chip" data-rm="${i}" aria-label="${esc(x("remove"))} ${i + 1}">✕</button></figure>`).join("");
      sheet.querySelectorAll("[data-rm]").forEach(b => b.onclick = () => { pages.splice(+b.dataset.rm, 1); draw(); });
      const done = sheet.querySelector("#scDone"); done.disabled = !pages.length; done.textContent = x("done")(pages.length);
      sheet.querySelector("#scAdd").innerHTML = `📷 ${esc(pages.length ? x("add") : x("camera"))}`;
    };
    sheet.querySelector("#scAdd").onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sheet.querySelector("#scIn").click(); } };
    sheet.querySelector("#scIn").onchange = async e => {
      for (const f of e.target.files) pages.push(await enhance(f));
      e.target.value = ""; draw();
    };
    sheet.querySelector("#scCancel").onclick = close;
    sheet.querySelector("#scDone").onclick = async () => {
      const msg = sheet.querySelector("#scMsg");
      sheet.querySelector("#scDone").disabled = true;
      try {
        await load(TESS);
        const texts = [];
        for (let i = 0; i < pages.length; i++) {
          const { data } = await Tesseract.recognize(pages[i], "eng+ara", {
            logger: m => { if (m.status === "recognizing text") msg.textContent = x("ocr")(i + 1, pages.length, Math.round(100 * m.progress)); } });
          texts.push(data.text);
        }
        msg.textContent = x("saving");
        let id = null;
        try {
          await load(JSPDF);
          const { jsPDF } = root.jspdf;
          const pdf = new jsPDF({ unit: "pt", format: "a4" });
          pages.forEach((c, i) => {
            if (i) pdf.addPage();
            const W = pdf.internal.pageSize.getWidth(), H = pdf.internal.pageSize.getHeight(), k = Math.min(W / c.width, H / c.height);
            pdf.addImage(c.toDataURL("image/jpeg", .8), "JPEG", (W - c.width * k) / 2, (H - c.height * k) / 2, c.width * k, c.height * k);
          });
          id = "doc-" + Date.now();
          await saveDoc({ id, created: Date.now(), date: null, pages: pages.length, pdf: pdf.output("blob") });
        } catch { /* the values still get read even if the PDF could not be stored */ }
        close();
        onText(texts.join("\n"), id);
      } catch (err) { msg.textContent = err.message || String(err); sheet.querySelector("#scDone").disabled = false; }
    };
    draw();
    setTimeout(() => sheet.querySelector("#scAdd").focus(), 50);
  }

  // ---------- list of saved documents (for the results timeline)
  async function docsCard(host) {
    const docs = (await listDocs()).sort((a, b) => (b.date || "").localeCompare(a.date || "") || b.created - a.created);
    const fmt = d => d.date ? new Date(d.date + "T00:00:00").toLocaleDateString(L() === "ar" ? "ar-AE" : "en-GB", { day: "numeric", month: "long", year: "numeric" })
      : new Date(d.created).toLocaleDateString(L() === "ar" ? "ar-AE" : "en-GB", { day: "numeric", month: "long", year: "numeric" });
    host.innerHTML = `<div class="card"><h3>📄 ${esc(x("docs"))}</h3><p class="small muted">🔒 ${esc(x("onPhone"))}</p>
      ${docs.length ? `<ul class="scan-docs">${docs.map(d => `<li><span><b>${esc(fmt(d))}</b> <span class="muted small">${esc(x("pages")(d.pages))}</span></span>
        <span class="row"><button class="chip" data-open="${d.id}">${esc(x("open"))}</button><button class="chip" data-docx="${d.id}">${esc(x("del"))}</button></span></li>`).join("")}</ul>`
        : `<p class="small muted">${esc(x("none"))}</p>`}</div>`;
    host.querySelectorAll("[data-open]").forEach(b => b.onclick = async () => {
      const d = docs.find(v => v.id === b.dataset.open); if (d) window.open(URL.createObjectURL(d.pdf), "_blank", "noopener");
    });
    host.querySelectorAll("[data-docx]").forEach(b => b.onclick = async () => { await delDoc(b.dataset.docx); docsCard(host); });
  }

  root.Scan = { open, docsCard, setDate, enhance };
})(window);
