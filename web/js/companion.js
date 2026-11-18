/* Riaya companion, connected journey and privacy centre.
   - Safe next steps and a private "ask about my summary" box on the result page. Answers come only from his own
     summary and the evidence map; nothing he types is stored or sent to an outside AI service.
   - A pathway stepper on every check: check, doctor review, clinic, appointment, specialist visit, visit summary,
     follow-up, re-check.
   - Who sees what: per-recipient sharing choices, live share codes, consent receipts and an access log. */
const CP = {
  en: { nsTitle: "Your safe next steps", now: "Now", soon: "In the next few weeks", later: "Over the next 3 months", dont: "Please don't",
    askTitle: "Ask about your summary", askSub: "Private: answers come only from your own summary and the evidence map. Riaya doesn't diagnose or prescribe, and your question isn't saved.",
    askPh: "e.g. Why do I need to see a doctor?", ask: "Ask", sources: "Based on", urgentNote: "This needs attention now.",
    msgDoctor: "Ask a doctor instead", grade: "Evidence",
    pwTitle: "Your care pathway", current: "Now", stopped: "Stopped", skipped: "Not needed", due: d => `due ${d}`,
    conTitle: "After your specialist visit", conTests: "Tests ordered", conPlan: "Plan", conNext: "Next", conFu: "Follow-up",
    fuCal: "Add follow-up to calendar", fuDone: "I had my follow-up",
    shTitle: "Who sees what", shSub: "Choose what each part of your care can see. The summary always travels with a referral so it is safe; everything else is your choice and applies straight away, including to codes you have already given.",
    shSave: "Save sharing choices", shSaved: "Saved. It applies now.", required: "always shared",
    codesT: "Active share codes", codesNone: "No active codes.", used: "opened", unused: "not opened yet", expires: d => `expires ${d}`, revoke: "Withdraw",
    logT: "Who opened my record", logNone: "No one from the care side has opened your record yet.",
    recT: "Consent receipts", recSub: "A record of every permission you gave or withdrew.", recDl: "Download receipts",
    act: { granted: "Allowed", withdrawn: "Withdrawn", changed: "Changed", declined: "Not allowed" }, partnerOn: n => `${n} active link for your wife (status only)`,
    rec: { doctor: "Riaya doctor", clinic: "Clinic", partner: "Wife (status only)", share_code: "Share code", core: "Your summary", wearables: "Device data", research: "Anonymous improvement" } },
  ar: { nsTitle: "خطواتك التالية الآمنة", now: "الآن", soon: "خلال الأسابيع القادمة", later: "خلال الأشهر الثلاثة القادمة", dont: "من فضلك لا",
    askTitle: "اسأل عن ملخصك", askSub: "خاص: الإجابات من ملخصك وخريطة الأدلة فقط. رعاية لا تشخّص ولا تصف أدوية، ولا يُحفظ سؤالك.",
    askPh: "مثلاً: لماذا أحتاج إلى طبيب؟", ask: "اسأل", sources: "المصدر", urgentNote: "هذا يحتاج اهتماماً الآن.",
    msgDoctor: "اسأل طبيباً بدلاً من ذلك", grade: "الدليل",
    pwTitle: "مسار رعايتك", current: "الآن", stopped: "متوقف", skipped: "غير مطلوب", due: d => `موعده ${d}`,
    conTitle: "بعد زيارة المختص", conTests: "الفحوصات المطلوبة", conPlan: "الخطة", conNext: "التالي", conFu: "المتابعة",
    fuCal: "أضف المتابعة إلى التقويم", fuDone: "أجريت المتابعة",
    shTitle: "من يرى ماذا", shSub: "اختر ما يراه كل طرف في رعايتك. الملخص يرافق الإحالة دائماً حفاظاً على سلامتك؛ وكل ما عداه باختيارك ويُطبّق فوراً، حتى على الرموز التي أعطيتها.",
    shSave: "احفظ خيارات المشاركة", shSaved: "تم الحفظ. يُطبّق الآن.", required: "يُشارك دائماً",
    codesT: "رموز المشاركة الفعّالة", codesNone: "لا توجد رموز فعّالة.", used: "فُتح", unused: "لم يُفتح بعد", expires: d => `ينتهي ${d}`, revoke: "اسحب",
    logT: "من فتح سجلي", logNone: "لم يفتح أحد من جهة الرعاية سجلك بعد.",
    recT: "إيصالات الموافقة", recSub: "سجل بكل إذن منحته أو سحبته.", recDl: "تحميل الإيصالات",
    act: { granted: "سُمح", withdrawn: "سُحب", changed: "تغيّر", declined: "لم يُسمح" }, partnerOn: n => `${n} رابط فعّال لزوجتك (الحالة فقط)`,
    rec: { doctor: "طبيب رعاية", clinic: "العيادة", partner: "الزوجة (الحالة فقط)", share_code: "رمز مشاركة", core: "ملخصك", wearables: "بيانات الأجهزة", research: "تحسين دون هوية" } },
};
const cp = k => CP[LANG][k];
const cpDate = ts => new Date(ts * 1000).toLocaleDateString(LANG === "ar" ? "ar-AE" : "en-GB", { day: "numeric", month: "short", year: "numeric" });

