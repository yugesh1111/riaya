/* Reach the clinic or your own doctor in one tap, on iPhone and Android.
   - Call: a tel: link (speed dial). WhatsApp: the clinic's official WhatsApp, with a message that holds only the
     handover code, never health details.
   - Save to contacts: a vCard that iPhone and Android both open, saved under a discreet name if he wants.
   - My own doctor: on Android Chrome he can pick the doctor straight from his phone contacts (Contact Picker API);
     on iPhone he types the number. It is kept on this phone only and never sent to Riaya. */
(function (root) {
  const T = {
    en: { reach: "Reach the clinic", call: "Call", wa: "WhatsApp", save: "Save to contacts", discreet: "Save under a discreet name (“Clinic”)",
          waMsg: (code, link) => `Hello, I have a referral from Riaya.${code ? ` My handover code is ${code}.` : ""}${link ? ` ${link}` : ""}`,
          myDoc: "My own doctor", myDocSub: "Add your family doctor so you can call or send them your handover code in one tap. Kept on this phone only.",
          pick: "Choose from contacts", or: "or type the number", name: "Name", num: "Mobile number", keep: "Save", remove: "Remove",
          send: "Send my code on WhatsApp", hours: "Clinic phone lines are usually open on working days.",
          checked: "Numbers from the clinic's official website." },
    ar: { reach: "تواصل مع العيادة", call: "اتصال", wa: "واتساب", save: "احفظ في جهات الاتصال", discreet: "احفظ باسم غير لافت («عيادة»)",
          waMsg: (code, link) => `مرحباً، لدي إحالة من رعاية.${code ? ` رمز التسليم الخاص بي هو ${code}.` : ""}${link ? ` ${link}` : ""}`,
          myDoc: "طبيبي الخاص", myDocSub: "أضف طبيب العائلة لتتصل به أو ترسل له رمز التسليم بلمسة واحدة. يُحفظ على هذا الهاتف فقط.",
          pick: "اختر من جهات الاتصال", or: "أو اكتب الرقم", name: "الاسم", num: "رقم الجوال", keep: "حفظ", remove: "إزالة",
          send: "أرسل رمزي عبر واتساب", hours: "خطوط هواتف العيادات تعمل عادةً في أيام العمل.",
          checked: "الأرقام من الموقع الرسمي للعيادة." },
  };
  const L = () => (typeof LANG !== "undefined" && LANG === "ar" ? "ar" : "en");
  const x = k => T[L()][k];
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const digits = s => String(s || "").replace(/[^\d+]/g, "");
  const waNum = s => digits(s).replace(/^\+/, "").replace(/^0/, "971");
  const canPick = !!(navigator.contacts && navigator.contacts.select);
  const DOC_KEY = "riaya_my_doctor";
  const getDoc = () => { try { return JSON.parse(localStorage.getItem(DOC_KEY) || "null"); } catch { return null; } };
  const setDoc = d => { try { d ? localStorage.setItem(DOC_KEY, JSON.stringify(d)) : localStorage.removeItem(DOC_KEY); } catch {} };

  function vcard(name, tel, url) {
    return ["BEGIN:VCARD", "VERSION:3.0", `FN:${name}`, `N:${name};;;;`, tel ? `TEL;TYPE=WORK,VOICE:${digits(tel)}` : "", url ? `URL:${url}` : "", "END:VCARD", ""]
      .filter(Boolean).join("\r\n");
  }
  function download(text, file) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/vcard" }));
    a.download = file; document.body.appendChild(a); a.click(); a.remove();
  }

  /* Contact bar for a clinic. code = his handover code (optional). */
  function clinicBar(p, code) {
    if (!p || !(p.phone || p.whatsapp)) return "";
    const link = code ? `${location.origin}/clinic.html#code=${code}` : "";
    return `<div class="reach" data-reach="${esc(p.id)}">
      <p class="small" style="margin:0 0 8px"><b>${esc(x("reach"))}</b></p>
      <div class="reach-row">
        ${p.phone ? `<a class="reach-btn" href="tel:${esc(digits(p.phone))}"><span aria-hidden="true">✆</span>${esc(x("call"))}<small dir="ltr">${esc(p.phone)}</small></a>` : ""}
        ${p.whatsapp ? `<a class="reach-btn wa" target="_blank" rel="noopener noreferrer" href="https://wa.me/${esc(waNum(p.whatsapp))}?text=${encodeURIComponent(x("waMsg")(code, link))}"><span aria-hidden="true">◉</span>${esc(x("wa"))}<small dir="ltr">${esc(p.whatsapp)}</small></a>` : ""}
        <button class="reach-btn" type="button" data-vcf><span aria-hidden="true">＋</span>${esc(x("save"))}</button>
      </div>
      <label class="small check" style="margin-top:6px"><input type="checkbox" data-discreet checked><div>${esc(x("discreet"))}</div></label>
      <p class="small muted" style="margin:4px 0 0">${esc(x("checked"))} ${esc(x("hours"))}</p></div>`;
  }

  /* His own doctor, kept on this phone only. */
  function myDoctor(code) {
    const d = getDoc();
    const link = code ? `${location.origin}/clinic.html#code=${code}` : "";
    return `<div class="card reach-doc" id="myDoc"><h3>${esc(x("myDoc"))}</h3><p class="small muted">${esc(x("myDocSub"))}</p>
      ${d ? `<p><b>${esc(d.name)}</b> <span class="muted" dir="ltr">${esc(d.tel)}</span></p>
        <div class="reach-row"><a class="reach-btn" href="tel:${esc(digits(d.tel))}"><span aria-hidden="true">✆</span>${esc(x("call"))}</a>
        <a class="reach-btn wa" target="_blank" rel="noopener noreferrer" href="https://wa.me/${esc(waNum(d.tel))}?text=${encodeURIComponent(x("waMsg")(code, link))}"><span aria-hidden="true">◉</span>${esc(x("send"))}</a>
        <button class="chip" type="button" data-docdel>${esc(x("remove"))}</button></div>`
      : `${canPick ? `<p><button class="btn ghost" type="button" data-docpick>${esc(x("pick"))}</button></p><p class="small muted">${esc(x("or"))}</p>` : ""}
        <div class="row"><input data-docname placeholder="${esc(x("name"))}" autocomplete="off" style="flex:1;min-width:120px">
        <input data-doctel type="tel" dir="ltr" placeholder="${esc(x("num"))}" autocomplete="off" style="flex:1;min-width:140px">
        <button class="btn" type="button" data-docsave>${esc(x("keep"))}</button></div>`}</div>`;
  }

  function wire(host, p, code, rerender) {
    host.querySelectorAll("[data-vcf]").forEach(b => b.onclick = () => {
      const box = b.closest(".reach").querySelector("[data-discreet]");
      const name = box && box.checked ? (L() === "ar" ? "عيادة" : "Clinic") : p.name_en || p.name;
      download(vcard(name, p.phone || p.whatsapp, p.website), "clinic.vcf");
    });
    const doc = host.querySelector("#myDoc");
    if (!doc) return;
    const pickBtn = doc.querySelector("[data-docpick]");
    if (pickBtn) pickBtn.onclick = async () => {
      try {
        const [c] = await navigator.contacts.select(["name", "tel"], { multiple: false });
        if (c && c.tel && c.tel.length) { setDoc({ name: (c.name && c.name[0]) || "Doctor", tel: c.tel[0] }); rerender(); }
      } catch { /* he closed the picker */ }
    };
    const save = doc.querySelector("[data-docsave]");
    if (save) save.onclick = () => {
      const name = doc.querySelector("[data-docname]").value.trim(), tel = doc.querySelector("[data-doctel]").value.trim();
      if (digits(tel).length < 7) { doc.querySelector("[data-doctel]").focus(); return; }
      setDoc({ name: name || (L() === "ar" ? "طبيبي" : "My doctor"), tel }); rerender();
    };
    const del = doc.querySelector("[data-docdel]");
    if (del) del.onclick = () => { setDoc(null); rerender(); };
  }

  root.Reach = { clinicBar, myDoctor, wire, canPick };
})(window);
