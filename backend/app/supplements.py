"""Gym product checker: reads a supplement / "test booster" / injectable label and flags what can switch off sperm production.

Anabolic steroids, testosterone and SARMs shut down the hormones (LH/FSH) that drive sperm production; this is one of
the most common and most reversible causes of low or absent sperm in young men who train. Recovery after stopping can
take 6-12 months or more. The checker matches ingredient names (English and Arabic, common brand and code names) and
explains each finding with its evidence. It never says a product is safe to take: it says what the label shows.
"""
import re

# level: stop = suppresses sperm production; caution = may affect hormones / sleep / sperm, or needs a doctor; ok = no known harm to sperm at usual doses
# (names, level, why en, why ar, source)
LEXICON = [
    (["testosterone", "test cyp", "cypionate", "enanthate", "propionate", "undecanoate", "sustanon", "تستوستيرون"], "stop",
     "Testosterone from outside switches off your own sperm production; it often drops to zero within months.",
     "التستوستيرون من خارج الجسم يوقف إنتاجك للحيوانات المنوية، وقد ينخفض إلى الصفر خلال أشهر.", "AUA/ASRM male infertility guideline 2020; Endocrine Society 2018"),
    (["nandrolone", "deca", "trenbolone", "tren", "boldenone", "equipoise", "stanozolol", "winstrol", "oxandrolone", "anavar", "methandrostenolone",
      "dianabol", "dbol", "oxymetholone", "anadrol", "drostanolone", "masteron", "primobolan", "methenolone", "turinabol", "ستيرويد", "منشطات", "ديكا", "ترينبولون"],
     "stop", "Anabolic steroid: suppresses LH and FSH, so the testes stop making sperm. Recovery after stopping can take 6-12 months or longer.",
     "ستيرويد بنائي: يثبط هرموني LH وFSH فتتوقف الخصيتان عن إنتاج الحيوانات المنوية. قد يستغرق التعافي بعد التوقف ٦-١٢ شهراً أو أكثر.",
     "Rahnema 2014 Fertil Steril; Kanayama 2015"),
    (["ostarine", "mk-2866", "mk2866", "enobosarm", "ligandrol", "lgd-4033", "lgd4033", "rad-140", "rad140", "testolone", "andarine", "s4", "s-4",
      "yk-11", "yk11", "s23", "sarm", "sarms", "سارمز"],
     "stop", "SARM: lowers testosterone, LH and FSH like a steroid does. Not approved for any use; products are often mislabelled.",
     "SARM: يخفض التستوستيرون وLH وFSH كما تفعل الستيرويدات. غير مرخص لأي استخدام، وكثيراً ما تكون ملصقاته غير دقيقة.",
     "FDA warning 2017; Van Wagoner 2017 JAMA"),
    (["1-andro", "4-andro", "prohormone", "epiandrosterone", "androstenedione", "methyl-1-test", "superdrol", "halodrol"], "stop",
     "Prohormone: turns into anabolic steroid in the body, with the same effect on sperm.",
     "طليعة هرمون: يتحول في الجسم إلى ستيرويد بنائي وله الأثر نفسه على الحيوانات المنوية.", "FDA; WADA prohibited list"),
    (["dmaa", "1,3-dimethylamylamine", "geranium extract", "dmha", "octodrine", "ephedra", "ephedrine"], "stop",
     "Banned stimulant (heart and blood-pressure risks).", "منبّه محظور (مخاطر على القلب وضغط الدم).", "FDA DMAA warning; WADA"),
    (["cardarine", "gw501516", "gw-501516"], "stop", "Abandoned drug linked to cancer in animal studies; not a supplement.",
     "دواء متوقف ارتبط بالسرطان في دراسات على الحيوانات؛ ليس مكملاً.", "WADA alert 2013"),
    (["hcg", "human chorionic gonadotropin", "clomiphene", "clomid", "enclomiphene", "tamoxifen", "nolvadex", "anastrozole", "arimidex", "letrozole", "pct"],
     "caution", "A prescription medicine. Doctors do use some of these for male fertility, but only after tests and with monitoring, never as a self-run 'PCT'.",
     "دواء بوصفة طبية. يستخدم الأطباء بعضها لخصوبة الرجل، لكن بعد فحوصات وتحت المتابعة فقط، وليس كـ«PCT» ذاتي.", "AUA/ASRM 2020"),
    (["mk-677", "mk677", "ibutamoren", "hgh", "growth hormone", "somatropin"], "caution",
     "Growth-hormone product: raises blood sugar and is not approved as a supplement; effects on fertility are unclear.",
     "منتج هرمون نمو: يرفع سكر الدم وغير مرخص كمكمل؛ أثره على الخصوبة غير واضح.", "FDA; Endocrine Society"),
    (["dhea", "dehydroepiandrosterone"], "caution", "A hormone precursor; can change your hormone balance. Ask a doctor first.",
     "طليعة هرمونية؛ قد تغيّر توازن هرموناتك. استشر طبيباً أولاً.", "Endocrine Society"),
    (["finasteride", "dutasteride", "propecia", "avodart"], "caution",
     "Hair-loss/prostate medicine; in some men it lowers semen volume and count. Tell your doctor if you are trying for a child.",
     "دواء لتساقط الشعر/البروستاتا؛ قد يخفض حجم السائل المنوي والعدد لدى بعض الرجال. أخبر طبيبك إن كنت تحاول الإنجاب.", "AUA/ASRM 2020"),
    (["yohimbine", "yohimbe"], "caution", "Stimulant: raises heart rate and anxiety; no proven benefit for fertility.",
     "منبّه: يرفع نبض القلب والقلق؛ لا فائدة مثبتة للخصوبة.", "NIH ODS"),
    (["caffeine", "pre-workout", "preworkout", "كافيين"], "caution", "Fine in moderation; a late-day pre-workout can cut your sleep, and sleep matters for testosterone.",
     "لا بأس باعتدال؛ لكن منشّط ما قبل التمرين في وقت متأخر قد يقلّل نومك، والنوم مهم للتستوستيرون.", "Leproult & Van Cauter 2011 JAMA"),
    (["proprietary blend", "test booster", "testosterone booster", "تعزيز التستوستيرون"], "caution",
     "'Booster' blends rarely list doses, and some have been found to contain hidden steroids. Check the full ingredient list.",
     "خلطات «المعززات» نادراً ما تذكر الجرعات، وقد وُجدت في بعضها ستيرويدات مخفية. افحص قائمة المكونات كاملة.", "FDA tainted products database"),
    (["tribulus", "fenugreek", "ashwagandha", "tongkat", "maca", "d-aspartic", "d-aspartic acid"], "ok",
     "Herbal 'booster': no known harm to sperm at usual doses; evidence of benefit is weak.", "مكوّن عشبي «معزز»: لا ضرر معروف على الحيوانات المنوية بالجرعات المعتادة؛ أدلة فائدته ضعيفة.", "Cochrane-type reviews; low quality"),
    (["zinc", "selenium", "folate", "folic acid", "vitamin d", "coq10", "coenzyme q10", "l-carnitine", "omega-3", "vitamin c", "vitamin e", "زنك", "سيلينيوم", "فيتامين د"], "ok",
     "Antioxidant/vitamin: generally safe; may help sperm in some men, but the evidence is low quality and a balanced diet matters more.",
     "مضاد أكسدة/فيتامين: آمن عموماً؛ قد يفيد الحيوانات المنوية لدى بعض الرجال، لكن الأدلة ضعيفة والنظام الغذائي المتوازن أهم.", "Cochrane 2019 (antioxidants for male subfertility)"),
    (["creatine", "whey", "protein", "bcaa", "glutamine", "كرياتين", "بروتين"], "ok",
     "No known effect on sperm at usual doses.", "لا أثر معروف على الحيوانات المنوية بالجرعات المعتادة.", "ISSN position stands"),
]
ORDER = {"stop": 0, "caution": 1, "ok": 2}
VERDICT = {
    "en": {"stop": "Stop: this can switch off sperm production", "caution": "Check with a doctor before using", "ok": "Nothing on this label is known to harm sperm",
           "none": "No ingredients recognised. Type the ingredient list, or try a clearer photo of the back label."},
    "ar": {"stop": "توقف: قد يوقف هذا إنتاج الحيوانات المنوية", "caution": "استشر طبيباً قبل الاستخدام", "ok": "لا يوجد في هذا الملصق ما يُعرف أنه يضر الحيوانات المنوية",
           "none": "لم نتعرف على مكونات. اكتب قائمة المكونات، أو جرّب صورة أوضح للملصق الخلفي."},
}
NEXT = {
    "en": {"stop": ["Don't start it. If you already use it, don't stop suddenly on your own: talk to a doctor, privately, through Riaya.",
                    "Sperm usually recover after stopping, but it can take 6-12 months or more. A semen test shows where you are."],
           "caution": ["Ask a doctor before using it, especially if you are trying for a child."], "ok": ["Keep doses to the label. Food, sleep and training still matter most."]},
    "ar": {"stop": ["لا تبدأ به. إن كنت تستخدمه، لا توقفه فجأة وحدك: تحدّث مع طبيب بسرية عبر رعاية.",
                    "تتعافى الحيوانات المنوية عادة بعد التوقف، لكن قد يستغرق ذلك ٦-١٢ شهراً أو أكثر. تحليل السائل المنوي يوضح وضعك."],
           "caution": ["استشر طبيباً قبل الاستخدام، خاصة إن كنتم تحاولون الإنجاب."], "ok": ["التزم بالجرعة المكتوبة. الطعام والنوم والتمرين تبقى الأهم."]},
}


def _norm(text):
    t = text.lower().replace("ـ", "")
    t = re.sub(r"[إأآ]", "ا", t)
    return re.sub(r"\s+", " ", t)


def check(text, lang="en"):
    L = "ar" if lang == "ar" else "en"
    t = _norm(text or "")
    found, seen = [], set()
    for names, level, en, ar, src in LEXICON:
        for n in names:
            nn = _norm(n)
            pat = (r"(?<![a-z0-9])" + re.escape(nn) + r"(?![a-z0-9])") if re.match(r"[a-z0-9]", nn) else re.escape(nn)
            if re.search(pat, t):
                key = (level, en)
                if key not in seen:
                    seen.add(key)
                    found.append({"match": n, "level": level, "why": ar if L == "ar" else en, "source": src})
                break
    found.sort(key=lambda f: ORDER[f["level"]])
    worst = found[0]["level"] if found else None
    return {"verdict": worst, "headline": VERDICT[L][worst or "none"], "findings": found, "next": NEXT[L].get(worst, []),
            "note": ("هذه أداة توعية تقرأ الملصق، وليست فحصاً مخبرياً للمنتج." if L == "ar"
                     else "An awareness tool that reads the label. It cannot test what is actually inside the product.")}
