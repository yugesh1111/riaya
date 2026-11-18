/* Clinic portal: the receiving specialist opens a referral with the handover code the man gave them.
   No Riaya account. The page shows only what he chose to share with his clinic, and access ends the moment
   the code expires or he withdraws it. The clinic records attendance and sends the visit summary back, which
   updates his journey, his calendar follow-up and his companion's next steps. */
const view = () => $("#view");
const fmt = ts => new Date(ts * 1000).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
const WH = { answers: "questionnaire answers", devices: "watch and sensor data", labs: "lab results", plan: "12-week plan" };
const LEVEL = { andrology: "Andrology / male fertility", urgent_specialist: "Urgent urology", fertility_services: "Couple's fertility services",
  primary_care: "Primary care", same_day_primary: "Same-day primary care", emergency: "Emergency", self_care: "Self-care" };

function signIn(msg) {
  API.token = null;
  sessionStorage.removeItem("cltoken");
  $("#close").classList.add("hidden");
  view().innerHTML = `<div class="card" style="max-width:520px;margin:40px auto">
    <h1>Open a referral</h1>
    <p class="muted">Enter the handover code the patient gave you. You will see only what he chose to share with his clinic. Access lasts up to 12 hours and ends straight away if he withdraws the code.</p>
    ${msg ? `<div class="banner small">${esc(msg)}</div>` : ""}
    <form id="openF"><input type="text" class="codein" id="code" maxlength="20" autocomplete="off" spellcheck="false" aria-label="Handover code" placeholder="XXXX-XXXX" dir="ltr">
      <p class="row"><button class="btn" type="submit">Open referral</button><span class="small" id="oMsg" role="status"></span></p></form>
    <p class="small muted">Every opening is recorded and shown to the patient in his access log.</p></div>`;
  $("#openF").onsubmit = async e => {
    e.preventDefault();
    try {
      const r = await API.post("/api/clinic/open", { code: $("#code").value.trim() });
      API.token = r.token; sessionStorage.setItem("cltoken", r.token); load();
    } catch (err) { $("#oMsg").textContent = err.message; }
  };
  const pre = new URLSearchParams(location.hash.slice(1)).get("code");
  if (pre) $("#code").value = pre;
  $("#code").focus();
}

