/* Riaya-Net on the device: the same small network as the server (backend/app/riayanet.py), from web/models/riayanet.json.
   Nothing leaves the phone to run it. Returns a probability and each factor's contribution (log-odds, occlusion). */
(function (root) {
  function logit(m, x) {
    let h = x.map((v, i) => (v - m.mean[i]) / m.scale[i]);
    m.weights.forEach((W, l) => {
      const out = W[0].map((_, j) => h.reduce((s, v, i) => s + v * W[i][j], m.biases[l][j]));
      h = l < m.weights.length - 1 ? out.map(v => Math.max(0, v)) : out;
    });
    return h[0];
  }
  function predict(m, x) {
    const z = logit(m, x);
    const contributions = m.features.map((f, i) => {
      const x0 = x.slice(); x0[i] = m.fill[i];
      return { feature: f, label: m.labels[f] || f, logit: +(z - logit(m, x0)).toFixed(3) };
    }).filter(c => Math.abs(c.logit) > 1e-4).sort((a, b) => Math.abs(b.logit) - Math.abs(a.logit));
    return { probability: +(1 / (1 + Math.exp(-z))).toFixed(3), contributions };
  }
  let cached = null;
  async function load(url = "models/riayanet.json") { return cached || (cached = await (await fetch(url)).json()); }
  root.RiayaNet = { logit, predict, load };
  if (typeof module !== "undefined") module.exports = root.RiayaNet;
})(typeof window !== "undefined" ? window : globalThis);
