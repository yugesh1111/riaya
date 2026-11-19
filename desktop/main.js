// Riaya for Mac: a secure window onto the Riaya web app. Nothing is stored by this wrapper itself; the app's own
// lock, encryption and privacy screen work exactly as in the browser. Links to other sites open in the browser.
const { app, BrowserWindow, shell, session } = require("electron");
const path = require("path");
const URL_APP = process.env.RIAYA_URL || "https://riaya-xhby.onrender.com/";

function createWindow() {
  const win = new BrowserWindow({
    width: 430, height: 900, minWidth: 360, minHeight: 640, title: "Riaya", backgroundColor: "#0f2a3a",
    titleBarStyle: "hiddenInset",
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, "preload.js") },
  });
  const origin = new URL(URL_APP).origin;
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(origin) || url.startsWith("blob:")) return { action: "allow" };
    shell.openExternal(url); return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e, url) => { if (!url.startsWith(origin)) { e.preventDefault(); shell.openExternal(url); } });
  win.webContents.on("did-fail-load", () => win.loadFile(path.join(__dirname, "offline.html")));
  win.loadURL(URL_APP);
}

app.whenReady().then(() => {
  // microphone for voice answers; camera for scanning reports; nothing else
  session.defaultSession.setPermissionRequestHandler((wc, perm, cb) => cb(["media", "clipboard-sanitized-write"].includes(perm)));
  createWindow();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
