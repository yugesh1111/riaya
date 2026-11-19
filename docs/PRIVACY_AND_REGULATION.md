# Privacy by design

## Rules that apply (Abu Dhabi)
- **UAE Federal Law No. 2 of 2019** (ICT in health fields) and its implementing decisions: health data is created and stored in the UAE, cross-border transfer is restricted, and there are retention and confidentiality duties.
- **DoH Abu Dhabi ADHICS** (Healthcare Information and Cyber Security Standard): security controls for DoH-licensed entities, with restrictions on cloud use for health information unless approved. Licensed facilities must be certified.
- **Federal Decree-Law 45/2021 (PDPL)** treats health and sexual data as sensitive personal data, but it defers to sector-specific health-data legislation where that exists.
- ADGM Data Protection Regulations apply only to entities inside the ADGM free zone, and only if the operator is based there.

Confirm with legal counsel before the pilot. This is the team's reading, not legal advice.

## What the code does today

| Principle | Implementation |
|---|---|
| Explicit, granular consent | Four separate purposes (core summary, clinician review, device data, research), versioned and timestamped. Core is required. Research is off by default. Without device consent, uploads are refused. (`/api/consent`) |
| Data minimisation | No identity data is collected. Unknown answer fields are dropped on save. Raw Apple Health/CGM files are parsed in memory and discarded; only the summary (for example "average sleep 5.6 h") is stored. Cohort labels for fairness reporting are coarse (age decade and background). |
| Encryption at rest | Answers, device summaries, test results, results and clinician notes are encrypted with Fernet (AES-128-CBC + HMAC-SHA256). The key comes from `RIAYA_DATA_KEY` (use an HSM/KMS in production) or a local 0600 key file. Tested: `test_data_encrypted_at_rest`. |
| User-controlled sharing | Clinicians see a case only if the man consented to review, or if he gave them an 8-character one-time code. The code expires after 72 h and he can revoke it; revoking removes access immediately (tested). |
| Right to erase / export | `DELETE /api/me` erases all rows (SQLite `secure_delete` overwrites them) and unlinks event counters. `GET /api/me/export` returns everything held about him. |
| Access control and audit | Clinician passwords use PBKDF2-SHA256 (310k iterations), sessions last 8 h, and every login, queue view, case view, review and status change is logged with time and actor. |
| Messages and partner view | Patient–clinician messages are encrypted at rest and erased with his data. The partner link shows status only, expires in 30 days, can be revoked, and keeps its token in the URL fragment (not sent to servers or in Referer headers). Video rooms use unguessable names; production should use a self-hosted Jitsi in the UAE. |
| No trail at home | No push notifications, SMS or email. Quick exit. Pages send `Cache-Control: no-store`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`. |
| Human oversight | Any referral at fertility-services level or above, any high signal tier and any red flag is held as `pending_review` until a clinician approves or changes it. Time-critical red flags show immediate instructions to the man first. |

## For production
- Hosting in UAE (UAE-region cloud approved under ADHICS, or on-premise at the partner facility). Postgres with column encryption and KMS-managed keys.
- SSO for clinicians (UAE PASS / facility IdP), role-based access, and periodic access review.
- DPIA, penetration test, ADHICS certification through the hosting partner.


## On the phone: lock, encryption and disguise (added November 2026)

| Control | How it works |
|---|---|
| Locked by default | After his first summary Riaya requires a 4–6 digit PIN. Every opening and every return after 15 seconds away shows the lock first. Face ID / Touch ID / fingerprint can unlock it (WebAuthn platform authenticator with user verification, checked on the phone). |
| PIN storage | Never stored. Only PBKDF2-SHA-256 (210,000 iterations, random 16-byte salt). Five wrong tries pause input for 30 s, then longer. |
| Documents on the phone | Scanned reports are kept only on the phone (IndexedDB), encrypted with AES-256-GCM. The key is generated on the phone as a non-extractable WebCrypto key and is used only while the app is unlocked. |
| Disguise | `/calc.html` installs as "Calculator" with a calculator icon and works as a calculator. The PIN followed by "=" opens Riaya. Installed apps cannot change their icon later, so the disguise is chosen at install. |
| Forgotten PIN | He can erase Riaya from the phone; his record can be restored with his recovery code. Riaya cannot reset the PIN for him, by design. |
| Clinicians | The console has its own PIN lock for shared computers; clinician sessions also end when the tab closes. |
| What travels | WhatsApp and reminders carry only neutral text and one-time codes, never results. Reports he scans stay on the phone; only the values he confirms are sent, encrypted at rest on the server. |

Limits, stated plainly: a web-app lock protects against someone picking up an unlocked phone and against casual inspection; it is not a replacement for the phone's own passcode. Anyone with the phone's own unlock and developer tools could still delete data. The production plan keeps one encrypted server database owned by the programme (see the roadmap).
