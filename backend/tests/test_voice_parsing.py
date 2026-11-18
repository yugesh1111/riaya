"""Spoken and typed answers in English and Gulf Arabic, as the voice chat and WhatsApp receive them.

The browser side (web/js/nlu.js) is checked by running it in Node when Node is installed.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.conversation import _months

ROOT = Path(__file__).resolve().parents[2]

NUMBERS = [("I am thirty two", 32), ("عمري اثنين وثلاثين", 32), ("٣٤ سنة", 34), ("ست ونص", 6.5), ("six and a half hours", 6.5),
           ("one seventy eight", 178), ("one hundred and seventy eight", 178), ("a hundred and eighty", 180), ("ninety five kilos", 95),
           ("مية وثمانين", 180), ("مية وخمسة وسبعين", 175), ("خمسة وتسعين", 95), ("175", 175)]
MONTHS = [("18 months", 18), ("eighteen months", 18), ("a year and a half", 18), ("2 years", 24), ("three and a half years", 42),
          ("سنة ونص", 18), ("سنة", 12), ("سنتين", 24), ("ثلاث سنوات", 36), ("ستة اشهر", 6)]
YESNO = [("yeah I do", "yes"), ("لا ما أدخن", "no"), ("ايه", "yes"), ("مب متأكد", "unsure"), ("مادري", "unsure"), ("skip", "skip")]


@pytest.mark.skipif(not shutil.which("node"), reason="Node is not installed")
def test_browser_understanding_in_both_languages():
    script = f"""
      const N = require({json.dumps(str(ROOT / "web/js/nlu.js"))});
      const out = {{
        numbers: {json.dumps(NUMBERS, ensure_ascii=False)}.map(([t]) => N.number(t)),
        months: {json.dumps(MONTHS, ensure_ascii=False)}.map(([t]) => N.months(t)),
        yesno: {json.dumps(YESNO, ensure_ascii=False)}.map(([t]) => N.yesNo(t)),
      }};
      console.log(JSON.stringify(out));"""
    got = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert got["numbers"] == [e for _, e in NUMBERS]
    assert got["months"] == [e for _, e in MONTHS]
    assert got["yesno"] == [e for _, e in YESNO]


def test_whatsapp_understands_years():
    for text, expected in [("18", 18), ("2 years", 24), ("سنة ونص", 18), ("سنتين", 24), ("١٨ شهر", 18), ("a year", 12), ("3 سنوات", 36)]:
        assert _months(text) == expected, text
