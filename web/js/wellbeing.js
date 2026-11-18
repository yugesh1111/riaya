/* Wellbeing check (WHO-5), fresh start after a lapse, Ramadan mode and the behaviour-change techniques behind each goal.
   Rendered inside the 12-week plan screen. Everything here talks only to his own plan. */
(function (root) {
  const T = {
    en: {
      who5T: "Two-minute wellbeing check", who5Sub: p => ({ day0: "Your starting point.", day30: "One month in: let's see what changed.", day84: "Twelve weeks: your final check." })[p],
      who5Private: "For you only. A score is never shared unless a doctor review is on and it is very low.",
      who5Save: "Save my answers", who5Score: s => `Your score: ${s} out of 100`,
      who5Chart: "Wellbeing over your plan", points: { day0: "Start", day30: "Day 30", day84: "Day 84" },
      change: c => c == null ? "" : `${c > 0 ? "+" : ""}${c} points since you started` + (Math.abs(c) >= 10 ? (c > 0 ? ": a real improvement." : ": worth talking about.") : "."),
      lapseT: "A rough couple of weeks is normal", lapseSub: "Most people slip at some point. A smaller goal and a plan for what got in the way works better than starting over.",
      keep: "Keep one goal", what: "What got in the way?", fresh: "Make my fresh start",
      ifThen: "Your if-then plan", restarted: "Fresh start",
      ramT: "Ramadan mode", ramSub: "Advice and reminders fit the fast: check-ins after iftar, nothing while you fast.",
      ram: { auto: "Follow the calendar", on: "On", off: "Off" }, ramOn: "Ramadan mode is on",
      how: "Why this works", comb: "Targets",
    },
    ar: {
      who5T: "فحص صحتك النفسية في دقيقتين", who5Sub: p => ({ day0: "نقطة البداية.", day30: "مرّ شهر: لنرَ ما تغيّر.", day84: "اثنا عشر أسبوعاً: فحصك الأخير." })[p],
      who5Private: "لك وحدك. لا تُشارك النتيجة إلا إذا كانت مراجعة الطبيب مفعّلة وكانت منخفضة جداً.",
      who5Save: "احفظ إجاباتي", who5Score: s => `نتيجتك: ${s} من ١٠٠`,
      who5Chart: "صحتك النفسية خلال الخطة", points: { day0: "البداية", day30: "اليوم ٣٠", day84: "اليوم ٨٤" },
      change: c => c == null ? "" : `${c > 0 ? "+" : ""}${c} نقطة منذ البداية` + (Math.abs(c) >= 10 ? (c > 0 ? ": تحسّن حقيقي." : ": يستحق الحديث عنه.") : "."),
      lapseT: "أسبوعان صعبان أمر طبيعي", lapseSub: "معظم الناس يتعثرون في وقت ما. هدف أصغر وخطة لما أعاقك أفضل من البدء من الصفر.",
      keep: "احتفظ بهدف واحد", what: "ما الذي أعاقك؟", fresh: "ابدأ بداية جديدة",
      ifThen: "خطتك «إذا… فإن»", restarted: "بداية جديدة",
      ramT: "وضع رمضان", ramSub: "النصائح والتذكيرات تناسب الصيام: المتابعة بعد الإفطار، ولا شيء أثناء الصيام.",
      ram: { auto: "حسب التقويم", on: "تشغيل", off: "إيقاف" }, ramOn: "وضع رمضان مفعّل",
      how: "لماذا ينجح هذا", comb: "يستهدف",
    },
  };
  const L = () => (typeof LANG !== "undefined" && LANG === "ar" ? "ar" : "en");
  const x = k => T[L()][k];
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  let form = null;

  function who5Chart(w) {
    const pts = ["day0", "day30", "day84"].map(p => ({ p, s: (w.entries.find(e => e.point === p) || {}).score }));
    if (!pts.some(p => p.s != null)) return "";
    const W = 300, H = 90, X = i => 20 + i * 130, Y = s => 8 + (H - 16) * (1 - s / 100);
    const have = pts.map((p, i) => ({ ...p, i })).filter(p => p.s != null);
    return `<svg viewBox="0 0 ${W} ${H + 18}" width="100%" style="max-width:380px;display:block" dir="ltr" role="img"
      aria-label="${esc(x("who5Chart"))}: ${have.map(p => `${x("points")[p.p]} ${p.s}`).join(", ")}">
      <rect x="0" y="${Y(50)}" width="${W}" height="${Y(28) - Y(50)}" fill="var(--saffron)" opacity=".10"/>
      <rect x="0" y="${Y(28)}" width="${W}" height="${Y(0) - Y(28)}" fill="var(--danger, #c0392b)" opacity=".08"/>
      ${have.length > 1 ? `<polyline points="${have.map(p => `${X(p.i)},${Y(p.s)}`).join(" ")}" fill="none" stroke="var(--brand)" stroke-width="2.5"/>` : ""}
      ${have.map(p => `<circle cx="${X(p.i)}" cy="${Y(p.s)}" r="5" fill="var(--brand)"/><text x="${X(p.i)}" y="${Y(p.s) - 9}" font-size="11" text-anchor="middle" fill="var(--ink)">${p.s}</text>`).join("")}
      ${pts.map((p, i) => `<text x="${X(i)}" y="${H + 14}" font-size="10" text-anchor="middle" fill="var(--muted)">${esc(x("points")[p.p])}</text>`).join("")}
    </svg>`;
  }

  function cards(plan) {
    const out = [];
    const w = plan.who5 || {};
    if (plan.ramadan && plan.ramadan.active) {
      out.push(`<div class="card wb-ram"><h3>☾ ${esc(x("ramOn"))}</h3><ul class="small">${plan.ramadan.notes.map(n => `<li>${esc(n)}</li>`).join("")}</ul></div>`);
    }
    if (plan.lapse && !plan.restart && plan.items.length) {
      out.push(`<div class="card wb-lapse" style="border-inline-start:4px solid var(--saffron)"><h2>${esc(x("lapseT"))}</h2><p class="small">${esc(x("lapseSub"))}</p>
        <p class="small"><b>${esc(x("keep"))}</b></p><div class="opts" id="wbKeep">${plan.items.map((i, k) => `<span class="opt${k ? "" : " on"}" role="button" tabindex="0" data-n="${esc(i.node)}">${esc(i.label)}</span>`).join("")}</div>
        <p class="small"><b>${esc(x("what"))}</b></p><div class="opts" id="wbBar"></div>
        <p class="row"><button class="btn" id="wbFresh">${esc(x("fresh"))}</button><span class="small" id="wbMsg" role="status"></span></p></div>`);
    }
    if (plan.restart) {
      out.push(`<div class="card"><span class="tag">${esc(x("restarted"))}</span><h3>${esc(x("ifThen"))}</h3><p>${esc(plan.restart.if_then)}</p></div>`);
    }
    if (w.due) {
      out.push(`<div class="card wb-who5" id="wbWho5"><h2>${esc(x("who5T"))}</h2><p class="small">${esc(x("who5Sub")(w.due))} <span class="muted">${esc(x("who5Private"))}</span></p><div id="wbForm"><p class="muted small">…</p></div>
        <p class="row"><button class="btn" id="wbSave" disabled>${esc(x("who5Save"))}</button><span class="small" id="wbWMsg" role="status"></span></p></div>`);
    }
    if (w.entries && w.entries.length) {
      const band = w.latest_band;
      out.push(`<div class="card"><h3>${esc(x("who5Chart"))}</h3>${who5Chart(w)}
        <p class="small">${esc(x("change")(w.change && w.change.change))}</p>${band ? `<p class="small muted">${esc(band.text)}</p>` : ""}</div>`);
    }
    return out.join("");
  }

  function tags(item) {
    const t = item.techniques;
    const ram = item.ramadan ? `<p class="small wb-ramgoal">☾ ${esc(item.ramadan)}</p>` : "";
    if (!t) return ram;
    return `${ram}<details class="wb-how"><summary class="small">${esc(x("how"))}</summary><p class="small muted" style="margin:6px 0">${esc(x("comb"))}: ${esc(t.com_b)}</p>
      <div class="wb-tags">${t.bct.map(b => `<span class="tag" title="BCT ${esc(b.code)}">${esc(b.code)} ${esc(b.name)}</span>`).join("")}</div></details>`;
  }

  function ramadanSetting(plan) {
    const s = (plan.ramadan && plan.ramadan.setting) || "auto";
    return `<div class="card"><h3>☾ ${esc(x("ramT"))}</h3><p class="small muted">${esc(x("ramSub"))}</p>
      <div class="opts" id="wbRam" role="radiogroup" aria-label="${esc(x("ramT"))}">${["auto", "on", "off"].map(k => `<span class="opt${k === s ? " on" : ""}" role="radio" tabindex="0" aria-checked="${k === s}" data-r="${k}">${esc(x("ram")[k])}</span>`).join("")}</div></div>`;
  }

  const pick = (host, el) => { host.querySelectorAll(".opt").forEach(o => { o.classList.toggle("on", o === el); o.setAttribute("aria-checked", o === el); }); };
  const keyable = (host, fn) => host && host.querySelectorAll(".opt").forEach(o => {
    o.onclick = () => fn(o);  // Enter and Space are handled for every .opt by the shared accessibility helper
  });

  async function wire(plan, rerender) {
    keyable(document.getElementById("wbKeep"), o => pick(o.parentElement, o));
    keyable(document.getElementById("wbRam"), async o => {
      pick(o.parentElement, o);
      await API.post(`/api/me/ramadan?lang=${L()}`, { setting: o.dataset.r }); rerender();
    });
    const bar = document.getElementById("wbBar");
    if (bar) {
      const { barriers } = await API.get(`/api/me/plan/barriers?lang=${L()}`);
      bar.innerHTML = barriers.map(b => `<span class="opt" role="button" tabindex="0" data-b="${esc(b.key)}">${esc(b.label)}</span>`).join("");
      keyable(bar, o => pick(bar, o));
      document.getElementById("wbFresh").onclick = async () => {
        const keep = document.querySelector("#wbKeep .opt.on"), b = bar.querySelector(".opt.on");
        if (!b) { document.getElementById("wbMsg").textContent = x("what"); return; }
        await API.post(`/api/me/plan/restart?lang=${L()}`, { keep: keep.dataset.n, barrier: b.dataset.b }); rerender();
      };
    }
    const host = document.getElementById("wbForm");
    if (host) {
      form = form && form._lang === L() ? form : Object.assign(await API.get(`/api/wellbeing/who5?lang=${L()}`), { _lang: L() });
      host.innerHTML = `<p class="small"><b>${esc(form.title)}</b></p>` + form.items.map(it => `<fieldset class="wb-q"><legend class="small">${esc(it.text)}</legend>
        <div class="opts wb-scale" data-i="${it.i}">${form.scale.map((s, k) => `<span class="opt" role="radio" tabindex="0" aria-checked="false" data-v="${5 - k}">${esc(form.scale[5 - k])}</span>`).join("")}</div></fieldset>`).join("");
      const save = document.getElementById("wbSave");
      host.querySelectorAll(".wb-scale").forEach(g => keyable(g, o => { pick(g, o); save.disabled = host.querySelectorAll(".wb-scale .opt.on").length < 5; }));
      save.onclick = async () => {
        const answers = [...host.querySelectorAll(".wb-scale")].map(g => Number(g.querySelector(".opt.on").dataset.v));
        save.disabled = true;
        try {
          const r = await API.post(`/api/me/plan/who5?lang=${L()}`, { answers });
          const card = document.getElementById("wbWho5");
          card.innerHTML = `<h2>${esc(x("who5Score")(r.score))}</h2><p>${esc(r.band.text)}</p>${r.support_line ? `<p class="small"><b>${esc(r.support_line)}</b></p>` : ""}`;
          setTimeout(rerender, r.band.band === "good" ? 1600 : 6000);
        } catch (e) { document.getElementById("wbWMsg").textContent = e.message; save.disabled = false; }
      };
    }
  }

  root.WB = { cards, tags, wire, ramadanSetting };
})(window);
