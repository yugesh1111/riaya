/* Disguise: Riaya can be installed as "Calculator", with a calculator icon. It opens as a working calculator;
   typing the Riaya PIN and then "=" opens Riaya. An installed app cannot change its own icon later, so he chooses
   the disguise when he adds it to his home screen (or installs the Calculator APK on Android). */
(function (root) {
  const T = {
    en: { t: "Disguise Riaya as a calculator", s: "Anyone who picks up your phone sees a calculator. Type your PIN, then =, to open Riaya.",
          steps: ["Open the calculator version below.", "iPhone: Share → Add to Home Screen. Android: menu ⋮ → Add to Home screen (or install the Calculator APK).", "Remove the normal Riaya icon if you like. Your record stays the same."],
          open: "Open the calculator version", pin: "Set a PIN first (App lock above): the calculator needs it." },
    ar: { t: "أخفِ رعاية على شكل آلة حاسبة", s: "من يمسك هاتفك يرى آلة حاسبة. اكتب رمزك ثم = لتفتح رعاية.",
          steps: ["افتح نسخة الآلة الحاسبة أدناه.", "آيفون: مشاركة ← إضافة إلى الشاشة الرئيسية. أندرويد: القائمة ⋮ ← إضافة إلى الشاشة الرئيسية (أو ثبّت تطبيق الآلة الحاسبة APK).", "يمكنك حذف أيقونة رعاية العادية. يبقى سجلك كما هو."],
          open: "افتح نسخة الآلة الحاسبة", pin: "ضع رمزاً سرياً أولاً (قفل التطبيق أعلاه): الآلة الحاسبة تحتاجه." },
  };
  root.disguiseCard = () => {
    const x = T[typeof LANG !== "undefined" && LANG === "ar" ? "ar" : "en"];
    const pin = root.Lock && root.Lock.hasPin();
    return `<div class="card disguise"><div class="row" style="gap:14px;align-items:center"><img src="icons/calc-192.png" alt="" width="52" height="52" style="border-radius:12px">
      <div><h3 style="margin:0">${esc(x.t)}</h3><p class="small muted" style="margin:4px 0 0">${esc(x.s)}</p></div></div>
      <ol class="small">${x.steps.map(s => `<li>${esc(s)}</li>`).join("")}</ol>
      ${pin ? `<p><a class="btn ghost" href="calc.html">${esc(x.open)}</a></p>` : `<p class="small muted">${esc(x.pin)}</p>`}</div>`;
  };
})(window);