(function companionStyles() {
  const s = document.createElement("style");
  s.textContent = `
    .ladder { display: grid; gap: 14px; margin-top: 6px; }
    .ladder h3 { margin: 6px 0 2px; font-size: .95em; color: var(--ink-2); }
    .step-item { padding: 10px 0; border-top: 1px solid var(--line); }
    .step-item.urgent { border-inline-start: 4px solid var(--alert); padding-inline-start: 12px; }
    .step-item .why { color: var(--muted); font-size: .9em; margin-top: 4px; }
    .ask-log { display: grid; gap: 10px; margin: 12px 0; max-height: 420px; overflow-y: auto; }
    .ask-q { justify-self: end; background: var(--raise); border-radius: 14px; padding: 8px 12px; max-width: 85%; }
    .ask-a { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 10px 12px; white-space: pre-line; max-width: 95%; }
    .ask-a.urgent { border-color: var(--alert); border-width: 2px; }
    .ask-a .src { color: var(--muted); font-size: .85em; margin-top: 8px; white-space: normal; }
    .pathway { list-style: none; padding: 0; margin: 10px 0; display: grid; gap: 0; }
    .pathway li { position: relative; padding: 4px 0 12px; padding-inline-start: 28px; }
    .pathway li::before { content: ""; position: absolute; inset-inline-start: 6px; top: 8px; width: 12px; height: 12px; border-radius: 50%;
      border: 2px solid var(--line); background: var(--surface); box-sizing: border-box; }
    .pathway li::after { content: ""; position: absolute; inset-inline-start: 11px; top: 22px; bottom: -6px; width: 2px; background: var(--line); }
    .pathway li:last-child::after { display: none; }
    .pathway li.done::before { background: var(--good); border-color: var(--good); }
    .pathway li.current::before { background: var(--saffron); border-color: var(--saffron); box-shadow: 0 0 0 4px var(--accent-soft); }
    .pathway li.stopped::before { background: var(--alert); border-color: var(--alert); }
    .pathway li.skipped { color: var(--muted); }
    .pathway li .na { display: block; color: var(--ink-2); font-size: .92em; }
    .share-grid { width: 100%; border-collapse: collapse; }
    .share-grid th, .share-grid td { padding: 8px 6px; border-bottom: 1px solid var(--line); text-align: start; vertical-align: top; }
    .share-grid td.c { text-align: center; width: 90px; }
    .share-grid input { width: 20px; height: 20px; }`;
  document.head.appendChild(s);
})();

