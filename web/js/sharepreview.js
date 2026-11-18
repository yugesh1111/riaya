/* "See exactly what they'll see": the referral letter as the doctor or clinic would receive it, built by the same server code
   that builds their view, plus the questions he wants to ask. Previewing shares nothing. */
(function () {
  const PT = {
    en: { title: "See exactly what they'll see", sub: "This is the letter, word for word, that the person you choose receives. Previewing shares nothing.",
      doctor: "Riaya doctor", clinic: "Your clinic", notShared: "Not shared", unsaved: "Preview of your unsaved choice", paused: "Sharing is paused: right now nobody can open this.",
      qT: "Questions you want to ask", qSub: "One per line. They go at the top of the letter, in your words.", qPh: "e.g. Could my sleep be part of this?",
      qSave: "Save questions", qSaved: "Saved. They're in the letter.", cats: { answers: "answers", devices: "watch data", labs: "lab results", plan: "12-week plan" }, doc: "Referral letter" },
    ar: { title: "شاهد بالضبط ما سيرونه", sub: "هذه الرسالة كما تصل حرفياً إلى من تختاره. المعاينة لا تشارك شيئاً.",
      doctor: "طبيب رعاية", clinic: "عيادتك", notShared: "لا يُشارك", unsaved: "معاينة لاختيارك غير المحفوظ", paused: "المشاركة متوقفة: لا يستطيع أحد فتح هذا الآن.",
      qT: "أسئلة تريد طرحها", qSub: "سؤال في كل سطر. توضع في أعلى الرسالة بكلماتك.", qPh: "مثلاً: هل يمكن أن يكون للنوم دور؟",
      qSave: "احفظ الأسئلة", qSaved: "حُفظت. أصبحت في الرسالة.", cats: { answers: "الإجابات", devices: "بيانات الساعة", labs: "نتائج المختبر", plan: "خطة ١٢ أسبوعاً" }, doc: "رسالة الإحالة" },
  };
  const pt = k => PT[LANG === "ar" ? "ar" : "en"][k];
  const css = document.createElement("style");
  css.textContent = `
    .sp-tabs { display: inline-flex; gap: 4px; padding: 4px; border-radius: 99px; background: var(--raise); border: 1px solid var(--line); margin: 4px 0 14px; }
    .sp-tabs button { border: 0; background: transparent; padding: 7px 16px; border-radius: 99px; cursor: pointer; color: var(--ink-2); font-size: 14px; }
    .sp-tabs button[aria-pressed=true] { background: var(--surface); color: var(--ink); font-weight: 500; box-shadow: 0 1px 2px rgba(0,0,0,.06); }
    .sp-paper { position: relative; background: #fffefa; color: #1d2a24; border-radius: 6px; padding: 26px 28px 22px; font-size: 13.5px; line-height: 1.55;
      box-shadow: 0 1px 0 var(--line), 0 18px 40px -22px rgba(0,0,0,.35); border: 1px solid var(--line); max-height: 440px; overflow: auto; direction: ltr; text-align: left; }
    .sp-paper .hd { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid #e7e1d3; padding-bottom: 10px; margin-bottom: 10px; font-size: 12px; color: #6d7a72; }
    .sp-paper h4 { margin: 14px 0 4px; font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: #6d7a72; }
    .sp-paper ul { margin: 0; padding-left: 18px; }
    .sp-paper .q { background: #f6eedc; border-radius: 6px; padding: 8px 12px; margin-top: 4px; }
    .sp-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 12px; }
    .sp-chips span { font-size: 12.5px; padding: 3px 10px; border-radius: 99px; border: 1px dashed var(--line); color: var(--muted); text-decoration: line-through; }
    .sp-note { font-size: 12.5px; color: var(--saffron); margin: 0 0 8px; }
    @media (prefers-reduced-motion: no-preference) { .sp-paper.flash { animation: sp-flash .5s var(--ease, ease); } @keyframes sp-flash { from { opacity: .4; transform: translateY(4px); } } }`;
  document.head.appendChild(css);

  async function renderSharePreview(host, aid, recipient = "clinic", categories = null) {
    if (!host || !aid) return;
    const q = categories ? `&categories=${encodeURIComponent(categories.join(","))}` : "";
    let p, qs;
    try {
      [p, qs] = await Promise.all([API.get(`/api/assessments/${aid}/share-preview?recipient=${recipient}${q}`), API.get(`/api/assessments/${aid}/questions`)]);
    } catch { host.innerHTML = ""; return; }
    const letter = p.letter;
    host.innerHTML = `<div class="card"><h2>${pt("title")}</h2><p class="muted small">${pt("sub")}</p>
      <div class="sp-tabs" role="group">${["clinic", "doctor"].map(r => `<button data-sp="${r}" aria-pressed="${r === recipient}">${pt(r)}</button>`).join("")}</div>
      ${p.paused ? `<p class="sp-note">${pt("paused")}</p>` : ""}${categories ? `<p class="sp-note">${pt("unsaved")}</p>` : ""}
      ${p.withheld.length ? `<div class="sp-chips"><b class="small" style="margin-inline-end:4px">${pt("notShared")}:</b>${p.withheld.map(w => `<span>${esc(pt("cats")[w] || w)}</span>`).join("")}</div>` : ""}
      <div class="sp-paper flash"><div class="hd"><b>${pt("doc")} · ${esc(letter.to)}</b><span>${esc(letter.date)}</span></div>
        ${letter.sections.map(s => `<h4>${esc(s.title)}</h4>${s.title === "Questions he wants to discuss" ? s.lines.map(l => `<div class="q">${esc(l)}</div>`).join("") : `<ul>${s.lines.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`}`).join("")}</div>
      <h3 style="margin-top:22px">${pt("qT")}</h3><p class="muted small">${pt("qSub")}</p>
      <textarea id="spQ" rows="3" maxlength="1600" placeholder="${pt("qPh")}">${esc(qs.questions.join("\n"))}</textarea>
      <p class="row"><button class="btn ghost" id="spSave">${pt("qSave")}</button><span class="small" id="spMsg" role="status"></span></p></div>`;
    host.querySelectorAll("[data-sp]").forEach(b => b.onclick = () => renderSharePreview(host, aid, b.dataset.sp));
    host.querySelector("#spSave").onclick = async () => {
      await API.put(`/api/assessments/${aid}/questions`, { questions: host.querySelector("#spQ").value.split("\n") });
      await renderSharePreview(host, aid, recipient, categories);
      host.querySelector("#spMsg").textContent = pt("qSaved");
    };
  }
  window.renderSharePreview = renderSharePreview;
})();
