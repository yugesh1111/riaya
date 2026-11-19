/* Understands short spoken or typed answers in Gulf Arabic, MSA and English.
   Deterministic and on-device: no answer text leaves the phone for interpretation. */
(function (root) {
  const AR_DIGITS = { "٠": 0, "١": 1, "٢": 2, "٣": 3, "٤": 4, "٥": 5, "٦": 6, "٧": 7, "٨": 8, "٩": 9 };
  const NUM_WORDS = {
    zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12,
    thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20, thirty: 30,
    forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90, hundred: 100, half: 0.5,
    "صفر": 0, "واحد": 1, "وحدة": 1, "اثنين": 2, "اثنان": 2, "ثنين": 2, "ثلاث": 3, "ثلاثة": 3, "ثلاثه": 3, "اربع": 4, "أربع": 4, "اربعة": 4, "أربعة": 4,
    "خمس": 5, "خمسة": 5, "خمسه": 5, "ست": 6, "ستة": 6, "سته": 6, "سبع": 7, "سبعة": 7, "سبعه": 7, "ثمان": 8, "ثمانية": 8, "ثمانيه": 8, "ثمن": 8,
    "تسع": 9, "تسعة": 9, "تسعه": 9, "عشر": 10, "عشرة": 10, "عشره": 10, "احدعش": 11, "احدى عشر": 11, "اثنعش": 12, "اثنا عشر": 12,
    "ثلطعش": 13, "ثلاثطعش": 13, "اربعطعش": 14, "خمسطعش": 15, "ستطعش": 16, "سبعطعش": 17, "ثمنطعش": 18, "تسعطعش": 19,
    "عشرين": 20, "عشرون": 20, "ثمانين": 80, "تسعين": 90, "مية": 100, "مئة": 100, "مائة": 100, "ثلاثين": 30, "ثلاثون": 30, "اربعين": 40, "أربعين": 40, "خمسين": 50, "ستين": 60, "سبعين": 70,
    "نص": 0.5, "نصف": 0.5,
  };

  const HUNDRED_AR = ["مية", "ميه", "مئة", "مئه", "مائة", "مائه", "مايه"];
  const TWO_HUNDRED = { "ميتين": 1, "مئتين": 1, "مئتان": 1, "مايتين": 1, "two hundred": 1 };

  const norm = s => String(s || "").toLowerCase()
    .replace(/[٠-٩]/g, d => AR_DIGITS[d])
    .replace(/[إأآ]/g, "ا").replace(/ى/g, "ي").replace(/[ًٌٍَُِّْـ]/g, "")
    .replace(/[^\p{L}\p{N}.\s]/gu, " ")
    .replace(/(?<!\d)\.|\.(?!\d)/g, " ")  // full stops end words ("four." "no."); keep decimal points ("5.5")
    .replace(/\s+/g, " ").trim();

  function number(text) {
    const t = norm(text);
    const m = t.match(/\d+(?:\.\d+)?/);
    if (m) return parseFloat(m[0]);
    // word numbers: "thirty two", "اثنين وثلاثين", "ست ونص", "one hundred and seventy eight",
    // and the way heights and weights are usually spoken: "one seventy eight" = 178, "مية وثمانين" = 180
    let total = 0, found = false, prevUnit = false;
    for (const raw of t.split(/\s+|و(?=\S)/)) {
      const w = raw.replace(/^و/, "");
      if (w === "hundred" || HUNDRED_AR.includes(w)) {  // "one hundred" = 100 x 1; "a hundred" / "مية" = 100
        total = (total >= 1 && total <= 9 ? total : 1) * 100; found = true; prevUnit = false; continue;
      }
      if (w in TWO_HUNDRED) { total += 200; found = true; prevUnit = false; continue; }
      if (!(w in NUM_WORDS)) continue;
      const v = NUM_WORDS[w];
      // English "one seventy" -> 170. Not Arabic: there units come first ("اثنين وثلاثين" = 32).
      if (prevUnit && /^[a-z]/.test(w) && total >= 1 && total <= 9 && v >= 20 && v <= 90 && v % 10 === 0) total = total * 100 + v;
      else total += v;
      found = true;
      prevUnit = v >= 1 && v <= 9 && Number.isInteger(v);
    }
    return found ? total : null;
  }

  /* durations in months: "18 months", "a year and a half", "2 years", "سنة ونص", "سنتين", "ثلاث سنوات" */
  const YEAR_WORDS = ["year", "years", "yr", "yrs", "سنة", "سنه", "سنين", "سنوات", "عام", "اعوام"];
  const TWO_YEARS = ["سنتين", "سنتان", "عامين"];
  function months(text) {
    const t = norm(text);
    const words = t.split(/\s+/).map(w => w.replace(/^و/, ""));
    if (words.some(w => TWO_YEARS.includes(w))) { const rest = number(t.replace(/سنتين|سنتان|عامين/g, "")); return 24 + (rest && rest < 1 ? rest * 12 : 0); }
    if (words.some(w => YEAR_WORDS.includes(w))) {
      // "a year and <something we didn't catch>" must not quietly become 12 months: ask again instead
      const leftover = words.filter(w => !YEAR_WORDS.includes(w) && !(w in NUM_WORDS) && !HUNDRED_AR.includes(w) && !/^\d/.test(w) &&
        !["a", "and", "about", "around", "almost", "nearly", "over", "more", "than", "just", "ago", "for", "we", "have", "been", "trying", "تقريبا", "حوالي", "اكثر", "من", "صار", "لنا", "لي", "تقريبًا", "بس", "يعني", "واحد", "وحدة", "حدود"].includes(w));
      if (/(^|\s)(and|و)\s*$/.test(t) || leftover.length > 1) return null;
      const n = number(t.replace(/\ba\b/g, ""));
      return Math.round((n == null ? 1 : n < 1 ? 1 + n : n) * 12);  // "a year" = 12, "a year and a half" = 18
    }
    return number(t);
  }

  const YES = ["yes", "yeah", "yep", "sure", "correct", "right", "true", "i do", "نعم", "اي", "ايه", "ايوه", "ايوا", "اكيد", "صح", "بلى", "اجل", "طبعا", "يب", "اوكي", "ok", "okay"];
  const NO = ["no", "nope", "not", "never", "dont", "don t", "nah", "لا", "لاء", "مب", "مو", "ابدا", "ما", "مافي", "ماشي", "كلا", "none"];
  const UNSURE = ["not sure", "dont know", "don t know", "maybe", "unsure", "مادري", "ما ادري", "لا اعرف", "مش متاكد", "مب متاكد", "يمكن", "ربما"];
  const SKIP = ["skip", "prefer not", "pass", "next", "تخطي", "تخطى", "افضل عدم", "ما ابي اجاوب", "بعدين", "التالي"];

  // agreement said with a negative word in it: "no problem", "I don't mind", "ما عندي مانع"
  const YES_PHRASES = ["no problem", "dont mind", "don t mind", "i don t mind", "of course", "go ahead", "why not", "sounds good",
                       "ما عندي مانع", "ماعندي مانع", "لا مانع", "ما في مانع", "مافي مانع", "ما في مشكلة", "مافي مشكلة", "ما في مشكله", "مافي مشكله", "ولا يهمك", "على راسي"];
  const has = (t, words) => words.some(w => new RegExp(`(^|\\s)${norm(w)}(\\s|$)`).test(t));
  const first = t => t.split(" ")[0];

  function yesNo(text, allowUnsure = true) {
    const t = norm(text);
    if (has(t, SKIP)) return "skip";
    if (allowUnsure && has(t, UNSURE)) return "unsure";
    if (has(t, YES_PHRASES)) return "yes";
    // a clear yes or no at the start decides: "yes, my wife says I snore", "no, never"
    if (YES.map(norm).includes(first(t))) return "yes";
    if (["no", "nope", "nah", "لا", "لاء", "كلا", "never", "ابدا"].includes(first(t))) return "no";
    if (has(t, NO)) return "no";
    if (has(t, YES)) return "yes";
    return null;
  }

  // edit distance, for words the speech service slightly misheard ("dayly", "tite", "يوميه")
  function lev(a, b) {
    if (Math.abs(a.length - b.length) > 2) return 9;
    const d = Array.from({ length: a.length + 1 }, (_, i) => [i]);
    for (let j = 1; j <= b.length; j++) d[0][j] = j;
    for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    return d[a.length][b.length];
  }
  const close = (word, key) => key.length >= 4 && !/\s/.test(key) && word.length >= 3 && lev(word, key) <= (key.length >= 7 ? 2 : 1);

  /* options: [{value, keys: ["word", ...]}] — returns the option whose key appears; earliest/longest match wins.
     If nothing matches exactly, a word within one or two letters of a key counts (NLU.lastFuzzy tells the page). */
  function choice(text, options) {
    const t = norm(text);
    root.NLU.lastFuzzy = false;
    if (has(t, SKIP)) return "skip";
    let best = null, bestLen = 0;
    for (const o of options) for (const k of o.keys) {
      const nk = norm(k);
      if (nk && t.includes(nk) && nk.length > bestLen) { best = o.value; bestLen = nk.length; }
    }
    if (best != null) return best;
    const words = t.split(" ");
    let fz = null, fzScore = 9;
    for (const o of options) for (const k of o.keys) {
      const nk = norm(k);
      for (const w of words) if (close(w, nk)) { const sc = lev(w, nk); if (sc < fzScore) { fz = o.value; fzScore = sc; } }
    }
    if (fz != null) root.NLU.lastFuzzy = true;
    return fz;
  }

  root.NLU = { norm, number, months, yesNo, choice, lev, lastFuzzy: false };
  if (typeof module !== "undefined") module.exports = root.NLU;
})(typeof window !== "undefined" ? window : globalThis);
