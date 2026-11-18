/* "Your best changes" and the 12-week projection (prescriptive + predictive), on the summary page.
   He can switch changes on and off; the chart redraws from the evidence map. Signals only: never a chance of pregnancy. */
(function () {
  const FT = {
    en: { title: "Your best changes", sub: "Ranked by how much each would lower your signals, how strong the research is, and how hard it is.",
      one: "If you do one thing", together: "Together", synergy: (a, b) => `Doing them together lowers your signals by about ${a}%, more than the ${b}% you'd expect from adding them up, because they work on the same pathways.`,
      tiers: { low: "a few signals", moderate: "some signals", high: "several signals" }, from: "from", to: "to",
      pick: "Tap a change to add or remove it from your projection.", chartT: "How your signals could change over 12 weeks", week: "Week",
      first: "First step", effort: "Effort", impact: "on its own" },
    ar: { title: "أفضل التغييرات لك", sub: "مرتبة حسب مقدار خفضها لمؤشراتك، وقوة الدليل، وصعوبتها.",
      one: "إن فعلت شيئاً واحداً", together: "معاً", synergy: (a, b) => `القيام بها معاً يخفض مؤشراتك بنحو ${a}٪، أكثر من ${b}٪ عند جمعها منفردة، لأنها تعمل على المسارات نفسها.`,
      tiers: { low: "مؤشرات قليلة", moderate: "بعض المؤشرات", high: "عدة مؤشرات" }, from: "من", to: "إلى",
      pick: "اضغط على تغيير لإضافته إلى توقعك أو إزالته.", chartT: "كيف قد تتغير مؤشراتك خلال ١٢ أسبوعاً", week: "الأسبوع",
      first: "الخطوة الأولى", effort: "الجهد", impact: "منفرداً" },
  };
  const ft = k => FT[LANG === "ar" ? "ar" : "en"][k];
  const css = document.createElement("style");
  css.textContent = `
    .fc-one { display: grid; grid-template-columns: auto 1fr; gap: 4px 16px; align-items: baseline; padding: 18px 20px; border-radius: 16px;
      background: linear-gradient(135deg, color-mix(in srgb, var(--saffron) 14%, var(--surface)), var(--surface)); border: 1px solid color-mix(in srgb, var(--saffron) 35%, var(--line)); margin: 6px 0 18px; }
    .fc-one .big { font-family: var(--display); font-size: 40px; line-height: 1; letter-spacing: -.02em; grid-row: span 2; }
    .fc-one .k { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
    .fc-row { display: grid; grid-template-columns: 22px minmax(0, 1.4fr) minmax(70px, 1fr) auto; gap: 10px 12px; align-items: center; padding: 12px 0;
      border-top: 1px solid var(--line); cursor: pointer; }
    .fc-row:hover .fc-name { color: var(--ink); }
    .fc-row input { width: 18px; height: 18px; accent-color: var(--saffron); }
    .fc-name { font-weight: 600; } .fc-name small { display: block; font-weight: 400; color: var(--muted); margin-top: 2px; }
    .fc-bar { height: 8px; border-radius: 8px; background: var(--line); overflow: hidden; }
    .fc-bar i { display: block; height: 100%; border-radius: 8px; background: var(--saffron); transform-origin: left; transition: width .5s cubic-bezier(.2,.75,.25,1); }
    [dir=rtl] .fc-bar i { transform-origin: right; }
    .fc-meta { font-size: 12.5px; color: var(--muted); text-align: end; white-space: nowrap; }
    .fc-pill { display: inline-block; padding: 2px 9px; border-radius: 99px; border: 1px solid var(--line); font-size: 12px; margin-inline-start: 6px; }
    .fc-sum { margin: 14px 0 4px; padding: 14px 16px; border-radius: 14px; background: var(--raise); }
    .fc-chart { width: 100%; height: auto; display: block; margin-top: 8px; overflow: visible; }
    .fc-chart .grid line { stroke: var(--line); stroke-width: 1; }
    .fc-chart text { fill: var(--muted); font: 11px var(--font, system-ui); }
    .fc-chart .l { fill: none; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
    @media (prefers-reduced-motion: no-preference) { .fc-chart .l { stroke-dasharray: 900; stroke-dashoffset: 900; animation: fc-draw 1.2s .1s cubic-bezier(.2,.75,.25,1) forwards; } }
    @keyframes fc-draw { to { stroke-dashoffset: 0; } }
    .fc-chart .l.none { stroke: var(--muted); stroke-dasharray: 4 5 !important; stroke-dashoffset: 0 !important; animation: none !important; }
    .fc-chart .l.half { stroke: color-mix(in srgb, var(--saffron) 55%, var(--surface)); }
    .fc-chart .l.full { stroke: var(--saffron); }
    .fc-legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12.5px; color: var(--muted); margin-top: 8px; }
    .fc-legend i { display: inline-block; width: 18px; height: 3px; border-radius: 3px; vertical-align: middle; margin-inline-end: 6px; }
    .fc-tip { font-size: 12px; }
    @media (max-width: 560px) { .fc-row { grid-template-columns: 22px 1fr; } .fc-bar, .fc-meta { grid-column: 2; text-align: start; } .fc-one .big { font-size: 32px; } }`;
  document.head.appendChild(css);

  const n = v => LANG === "ar" ? String(v).replace(/\d/g, d => "٠١٢٣٤٥٦٧٨٩"[d]).replace(".", "٫") : String(v);

  function chart(p) {
    const W = 640, H = 230, L = 34, R = 12, T = 14, B = 30;
    const all = Object.values(p.scenarios).flatMap(s => s.values);
    const lo = Math.max(0, Math.floor((Math.min(...all) - 5) / 10) * 10), hi = 100;
    const x = w => L + (W - L - R) * w / (p.weeks.length - 1), y = v => T + (H - T - B) * (hi - v) / (hi - lo);
    const line = vals => vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const ticks = []; for (let v = lo; v <= hi; v += 10) ticks.push(v);
    const full = p.scenarios.full.values;
    return `<svg class="fc-chart" viewBox="0 0 ${W} ${H}" role="img" dir="ltr" aria-label="${esc(ft("chartT"))}">
      <g class="grid">${ticks.map(v => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${n(v)}</text>`).join("")}</g>
      ${p.weeks.filter(w => w % 2 === 0).map(w => `<text x="${x(w)}" y="${H - 10}" text-anchor="middle">${n(w)}</text>`).join("")}
      ${p.milestones.map(m => `<line x1="${x(m.week)}" x2="${x(m.week)}" y1="${T}" y2="${H - B}" stroke="var(--line)" stroke-dasharray="2 4"/>
        <circle cx="${x(m.week)}" cy="${y(full[m.week])}" r="4.5" fill="var(--surface)" stroke="var(--saffron)" stroke-width="2"><title>${esc(m.text)}</title></circle>`).join("")}
      ${["none", "half", "full"].map(k => `<path class="l ${k}" d="${line(p.scenarios[k].values)}"><title>${esc(p.scenarios[k].label)}: ${n(p.scenarios[k].values.at(-1))}</title></path>`).join("")}
      <text x="${x(p.weeks.length - 1)}" y="${y(full.at(-1)) - 9}" text-anchor="end" style="fill:var(--ink);font-weight:600">${n(full.at(-1))}</text>
    </svg>
    <div class="fc-legend">${["none", "half", "full"].map(k => `<span><i style="background:${k === "none" ? "var(--muted)" : k === "half" ? "color-mix(in srgb, var(--saffron) 55%, var(--surface))" : "var(--saffron)"}"></i>${esc(p.scenarios[k].label)}</span>`).join("")}
      <span>${esc(p.unit === "signal load, today = 100" && LANG === "ar" ? "حِمل المؤشرات، اليوم = ١٠٠" : p.unit)}</span></div>
    <ul class="small muted" style="margin:10px 0 0;padding-inline-start:18px">${p.milestones.map(m => `<li>${ft("week")} ${n(m.week)}: ${esc(m.text)}</li>`).join("")}</ul>`;
  }

  async function loadForecast(nodes) {
    const box = document.getElementById("forecast");
    if (!box || !S.aid) return;
    const f = await API.get(`/api/assessments/${S.aid}/forecast?lang=${LANG}${nodes ? `&nodes=${encodeURIComponent(nodes.join(","))}` : ""}`);
    const b = f.best;
    if (!b.ranked.length) { box.innerHTML = ""; return; }
    const sel = new Set(f.selected);
    const max = Math.max(...b.ranked.map(r => r.impact_pct));
    const o = b.one_thing;
    box.innerHTML = `<div class="card"><h2>${ft("title")}</h2><p class="muted small">${ft("sub")}</p>
      ${o ? `<div class="fc-one"><span class="big">−${n(o.impact_pct)}%</span><span class="k">${ft("one")}</span>
        <span><b>${esc(o.label)}</b> ${o.grade ? gradeTag(o.grade) : ""}<br><span class="small">${ft("first")}: ${esc(o.first_step || "")}</span></span></div>` : ""}
      <p class="small muted">${ft("pick")}</p>
      <div>${b.ranked.slice(0, 7).map(r => `<label class="fc-row"><input type="checkbox" data-node="${r.node}" ${sel.has(r.node) ? "checked" : ""}>
          <span class="fc-name">${esc(r.label)} ${r.grade ? gradeTag(r.grade) : ""}<small>${esc(r.first_step || "")}</small></span>
          <span class="fc-bar" title="−${r.impact_pct}% ${ft("impact")}"><i style="width:${Math.max(4, 100 * r.impact_pct / max)}%"></i></span>
          <span class="fc-meta">−${n(r.impact_pct)}% ${ft("impact")}<span class="fc-pill">${esc(r.effort_label)}</span><br>${esc(r.when)}</span></label>`).join("")}</div>
      ${f.projection.changes.length ? `<div class="fc-sum small"><b>${ft("together")}: −${n(Math.round(100 - f.projection.scenarios.full.values.at(-1)))}%</b>
        ${b.bundle && f.selected.join() === b.bundle.nodes.join() && b.bundle.impact_pct > b.bundle.sum_of_parts_pct + 3 ? `<br>${esc(ft("synergy")(n(Math.round(b.bundle.impact_pct)), n(Math.round(b.bundle.sum_of_parts_pct))))}` : ""}</div>` : ""}
      <h3 style="margin-top:22px">${ft("chartT")}</h3>${f.projection.changes.length ? chart(f.projection) : ""}
      <p class="small muted" style="margin-top:10px">${esc(b.note)}</p></div>`;
    const ft2 = document.getElementById("fTogether");
    if (ft2 && b.bundle && !nodes) ft2.textContent = `−${n(Math.round(b.bundle.impact_pct))}%`;
    box.querySelectorAll("input[data-node]").forEach(i => i.onchange = () => {
      const pick = [...box.querySelectorAll("input[data-node]:checked")].map(x => x.dataset.node);
      loadForecast(pick.length ? pick : ["none"]);
    });
  }
  window.loadForecast = loadForecast;
})();