async function load() {
  let c;
  try { c = await API.get("/api/clinic/case"); }
  catch (e) { return signIn(e.status === 401 ? "Access to this referral has ended. The code expired, or the patient withdrew it or paused sharing." : e.message); }
  $("#close").classList.remove("hidden");
  const L = c.letter;
  const appt = c.appointment;
  const con = c.consultation;
  view().innerHTML = `<div class="cgrid">
    <div>
      <div class="card"><p class="muted small">Referral to ${esc(L.to)} · ${esc(L.date)} · ${c.doctor_reviewed ? `<span class="tag ok">Approved by a Riaya doctor</span>` : `<span class="tag">Not doctor-reviewed</span>`}</p>
        <h1 style="margin-top:4px">${esc(LEVEL[c.level] || c.level)}</h1>
        <p>${esc(c.next_step)}</p>
        ${c.view_only ? `<div class="banner small">View only${c.purpose === "second_opinion" ? ", shared for a second opinion" : ""}. Access ends ${fmt(c.expires_at)} or when he withdraws it.</div>` : ""}
        ${c.withheld.length ? `<div class="banner small withheld">He chose not to share: <b>${c.withheld.map(w => WH[w] || w).join(", ")}</b>. Ask him at the visit if you need it.</div>` : ""}
        <div class="letter">${L.sections.map(s => `<h3>${esc(s.title)}</h3><ul class="small">${s.lines.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`).join("")}</div>
        <p class="row" style="margin-top:16px"><button class="btn ghost" id="fhir">Download FHIR R4 referral</button><button class="btn ghost" id="print">Print</button></p></div>
      ${c.labs && c.labs.length ? `<div class="card"><h2>Results he shared</h2><table class="small"><tr><th>Test</th><th>Latest</th><th>Lab range</th><th>Date</th></tr>
        ${c.labs.filter(x => x.latest).map(x => { const p = x.latest, r = p.ref || {}; return `<tr><td>${esc(x.name)}</td><td><b>${esc(p.value)}</b> ${esc(x.unit || "")}</td>
          <td>${esc(r.text || (r.low != null || r.high != null ? `${r.low ?? ""}–${r.high ?? ""}` : "typical range"))}</td><td>${esc(p.date || "")}</td></tr>`; }).join("")}</table></div>` : ""}
    </div>
    <div>
      ${appt ? `<div class="card"><h2>Appointment</h2><p>${esc(appt.clinic)} · <b>${esc(appt.status)}</b></p>
        ${appt.slot_at ? `<p>${fmt(appt.slot_at)}</p>` : `<p class="muted small">Prefers: ${esc([...(appt.times || []), ...(appt.days || [])].join(", ") || "any time")}</p>`}
        <p class="small muted">Contact: ${appt.contact === "phone" ? "by phone (number held by the coordinator)" : "through Riaya messages only, no calls or SMS"}</p>
        ${!con && appt.status !== "attended" ? `<p class="row"><button class="btn" data-att="attended">He attended</button><button class="btn ghost" data-att="missed">He didn't attend</button></p>` : ""}
        <span class="small" id="aMsg" role="status"></span></div>` : ""}
      ${c.view_only ? "" : `<div class="card"><h2>Visit summary</h2>
        ${con ? `<p>${esc(con.summary)}</p>${con.tests.length ? `<p class="small"><b>Tests ordered:</b> ${con.tests.map(t => `${esc(t.name)}${t.done ? " ✓" : ""}`).join(", ")}</p>` : ""}
          ${con.plan ? `<p class="small"><b>Plan:</b> ${esc(con.plan)}</p>` : ""}<p class="small"><b>Next:</b> ${esc(con.next_label)}${con.followup_at ? `, ${fmt(con.followup_at)}` : ""}</p>
          <p class="small muted">Sent to him. He sees it in his journey, with a calendar entry that says only "Follow-up".</p>`
        : `<p class="small muted">After the visit, write what you found and what happens next in plain words. He sees it in his journey, and his reminders and next steps follow your plan.</p>
        <label class="small">What you found<textarea id="cSum" rows="4" maxlength="1500" placeholder="e.g. Examined today. Small left varicocele, no treatment needed now."></textarea></label>
        <label class="small">Tests ordered (comma-separated)<input type="text" id="cTests" maxlength="400" placeholder="e.g. Semen analysis, FSH, LH, testosterone"></label>
        <label class="small">Plan<textarea id="cPlan" rows="2" maxlength="1500" placeholder="e.g. Stop smoking, cooling habits; repeat tests in 10 weeks."></textarea></label>
        <div class="row"><label class="small" style="flex:2">Next<select id="cNext">${Object.entries(c.next_kinds).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("")}</select></label>
          <label class="small" style="flex:1">in weeks<input type="number" id="cWeeks" min="1" max="52" value="10"></label></div>
        <p class="row"><button class="btn" id="cSave">Send visit summary</button><span class="small" id="cMsg" role="status"></span></p>`}</div>`}
      <div class="card"><h2>Message him</h2><p class="small muted">Goes to his private Riaya messages. Nothing by SMS.</p>
        <textarea id="mBody" rows="2" maxlength="1000"></textarea><p class="row"><button class="btn ghost" id="mSend">Send</button><span class="small" id="mMsg" role="status"></span></p></div>
    </div></div>`;
  $("#fhir").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(c.fhir, null, 1)], { type: "application/fhir+json" })); a.download = "referral.fhir.json"; a.click(); };
  $("#print").onclick = () => window.print();
  $$("[data-att]").forEach(b => b.onclick = async () => { try { await API.post("/api/clinic/attendance", { outcome: b.dataset.att }); load(); } catch (e) { $("#aMsg").textContent = e.message; } });
  if ($("#cSave")) $("#cSave").onclick = async () => {
    const next = $("#cNext").value;
    try {
      await API.post("/api/clinic/consultation", { summary: $("#cSum").value.trim(), plan: $("#cPlan").value.trim() || null, next,
        tests_ordered: $("#cTests").value.split(",").map(x => x.trim()).filter(Boolean), followup_weeks: next === "discharge" ? null : Number($("#cWeeks").value) || null });
      load();
    } catch (e) { $("#cMsg").textContent = e.status === 422 ? "Write at least a sentence about what you found." : e.message; }
  };
  $("#mSend").onclick = async () => {
    const body = $("#mBody").value.trim(); if (!body) return;
    try { await API.post("/api/clinic/message", { body }); $("#mBody").value = ""; $("#mMsg").textContent = "Sent"; } catch (e) { $("#mMsg").textContent = e.message; }
  };
}

$("#close").onclick = () => signIn();
API.token = sessionStorage.getItem("cltoken");
if (API.token) load(); else signIn();
