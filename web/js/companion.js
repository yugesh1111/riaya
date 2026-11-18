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
    rec: { doctor: "Riaya doctor", clinic: "Clinic", partner: "Wife (status only)", share_code: "Share code", core: "Your summary", wearables: "Device data", research: "Anonymous improvement",
      all_sharing: "All sharing", retention: "How long data is kept" },
    specFirst: "From your specialist", testsT: "Tests your specialist ordered", testDone: "Done", testMark: "Mark done", testUndo: "Not done yet",
    viaResult: "result saved", addResult: "Add the result", allTests: "All ordered tests are done. Bring the results to your follow-up.",
    pausedBanner: "You've paused all sharing. Your doctor and clinic can't see your record, and handover codes don't open, until you turn it back on in Privacy.",
    clinicHow: u => `The clinic opens it at ${u}. Every opening appears in your access log, and you can withdraw the code at any time.`,
    pvTitle: "Your privacy switches", pause: "Pause all sharing", pauseSub: "One switch: no doctor or clinic can open your record, and codes you've given stop working. Your appointments stay booked. Turn it back on any time.",
    paused: "Sharing is paused", resume: "Turn sharing back on", keepT: "Keep my data", keepSub: "Counted from your last visit to Riaya. When the time passes, everything is deleted, as if you pressed Delete.",
    keep: { null: "Until I delete it", 3: "3 months", 6: "6 months", 12: "12 months", 24: "24 months" }, delOn: d => `Deleted on ${d} unless you come back before then.`,
    act2: { paused: "Paused", resumed: "Resumed" },
    remT: "Gentle reminders", remSub: "A short private message in Riaya if a step has waited a while, and when your re-check is due. Never an SMS or a call.",
    remOn: "Reminders on", remOff: "Reminders off",
    soTitle: "Share with another doctor", soSub: "For a second opinion or a doctor outside Riaya. Pick exactly what this code shows and for how long. They open it at the clinic page; it is view-only.",
    soDays: { 24: "1 day", 72: "3 days", 168: "7 days" }, soMake: "Create code", soMade: "Give this code to the doctor:", soLink: "They open:",
    purpose: { clinic: "your clinic", second_opinion: "another doctor" }, shows: "shows",
    prepT: "Get ready for your visit", prepSrc: "Source",
    fbT: "How was your visit?", fbSub: "Three quick ratings. Clinics only see averages from 5 or more men, never yours.",
    fbQ: { respect: "I was treated with respect", privacy: "My privacy was kept", explained: "Things were explained clearly" }, fbRec: "Would you recommend this clinic?",
    fbWait: "Days from booking to the visit (optional)", yes: "Yes", no: "No", fbSend: "Send", fbThanks: "Thank you. This helps other men choose." },
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
    rec: { doctor: "طبيب رعاية", clinic: "العيادة", partner: "الزوجة (الحالة فقط)", share_code: "رمز مشاركة", core: "ملخصك", wearables: "بيانات الأجهزة", research: "تحسين دون هوية",
      all_sharing: "كل المشاركة", retention: "مدة الاحتفاظ بالبيانات" },
    specFirst: "من المختص", testsT: "الفحوصات التي طلبها المختص", testDone: "تم", testMark: "علّمه منجزاً", testUndo: "لم يُنجز بعد",
    viaResult: "حُفظت النتيجة", addResult: "أضف النتيجة", allTests: "أُنجزت كل الفحوصات المطلوبة. أحضر نتائجها إلى المتابعة.",
    pausedBanner: "أوقفت كل المشاركة مؤقتاً. لا يستطيع طبيبك ولا العيادة رؤية سجلك، ولا تفتح رموز التسليم، حتى تعيد تشغيلها من «الخصوصية».",
    clinicHow: u => `تفتحه العيادة من ${u}. كل فتح يظهر في سجل الوصول، ويمكنك سحب الرمز في أي وقت.`,
    pvTitle: "مفاتيح خصوصيتك", pause: "أوقف كل المشاركة مؤقتاً", pauseSub: "مفتاح واحد: لا يستطيع أي طبيب أو عيادة فتح سجلك، وتتوقف الرموز التي أعطيتها. تبقى مواعيدك محجوزة. أعد تشغيلها متى شئت.",
    paused: "المشاركة متوقفة", resume: "أعد تشغيل المشاركة", keepT: "احتفظ ببياناتي", keepSub: "تُحسب من آخر زيارة لك إلى رعاية. عند انقضاء المدة يُحذف كل شيء، كأنك ضغطت «حذف».",
    keep: { null: "حتى أحذفها بنفسي", 3: "٣ أشهر", 6: "٦ أشهر", 12: "١٢ شهراً", 24: "٢٤ شهراً" }, delOn: d => `تُحذف في ${d} ما لم تعد قبل ذلك.`,
    act2: { paused: "أُوقفت", resumed: "استؤنفت" },
    remT: "تذكيرات لطيفة", remSub: "رسالة قصيرة خاصة في رعاية إن انتظرت خطوة طويلاً، وعند حلول موعد فحص المتابعة. لا رسائل نصية ولا مكالمات.",
    remOn: "التذكيرات مفعّلة", remOff: "التذكيرات متوقفة",
    soTitle: "شارك مع طبيب آخر", soSub: "لرأي ثانٍ أو لطبيب خارج رعاية. اختر بالضبط ما يظهره هذا الرمز ولأي مدة. يفتحه من صفحة العيادة، للاطلاع فقط.",
    soDays: { 24: "يوم واحد", 72: "٣ أيام", 168: "٧ أيام" }, soMake: "أنشئ رمزاً", soMade: "أعطِ هذا الرمز للطبيب:", soLink: "يفتحه من:",
    purpose: { clinic: "عيادتك", second_opinion: "طبيب آخر" }, shows: "يُظهر",
    prepT: "استعد لزيارتك", prepSrc: "المصدر",
    fbT: "كيف كانت زيارتك؟", fbSub: "ثلاثة تقييمات سريعة. لا ترى العيادات إلا متوسطات من ٥ رجال أو أكثر، وليس تقييمك.",
    fbQ: { respect: "عوملت باحترام", privacy: "حُفظت خصوصيتي", explained: "شُرحت الأمور بوضوح" }, fbRec: "هل تنصح بهذه العيادة؟",
    fbWait: "عدد الأيام من الحجز إلى الزيارة (اختياري)", yes: "نعم", no: "لا", fbSend: "أرسل", fbThanks: "شكراً. هذا يساعد غيرك على الاختيار." },
};
const cp = k => CP[LANG][k];
window.cp = cp;
const cpDate = ts => new Date(ts * 1000).toLocaleDateString(LANG === "ar" ? "ar-AE" : "en-GB", { day: "numeric", month: "short", year: "numeric" });

