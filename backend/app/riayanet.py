"""Riaya-Net: our own small neural network, pre-trained on our simulated cohort and fine-tuned on real data.

1. Pre-training: 20,000 simulated men from synth.simulate(), whose semen outcomes follow the effect sizes in our
   evidence graph (each effect cites its study). This teaches the network the shape of the evidence.
2. Fine-tuning: the same network keeps training, at a lower learning rate, on the real UCI Fertility data
   (100 men, WHO semen analysis). A small replay sample of the simulated cohort is mixed in so it does not
   forget what it learned. Features the real data lacks are filled with the cohort average.
3. Evaluation (honest): repeated stratified 5-fold cross-validation on the real data, against a logistic
   regression trained on the real data alone, the same network trained from scratch, and the pre-trained
   network with no fine-tuning. The simulated hold-out shows whether fine-tuning made it forget.

The exported weights (data/riayanet.json, web/models/riayanet.json) are small enough to run on the phone,
so the model can work with no data leaving the device. It gives clinicians a second opinion with
per-factor contributions. The man never sees a probability.
"""
import json
from pathlib import Path

import numpy as np

from . import ml, synth

ROOT = Path(__file__).resolve().parents[2]
MODEL_FILE = ROOT / "data" / "riayanet.json"
WEB_FILE = ROOT / "web" / "models" / "riayanet.json"
FEATURES = synth.FEATURES + ["fever_recent"]
LABELS = {"age": "Age", "bmi": "BMI", "smoker": "Daily smoking", "alcohol_units": "Alcohol (units/week)", "sleep_h": "Sleep (h)",
          "pss4": "Stress (PSS-4)", "sitting_h": "Sitting (h/day)", "tight": "Tight underwear", "hot_bath": "Regular hot baths/sauna",
          "aas": "Anabolic steroids now", "varicocele": "Varicocele / scrotal surgery", "cryptorchid": "Undescended testis",
          "mumps": "Mumps / childhood illness", "diabetes": "Diabetes", "stop_bang": "Sleep apnoea score", "vitd_low": "Low vitamin D",
          "fever_recent": "High fever in last 3 months"}
HIDDEN = (24, 12)
SEED = 7


# ---------------------------------------------------------------- data
def pretrain_data(n=20000, seed=42):
    X, y, _ = synth.simulate(n, seed)
    return np.column_stack([X, np.zeros(len(X))]), y  # no fever effect is assumed in the simulation


def uci_data(fill):
    """UCI rows mapped onto our features. `fill` = cohort means for features the real data does not record."""
    Xu, y = ml.load()
    season, age01, child, trauma, surgery, fever, alc, smoke, sit = Xu.T
    units = np.select([alc <= 0.2, alc <= 0.4, alc <= 0.6, alc <= 0.8], [35, 20, 10, 3], 0)
    X = np.tile(np.array(fill, dtype=float), (len(y), 1))
    col = {f: i for i, f in enumerate(FEATURES)}
    X[:, col["age"]] = 18 + age01 * 18
    X[:, col["smoker"]] = (smoke == 1).astype(float)
    X[:, col["alcohol_units"]] = units
    X[:, col["sitting_h"]] = sit * 16
    X[:, col["mumps"]] = child
    X[:, col["varicocele"]] = np.maximum(surgery, trauma)
    X[:, col["fever_recent"]] = (fever == -1).astype(float)
    return X, y


# ---------------------------------------------------------------- the network
def _net(lr=0.003, seed=SEED):
    from sklearn.neural_network import MLPClassifier
    return MLPClassifier(hidden_layer_sizes=HIDDEN, activation="relu", alpha=1e-3, learning_rate_init=lr,
                         max_iter=60, batch_size=256, early_stopping=False, random_state=seed)


def _scaler(X):
    from sklearn.preprocessing import StandardScaler
    return StandardScaler().fit(X)


def pretrain(Xs, ys, seed=SEED):
    import warnings
    sc = _scaler(Xs)
    m = _net(seed=seed)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m.fit(sc.transform(Xs), ys)
    return sc, m


def finetune(sc, m, Xr, yr, Xs, ys, epochs=40, lr=0.0008, replay=400, seed=SEED):
    """Continues training on the real rows (positives up-weighted by repetition) mixed with a replay sample."""
    import copy
    rng = np.random.default_rng(seed)
    m = copy.deepcopy(m)
    m.set_params(learning_rate_init=lr, batch_size=64)
    pos = np.where(yr == 1)[0]
    reps = max(1, int(round((len(yr) - len(pos)) / max(1, len(pos)))) - 1)
    Xr2 = np.vstack([Xr] + [Xr[pos]] * reps)
    yr2 = np.concatenate([yr] + [yr[pos]] * reps)
    for _ in range(epochs):
        idx = rng.choice(len(ys), replay, replace=False)
        X = np.vstack([Xr2, Xs[idx]])
        y = np.concatenate([yr2, ys[idx]])
        order = rng.permutation(len(y))
        m.partial_fit(sc.transform(X[order]), y[order])
    return m


def _auc(y, p):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p))


