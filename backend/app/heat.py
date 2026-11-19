"""UAE heat guard: today's forecast for his emirate, turned into one practical tip.

Heat is a real factor for sperm in the UAE: the testes work best ~2-4 °C below body temperature, and long heat exposure
(outdoor work, hot cars, saunas) lowers sperm counts for about 3 months. The server asks Open-Meteo (free, no key) for the
emirate's forecast, so his own location never leaves the phone: he picks an emirate, not a GPS point. Cached for an hour.
"""
import json
import time
import urllib.request

EMIRATES = {
    "abu_dhabi": ("Abu Dhabi", "أبوظبي", 24.45, 54.38), "al_ain": ("Al Ain", "العين", 24.21, 55.74),
    "al_dhafra": ("Al Dhafra", "الظفرة", 23.65, 53.70), "dubai": ("Dubai", "دبي", 25.20, 55.27),
    "sharjah": ("Sharjah", "الشارقة", 25.35, 55.39), "ajman": ("Ajman", "عجمان", 25.41, 55.51),
    "umm_al_quwain": ("Umm Al Quwain", "أم القيوين", 25.56, 55.55), "ras_al_khaimah": ("Ras Al Khaimah", "رأس الخيمة", 25.79, 55.94),
    "fujairah": ("Fujairah", "الفجيرة", 25.13, 56.33),
}
_cache = {}
SOURCE = "Durairajanayagam 2015 (heat and male fertility); WHO 2021 semen manual"


def _fetch(lat, lon):
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&daily=temperature_2m_max,apparent_temperature_max,uv_index_max&timezone=Asia%2FDubai&forecast_days=1")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "riaya-heat/1.0"}), timeout=6) as r:
        d = json.loads(r.read().decode())["daily"]
    return {"max_c": round(d["temperature_2m_max"][0]), "feels_c": round(d["apparent_temperature_max"][0]), "uv": round(d["uv_index_max"][0])}


def band(feels):
    return "extreme" if feels >= 46 else "very_hot" if feels >= 40 else "hot" if feels >= 34 else "warm" if feels >= 28 else "mild"


TIPS = {
    "en": {"extreme": "Extreme heat today. Stay out of the midday sun (11-4), keep the car cool before you sit, and take cool breaks if you work outside. Loose cotton underwear, and no laptop on your lap.",
           "very_hot": "Very hot today. Cool breaks every hour outdoors, water before you feel thirsty, loose cotton underwear, and skip the sauna and jacuzzi.",
           "hot": "Hot today. Drink water through the day and wear loose, breathable clothes; long hot car rides and heated seats add up.",
           "warm": "Warm today: a good day for a walk in the evening. Keep the phone out of your trouser pocket.",
           "mild": "Mild weather: a good day to be active outdoors."},
    "ar": {"extreme": "حرارة شديدة جداً اليوم. ابتعد عن شمس الظهيرة (١١-٤)، برّد السيارة قبل الجلوس، وخذ استراحات باردة إن كنت تعمل في الخارج. ملابس داخلية قطنية فضفاضة، ولا حاسوب على حضنك.",
           "very_hot": "حار جداً اليوم. استراحة باردة كل ساعة في الخارج، اشرب الماء قبل أن تعطش، ملابس داخلية قطنية فضفاضة، وتجنّب الساونا والجاكوزي.",
           "hot": "حار اليوم. اشرب الماء طوال اليوم والبس ملابس فضفاضة؛ رحلات السيارة الطويلة والمقاعد المدفأة تتراكم.",
           "warm": "طقس دافئ اليوم: يوم مناسب للمشي مساءً. أبعد الهاتف عن جيب البنطال.",
           "mild": "طقس معتدل: يوم جيد للنشاط في الخارج."},
}
WHY = {"en": "The testes work best 2-4 °C below body temperature; long heat exposure lowers sperm counts for about 3 months.",
       "ar": "تعمل الخصيتان بأفضل شكل عند حرارة أقل من حرارة الجسم بـ٢-٤ درجات؛ والتعرض الطويل للحرارة يخفض عدد الحيوانات المنوية لنحو ٣ أشهر."}


def today(emirate, lang="en", fetch=_fetch):
    L = "ar" if lang == "ar" else "en"
    if emirate not in EMIRATES:
        emirate = "abu_dhabi"
    name_en, name_ar, lat, lon = EMIRATES[emirate]
    now = time.time()
    hit = _cache.get(emirate)
    if not hit or now - hit[0] > 3600:
        try:
            hit = (now, fetch(lat, lon))
            _cache[emirate] = hit
        except Exception as e:
            return {"emirate": emirate, "name": name_ar if L == "ar" else name_en, "available": False, "reason": type(e).__name__ + ": " + str(e)[:120],
                    "emirates": [{"key": k, "name": v[1] if L == "ar" else v[0]} for k, v in EMIRATES.items()]}
    w = hit[1]
    b = band(w["feels_c"])
    return {"emirate": emirate, "name": name_ar if L == "ar" else name_en, "available": True, **w, "band": b, "tip": TIPS[L][b], "why": WHY[L],
            "source": SOURCE, "emirates": [{"key": k, "name": v[1] if L == "ar" else v[0]} for k, v in EMIRATES.items()]}
