/* Voice in and out, on every kind of phone.
   Listening:
     1. the browser's own speech recognition (iPhone Safari, Android Chrome, Samsung Internet, Edge, desktop Chrome/Safari)
     2. otherwise, or when "private mode" is on: Whisper (open-source, OpenAI) running inside the browser with
        transformers.js. Audio never leaves the phone. The model (~40-80 MB) downloads once and is cached.
   Speaking: the device's own voices (SpeechSynthesis). iPhones need one tap before audio can play. */
(function (root) {
  const SR = root.SpeechRecognition || root.webkitSpeechRecognition;
  const canRecord = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && root.MediaRecorder);
  const TRANSFORMERS = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.0.2";
  const MODELS = ["onnx-community/whisper-base", "Xenova/whisper-base", "Xenova/whisper-tiny"];
  let unlocked = false, whisper = null, whisperLoading = null;

  function unlockAudio() {
    if (unlocked || !root.speechSynthesis) return;
    try { const u = new SpeechSynthesisUtterance(" "); u.volume = 0; speechSynthesis.speak(u); } catch {}
    unlocked = true;
  }
  ["pointerdown", "keydown", "touchend"].forEach(ev => document.addEventListener(ev, unlockAudio, { once: true, capture: true }));

  /* Accents he can choose. The locale steers both speech recognition and which voice reads to him. */
  const ACCENTS = {
    ar: [{ key: "ae", locale: "ar-AE", en: "Emirati", ar: "إماراتي" }, { key: "sa", locale: "ar-SA", en: "Saudi", ar: "سعودي" },
         { key: "eg", locale: "ar-EG", en: "Egyptian", ar: "مصري" }, { key: "lv", locale: "ar-JO", en: "Levantine", ar: "شامي" }],
    en: [{ key: "gb", locale: "en-GB", en: "British", ar: "بريطاني" }, { key: "us", locale: "en-US", en: "American", ar: "أمريكي" },
         { key: "in", locale: "en-IN", en: "Indian", ar: "هندي" }],
  };
  const NATURAL = /natural|neural|online|premium|enhanced|siri|wavenet|studio/i;
  const KNOWN_GOOD = /hamdan|fatima|hamed|zariyah|shakir|salma|taim|amany|majed|laila|tarik|mariam|sonia|ryan|libby|thomas|jenny|guy|aria|neerja|prabhat|daniel|serena|kate|jamie|google uk english|google us english/i;
  const ROBOTIC = /espeak|compact|pico|bahh|bells|boing|bubbles|cellos|wobble|zarvox|trinoids|whisper|organ|jester|superstar|albert|fred|junior|ralph|kathy|grandma|grandpa|rocko|shelley|eddy|flo|reed|sandy|bad news|good news/i;

  /* Every voice for this language, best first: the most natural-sounding voices (neural / premium / enhanced), then
     the ones that match his accent, then the rest. Novelty and robotic voices are left out. */
  function voicesFor(lang, locale) {
    if (!root.speechSynthesis) return [];
    const want = (locale || "").toLowerCase();
    const score = v => {
      const l = v.lang.toLowerCase().replace("_", "-");
      return (NATURAL.test(v.name) ? 100 : 0) + (KNOWN_GOOD.test(v.name) ? 30 : 0) + (want && l === want ? 20 : 0) + (v.localService ? 0 : 5);
    };
    return speechSynthesis.getVoices()
      .filter(v => v.lang.toLowerCase().replace("_", "-").startsWith(lang) && !ROBOTIC.test(v.name))
      .map(v => ({ v, s: score(v) })).sort((a, b) => b.s - a.s).map(x => Object.assign(x.v, { _natural: x.s >= 100 }));
  }
  const isNatural = v => !!(v && NATURAL.test(v.name));

  /* Speaks sentence by sentence with a short breath between them: sounds more like a person, and avoids the
     cut-off some browsers apply to long utterances. onstart/onend let the page animate the voice orb. */
  let speakToken = 0;
  function speak(text, { lang, locale, voiceName, onend, onstart } = {}) {
    if (!root.speechSynthesis) { onend && onend(); return; }
    speechSynthesis.cancel();
    const token = ++speakToken;
    const list = voicesFor(lang, locale);
    const v = list.find(x => x.name === voiceName) || list[0];
    const parts = String(text).replace(/\n+/g, " \n ").split(/(?<=[.!?؟\n])\s+/).map(x => x.trim()).filter(x => x && x !== "\n");
    let done = false;
    const finish = () => { if (!done) { done = true; onend && onend(); } };
    // some Android builds never fire onend: fall back on an estimate
    const guard = setTimeout(finish, Math.min(45000, 3000 + text.length * (lang === "ar" ? 120 : 95)));
    const next = i => {
      if (token !== speakToken) return;
      if (i >= parts.length) { clearTimeout(guard); return finish(); }
      const u = new SpeechSynthesisUtterance(parts[i]);
      u.lang = (v && v.lang) || locale || (lang === "ar" ? "ar-AE" : "en-GB");
      if (v) u.voice = v;
      u.rate = isNatural(v) ? 1.0 : 0.95;
      u.pitch = 1;
      if (i === 0) u.onstart = () => onstart && onstart();
      u.onend = () => setTimeout(() => next(i + 1), /[?؟]$/.test(parts[i]) ? 260 : 180);
      u.onerror = () => next(i + 1);
      speechSynthesis.speak(u);
    };
    next(0);
  }
  function stopSpeaking() { speakToken++; if (root.speechSynthesis) speechSynthesis.cancel(); }

  /* size "base" (default, ~80 MB, fine for English and short answers) or "small" (~250 MB, much better for Arabic;
     used by the demo and offered for private mode on a good connection). */
  const SMALL = ["onnx-community/whisper-small", "Xenova/whisper-small"];
  const models = {}, loading = {};
  async function loadWhisper(onProgress, size = "base") {
    if (models[size]) return models[size];
    if (loading[size]) return loading[size];
    loading[size] = (async () => {
      const { pipeline, env } = await import(TRANSFORMERS);
      env.allowLocalModels = false;
      let lastErr;
      for (const id of size === "small" ? SMALL : MODELS) {
        try {
          models[size] = await pipeline("automatic-speech-recognition", id, { progress_callback: onProgress });
          if (size === "base") whisper = models[size];
          return models[size];
        } catch (e) { lastErr = e; }
      }
      throw lastErr;
    })();
    try { return await loading[size]; } finally { loading[size] = null; }
  }

  async function toMono16k(blob) {
    const buf = await blob.arrayBuffer();
    const Ctx = root.AudioContext || root.webkitAudioContext;
    const ctx = new Ctx();
    const decoded = await ctx.decodeAudioData(buf);
    const off = new OfflineAudioContext(1, Math.ceil(decoded.duration * 16000), 16000);
    const src = off.createBufferSource(); src.buffer = decoded; src.connect(off.destination); src.start();
    const out = await off.startRendering();
    ctx.close && ctx.close();
    return out.getChannelData(0);
  }

  /* Records until stop() is called, until he has been quiet for a moment after speaking, or the time limit.
     Returns {stop, promise<Blob>, heard: () => boolean}. autoStop=false keeps recording (voice notes). */
  async function record(maxMs = 15000, { autoStop = true, silenceMs = 1300, waitMs = 8000 } = {}) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    const type = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm", "audio/ogg"].find(t => MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t)) || "";
    const mr = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
    const chunks = [];
    let heard = false, vad = null, ctx = null;
    const stop = () => { clearTimeout(timer); clearInterval(vad); mr.state !== "inactive" && mr.stop(); };
    mr.ondataavailable = e => e.data.size && chunks.push(e.data);
    const promise = new Promise(res => mr.onstop = () => {
      clearInterval(vad); stream.getTracks().forEach(t => t.stop()); ctx && ctx.close && ctx.close().catch(() => {});
      res(new Blob(chunks, { type: mr.mimeType || type || "audio/webm" }));
    });
    mr.start(250);
    const timer = setTimeout(stop, maxMs);
    const Ctx = root.AudioContext || root.webkitAudioContext;
    if (autoStop && Ctx) {
      try {
        ctx = new Ctx();
        const an = ctx.createAnalyser(); an.fftSize = 1024;
        ctx.createMediaStreamSource(stream).connect(an);
        const buf = new Float32Array(an.fftSize);
        let floor = 0.01, quietSince = 0;
        const started = Date.now();
        vad = setInterval(() => {
          an.getFloatTimeDomainData(buf);
          let sum = 0; for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
          const rms = Math.sqrt(sum / buf.length), now = Date.now();
          if (!heard) floor = 0.95 * floor + 0.05 * Math.min(rms, 0.05);  // learn the room's noise level before he speaks
          const loud = rms > Math.max(0.02, floor * 3);
          if (loud) { heard = true; quietSince = 0; }
          else if (heard) { quietSince = quietSince || now; if (now - quietSince > silenceMs) stop(); }
          else if (now - started > waitMs) stop();
        }, 80);
      } catch { /* no analyser: fall back on the time limit or the stop button */ }
    }
    return { stop, promise, heard: () => heard };
  }

  const IOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

  /* listen({lang, privateMode, onState, onPartial}) -> {stop, result: Promise<string[] alternatives>}
     onPartial(text) receives the words heard so far, so he can see that it is working. */
  function listen({ lang, locale, privateMode, onState = () => {}, onPartial = () => {} }) {
    if (SR && !privateMode) {
      const rec = new SR();
      rec.lang = locale || (lang === "ar" ? "ar-AE" : "en-US");
      // keep listening through short pauses ("thirty... four"); iOS Safari handles continuous mode badly
      rec.continuous = !IOS; rec.interimResults = true; rec.maxAlternatives = 3;
      const finals = [];
      let interim = "", quiet = null, error = null, done = false;
      const end = () => { if (!done) { done = true; try { rec.stop(); } catch {} } };
      const result = new Promise((resolve, reject) => {
        rec.onresult = e => {
          interim = "";
          for (let i = e.resultIndex; i < e.results.length; i++) {
            const r = e.results[i];
            if (r.isFinal) finals.push([...r].map(a => a.transcript.trim()).filter(Boolean));
            else interim += r[0].transcript;
          }
          onPartial([...finals.map(f => f[0]), interim].join(" ").replace(/\s+/g, " ").trim());
          clearTimeout(quiet); quiet = setTimeout(end, 1400);  // he has stopped talking
        };
        rec.onerror = e => { error = e.error || "speech"; };
        rec.onend = () => {
          clearTimeout(quiet); clearTimeout(limit); onState("idle");
          if (finals.length) {
            // alternatives for the whole answer: the k-th guess for every phrase, joined
            const alts = [0, 1, 2].map(k => finals.map(f => f[k] || f[0]).join(" ").trim());
            return resolve([...new Set(alts.filter(Boolean))]);
          }
          if (interim.trim()) return resolve([interim.trim()]);
          if (error && !/no-speech|aborted/.test(error)) return reject(new Error(error));
          resolve([]);  // heard nothing
        };
      });
      const limit = setTimeout(end, 20000);
      onState("listening");
      try { rec.start(); } catch (e) { return { stop() {}, result: Promise.reject(e), engine: "browser" }; }
      return { stop: end, result, engine: "browser" };
    }
    if (!canRecord) return { stop() {}, result: Promise.reject(new Error("no-microphone")), engine: "none" };
    let handle, recording = true, pct = 0, ready = false;
    const result = (async () => {
      const modelReady = loadWhisper(p => {
        if (p && p.status === "progress") { pct = Math.round(p.progress || 0); if (!recording) onState("loading", pct); }
      }).then(m => { ready = true; return m; });
      onState("listening");
      handle = await record(20000);
      const blob = await handle.promise;
      recording = false;
      if (!handle.heard()) { onState("idle"); return []; }  // nothing said: don't run the model on silence
      onState(ready ? "thinking" : "loading", pct);
      const [asr, audio] = await Promise.all([modelReady, toMono16k(blob)]);
      const out = await asr(audio, { language: lang === "ar" ? "arabic" : "english", task: "transcribe", chunk_length_s: 30 });
      onState("idle");
      return [String(out.text || "").trim()].filter(Boolean);
    })();
    return { stop: () => handle && handle.stop(), result, engine: "whisper" };
  }

  // errors that mean the browser's speech service itself is unusable here (blocked, offline, or no such language)
  const SERVICE_DOWN = /network|service-not-allowed|language-not-supported|not-supported|bad-grammar/i;
  /* Recognises a recorded clip on the phone with Whisper (used by the demo mode, which plays a recorded answer aloud
     and lets the same on-device model that serves "private mode" understand it). */
  async function transcribe(blob, lang, onProgress, size = "base") {
    const [asr, audio] = await Promise.all([loadWhisper(onProgress, size), toMono16k(blob)]);
    const out = await asr(audio, { language: lang === "ar" ? "arabic" : "english", task: "transcribe", chunk_length_s: 30 });
    return String(out.text || "").trim();
  }

  root.Voice = { speak, stopSpeaking, listen, transcribe, record, voicesFor, isNatural, ACCENTS, hasBrowserASR: !!SR, canRecord, loadWhisper, SERVICE_DOWN };
})(window);