# ---------------------------------------------------------------- evaluation
def evaluate(repeats=10, seed=0):
    from sklearn.metrics import brier_score_loss
    from sklearn.model_selection import RepeatedStratifiedKFold, train_test_split
    Xs, ys = pretrain_data()
    Xs_tr, Xs_te, ys_tr, ys_te = train_test_split(Xs, ys, test_size=0.2, random_state=seed, stratify=ys)
    sc, base = pretrain(Xs_tr, ys_tr)
    fill = Xs_tr.mean(0)
    Xr, yr = uci_data(fill)
    Xraw, _ = ml.load()
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=repeats, random_state=seed)
    res = {k: {"auc": [], "brier": []} for k in ("logistic_real_only", "network_from_scratch", "pretrained_only", "pretrained_finetuned")}
    forget = []
    for tr, te in cv.split(Xr, yr):
        preds = {}
        lg = ml._pipeline().fit(Xraw[tr], yr[tr])
        preds["logistic_real_only"] = lg.predict_proba(Xraw[te])[:, 1]
        sc0 = _scaler(Xr[tr])
        scratch = finetune(sc0, _net().partial_fit(sc0.transform(Xr[tr][:2]), yr[tr][:2], classes=[0, 1]), Xr[tr], yr[tr], Xs_tr, ys_tr,
                           epochs=60, lr=0.003, replay=0)
        preds["network_from_scratch"] = scratch.predict_proba(sc0.transform(Xr[te]))[:, 1]
        preds["pretrained_only"] = base.predict_proba(sc.transform(Xr[te]))[:, 1]
        ft = finetune(sc, base, Xr[tr], yr[tr], Xs_tr, ys_tr)
        preds["pretrained_finetuned"] = ft.predict_proba(sc.transform(Xr[te]))[:, 1]
        for k, p in preds.items():
            res[k]["auc"].append(_auc(yr[te], p))
            res[k]["brier"].append(float(brier_score_loss(yr[te], p)))
        forget.append(_auc(ys_te[:2000], ft.predict_proba(sc.transform(Xs_te[:2000]))[:, 1]))
    out = {}
    for k, v in res.items():
        a = np.array(v["auc"])
        out[k] = {"auc_mean": round(float(a.mean()), 3), "auc_ci95": [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)],
                  "brier": round(float(np.mean(v["brier"])), 3)}
    out["simulated_holdout_auc"] = {"pretrained_only": round(_auc(ys_te, base.predict_proba(sc.transform(Xs_te))[:, 1]), 3),
                                    "after_finetuning": round(float(np.mean(forget)), 3)}
    out["real_n"], out["real_positives"], out["folds"] = int(len(yr)), int(yr.sum()), 5 * repeats
    return out


# ---------------------------------------------------------------- final model and export
def train(evaluation=None):
    Xs, ys = pretrain_data()
    sc, base = pretrain(Xs, ys)
    fill = Xs.mean(0)
    Xr, yr = uci_data(fill)
    ft = finetune(sc, base, Xr, yr, Xs, ys)
    model = {"name": "Riaya-Net", "version": 1, "features": FEATURES, "labels": LABELS, "hidden": list(HIDDEN), "activation": "relu",
             "mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(), "fill": fill.tolist(),
             "weights": [w.round(6).tolist() for w in ft.coefs_], "biases": [b.round(6).tolist() for b in ft.intercepts_],
             "pretraining": {"data": "Riaya simulated cohort (synth.simulate, literature effect sizes)", "n": int(len(ys)),
                             "prevalence": round(float(ys.mean()), 3)},
             "finetuning": {"data": "UCI Fertility (Gil et al. 2012), WHO semen analysis", "n": int(len(yr)), "positives": int(yr.sum()),
                            "replay": "400 simulated rows per epoch", "missing_features": "filled with the cohort average"},
             "evaluation": evaluation,
             "use": "Clinician second opinion only, with per-factor contributions. Never shown to the man as a probability."}
    for f in (MODEL_FILE, WEB_FILE):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(model, separators=(",", ":")))
    _cache.clear()
    return model


_cache = {}


def model():
    if "m" not in _cache:
        if not MODEL_FILE.exists():
            train()
        _cache["m"] = json.loads(MODEL_FILE.read_text())
    return _cache["m"]


def _forward(m, x):
    h = (np.asarray(x, float) - np.array(m["mean"])) / np.array(m["scale"])
    for i, (W, b) in enumerate(zip(m["weights"], m["biases"])):
        h = h @ np.array(W) + np.array(b)
        if i < len(m["weights"]) - 1:
            h = np.maximum(h, 0)
    return float(h[0]) if np.ndim(h) else float(h)  # logit


def encode(answers, ins, wearable=None):
    return synth.encode(answers, ins, wearable) + [1.0 if answers.get("fever") == "yes" else 0.0]


def predict(answers, ins, wearable=None):
    """Probability of a below-reference semen analysis, and each factor's contribution in log-odds:
    how much the logit changes when that one factor is set to the cohort average (occlusion)."""
    m = model()
    x = np.array(encode(answers, ins, wearable), float)
    logit = _forward(m, x)
    contrib = []
    for i, f in enumerate(m["features"]):
        x0 = x.copy()
        x0[i] = m["fill"][i]
        d = logit - _forward(m, x0)
        if abs(d) > 1e-4:
            contrib.append({"feature": f, "label": m["labels"].get(f, f), "value": round(float(x[i]), 2), "logit": round(float(d), 3)})
    contrib.sort(key=lambda c: -abs(c["logit"]))
    ev = m.get("evaluation") or {}
    return {"probability": round(1 / (1 + np.exp(-logit)), 3), "contributions": contrib[:8], "model": "Riaya-Net (pre-trained on our cohort, fine-tuned on real data)",
            "real_data_auc": (ev.get("pretrained_finetuned") or {}).get("auc_mean"), "units": "log-odds"}


if __name__ == "__main__":
    ev = evaluate()
    print(json.dumps(ev, indent=1))
    train(ev)
    print("saved", MODEL_FILE, WEB_FILE)
