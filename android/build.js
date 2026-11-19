// Builds the signed Android app from the live site with Google's Bubblewrap: Riaya.apk (ae.riaya.app).
// The calculator cover is inside the app (chosen at first setup), so there is one app, not two.
// Usage: node build.js   (needs JDK 17 and the Android SDK; see README in this folder)
const fs = require("fs"), path = require("path"), crypto = require("crypto");
const { TwaManifest, TwaGenerator, ConsoleLog, Config, JdkHelper, AndroidSdkTools, GradleWrapper, KeyTool } = require("@bubblewrap/core");
const HOST = process.env.RIAYA_HOST || "riaya-xhby.onrender.com";
const JDK = process.env.JDK_PATH || "/Library/Java/JavaVirtualMachines/zulu-17.jdk";
const SDK = process.env.ANDROID_HOME || path.join(process.env.HOME, "Library/Android/sdk");
const log = new ConsoleLog("riaya");
const SIGN = path.join(__dirname, "signing");

async function key(jdk) {
  fs.mkdirSync(SIGN, { recursive: true });
  const ks = path.join(SIGN, "riaya.keystore"), pwFile = path.join(SIGN, "password.txt");
  if (!fs.existsSync(pwFile)) fs.writeFileSync(pwFile, crypto.randomBytes(18).toString("base64url"), { mode: 0o600 });
  const pw = fs.readFileSync(pwFile, "utf8").trim();
  if (!fs.existsSync(ks)) await new KeyTool(jdk, log).createSigningKey({ path: ks, alias: "riaya", password: pw, keypassword: pw,
    fullName: "Riaya", organizationalUnit: "Riaya", organization: "Riaya", country: "AE" });
  return { ks, pw };
}

async function build(app, sdk, jdk, k) {
  const dir = path.join(__dirname, "build", app.id);
  fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
  const m = await TwaManifest.fromWebManifest(`https://${HOST}/${app.manifest}`);
  Object.assign(m, { packageId: app.packageId, host: HOST, name: app.name, launcherName: app.name, startUrl: app.start,
    appVersionName: "1.0.0", appVersionCode: 1,
    enableNotifications: false, signingKey: { path: k.ks, alias: "riaya" }, generatorApp: "riaya-build" });
  await new TwaGenerator().createTwaProject(dir, m, log);
  const gradle = new GradleWrapper(process, sdk, dir);
  await gradle.assembleRelease();
  const unsigned = path.join(dir, "app/build/outputs/apk/release/app-release-unsigned.apk");
  const aligned = path.join(dir, "aligned.apk"), out = path.join(__dirname, app.out);
  await sdk.zipalign(unsigned, aligned);
  await sdk.apksigner(k.ks, k.pw, "riaya", k.pw, aligned, out);
  log.info("built " + out);
}

(async () => {
  const config = new Config(JDK, SDK);
  const jdk = new JdkHelper(process, config);
  const sdk = await AndroidSdkTools.create(process, config, jdk, log);
  const k = await key(jdk);
  await build({ id: "riaya", manifest: "manifest.webmanifest", packageId: "ae.riaya.app", name: "Riaya", start: "/index.html", color: "#0f2a3a", out: "Riaya.apk" }, sdk, jdk, k);
})().catch(e => { console.error(e); process.exit(1); });
