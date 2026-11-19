# Security in Riaya: what an attacker would face

Riaya holds some of the most sensitive data a man has. This document lists the ways someone could try to get at it, what stops them, and what is still open. Nothing here is a promise that no attack can ever work. It is the design, written down so it can be checked.

## 1. Someone picks up his phone

| Attack | Protection |
|---|---|
| Opens the app | **Locked by default.** A PIN is required once he has a summary. Every opening, and every return after 15 seconds away, shows the lock first. The page underneath is hidden, not just covered. |
| Guesses the PIN | 4–6 digits. Only a PBKDF2-SHA-256 hash is kept (210,000 rounds, random salt), never the PIN. After 5 wrong tries, input pauses for 30 s, then longer each time. |
| Sees the app icon | **Calculator disguise.** Installed as "Calculator", it works as a calculator. The PIN followed by "=" opens Riaya. |
| Looks over his shoulder or at the app switcher | The screen blurs whenever the app loses focus. A one-tap "hide" covers it with a neutral tip, and the page title changes. |
| Opens a document after he unlocked the app and left the phone | **Every vault document asks for Face ID / fingerprint / PIN again**, and closes itself when he leaves the app. |
| Reads the phone's storage directly (a stolen, unlocked phone, or developer tools) | Documents are stored encrypted with AES-256-GCM. The key is a non-extractable WebCrypto key: page code can use it but not read it. |

## 2. Someone attacks the server

| Attack | Protection |
|---|---|
| Steals the database file | Health data is encrypted at rest (Fernet: AES-128-CBC + HMAC-SHA256). The key comes from `RIAYA_DATA_KEY`, kept outside the database. |
| Identifies a man from the data | Riaya never asks for a name, phone number, email or Emirates ID. Each man is a random token held only on his phone. |
| Brute-forces clinician sign-in | 5 wrong passwords from one address, or for one username, within 15 minutes block sign-in for 15 minutes. Passwords are hashed with PBKDF2-SHA-256 (310,000 rounds). Sessions expire. |
| Guesses handover codes or recovery codes | Codes are random, expire, and are rate-limited per address (too many tries in an hour → refused). |
| Injects a script or frames the app (XSS, clickjacking) | Content Security Policy: scripts only from Riaya and two public CDNs, no plugins, no framing (`frame-ancestors 'none'`, `X-Frame-Options: DENY`), forms post only to Riaya. HSTS, `nosniff`, `no-referrer` and Cross-Origin-Opener-Policy are also set. |
| Reads data over the network | HTTPS only (HSTS). API responses are never cached (`Cache-Control: no-store`). |

## 3. Someone on the care side misuses access

| Attack | Protection |
|---|---|
| A doctor looks at a record they shouldn't | Clinicians see only men who agreed to review, or who chose their clinic. He can **pause all sharing with one switch**, and choose which parts each recipient sees. |
| Access without him knowing | **Every time a doctor or clinic opens his summary, labs or referral, he gets a private message** saying who (role), what and when, with a reminder of the pause switch. Every access is also in his access log, with consent receipts. |
| Data kept forever | He chooses how long data is kept (until he deletes it, or 3–24 months after his last visit). After that it is erased automatically. |
| The clinic sees too much | The clinic sees only what he shared, through a one-time code. He can preview the exact letter before sharing. |

## 4. Messages and other channels

- **WhatsApp:** carries only the check itself and neutral reminders. Results and documents stay in the app, and the phone number is never stored (only a salted hash).
- **Calendar entries** say only "Appointment" or "Weekly check-in".
- **Voice:** in private mode, speech is recognised on the phone (Whisper) and audio never leaves it. With the browser's speech service, only the text answer is kept.

## 5. What is still open (stated plainly)

1. **A web app runs inside the browser.** If the phone itself is fully compromised (malware with screen access), no app-level lock can protect what is on screen. This is true of every app, native or web.
2. **The PIN protects access, not the key.** The document key is non-extractable but not derived from the PIN, so Face ID can unlock it. Someone with the phone unlocked and developer tools could delete data or run code in the page, but cannot export the key.
3. **The demo server** is on Render's free plan, outside the UAE, and its disk resets on every deploy. Production should use one encrypted database owned by the programme, hosted in the UAE (for example Azure UAE North), with the key in a key vault.
4. **No external penetration test yet.** It is planned before any pilot with real men.

## Automated checks

- 75 API tests, including consent, revocation, pause and access notices (`backend/tests`).
- Measured scenario checks (`validation/SCENARIOS.md`): consent 15/15, guardrails 30/30.
- Accessibility (WCAG 2.2 AA, axe-core): no violations on the main pages.