async function loadCompanion() {
  const box = document.getElementById("companion");
  if (!box || !S.aid) return;
  const n = await API.get(`/api/assessments/${S.aid}/next-steps?lang=${LANG}`);
  const item = s => `<div class="step-item ${s.kind === "urgent" ? "urgent" : ""}"><b>${esc(s.text)}</b>${s.grade ? ` ${gradeTag(s.grade)}` : ""}
      ${s.why ? `<div class="why">${esc(s.why)}</div>` : ""}</div>`;
  const group = (k, list) => list.length ? `<div><h3>${cp(k)}</h3>${list.map(item).join("")}</div>` : "";
  box.innerHTML = `<div class="card"><h2>${cp("nsTitle")}</h2><div class="ladder">
      ${group("now", n.now)}${group("soon", n.soon)}${group("later", n.later)}
      <div><h3>${cp("dont")}</h3>${n.dont.map(d => `<div class="step-item">${esc(d)}</div>`).join("")}</div>
      <details class="step-item"><summary><b>${esc(n.safety_net.title)}</b></summary><ul class="small">${n.safety_net.items.map(x => `<li>${esc(x)}</li>`).join("")}</ul></details>
    </div></div>
    <div class="card" id="askCard"><h2>${cp("askTitle")}</h2><p class="muted small">${cp("askSub")}</p>
      <div class="opts" id="askSugg"></div><div class="ask-log" id="askLog" aria-live="polite"></div>
      <form class="row" id="askForm" style="flex-wrap:nowrap"><input type="text" id="askIn" maxlength="500" placeholder="${cp("askPh")}" aria-label="${cp("askTitle")}">
        <button class="btn" type="submit">${cp("ask")}</button></form></div>`;
  const suggest = list => { $("#askSugg").innerHTML = list.map(q => `<span class="opt">${esc(q)}</span>`).join(""); $$("#askSugg .opt").forEach(o => o.onclick = () => send(o.textContent)); };
  const send = async q => {
    q = q.trim(); if (!q) return;
    const log = $("#askLog");
    log.insertAdjacentHTML("beforeend", `<div class="ask-q">${esc(q)}</div>`);
    const a = await API.post(`/api/assessments/${S.aid}/ask?lang=${LANG}`, { question: q });
    const src = a.sources.length ? `<div class="src">${cp("sources")}: ${a.sources.map(s => `${esc(s.label)}${s.grade ? " " + gradeTag(s.grade) : ""}`).join("; ")}</div>` : "";
    log.insertAdjacentHTML("beforeend", `<div class="ask-a ${a.safety === "urgent" ? "urgent" : ""}">${a.safety === "urgent" ? `<b>${cp("urgentNote")}</b>\n` : ""}${esc(a.answer)}${src}
      ${a.safety === "redirect" && $("#msg") ? `<div><button class="chip" data-doc="1">${cp("msgDoctor")}</button></div>` : ""}</div>`);
    log.scrollTop = log.scrollHeight;
    $$("[data-doc]", log).forEach(b => b.onclick = () => { $("#msg").value = q; $("#msg").focus(); $("#msg").scrollIntoView({ behavior: "smooth", block: "center" }); });
    suggest(a.suggestions);
  };
  const first = await API.post(`/api/assessments/${S.aid}/ask?lang=${LANG}`, { question: "?" });
  suggest(first.suggestions);
  $("#askForm").onsubmit = e => { e.preventDefault(); const v = $("#askIn").value; $("#askIn").value = ""; send(v); };
}

function pathwayHTML(c) {
  if (!c.pathway) return "";
  return `<h3>${cp("pwTitle")}</h3><ol class="pathway small">${c.pathway.map(s => `<li class="${s.status}">
      <b>${esc(s.label)}</b>${s.at && s.status === "done" ? ` <span class="muted">${cpDate(s.at)}</span>` : ""}
      ${s.status === "current" ? ` <span class="tag">${cp("current")}</span>` : ""}${s.status === "skipped" ? ` <span class="muted">· ${cp("skipped")}</span>` : ""}
      ${s.status === "stopped" ? ` <span class="tag">${cp("stopped")}</span>${s.barrier ? ` (${esc(t("barrier")[s.barrier] || s.barrier)})` : ""}` : ""}
      ${s.due && s.status !== "done" && s.status !== "skipped" ? ` <span class="muted">· ${esc(cp("due")(cpDate(s.due)))}</span>` : ""}
      ${s.next_action ? `<span class="na">${esc(s.next_action)}</span>` : ""}</li>`).join("")}</ol>`;
}

function consultHTML(con, aid) {
  if (!con) return "";
  return `<div class="card" style="border-inline-start:4px solid var(--good)"><h3>${cp("conTitle")}</h3>
    <p>${esc(con.summary)}</p>
    ${con.tests_ordered.length ? `<p class="small"><b>${cp("conTests")}:</b> ${con.tests_ordered.map(esc).join(", ")}</p>` : ""}
    ${con.plan ? `<p class="small"><b>${cp("conPlan")}:</b> ${esc(con.plan)}</p>` : ""}
    <p class="small"><b>${cp("conNext")}:</b> ${esc(con.next_label)}${con.followup_at ? ` · <b>${cp("conFu")}:</b> ${cpDate(con.followup_at)}` : ""}</p>
    ${con.followup_at && !con.followup_done_at ? `<p class="row"><button class="btn ghost" data-fu-ics="${aid}">${cp("fuCal")}</button><button class="chip" data-fu-done="${aid}">${cp("fuDone")}</button></p>` : ""}</div>`;
}

