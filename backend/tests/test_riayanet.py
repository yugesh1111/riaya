"""Riaya-Net: our network, pre-trained on our simulated cohort and fine-tuned on real data."""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from app import riayanet

ROOT = Path(__file__).resolve().parents[2]
SMOKER = {"age": 34, "smoking": "daily", "sitting_h": 11, "sleep_h": 5.5, "underwear": "tight", "fever": "yes"}
INS = {"bmi": 32, "pss4": 11, "stop_bang": 4, "audit_c": 0}


def test_model_file_is_complete_and_honest():
    m = riayanet.model()
    assert m["features"] == riayanet.FEATURES and len(m["weights"]) == 3
    ev = m["evaluation"]
    for k in ("logistic_real_only", "network_from_scratch", "pretrained_only", "pretrained_finetuned"):
        assert 0 < ev[k]["auc_mean"] < 1 and len(ev[k]["auc_ci95"]) == 2
    assert ev["real_n"] == 100 and ev["folds"] == 50
    assert "Never shown to the man" in m["use"]


def test_prediction_and_contributions():
    out = riayanet.predict(SMOKER, INS)
    assert 0 < out["probability"] < 1 and out["contributions"]
    healthy = riayanet.predict({"age": 30, "smoking": "never", "sitting_h": 4, "sleep_h": 7.5, "underwear": "loose"},
                               {"bmi": 23, "pss4": 3, "stop_bang": 1, "audit_c": 0})
    assert out["probability"] > healthy["probability"]  # more risk factors, higher estimate
    labels = [c["label"] for c in out["contributions"]]
    assert all(isinstance(c["logit"], float) for c in out["contributions"]) and labels


def test_uci_mapping():
    X, y = riayanet.uci_data(riayanet.pretrain_data(2000)[0].mean(0))
    col = {f: i for i, f in enumerate(riayanet.FEATURES)}
    assert X.shape == (100, len(riayanet.FEATURES)) and y.sum() == 12
    assert X[:, col["age"]].min() >= 18 and X[:, col["age"]].max() <= 36 and set(np.unique(X[:, col["smoker"]])) <= {0.0, 1.0}


@pytest.mark.skipif(not shutil.which("node"), reason="Node is not installed")
def test_on_device_copy_matches_server():
    x = riayanet.encode(SMOKER, INS)
    server = riayanet.predict(SMOKER, INS)["probability"]
    web = ROOT / "web" / "models" / "riayanet.json"
    assert json.loads(web.read_text())["weights"] == riayanet.model()["weights"]
    script = f"""const R = require({json.dumps(str(ROOT / 'web/js/riayanet.js'))});
      const m = require({json.dumps(str(web))}); console.log(R.predict(m, {json.dumps(x)}).probability);"""
    device = float(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert abs(device - server) < 1e-3
