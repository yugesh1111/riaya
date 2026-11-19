/* App lock. Riaya is locked by default: once he has anything saved, the app asks him to set a PIN, and from then on
   every opening, and every return from another app, shows the lock first. Face ID, Touch ID or fingerprint can
   unlock it too (WebAuthn platform authenticator, checked on this phone only).
   - The PIN is never stored: only a PBKDF2-SHA-256 hash (210,000 rounds, random salt).
   - Documents kept on the phone (scanned reports, files from the doctor) are encrypted with AES-GCM using a key that
     is generated on the phone and cannot be exported from the browser. They open only after unlocking.
   - Forgot the PIN: he can erase Riaya from this phone and restore his record later with his recovery code.
   - Calculator disguise: calc.html unlocks with PIN then "=", and hands over here without showing the lock again.
   Scope "user" protects the man's app; scope "doc" protects the clinician console on a shared computer. */
(function (root) {
  const T = {
    en: { title: "Riaya is locked", sub: "Enter your PIN", setT: "Protect Riaya with a PIN", setSub: "Your summary, reports and messages stay locked until you enter it. 4 to 6 digits.",
          again: "Enter it again", wrong: "That PIN isn't right", mismatch: "The two PINs don't match. Try again.", bio: "Use Face ID / fingerprint",
          bioSet: "Also unlock with Face ID / fingerprint", forgot: "Forgot PIN?", forgotQ: "Erase Riaya from this phone? You can restore your record later with your recovery code.",
          erase: "Erase from this phone", cancel: "Cancel", wait: s => `Too many tries. Wait ${s} s.`, del: "Delete", locked: "Locked",
          lockNow: "Lock now", change: "Change PIN", bioOn: "Face ID / fingerprint is on", bioOff: "Turn on Face ID / fingerprint",
          card: "App lock", cardSub: "Riaya locks every time you open it or come back from another app. Documents on this phone are encrypted.",
          bioT: "Unlock with Face ID or fingerprint?", bioSub: "Faster than your PIN, and your face or fingerprint never leaves this phone. Your PIN still works.",
          bioYes: "Use Face ID / fingerprint", notNow: "Not now", bioDone: "All set", bioFail: "That didn't work. You can turn it on later in Privacy." },
    ar: { title: "رعاية مقفلة", sub: "أدخل رمزك", setT: "احمِ رعاية برمز سري", setSub: "يبقى ملخصك وتقاريرك ورسائلك مقفلة حتى تدخله. من ٤ إلى ٦ أرقام.",
          again: "أدخله مرة أخرى", wrong: "الرمز غير صحيح", mismatch: "الرمزان غير متطابقين. حاول مرة أخرى.", bio: "استخدم بصمة الوجه / الإصبع",
          bioSet: "افتح أيضاً ببصمة الوجه / الإصبع", forgot: "نسيت الرمز؟", forgotQ: "هل تريد مسح رعاية من هذا الهاتف؟ يمكنك استعادة سجلك لاحقاً برمز الاسترداد.",
          erase: "امسح من هذا الهاتف", cancel: "إلغاء", wait: s => `محاولات كثيرة. انتظر ${s} ثانية.`, del: "حذف", locked: "مقفلة",
          lockNow: "اقفل الآن", change: "غيّر الرمز", bioOn: "بصمة الوجه / الإصبع مفعّلة", bioOff: "فعّل بصمة الوجه / الإصبع",
          card: "قفل التطبيق", cardSub: "تُقفل رعاية في كل مرة تفتحها أو تعود إليها من تطبيق آخر. المستندات على هذا الهاتف مشفّرة.",
          bioT: "هل تفتح ببصمة الوجه أو الإصبع؟", bioSub: "أسرع من الرمز، وبصمتك لا تغادر هذا الهاتف أبداً. يبقى رمزك صالحاً.",
          bioYes: "استخدم بصمة الوجه / الإصبع", notNow: "ليس الآن", bioDone: "تم", bioFail: "لم ينجح ذلك. يمكنك تفعيله لاحقاً من الخصوصية." },
  };
  const L = () => ((typeof LANG !== "undefined" ? LANG : document.documentElement.lang) === "ar" ? "ar" : "en");
  const x = k => T[L()][k];
  const scope = (document.currentScript && document.currentScript.dataset.scope) || "user";
  const KEY = scope === "doc" ? "riaya_lock_doc" : "riaya_lock";
  const UNLOCK_FLAG = KEY + "_open";   // sessionStorage: unlocked in this tab (survives reloads, not app restarts)
  const enc = new TextEncoder();
  const b64 = buf => btoa(String.fromCharCode(...new Uint8Array(buf)));
  const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch { return null; } };
  const write = v => { try { v ? localStorage.setItem(KEY, JSON.stringify(v)) : localStorage.removeItem(KEY); } catch {} };
  const ss = { get: k => { try { return sessionStorage.getItem(k); } catch { return null; } }, set: (k, v) => { try { sessionStorage.setItem(k, v); } catch {} },
               del: k => { try { sessionStorage.removeItem(k); } catch {} } };

  async function hash(pin, salt) {
    const k = await crypto.subtle.importKey("raw", enc.encode(pin), "PBKDF2", false, ["deriveBits"]);
    return b64(await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations: 210000 }, k, 256));
  }
  async function checkPin(pin) {
    const s = read();
    return !!s && (await hash(pin, unb64(s.salt))) === s.hash;
  }

  // ---------- on-phone encryption key (non-extractable AES-GCM, kept in IndexedDB)
  let dataKey = null;
  function idb() {
    return new Promise((ok, no) => { const r = indexedDB.open("riaya-keys", 1); r.onupgradeneeded = () => r.result.createObjectStore("k"); r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  }
  async function keyStore(op, val) {
    const d = await idb();
    return new Promise((ok, no) => { const tx = d.transaction("k", op === "get" ? "readonly" : "readwrite"), st = tx.objectStore("k");
      const r = op === "get" ? st.get("data") : op === "del" ? st.delete("data") : st.put(val, "data"); r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });
  }
  async function getKey() {
    if (dataKey) return dataKey;
    dataKey = await keyStore("get").catch(() => null);
    if (!dataKey) { dataKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]); await keyStore("put", dataKey).catch(() => {}); }
    return dataKey;
  }
  async function encryptBlob(blob) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const data = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await getKey(), await blob.arrayBuffer());
    return { iv: b64(iv), data, type: blob.type, encrypted: true };
  }
  async function decryptBlob(rec) {
    if (!rec || !rec.encrypted) return rec instanceof Blob ? rec : null;
    if (!isOpen()) throw new Error(x("locked"));
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(rec.iv) }, await getKey(), rec.data);
    return new Blob([plain], { type: rec.type });
  }

  // ---------- biometrics (local user verification)
  const bioAvailable = async () => !!(root.PublicKeyCredential && PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable &&
    await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable().catch(() => false));
  async function enrolBio() {
    const s = read(); if (!s) return false;
    const cred = await navigator.credentials.create({ publicKey: {
      challenge: crypto.getRandomValues(new Uint8Array(32)), rp: { name: "Riaya" },
      user: { id: crypto.getRandomValues(new Uint8Array(16)), name: "riaya-" + scope, displayName: "Riaya" },
      pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }],
      authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required", residentKey: "discouraged" }, timeout: 60000 } });
    write({ ...s, bio: b64(cred.rawId) });
    return true;
  }
  async function bioUnlock() {
    const s = read(); if (!s || !s.bio) return false;
    try {
      await navigator.credentials.get({ publicKey: { challenge: crypto.getRandomValues(new Uint8Array(32)), allowCredentials: [{ type: "public-key", id: unb64(s.bio) }],
                                                     userVerification: "required", timeout: 60000 } });
      return true;
    } catch { return false; }
  }

  const BIO_ICON = `<svg viewBox="0 0 64 64" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M6 20V12a6 6 0 0 1 6-6h8M44 6h8a6 6 0 0 1 6 6v8M58 44v8a6 6 0 0 1-6 6h-8M20 58h-8a6 6 0 0 1-6-6v-8"/>
    <path d="M23 24v4M41 24v4M32 24v12h-3M24 43c4.5 4 11.5 4 16 0"/></svg>`;

  // ---------- state
  const hasPin = () => !!read();
  const isOpen = () => ss.get(UNLOCK_FLAG) === "1";
  const touring = () => !!(root.Tour && root.Tour.state && root.Tour.state.on);
  const needsSetup = () => !touring() && (scope === "user" ? !hasPin() && !!(localStorage.getItem("token")) && localStorage.getItem("done") === "1"
                                                             : !hasPin() && !!ss.get("ctoken"));
  function open() { ss.set(UNLOCK_FLAG, "1"); document.documentElement.classList.remove("locked"); sheet && sheet.remove(); sheet = null; root.dispatchEvent(new Event("riaya:unlocked")); }
  function lock() { if (!hasPin()) return; ss.del(UNLOCK_FLAG); show(); }

  // ---------- the lock screen
  let sheet = null, entry = "", first = null, fails = 0, until = 0;
  const css = document.createElement("style");
  css.textContent = `
    html.locked body > *:not(.lk) { visibility: hidden !important; }
    .lk { position: fixed; inset: 0; z-index: 1000; background: radial-gradient(120% 90% at 50% 0%, #143041, #0b1a24 60%); color: #eef0ec;
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; padding: 24px; font-family: "IBM Plex Sans", "IBM Plex Sans Arabic", system-ui, sans-serif; }
    .lk img { width: 64px; height: 64px; border-radius: 16px; }
    .lk h2 { margin: 4px 0 0; font-weight: 500; font-size: 22px; text-align: center; } .lk p { margin: 0; color: #9fb0ba; text-align: center; max-width: 320px; font-size: 14px; }
    .lk .dots { display: flex; gap: 12px; margin: 10px 0 4px; direction: ltr; } .lk .dots i { width: 13px; height: 13px; border-radius: 50%; border: 1.5px solid #c9a86a; transition: background .15s; }
    .lk .dots i.on { background: #c9a86a; } .lk .dots.shake { animation: lkshake .35s; }
    @keyframes lkshake { 25% { transform: translateX(-8px); } 75% { transform: translateX(8px); } }
    .lk .pad { display: grid; grid-template-columns: repeat(3, 72px); gap: 12px; direction: ltr; }
    .lk .pad button { width: 72px; height: 72px; border-radius: 50%; border: 1px solid rgba(238,240,236,.16); background: rgba(238,240,236,.06); color: #eef0ec; font: 500 24px/1 inherit; cursor: pointer; }
    .lk .pad button:active { background: rgba(238,240,236,.18); } .lk .pad button:focus-visible, .lk .lnk:focus-visible { outline: 3px solid #c9a86a; outline-offset: 2px; }
    .lk .pad .ghost { border: 0; background: transparent; font-size: 15px; }
    .lk .lnk { background: none; border: 0; color: #c9a86a; font: inherit; font-size: 14px; cursor: pointer; padding: 8px; }
    .lk .msg { min-height: 20px; color: #f0b3a8; font-size: 14px; }
    .lk .bioic { width: 96px; height: 96px; color: #c9a86a; margin: 6px 0 4px; } .lk .bioic.ok { color: #9be15d; }
    .lk .bioic svg path { stroke-dasharray: 220; stroke-dashoffset: 220; animation: lkdraw 1.1s cubic-bezier(.2,.8,.2,1) forwards; }
    @keyframes lkdraw { to { stroke-dashoffset: 0; } }
    .lk .primary { min-width: 260px; padding: 15px 22px; border-radius: 999px; border: 0; background: #eef0ec; color: #0f2a3a; font: 600 16px/1 inherit; cursor: pointer; margin-top: 12px; }
    .lk .primary:focus-visible { outline: 3px solid #c9a86a; outline-offset: 3px; }
    .lk .step { display: flex; flex-direction: column; align-items: center; gap: 10px; animation: lkin .35s cubic-bezier(.2,.8,.2,1); }
    @keyframes lkin { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
    .lk .pad .bio { color: #c9a86a; padding: 20px; }
    @media (prefers-reduced-motion: reduce) { .lk .dots.shake, .lk .step, .lk .bioic svg path { animation: none; stroke-dashoffset: 0; } }`;
  document.head.appendChild(css);

  function show(setup) {
    document.documentElement.classList.add("locked");
    sheet && sheet.remove();
    entry = ""; first = null;
    sheet = document.createElement("div");
    sheet.className = "lk"; sheet.setAttribute("role", "dialog"); sheet.setAttribute("aria-modal", "true");
    const s = read();
    const mode = setup ? "set" : "unlock";
    sheet.innerHTML = `<img src="icons/icon-192.png" alt="">
      <h2 id="lkT">${esc(mode === "set" ? x("setT") : x("title"))}</h2><p id="lkS">${esc(mode === "set" ? x("setSub") : x("sub"))}</p>
      <div class="dots" id="lkD" aria-hidden="true">${"<i></i>".repeat(6)}</div><div class="msg" id="lkM" role="status" aria-live="assertive"></div>
      <div class="pad" role="group" aria-label="PIN">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => `<button type="button" data-k="${n}">${n}</button>`).join("")}
        <button type="button" class="ghost bio" data-k="bio" aria-label="${esc(x("bio"))}" ${mode === "unlock" && s && s.bio ? "" : "style='visibility:hidden'"}>${BIO_ICON}</button>
        <button type="button" data-k="0">0</button><button type="button" class="ghost" data-k="back" aria-label="${esc(x("del"))}">⌫</button></div>
      ${mode === "set" ? `<button type="button" class="lnk" id="lkOk" hidden>OK</button>` : `<button type="button" class="lnk" id="lkForgot">${esc(x("forgot"))}</button>`}`;
    document.body.appendChild(sheet);
    const dots = sheet.querySelector("#lkD"), msg = sheet.querySelector("#lkM");
    const paint = () => [...dots.children].forEach((d, i) => d.classList.toggle("on", i < entry.length));
    const shake = t => { msg.textContent = t; dots.classList.remove("shake"); void dots.offsetWidth; dots.classList.add("shake"); entry = ""; paint(); };
    const submit = async () => {
      if (mode === "unlock") {
        if (Date.now() < until) return shake(x("wait")(Math.ceil((until - Date.now()) / 1000)));
        if (await checkPin(entry)) { fails = 0; return open(); }
        if (++fails >= 5) until = Date.now() + 30000 * (fails - 4);
        return shake(x("wrong"));
      }
      if (!first) { first = entry; entry = ""; paint(); sheet.querySelector("#lkS").textContent = x("again"); sheet.querySelector("#lkOk").hidden = true; return; }
      if (entry !== first) { first = null; sheet.querySelector("#lkS").textContent = x("setSub"); return shake(x("mismatch")); }
      const salt = crypto.getRandomValues(new Uint8Array(16));
      write({ salt: b64(salt), hash: await hash(entry, salt), len: entry.length, at: Date.now() });
      await getKey().catch(() => {});
      if (await bioAvailable()) return bioStep();
      open();
    };
    // second step after the PIN: offer Face ID / fingerprint as its own clear choice
    const bioStep = () => {
      sheet.innerHTML = `<div class="step"><div class="bioic" id="lkBi">${BIO_ICON}</div>
        <h2>${esc(x("bioT"))}</h2><p>${esc(x("bioSub"))}</p>
        <button type="button" class="primary" id="lkYes">${esc(x("bioYes"))}</button>
        <button type="button" class="lnk" id="lkNo">${esc(x("notNow"))}</button><div class="msg" id="lkM2" role="status" aria-live="polite"></div></div>`;
      sheet.querySelector("#lkNo").onclick = () => open();
      sheet.querySelector("#lkYes").onclick = async () => {
        const ok = await enrolBio().catch(() => false);
        if (!ok) { sheet.querySelector("#lkM2").textContent = x("bioFail"); setTimeout(open, 1800); return; }
        const ic = sheet.querySelector("#lkBi"); ic.classList.add("ok");
        ic.innerHTML = `<svg viewBox="0 0 64 64" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M32 4a28 28 0 1 1 0 56a28 28 0 1 1 0-56M20 33l8 8 16-17"/></svg>`;
        sheet.querySelector("h2").textContent = x("bioDone");
        setTimeout(open, 900);
      };
      setTimeout(() => sheet.querySelector("#lkYes").focus(), 30);
    };
    const press = async k => {
      msg.textContent = "";
      if (k === "back") { entry = entry.slice(0, -1); paint(); return; }
      if (k === "bio") { if (await bioUnlock()) open(); return; }
      if (entry.length >= 6) return;
      entry += k; paint();
      if (mode === "set") { const ok = sheet.querySelector("#lkOk"); ok.hidden = entry.length < 4; ok.textContent = first ? "OK" : (L() === "ar" ? "التالي" : "Next"); if (entry.length === 6) submit(); }
      else if (entry.length >= 4 && entry.length === (read().len || 0)) submit();
      else if (entry.length === 6) submit();
    };
    sheet.querySelectorAll("[data-k]").forEach(b => b.onclick = () => press(b.dataset.k));
    if (mode === "set") sheet.querySelector("#lkOk").onclick = submit;
    sheet.addEventListener("keydown", e => { if (/^\d$/.test(e.key)) press(e.key); else if (e.key === "Backspace") press("back"); else if (e.key === "Enter") submit(); });
    const forgot = sheet.querySelector("#lkForgot");
    if (forgot) forgot.onclick = async () => {
      if (!confirm(x("forgotQ"))) return;
      try { localStorage.clear(); sessionStorage.clear(); } catch {}
      try { indexedDB.deleteDatabase("riaya-docs"); indexedDB.deleteDatabase("riaya-keys"); } catch {}
      location.reload();
    };
    setTimeout(() => sheet && sheet.querySelector("[data-k='1']").focus(), 30);
    if (mode === "unlock" && s && s.bio) bioUnlock().then(ok => ok && open());
  }

  // ---------- when to lock
  function guard() {
    if (touring()) return;
    if (needsSetup()) return show(true);
    if (hasPin() && !isOpen()) show(false);
  }
  // Away for more than 15 seconds (another app, the lock screen, a closed lid) locks it again. Shorter trips, such as
  // taking a photo of a report with the camera, don't; the privacy blur still hides the screen in the app switcher.
  let hiddenAt = 0;
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { hiddenAt = Date.now(); return; }
    if (hasPin() && hiddenAt && Date.now() - hiddenAt > 15000) ss.del(UNLOCK_FLAG);
    guard();
  });
  root.addEventListener("pageshow", guard);
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", guard) : guard();

  // settings card for the privacy page
  async function settingsCard() {
    const s = read(), bio = await bioAvailable();
    return `<div class="card" id="lkCard"><h3>🔒 ${esc(x("card"))}</h3><p class="small muted">${esc(x("cardSub"))}</p>
      <p class="row"><button class="btn ghost" type="button" data-lk="lock">${esc(x("lockNow"))}</button><button class="chip" type="button" data-lk="change">${esc(x("change"))}</button>
      ${bio ? (s && s.bio ? `<span class="tag">✓ ${esc(x("bioOn"))}</span>` : `<button class="chip" type="button" data-lk="bio">${esc(x("bioOff"))}</button>`) : ""}</p></div>`;
  }
  function wireCard(host, rerender) {
    host.querySelectorAll("[data-lk]").forEach(b => b.onclick = async () => {
      if (b.dataset.lk === "lock") lock();
      else if (b.dataset.lk === "change") { const old = read(); write(null); show(true); root.addEventListener("riaya:unlocked", () => { if (!read()) write(old); }, { once: true }); }
      else if (b.dataset.lk === "bio") { await enrolBio().catch(() => {}); rerender && rerender(); }
    });
  }

  root.Lock = { guard, lock, open, isOpen, hasPin, checkPin, encryptBlob, decryptBlob, settingsCard, wireCard, show, UNLOCK_FLAG, scope };
})(window);