function wireConsult(root, after) {
  $$("[data-fu-ics]", root).forEach(b => b.onclick = async () => {
    const r = await fetch(`/api/assessments/${b.dataset.fuIcs}/followup.ics`, { headers: { Authorization: `Bearer ${API.token}` } });
    const a = document.createElement("a"); a.href = URL.createObjectURL(await r.blob()); a.download = "follow-up.ics"; a.click();
  });
  $$("[data-fu-done]", root).forEach(b => b.onclick = async () => { await API.post(`/api/assessments/${b.dataset.fuDone}/progress`, { status: "followed_up" }); after && after(); });
}

async function renderSharing() {
  const box = document.getElementById("sharing");
  if (!box) return;
  const [s, log, rec] = await Promise.all([API.get(`/api/me/sharing?lang=${LANG}`), API.get(`/api/me/access-log?lang=${LANG}`), API.get(`/api/me/receipts?lang=${LANG}`)]);
  const recLabel = r => cp("rec")[r.recipient] || r.recipient_label;
  box.innerHTML = `<div class="card"><h2>${cp("shTitle")}</h2><p class="muted small">${cp("shSub")}</p>
      <table class="share-grid small"><tr><th></th>${s.recipients.map(r => `<th class="c">${esc(r.label)}</th>`).join("")}</tr>
      ${s.categories.map(c => `<tr><td>${esc(c.label)}${c.required ? `<br><span class="muted">${cp("required")}</span>` : ""}</td>
        ${s.recipients.map(r => `<td class="c"><input type="checkbox" data-r="${r.key}" data-c="${c.key}" ${s.prefs[r.key].includes(c.key) ? "checked" : ""} ${c.required ? "disabled" : ""}
          aria-label="${esc(r.label)}: ${esc(c.label)}"></td>`).join("")}</tr>`).join("")}</table>
      ${s.partner_links ? `<p class="small">${esc(cp("partnerOn")(s.partner_links))}</p>` : ""}
      <p class="row"><button class="btn" id="shSave">${cp("shSave")}</button><span class="small" id="shMsg" role="status"></span></p></div>
    <div class="card"><h3>${cp("codesT")}</h3>${s.active_codes.length ? s.active_codes.map(x => `<div class="row small" style="margin:6px 0"><span class="code" dir="ltr">${esc(x.code)}</span>
        <span class="muted">${x.used ? cp("used") : cp("unused")} · ${esc(cp("expires")(cpDate(x.expires_at)))}</span><span class="spacer"></span><button class="chip" data-rv="${esc(x.code)}">${cp("revoke")}</button></div>`).join("")
      : `<p class="muted small">${cp("codesNone")}</p>`}</div>
    <div class="card"><h3>${cp("logT")}</h3>${log.entries.length ? `<ul class="small">${log.entries.slice(0, 30).map(e => `<li>${esc(e.text)} <span class="muted">${new Date(e.ts * 1000).toLocaleString(LANG === "ar" ? "ar-AE" : "en-GB")}</span></li>`).join("")}</ul>`
      : `<p class="muted small">${cp("logNone")}</p>`}</div>
    <div class="card"><h3>${cp("recT")}</h3><p class="muted small">${cp("recSub")}</p>
      <ul class="small">${rec.receipts.slice(0, 12).map(r => `<li>${esc(cp("act")[r.action] || r.action)}: ${esc(recLabel(r))} <span class="muted">${cpDate(r.ts)}</span></li>`).join("")}</ul>
      <button class="btn ghost" id="recDl">${cp("recDl")}</button></div>`;
  $("#shSave").onclick = async () => {
    const body = {};
    s.recipients.forEach(r => { body[r.key] = $$(`[data-r="${r.key}"]`, box).filter(i => i.checked).map(i => i.dataset.c); });
    try { await API.post("/api/me/sharing", body); $("#shMsg").textContent = cp("shSaved"); renderSharing(); } catch (e) { $("#shMsg").textContent = e.message; }
  };
  $$("[data-rv]", box).forEach(b => b.onclick = async () => { await API.del(`/api/me/codes/${b.dataset.rv}`); renderSharing(); });
  $("#recDl").onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(rec, null, 1)], { type: "application/json" })); a.download = "riaya-consent-receipts.json"; a.click();
  };
}
