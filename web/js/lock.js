/* App lock. Riaya is locked by default: once he has anything saved, the app asks him to set a PIN, and from then on
   every opening, and every return from another app, shows the lock first. Face ID, Touch ID or fingerprint can
   unlock it too (WebAuthn platform authenticator, checked on this phone only).
   - The PIN is never stored: only a PBKDF2-SHA-256 hash (210,000 rounds, random salt).
   - Documents kept on the phone (scanned reports, files from the doctor) are encrypted with AES-GCM using a key that
     is generated on the phone and cannot be exported from the browser. They open only after unlocking.
   - Forgot the PIN: he can erase Riaya from this phone and restore his record later with his recovery code.
   - Calculator cover (his choice at setup): the lock screen is a working calculator; his PIN then "=" opens Riaya.
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
          bioYes: "Use Face ID / fingerprint", notNow: "Not now", bioDone: "All set", bioFail: "That didn't work. You can turn it on later in Privacy.",
          verT: "Confirm it's you", verSub: "To open this document",
          coverQ: "How should Riaya look when you open it?", coverSub: "You can change this later in Privacy.",
          plainT: "Riaya, with a PIN lock", plainS: "Opens to a lock screen. Face ID or fingerprint can open it.",
          calcT: "A calculator (cover)", calcS: "Anyone who opens it sees a working calculator. Type your PIN and press = to open Riaya.",
          setCalcT: "Choose your secret PIN", setCalcSub: "You'll type it into the calculator, then press =. 4 to 6 digits.",
          coverDone: "Done. From now on Riaya opens as a calculator.", coverHow: "To open Riaya: type your PIN, then press =.", gotIt: "Got it",
          coverOn: "Calculator cover is on", coverOff: "Use the calculator cover", coverTurnOff: "Turn the cover off" },
    ar: { title: "رعاية مقفلة", sub: "أدخل رمزك", setT: "احمِ رعاية برمز سري", setSub: "يبقى ملخصك وتقاريرك ورسائلك مقفلة حتى تدخله. من ٤ إلى ٦ أرقام.",
          again: "أدخله مرة أخرى", wrong: "الرمز غير صحيح", mismatch: "الرمزان غير متطابقين. حاول مرة أخرى.", bio: "استخدم بصمة الوجه / الإصبع",
          bioSet: "افتح أيضاً ببصمة الوجه / الإصبع", forgot: "نسيت الرمز؟", forgotQ: "هل تريد مسح رعاية من هذا الهاتف؟ يمكنك استعادة سجلك لاحقاً برمز الاسترداد.",
          erase: "امسح من هذا الهاتف", cancel: "إلغاء", wait: s => `محاولات كثيرة. انتظر ${s} ثانية.`, del: "حذف", locked: "مقفلة",
          lockNow: "اقفل الآن", change: "غيّر الرمز", bioOn: "بصمة الوجه / الإصبع مفعّلة", bioOff: "فعّل بصمة الوجه / الإصبع",
          card: "قفل التطبيق", cardSub: "تُقفل رعاية في كل مرة تفتحها أو تعود إليها من تطبيق آخر. المستندات على هذا الهاتف مشفّرة.",
          bioT: "هل تفتح ببصمة الوجه أو الإصبع؟", bioSub: "أسرع من الرمز، وبصمتك لا تغادر هذا الهاتف أبداً. يبقى رمزك صالحاً.",
          bioYes: "استخدم بصمة الوجه / الإصبع", notNow: "ليس الآن", bioDone: "تم", bioFail: "لم ينجح ذلك. يمكنك تفعيله لاحقاً من الخصوصية.",
          verT: "تأكيد هويتك", verSub: "لفتح هذا المستند",
          coverQ: "كيف تريد أن تبدو رعاية عند فتحها؟", coverSub: "يمكنك تغيير ذلك لاحقاً من الخصوصية.",
          plainT: "رعاية مع قفل برمز", plainS: "تُفتح على شاشة قفل. يمكن فتحها ببصمة الوجه أو الإصبع.",
          calcT: "آلة حاسبة (غطاء)", calcS: "من يفتحها يرى آلة حاسبة تعمل. اكتب رمزك واضغط = لتفتح رعاية.",
          setCalcT: "اختر رمزك السري", setCalcSub: "ستكتبه في الآلة الحاسبة ثم تضغط =. من ٤ إلى ٦ أرقام.",
          coverDone: "تم. من الآن تُفتح رعاية على شكل آلة حاسبة.", coverHow: "لفتح رعاية: اكتب رمزك ثم اضغط =.", gotIt: "فهمت",
          coverOn: "غطاء الآلة الحاسبة مفعّل", coverOff: "استخدم غطاء الآلة الحاسبة", coverTurnOff: "أوقف الغطاء" },
  };
  const L = () => ((typeof LANG !== "undefined" ? LANG : document.documentElement.lang) === "ar" ? "ar" : "en");

  /* Look and words follow the device: iPhone/iPad → Face ID and an iOS-style keypad; Mac → Touch ID; Android
     (Samsung One UI and others) → fingerprint and a flat One UI keypad. "?skin=apple" or "?skin=android" in the URL
     forces a look (for the demo video). */
  const ua = navigator.userAgent;
  const forced = (() => { try { const q = new URLSearchParams(location.search).get("skin"); if (q) sessionStorage.setItem("riaya_skin", q); return sessionStorage.getItem("riaya_skin"); } catch { return null; } })();
  const DEVICE = forced === "android" ? "android" : forced === "apple" ? "ios"
    : /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) ? "ios" : /Android/.test(ua) ? "android" : /Macintosh/.test(ua) ? "mac" : "other";
  const SKIN = DEVICE === "android" ? "android" : DEVICE === "other" ? "neutral" : "apple";
  const BIO_NAME = { ios: ["Face ID", "بصمة الوجه"], mac: ["Touch ID", "بصمة الإصبع"], android: ["fingerprint", "بصمة الإصبع"], other: ["Windows Hello", "Windows Hello"] }[DEVICE];
  const x = k => String(T[L()][k]).replace(/Face ID (?:\/|or) fingerprint/g, BIO_NAME[0]).replace(/بصمة الوجه (?:\/|أو) الإصبع/g, BIO_NAME[1]);
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

  const FP_ICON = `<svg viewBox="0 0 64 64" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true">
    <path d="M18 14a24 24 0 0 1 28 0M12 26a22 22 0 0 1 40 0M20 52c3-6 4-12 4-18a8 8 0 0 1 16 0c0 4-.5 8-1.5 12M32 34c0 8-2 15-6 21M44 38c0 6-1 11-3 16M14 42c2-2 3-5 3-8a15 15 0 0 1 30 0"/></svg>`;
  const BIO_GLYPH = DEVICE === "ios" ? BIO_ICON : FP_ICON;

  // ---------- state
  const hasPin = () => !!read();
  const isOpen = () => ss.get(UNLOCK_FLAG) === "1";
  const touring = () => !!(root.Tour && root.Tour.state && root.Tour.state.on);
  const needsSetup = () => !touring() && (scope === "user" ? !hasPin() && !!(localStorage.getItem("token")) && localStorage.getItem("done") === "1"
                                                             : !hasPin() && !!ss.get("ctoken"));
  let verifying = null;
  function open() {
    if (verifying) { const r = verifying; verifying = null; sheet && sheet.remove(); sheet = null; document.documentElement.classList.remove("locked"); return r(true); }
    if (savedTitle !== null) { document.title = savedTitle; savedTitle = null; }
    ss.set(UNLOCK_FLAG, "1"); document.documentElement.classList.remove("locked"); sheet && sheet.remove(); sheet = null; root.dispatchEvent(new Event("riaya:unlocked")); }
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
    .lk .lk-lang { position: absolute; top: max(16px, env(safe-area-inset-top)); inset-inline-end: 16px; display: inline-flex; padding: 3px; border-radius: 999px;
      border: 1px solid rgba(238,240,236,.2); background: transparent; cursor: pointer; direction: ltr; }
    .lk .lk-lang span { padding: 5px 11px; border-radius: 999px; font: 600 13px/1.2 inherit; color: #9fb0ba; } .lk .lk-lang span.on { background: #eef0ec; color: #0f2a3a; }
    .lk .msg { min-height: 20px; color: #f0b3a8; font-size: 14px; }
    .lk .bioic { width: 96px; height: 96px; color: #c9a86a; margin: 6px 0 4px; } .lk .bioic.ok { color: #9be15d; }
    .lk .bioic svg path { stroke-dasharray: 220; stroke-dashoffset: 220; animation: lkdraw 1.1s cubic-bezier(.2,.8,.2,1) forwards; }
    @keyframes lkdraw { to { stroke-dashoffset: 0; } }
    .lk .primary { min-width: 260px; padding: 15px 22px; border-radius: 999px; border: 0; background: #eef0ec; color: #0f2a3a; font: 600 16px/1 inherit; cursor: pointer; margin-top: 12px; }
    .lk .primary:focus-visible { outline: 3px solid #c9a86a; outline-offset: 3px; }
    .lk .step { display: flex; flex-direction: column; align-items: center; gap: 10px; animation: lkin .35s cubic-bezier(.2,.8,.2,1); }
    @keyframes lkin { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
    .lk .pad .bio { color: #c9a86a; padding: 20px; }
    .lk .pad button b { font-weight: inherit; } .lk .pad button small { display: block; }
    /* Apple: iOS passcode screen feel */
    .lk-apple { font-family: -apple-system, "SF Pro Text", "SF Arabic", system-ui, sans-serif; background: radial-gradient(140% 100% at 50% 0%, #2b4a5e 0%, #13263a 45%, #070d14 100%); }
    .lk-apple h2 { font-weight: 400; font-size: 20px; letter-spacing: -.01em; } .lk-apple p { color: rgba(255,255,255,.7); }
    .lk-apple img { width: 52px; height: 52px; border-radius: 12px; box-shadow: 0 6px 20px rgba(0,0,0,.35); }
    .lk-apple .dots { gap: 18px; } .lk-apple .dots i { width: 13px; height: 13px; border: 1.3px solid #fff; } .lk-apple .dots i.on { background: #fff; }
    .lk-apple .pad { grid-template-columns: repeat(3, 78px); gap: 16px 26px; margin-top: 18px; }
    .lk-apple .pad button { width: 78px; height: 78px; border: 0; background: rgba(255,255,255,.16); -webkit-backdrop-filter: blur(20px); backdrop-filter: blur(20px);
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px; transition: background .12s; }
    .lk-apple .pad button b { font-size: 36px; font-weight: 300; line-height: 1; }
    .lk-apple .pad button small { font-size: 10px; font-weight: 600; letter-spacing: .22em; opacity: .9; margin-inline-start: .22em; }
    .lk-apple .pad button:active { background: rgba(255,255,255,.45); }
    .lk-apple .pad .ghost { background: transparent; -webkit-backdrop-filter: none; backdrop-filter: none; font-size: 17px; font-weight: 400; }
    .lk-apple .pad .bio { color: #fff; padding: 22px; }
    .lk-apple .lnk { color: #fff; font-size: 16px; }
    .lk-apple .primary { background: #0a84ff; color: #fff; border-radius: 14px; font-weight: 600; }
    .lk-apple .bioic { color: #fff; } .lk-apple .bioic.ok { color: #30d158; }
    /* Android: Samsung One UI feel */
    .lk-android { font-family: "SamsungOne", "Roboto", "Noto Sans Arabic", system-ui, sans-serif; background: #0b0f14; justify-content: flex-start; padding-top: 14vh; }
    .lk-android img { width: 44px; height: 44px; border-radius: 50%; }
    .lk-android h2 { font-size: 22px; font-weight: 500; } .lk-android p { color: #a7b0b8; }
    .lk-android .dots { gap: 14px; margin-top: 18px; } .lk-android .dots i { width: 11px; height: 11px; border: 0; background: #3a4048; } .lk-android .dots i.on { background: #e8eaed; }
    .lk-android .pad { margin-top: auto; grid-template-columns: repeat(3, minmax(88px, 1fr)); gap: 6px 10px; width: min(360px, 100%); padding-bottom: 6vh; }
    .lk-android .pad button { width: 100%; height: 64px; border: 0; border-radius: 32px; background: transparent; }
    .lk-android .pad button b { font-size: 30px; font-weight: 400; }
    .lk-android .pad button:active { background: rgba(255,255,255,.12); }
    .lk-android .pad .ghost { font-size: 22px; } .lk-android .pad .bio { color: #8ab4f8; padding: 14px 30px; }
    .lk-android .lnk { color: #8ab4f8; }
    .lk-android .primary { background: #8ab4f8; color: #0b0f14; border-radius: 24px; }
    .lk-android .bioic { color: #8ab4f8; } .lk-android .bioic.ok { color: #81c995; }
    .lk-android .lk-lang span.on, .lk-apple .lk-lang span.on { background: #fff; color: #000; }
    .lk-choices { display: grid; gap: 12px; width: min(380px, 100%); margin-top: 8px; }
    .lk-choice { display: flex; gap: 14px; align-items: center; text-align: start; padding: 14px; border-radius: 18px; border: 1px solid rgba(255,255,255,.16);
      background: rgba(255,255,255,.06); color: #fff; font: inherit; cursor: pointer; }
    .lk-choice img { width: 52px; height: 52px; border-radius: 13px; flex: none; } .lk-choice b { display: block; font-size: 16px; } .lk-choice small { display: block; color: rgba(255,255,255,.7); font-size: 13px; margin-top: 3px; }
    .lk-choice:hover, .lk-choice:focus-visible { border-color: #c9a86a; outline: none; }
    /* calculator cover */
    .lk-calc { background: #000; justify-content: flex-end; padding: 16px 16px max(24px, env(safe-area-inset-bottom)); font-family: -apple-system, "Segoe UI", Roboto, system-ui, sans-serif; }
    .lk-calc .cx { width: min(400px, 100%); direction: ltr; }
    .lk-calc .cx-expr { text-align: right; color: #8e8e93; font-size: 20px; min-height: 26px; padding: 0 12px; }
    .lk-calc .cx-out { text-align: right; color: #fff; font-size: clamp(48px, 18vw, 76px); font-weight: 300; padding: 0 10px 14px; white-space: nowrap; overflow: hidden; }
    .lk-calc .cx-keys { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    .lk-calc .cx-keys button { aspect-ratio: 1; border: 0; border-radius: 50%; font-size: 28px; color: #fff; background: #333336; cursor: pointer; font-family: inherit; }
    .lk-calc .cx-keys button:active { filter: brightness(1.35); } .lk-calc .cx-keys button:focus-visible { outline: 3px solid #ff9f0a; outline-offset: 2px; }
    .lk-calc .cx-keys .fn { background: #a5a5aa; color: #000; } .lk-calc .cx-keys .op { background: #ff9f0a; } .lk-calc .cx-keys .op.on { background: #fff; color: #ff9f0a; }
    .lk-calc .cx-keys .zero { grid-column: span 2; aspect-ratio: auto; border-radius: 999px; text-align: left; padding-left: 30px; }
    @media (prefers-reduced-motion: reduce) { .lk .dots.shake, .lk .step, .lk .bioic svg path { animation: none; stroke-dashoffset: 0; } }`;
  document.head.appendChild(css);

  /* Calculator cover: when he chose it, the lock screen IS a working calculator. Typing his PIN (4-6 digits, no other
     keys in between) and then "=" opens Riaya; anything else simply calculates. Wrong PINs look like ordinary numbers,
     and after 5 of them the calculator stops accepting PINs for a while, silently. */
  const isCover = () => !!(read() && read().cover);
  let savedTitle = null;
  function calcSheet() {
    document.documentElement.classList.add("locked");
    sheet && sheet.remove();
    sheet = document.createElement("div");
    sheet.className = "lk lk-calc"; sheet.setAttribute("role", "application"); sheet.setAttribute("aria-label", "Calculator");
    if (savedTitle === null) { savedTitle = document.title; document.title = "Calculator"; }
    sheet.innerHTML = `<div class="cx"><div class="cx-expr" aria-live="polite"></div><div class="cx-out" role="status">0</div>
      <div class="cx-keys">${[["C", "AC", "fn"], ["±", "±", "fn"], ["%", "%", "fn"], ["/", "÷", "op"], ["7"], ["8"], ["9"], ["*", "×", "op"], ["4"], ["5"], ["6"], ["-", "−", "op"],
        ["1"], ["2"], ["3"], ["+", "+", "op"], ["0", "0", "zero"], [".", "."], ["=", "=", "op"]].map(([k, l, c]) => `<button type="button" class="${c || ""}" data-c="${k}">${l || k}</button>`).join("")}</div></div>`;
    document.body.appendChild(sheet);
    const out = sheet.querySelector(".cx-out"), ex = sheet.querySelector(".cx-expr");
    let cur = "0", acc = null, op = null, fresh = true, typed = "";
    const fmt = v => { if (!isFinite(v)) return "Error"; const t = String(+v.toPrecision(12)); return t.length > 12 ? (+v).toExponential(6) : t; };
    const calc = (a, b, o) => o === "+" ? a + b : o === "-" ? a - b : o === "*" ? a * b : o === "/" ? a / b : b;
    const sym = { "+": "+", "-": "−", "*": "×", "/": "÷" };
    const showv = () => { out.textContent = cur; sheet.querySelectorAll(".op").forEach(b => b.classList.toggle("on", b.dataset.c === op && fresh)); };
    const press = async k => {
      if (/^\d$/.test(k)) { typed = (typed + k).slice(-6); cur = fresh || cur === "0" ? k : (cur + k).slice(0, 12); fresh = false; }
      else if (k === ".") { typed = ""; if (fresh) { cur = "0."; fresh = false; } else if (!cur.includes(".")) cur += "."; }
      else if (k === "C") { cur = "0"; acc = null; op = null; fresh = true; typed = ""; ex.textContent = ""; }
      else if (k === "±") { typed = ""; cur = fmt(-parseFloat(cur)); }
      else if (k === "%") { typed = ""; cur = fmt(parseFloat(cur) / 100); }
      else if ("+-*/".includes(k)) {
        typed = "";
        if (op && !fresh) { acc = calc(acc, parseFloat(cur), op); cur = fmt(acc); } else acc = parseFloat(cur);
        op = k; fresh = true; ex.textContent = `${fmt(acc)} ${sym[k]}`;
      } else if (k === "=") {
        if (!op && typed.length >= 4 && Date.now() >= until) {
          if (await checkPin(typed)) { fails = 0; typed = ""; return open(); }
          if (++fails >= 5) until = Date.now() + 30000 * (fails - 4);
        }
        typed = "";
        if (op) { const b = parseFloat(cur); ex.textContent = `${fmt(acc)} ${sym[op]} ${fmt(b)} =`; cur = fmt(calc(acc, b, op)); acc = null; op = null; fresh = true; }
      }
      showv();
    };
    sheet.querySelectorAll("[data-c]").forEach(b => b.onclick = () => press(b.dataset.c));
    sheet.addEventListener("keydown", e => { const m = { Enter: "=", Escape: "C" }[e.key] || e.key; if (/^[\d.+\-*/=%]$/.test(m) || m === "C") { e.preventDefault(); press(m); } });
    setTimeout(() => sheet && sheet.querySelector("[data-c='7']").focus(), 30);
  }

  /* First-time choice: a normal lock, or the calculator cover. */
  function chooseCover(then) {
    document.documentElement.classList.add("locked");
    sheet && sheet.remove();
    sheet = document.createElement("div");
    sheet.className = "lk lk-" + SKIN; sheet.setAttribute("role", "dialog"); sheet.setAttribute("aria-modal", "true");
    sheet.innerHTML = `<div class="step"><img src="icons/icon-192.png" alt=""><h2>${esc(x("coverQ"))}</h2><p>${esc(x("coverSub"))}</p>
      <div class="lk-choices">
        <button type="button" class="lk-choice" data-cv="0"><img src="icons/icon-192.png" alt=""><span><b>${esc(x("plainT"))}</b><small>${esc(x("plainS"))}</small></span></button>
        <button type="button" class="lk-choice" data-cv="1"><img src="icons/calc-192.png" alt=""><span><b>${esc(x("calcT"))}</b><small>${esc(x("calcS"))}</small></span></button>
      </div></div>`;
    document.body.appendChild(sheet);
    sheet.querySelectorAll("[data-cv]").forEach(b => b.onclick = () => then(b.dataset.cv === "1"));
    setTimeout(() => sheet && sheet.querySelector("[data-cv='0']").focus(), 30);
  }

  /* Asks for the PIN or Face ID again before something sensitive opens (a vault document). Resolves true or false. */
  function verify() {
    if (!hasPin()) return Promise.resolve(true);
    return new Promise(res => { verifying = res; show(false, true); });
  }

  let wantCover = null;
  function show(setup, isVerify) {
    if (setup && wantCover === null) {
      if (scope !== "user") wantCover = false;   // the doctor console never wears a disguise
      else return chooseCover(c => { wantCover = c; show(true); });
    }
    if (!setup && !isVerify && isCover()) return calcSheet();
    document.documentElement.classList.add("locked");
    sheet && sheet.remove();
    entry = ""; first = null;
    sheet = document.createElement("div");
    sheet.className = "lk lk-" + SKIN; sheet.setAttribute("role", "dialog"); sheet.setAttribute("aria-modal", "true");
    const s = read();
    const mode = setup ? "set" : "unlock";
    sheet.innerHTML = `<button type="button" class="lk-lang" id="lkLang" aria-label="${L() === "ar" ? "English" : "العربية"}"><span class="${L() === "ar" ? "on" : ""}">ع</span><span class="${L() === "ar" ? "" : "on"}">EN</span></button>
      <img src="icons/icon-192.png" alt="">
      <h2 id="lkT">${esc(mode === "set" ? (wantCover ? x("setCalcT") : x("setT")) : isVerify ? x("verT") : x("title"))}</h2><p id="lkS">${esc(mode === "set" ? (wantCover ? x("setCalcSub") : x("setSub")) : isVerify ? x("verSub") : x("sub"))}</p>
      <div class="dots" id="lkD" aria-hidden="true">${"<i></i>".repeat(mode === "unlock" && s && s.len ? s.len : 6)}</div><div class="msg" id="lkM" role="status" aria-live="assertive"></div>
      <div class="pad" role="group" aria-label="PIN">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map(n => `<button type="button" data-k="${n}" aria-label="${n}"><b>${n}</b>${SKIN === "apple" ? `<small>${["", "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ"][n - 1]}</small>` : ""}</button>`).join("")}
        <button type="button" class="ghost bio" data-k="bio" aria-label="${esc(x("bio"))}" ${mode === "unlock" && s && s.bio ? "" : "style='visibility:hidden'"}>${BIO_GLYPH}</button>
        <button type="button" data-k="0" aria-label="0"><b>0</b>${SKIN === "apple" ? "<small>&nbsp;</small>" : ""}</button><button type="button" class="ghost back" data-k="back" aria-label="${esc(x("del"))}">${SKIN === "apple" ? esc(x("del")) : "⌫"}</button></div>
      ${mode === "set" ? `<button type="button" class="lnk" id="lkOk" hidden>OK</button>` : isVerify ? `<button type="button" class="lnk" id="lkCancel">${esc(x("cancel"))}</button>` : `<button type="button" class="lnk" id="lkForgot">${esc(x("forgot"))}</button>`}`;
    document.body.appendChild(sheet);
    sheet.querySelector("#lkLang").onclick = () => {
      const next = L() === "ar" ? "en" : "ar";
      try { localStorage.setItem("lang", next); } catch {}
      if (typeof LANG !== "undefined") { try { LANG = next; } catch {} }
      document.documentElement.lang = next; document.documentElement.dir = next === "ar" ? "rtl" : "ltr";
      if (mode === "set" && first) { location.reload(); return; }
      show(setup, isVerify);
    };
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
      write({ salt: b64(salt), hash: await hash(entry, salt), len: entry.length, at: Date.now(), cover: !!wantCover });
      await getKey().catch(() => {});
      if (wantCover) return coverDone();
      if (await bioAvailable()) return bioStep();
      open();
    };
    const coverDone = () => {
      sheet.innerHTML = `<div class="step"><img src="icons/calc-192.png" alt="" style="width:72px;height:72px;border-radius:18px"><h2>${esc(x("coverDone"))}</h2>
        <p>${esc(x("coverHow"))}</p><button type="button" class="primary" id="lkGot">${esc(x("gotIt"))}</button></div>`;
      sheet.querySelector("#lkGot").onclick = () => open();
      setTimeout(() => sheet.querySelector("#lkGot").focus(), 30);
    };
    // second step after the PIN: offer Face ID / fingerprint as its own clear choice
    const bioStep = () => {
      sheet.innerHTML = `<div class="step"><div class="bioic" id="lkBi">${BIO_GLYPH}</div>
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
    const cancel = sheet.querySelector("#lkCancel");
    if (cancel) cancel.onclick = () => { const r = verifying; verifying = null; sheet.remove(); sheet = null; document.documentElement.classList.remove("locked"); r && r(false); };
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
      ${bio && !(s && s.cover) ? (s && s.bio ? `<span class="tag">✓ ${esc(x("bioOn"))}</span>` : `<button class="chip" type="button" data-lk="bio">${esc(x("bioOff"))}</button>`) : ""}</p>
      <div class="row" style="align-items:center;gap:12px;margin-top:8px"><img src="icons/calc-192.png" alt="" width="40" height="40" style="border-radius:10px">
        <div style="flex:1"><b>${esc(s && s.cover ? x("coverOn") : x("calcT"))}</b><div class="small muted">${esc(x("calcS"))}</div></div>
        <button class="chip" type="button" data-lk="cover">${esc(s && s.cover ? x("coverTurnOff") : x("coverOff"))}</button></div></div>`;
  }
  function wireCard(host, rerender) {
    host.querySelectorAll("[data-lk]").forEach(b => b.onclick = async () => {
      if (b.dataset.lk === "lock") lock();
      else if (b.dataset.lk === "change") { const old = read(); write(null); show(true); root.addEventListener("riaya:unlocked", () => { if (!read()) write(old); }, { once: true }); }
      else if (b.dataset.lk === "bio") { await enrolBio().catch(() => {}); rerender && rerender(); }
      else if (b.dataset.lk === "cover") { const cur = read(); if (cur) { write({ ...cur, cover: !cur.cover }); rerender && rerender(); } }
    });
  }

  root.Lock = { verify, BIO_NAME, guard, lock, open, isOpen, hasPin, checkPin, encryptBlob, decryptBlob, settingsCard, wireCard, show, UNLOCK_FLAG, scope };
})(window);
