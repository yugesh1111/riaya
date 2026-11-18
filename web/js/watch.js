/* How Riaya looks on his wrist. A live preview built from his own Watch-first data: a square face (Apple Watch)
   or a round face (Wear OS, Galaxy Watch, Pixel Watch, Garmin). Screens cycle on their own, like glances:
   his rings for sleep and movement, one finding, and a discreet check-in that never names a health topic.
   Data comes from Apple Health (Apple Watch) or from Health Connect / Garmin / Fitbit exports. */
(function (root) {
  const T = {
    en: { title: "On your wrist", sub: "A preview of Riaya's watch glance, built from your own data. The reminder never says what it is about.",
          apple: "Apple Watch", round: "Wear OS · Garmin", sleep: "Sleep", steps: "Steps", hrv: "HRV", rest: "Resting HR",
          nightly: "h/night", daily: "a day", ms: "ms", bpm: "bpm", checkin: "Weekly check-in", tap: "Tap to open", one: "Tonight",
          tip: "Phone away an hour before bed", private: "Private · no names", pause: "Pause", play: "Play",
          works: "Works with Apple Health (Apple Watch), Health Connect (Wear OS, Galaxy, Pixel), Garmin and Fitbit exports." },
    ar: { title: "على معصمك", sub: "معاينة لنظرة رعاية على الساعة، مبنية من بياناتك. التذكير لا يذكر موضوعه أبداً.",
          apple: "Apple Watch", round: "Wear OS · Garmin", sleep: "النوم", steps: "الخطوات", hrv: "تقلب النبض", rest: "نبض الراحة",
          nightly: "س/ليلة", daily: "يومياً", ms: "م.ث", bpm: "ن/د", checkin: "متابعة أسبوعية", tap: "اضغط للفتح", one: "الليلة",
          tip: "أبعد الهاتف قبل النوم بساعة", private: "خاص · بلا أسماء", pause: "إيقاف", play: "تشغيل",
          works: "يعمل مع Apple Health (ساعة آبل)، وHealth Connect (Wear OS وGalaxy وPixel)، وتصدير Garmin وFitbit." },
  };
  const L = () => (typeof LANG !== "undefined" && LANG === "ar" ? "ar" : "en");
  const x = k => T[L()][k];
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  let timer = null;

  function ring(pct, color, r, w) {
    const C = 2 * Math.PI * r, p = Math.max(0.04, Math.min(1, pct));
    return `<circle r="${r}" cx="60" cy="60" fill="none" stroke="${color}" stroke-opacity=".22" stroke-width="${w}"/>
      <circle r="${r}" cx="60" cy="60" fill="none" stroke="${color}" stroke-width="${w}" stroke-linecap="round"
        stroke-dasharray="${C * p} ${C}" transform="rotate(-90 60 60)" class="wring"/>`;
  }

  function screens(sum, finding) {
    const sleep = sum.sleep_avg_h, steps = sum.steps_avg, hrv = sum.hrv_sdnn_avg, hr = sum.resting_hr_avg;
    const now = new Date(), hh = String(now.getHours()).padStart(2, "0"), mm = String(now.getMinutes()).padStart(2, "0");
    return [
      `<div class="wscr"><div class="wtime">${hh}:${mm}</div>
        <svg viewBox="0 0 120 120" class="wrings" aria-hidden="true">${ring((sleep || 0) / 8, "#7cc4ff", 50, 11)}${ring((steps || 0) / 8000, "#9be15d", 36, 11)}${hrv ? ring(hrv / 60, "#ffb86b", 22, 11) : ""}</svg>
        <div class="wlegend"><span style="color:#7cc4ff">${esc(x("sleep"))} ${sleep ?? "—"}</span><span style="color:#9be15d">${esc(x("steps"))} ${steps != null ? Math.round(steps).toLocaleString() : "—"}</span></div></div>`,
      `<div class="wscr"><div class="wapp"><i></i>Riaya</div>
        <div class="wbig">${sleep ?? "—"}<small>${esc(x("nightly"))}</small></div><div class="wlbl">${esc(x("sleep"))}</div>
        <div class="wrow"><span><b>${hrv ?? "—"}</b> ${esc(x("ms"))}<br><em>${esc(x("hrv"))}</em></span><span><b>${hr ?? "—"}</b> ${esc(x("bpm"))}<br><em>${esc(x("rest"))}</em></span></div></div>`,
      `<div class="wscr"><div class="wapp"><i></i>Riaya</div><div class="wlbl">${esc(x("one"))}</div>
        <div class="wtip">${esc(finding || x("tip"))}</div><div class="wpriv">🔒 ${esc(x("private"))}</div></div>`,
      `<div class="wscr wnote"><div class="wapp"><i></i>Riaya</div><div class="wtip">${esc(x("checkin"))}</div><div class="wbtn">${esc(x("tap"))}</div></div>`,
    ];
  }

  /* host: element; data: the Watch-first response {summary, findings} */
  function mount(host, data) {
    if (!host) return;
    const finding = data.findings && data.findings[0] ? (data.findings[0].label || "").split(" (")[0] : null;
    const scr = screens(data.summary || {}, finding);
    host.innerHTML = `<div class="card watchcard"><h2>⌚ ${esc(x("title"))}</h2><p class="small muted">${esc(x("sub"))}</p>
      <div class="wtabs" role="tablist"><button role="tab" class="on" data-face="square" aria-selected="true">${esc(x("apple"))}</button><button role="tab" data-face="round" aria-selected="false">${esc(x("round"))}</button>
        <span class="spacer" style="flex:1"></span><button class="chip" id="wPlay" aria-pressed="true">❚❚ ${esc(x("pause"))}</button></div>
      <div class="wstage"><div class="watch square" id="watch" dir="ltr" aria-live="polite">
        <div class="wcrown" aria-hidden="true"></div><div class="wface">${scr.map((s, i) => `<div class="wpane ${i ? "" : "on"}" data-i="${i}">${s}</div>`).join("")}</div>
        <div class="wdots">${scr.map((_, i) => `<i class="${i ? "" : "on"}"></i>`).join("")}</div></div></div>
      <p class="small muted">${esc(x("works"))}</p></div>`;
    const w = host.querySelector("#watch");
    let i = 0, playing = true;
    const go = n => {
      i = (n + scr.length) % scr.length;
      w.querySelectorAll(".wpane").forEach((p, k) => p.classList.toggle("on", k === i));
      w.querySelectorAll(".wdots i").forEach((d, k) => d.classList.toggle("on", k === i));
    };
    clearInterval(timer);
    timer = setInterval(() => { if (!document.body.contains(w)) return clearInterval(timer); if (playing) go(i + 1); }, 2800);
    w.onclick = () => go(i + 1);
    host.querySelectorAll("[data-face]").forEach(b => b.onclick = () => {
      w.classList.toggle("square", b.dataset.face === "square"); w.classList.toggle("round", b.dataset.face === "round");
      host.querySelectorAll("[data-face]").forEach(o => { o.classList.toggle("on", o === b); o.setAttribute("aria-selected", o === b); });
    });
    host.querySelector("#wPlay").onclick = e => {
      playing = !playing; e.currentTarget.setAttribute("aria-pressed", playing);
      e.currentTarget.textContent = playing ? `❚❚ ${x("pause")}` : `▶ ${x("play")}`;
    };
  }

  root.WatchPreview = { mount };
})(window);