(function companionStyles() {
  const s = document.createElement("style");
  s.textContent = `
    .ladder { display: grid; gap: 14px; margin-top: 6px; }
    .ladder h3 { margin: 6px 0 2px; font-size: .95em; color: var(--ink-2); }
    .step-item { padding: 10px 0; border-top: 1px solid var(--line); }
    .step-item.urgent { border-inline-start: 4px solid var(--alert); padding-inline-start: 12px; }
    .step-item.specialist { border-inline-start: 4px solid var(--good); padding-inline-start: 12px; }
    .step-item.privacy { border-inline-start: 4px solid var(--saffron); padding-inline-start: 12px; }
    .tests-list { list-style: none; padding: 0; margin: 6px 0; }
    .tests-list li { display: flex; gap: 8px; align-items: center; padding: 6px 0; border-top: 1px solid var(--line); flex-wrap: wrap; }
    .tests-list li.done b { text-decoration: line-through; color: var(--muted); }
    .switch-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
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
  const item = s => `<div class="step-item ${["urgent", "specialist", "privacy"].includes(s.kind) ? s.kind : ""}"><b>${esc(s.text)}</b>${s.grade ? ` ${gradeTag(s.grade)}` : ""}
      ${s.why ? `<div class="why">${esc(s.why)}</div>` : ""}</div>`;
  const group = (k, list) => list.length ? `<div><h3>${cp(k)}</h3>${list.map(item).join("")}</div>` : "";
  box.innerHTML = `<div class="card"><h2>${cp("nsTitle")}</h2><div class="ladder">
      ${n.specialist_first ? `<p class="small muted">${esc(n.specialist_first)}</p>` : ""}
      ${group("now", n.now)}${group("soon", n.soon)}${group("later", n.later)}
      <div><h3>${cp("dont")}</h3>${n.dont.map(d => `<div class="step-item">${esc(d)}</div>`).join("")}</div>
      <details class="step-item"><summary><b>${esc(n.safety_net.title)}</b></summary><ul class="small">${n.safety_net.items.map(x => `<li>${esc(x)}</li>`).join("")}</ul></details>
    </div></div>`;
  (document.getElementById("askHost") || box).insertAdjacentHTML("beforeend", `
    <div class="card" id="askCard"><h2>${cp("askTitle")}</h2><p class="muted small">${cp("askSub")}</p>
      <div class="opts" id="askSugg"></div><div class="ask-log" id="askLog" aria-live="polite"></div>
      <form class="row" id="askForm" style="flex-wrap:nowrap"><input type="text" id="askIn" maxlength="500" placeholder="${cp("askPh")}" aria-label="${cp("askTitle")}">
        <button class="btn" type="submit">${cp("ask")}</button></form></div>`);
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
  if (window.loadForecast) loadForecast().catch(() => {});
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
    ${con.tests && con.tests.length ? `<h3 style="margin-bottom:0">${cp("testsT")}</h3><ul class="tests-list small">${con.tests.map(x => `<li class="${x.done ? "done" : ""}">
        <b>${esc(x.name)}</b>${x.done ? ` <span class="tag">${x.via === "result" ? cp("viaResult") : cp("testDone")}</span>` : ""}<span class="spacer"></span>
        ${x.via === "result" ? "" : x.done ? `<button class="chip" data-tst="${esc(x.name)}" data-on="0" data-aid="${aid}">${cp("testUndo")}</button>`
          : `${x.uploadable && window.renderLabs ? `<button class="chip" data-addres="1">${cp("addResult")}</button>` : ""}<button class="chip" data-tst="${esc(x.name)}" data-on="1" data-aid="${aid}">${cp("testMark")}</button>`}</li>`).join("")}</ul>
      ${con.tests_all_done ? `<p class="small">${cp("allTests")}</p>` : ""}`
      : con.tests_ordered.length ? `<p class="small"><b>${cp("conTests")}:</b> ${con.tests_ordered.map(esc).join(", ")}</p>` : ""}
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
  $$("[data-tst]", root).forEach(b => b.onclick = async () => {
    await API.post(`/api/assessments/${b.dataset.aid}/consultation/tests?lang=${LANG}`, { test: b.dataset.tst, done: b.dataset.on === "1" }); after && after();
  });
  $$("[data-addres]", root).forEach(b => b.onclick = () => window.renderLabs && renderLabs());
}

async function renderSharing() {
  const box = document.getElementById("sharing");
  if (!box) return;
  const [s, log, rec, pv] = await Promise.all([API.get(`/api/me/sharing?lang=${LANG}`), API.get(`/api/me/access-log?lang=${LANG}`), API.get(`/api/me/receipts?lang=${LANG}`),
    API.get("/api/me/privacy")]);
  const recLabel = r => cp("rec")[r.recipient] || r.recipient_label;
  box.innerHTML = `<div class="card" style="${pv.paused ? "border-inline-start:4px solid var(--saffron)" : ""}"><h2>${cp("pvTitle")}</h2>
      <h3>${pv.paused ? cp("paused") : cp("pause")}</h3><p class="muted small">${cp("pauseSub")}</p>
      <p><button class="btn ${pv.paused ? "" : "ghost"}" id="cpPause">${pv.paused ? cp("resume") : cp("pause")}</button></p>
      <h3>${cp("keepT")}</h3><p class="muted small">${cp("keepSub")}</p>
      <div class="switch-row"><select id="cpKeep" aria-label="${cp("keepT")}">${pv.retention_options.map(m => `<option value="${m ?? ""}" ${m === pv.retention_months ? "selected" : ""}>${cp("keep")[m]}</option>`).join("")}</select>
        <span class="small muted" id="cpKeepMsg" role="status">${pv.delete_after ? esc(cp("delOn")(cpDate(pv.delete_after))) : ""}</span></div>
      <h3>${cp("remT")}</h3><p class="muted small">${cp("remSub")}</p>
      <label class="check"><input type="checkbox" id="cpRem" ${pv.reminders ? "checked" : ""}><div>${pv.reminders ? cp("remOn") : cp("remOff")}</div></label></div>
    <div class="card"${pv.paused ? ` style="opacity:.6"` : ""}><h2>${cp("shTitle")}</h2><p class="muted small">${cp("shSub")}</p>
      <table class="share-grid small"><tr><th></th>${s.recipients.map(r => `<th class="c">${esc(r.label)}</th>`).join("")}</tr>
      ${s.categories.map(c => `<tr><td>${esc(c.label)}${c.required ? `<br><span class="muted">${cp("required")}</span>` : ""}</td>
        ${s.recipients.map(r => `<td class="c"><input type="checkbox" data-r="${r.key}" data-c="${c.key}" ${s.prefs[r.key].includes(c.key) ? "checked" : ""} ${c.required ? "disabled" : ""}
          aria-label="${esc(r.label)}: ${esc(c.label)}"></td>`).join("")}</tr>`).join("")}</table>
      ${s.partner_links ? `<p class="small">${esc(cp("partnerOn")(s.partner_links))}</p>` : ""}
      <p class="row"><button class="btn" id="shSave">${cp("shSave")}</button><span class="small" id="shMsg" role="status"></span></p></div>
    <div id="sharePreview"></div>
    <div class="card"><h3>${cp("codesT")}</h3>${s.active_codes.length ? s.active_codes.map(x => `<div class="row small" style="margin:6px 0"><span class="code" dir="ltr">${esc(x.code)}</span>
        <span class="muted">${esc(cp("purpose")[x.purpose] || "")} · ${cp("shows")}: ${esc(x.scope.map(k => (s.categories.find(c => c.key === k) || { label: k }).label.split(":")[0]).join("، "))}
          · ${x.used ? cp("used") : cp("unused")} · ${esc(cp("expires")(cpDate(x.expires_at)))}</span><span class="spacer"></span><button class="chip" data-rv="${esc(x.code)}">${cp("revoke")}</button></div>`).join("")
      : `<p class="muted small">${cp("codesNone")}</p>`}
      <h3>${cp("soTitle")}</h3><p class="muted small">${cp("soSub")}</p>
      <div class="opts" id="soCats">${s.categories.map(c => `<label class="check small" style="margin:2px 0"><input type="checkbox" data-so="${c.key}" ${c.required ? "checked disabled" : ""}><div>${esc(c.label)}</div></label>`).join("")}</div>
      <div class="switch-row" style="margin-top:8px"><select id="soDays">${[24, 72, 168].map(h => `<option value="${h}">${cp("soDays")[h]}</option>`).join("")}</select>
        <button class="btn ghost" id="soMake" ${pv.paused ? "disabled" : ""}>${cp("soMake")}</button></div><div id="soOut" role="status"></div></div>
    <div class="card"><h3>${cp("logT")}</h3>${log.entries.length ? `<ul class="small">${log.entries.slice(0, 30).map(e => `<li>${esc(e.text)} <span class="muted">${new Date(e.ts * 1000).toLocaleString(LANG === "ar" ? "ar-AE" : "en-GB")}</span></li>`).join("")}</ul>`
      : `<p class="muted small">${cp("logNone")}</p>`}</div>
    <div class="card"><h3>${cp("recT")}</h3><p class="muted small">${cp("recSub")}</p>
      <ul class="small">${rec.receipts.slice(0, 12).map(r => `<li>${esc(cp("act")[r.action] || cp("act2")[r.action] || r.action)}: ${esc(recLabel(r))} <span class="muted">${cpDate(r.ts)}</span></li>`).join("")}</ul>
      <button class="btn ghost" id="recDl">${cp("recDl")}</button></div>`;
  $("#cpRem").onchange = async e => { await API.post("/api/me/privacy", { reminders: e.target.checked }); renderSharing(); };
  $("#soMake").onclick = async () => {
    const aid = S.aid || store.get("aid");
    if (!aid) return;
    const r = await API.post(`/api/assessments/${aid}/share`, { categories: $$("[data-so]", box).filter(i => i.checked).map(i => i.dataset.so),
      hours: Number($("#soDays").value), purpose: "second_opinion" });
    $("#soOut").innerHTML = `<p class="small">${cp("soMade")}</p><div class="code" dir="ltr">${esc(r.code)}</div>
      <p class="small muted">${cp("soLink")} <span dir="ltr">${esc(location.origin + "/clinic.html")}</span></p>`;
  };
  $("#cpPause").onclick = async () => { await API.post("/api/me/privacy", { paused: !pv.paused }); renderSharing(); };
  $("#cpKeep").onchange = async e => {
    const v = e.target.value === "" ? null : Number(e.target.value);
    try { await API.post("/api/me/privacy", { retention_months: v }); renderSharing(); } catch (err) { $("#cpKeepMsg").textContent = err.message; }
  };
  // the privacy simulator: ticking a box redraws exactly what that recipient would see, before anything is saved
  const aidNow = S.aid || store.get("aid");
  if (aidNow && window.renderSharePreview) {
    const live = recipient => renderSharePreview($("#sharePreview"), aidNow, recipient,
      $$(`[data-r="${recipient}"]`, box).filter(i => i.checked).map(i => i.dataset.c));
    $$(".share-grid input[data-r]", box).forEach(i => i.addEventListener("change", () => live(i.dataset.r)));
    renderSharePreview($("#sharePreview"), aidNow, "clinic").catch(() => {});
  }
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


/* Visit preparation: a checklist built from his own summary and the tests his referral asks for. */
async function loadPrep(aid) {
  const box = document.getElementById("prep");
  if (!box) return;
  const p = await API.get(`/api/assessments/${aid}/prepare?lang=${LANG}`);
  box.innerHTML = `<div class="card"><h2>${cp("prepT")}</h2>${p.sections.filter(sec => sec.items.length).map(sec => `<h3>${esc(sec.title)}</h3>
    <ul class="tests-list small">${sec.items.map(i => `<li><label class="check" style="margin:0"><input type="checkbox"><div>${esc(i.text)}${i.source ? `<br><span class="muted">${cp("prepSrc")}: ${esc(i.source)}</span>` : ""}</div></label></li>`).join("")}</ul>`).join("")}</div>`;
}

/* Three quick ratings after the visit; only k-anonymised averages per clinic leave the server. */
async function loadVisitFeedback(aid) {
  const box = document.getElementById("vfb");
  if (!box) return;
  const f = await API.get(`/api/assessments/${aid}/visit-feedback`);
  if (!f.can_rate) { box.innerHTML = ""; return; }
  if (f.given) { box.innerHTML = `<div class="card"><p class="small">${cp("fbThanks")}</p></div>`; return; }
  const scale = k => `<div style="margin:8px 0"><div class="small">${cp("fbQ")[k]}</div><div class="opts" data-k="${k}">${[1, 2, 3, 4, 5].map(n => `<span class="opt" data-v="${n}">${n}</span>`).join("")}</div></div>`;
  box.innerHTML = `<div class="card"><h2>${cp("fbT")}</h2><p class="muted small">${cp("fbSub")}</p>${["respect", "privacy", "explained"].map(scale).join("")}
    <div class="small">${cp("fbRec")}</div><div class="opts" data-k="recommend"><span class="opt" data-v="1">${cp("yes")}</span><span class="opt" data-v="0">${cp("no")}</span></div>
    <label class="small">${cp("fbWait")}<input type="number" id="fbWait" min="0" max="365" style="max-width:120px;display:block"></label>
    <p class="row"><button class="btn" id="fbSend">${cp("fbSend")}</button><span class="small" id="fbMsg" role="status"></span></p></div>`;
  const val = {};
  $$("[data-k]", box).forEach(g => $$(".opt", g).forEach(o => o.onclick = () => { $$(".opt", g).forEach(x => x.classList.remove("on")); o.classList.add("on"); val[g.dataset.k] = Number(o.dataset.v); }));
  $("#fbSend").onclick = async () => {
    try {
      await API.post(`/api/assessments/${aid}/visit-feedback`, { respect: val.respect, privacy: val.privacy, explained: val.explained,
        recommend: val.recommend === 1, wait_days: $("#fbWait").value === "" ? null : Number($("#fbWait").value) });
      loadVisitFeedback(aid);
    } catch (e) { $("#fbMsg").textContent = e.message; }
  };
}
