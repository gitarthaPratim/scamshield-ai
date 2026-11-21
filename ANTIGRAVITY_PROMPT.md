# Building ScamShield AI with Google Antigravity

Paste the master prompt below into Antigravity inside your cloned (empty) GitHub repo.
It recreates this exact v2 project. Then use the follow-up prompts for polish and testing.

## Master Prompt (paste this first)

```
Build a complete full-stack web application called "ScamShield AI" in this repository.

DOMAIN / PROBLEM: Cybersecurity. People receive fraudulent SMS, WhatsApp messages and
emails, and suspicious links, pretending to be from banks, delivery services and
government organisations. The app must help users identify potentially fraudulent
messages and URLs and understand the risks.

TECH CONSTRAINTS (strict — these override any usual framework choices):
- Backend in Python 3 using ONLY the standard library (http.server). No Flask, no pip
  packages, no scikit-learn/pandas, no frameworks, no node_modules. This is deliberate:
  the project must run on any computer with only Python 3 installed, with ZERO
  installation steps.
- Machine learning must be implemented in pure Python: a small Multinomial Naive
  Bayes text classifier (own code, in ml_model.py) trained at startup on ~46 short
  built-in labelled scam/safe sample messages embedded in the code. No dataset files,
  no model files. It returns a scam probability used as a SUPPORTING signal; the
  final risk score stays rule-based and explainable.
- Frontend in vanilla HTML, CSS and JavaScript only. No Bootstrap/Tailwind/Chart.js,
  no CDN links, no external fonts or images — it must work fully offline.
- The Python server serves the frontend AND the APIs from one process, on
  http://localhost:8000.
- Persistence in a local JSON file data.json (auto-created and seeded on first run
  with 5 realistic India-specific seed community reports: bank KYC fraud, Aadhaar
  update fraud, delivery COD fraud, fake job offer, electricity bill fraud).
  Do NOT use SQLite or MySQL in this version.
- Total project size well under 10 MB. Single branch (main) only.

FILES:
- server.py and ml_model.py at the root.
- public/index.html, public/style.css, public/app.js for the frontend.
- README.md, .env.example, docs/project_overview.md,
  start.bat (double-click: starts server and opens browser),
  start.sh, .gitignore (data.json, __pycache__, .env, venv).

RISK BANDS (used everywhere): 0-24 "Low Risk" (green), 25-49 "Moderate Risk"
(orange), 50-74 "High Risk" (orange-red), 75-100 "Critical Risk" (red).
Every reason in every response carries a "strength": "strong" (confirmed-type
indicator, e.g. OTP request, shortened or IP link) or "warning" (heuristic sign,
e.g. urgency words).

BACKEND APIs:
- POST /api/analyze  body {"message", "type": "SMS"|"WhatsApp"|"Email",
  "sender" (optional, Email only)} returns {"score", "verdict", "band", "category",
  "ml_scam_probability", "reasons": [{rule, points, detail, strength}], "advice"}.
  Category is one of: Banking/KYC Scam, Delivery/Courier Scam, Job Offer Scam,
  Lottery/Prize Scam, UPI/Payment Scam, Government Impersonation, Other/Unknown
  (keyword-based). Message rule weights: OTP/PIN/CVV/password request +35 (strong);
  shortened link +25 (strong); IP-address link +30 (strong); look-alike/punycode
  domain +20 (strong); email sender mismatch (claims bank/govt but sent from free
  Gmail/Yahoo) +25 (strong); http link +15; any link +10; KYC pressure +20;
  threat/account-block language +20; lottery/prize claim +20; urgency +15;
  fee/payment request +15; impersonation with link/action +15; unrealistic earning
  claim +15; "click here" pressure with link +10. Cap 100.
  Every analysis is saved to a detection history and increments total_checked.
- POST /api/scan-url  body {"url"} returns {"score", "verdict", "band",
  "category": "Phishing URL", "reasons", "advice"}. Parse the URL as text only —
  NEVER open or fetch it. Rules: IP host +30 (strong); shortener (bit.ly etc.) +25
  (strong); '@' in address +20 (strong); punycode +20 (strong); brand name hidden in
  subdomain +20 (strong); http +15; 2+ subdomains +15; suspicious keywords in URL
  (verify, login, kyc, secure, update, free, prize...) +15; hyphen-heavy domain +10;
  length > 75 chars +10. Saves to history and increments urls_scanned.
- POST /api/report  body {"message", "category", "contact" (optional)} saves the
  report and returns it with id and timestamp.
- GET /api/reports returns the latest community reports, newest first.
- GET /api/history returns detection history (latest first), with optional ?q=
  search over preview/category/verdict/type.
- DELETE /api/history/<id> deletes one history record.
- GET /api/stats returns {"total_checked", "fraud_found", "urls_scanned",
  "high_risk_count" (history records with score >= 50), "reports_count",
  "category_counts"} — computed ONLY from real app data, never invented.
- GET /api/health returns {"status": "ok"}.

FRONTEND (single page, dark navy/charcoal cybersecurity theme, electric blue and
cyan accents, green/orange/orange-red/red for the four bands, mobile responsive).
Sticky nav with anchors: Analyzer, URL Scanner, Dashboard, History, Community
Alerts, Awareness. Sections:
- Hero explaining the problem with buttons to the Analyzer and URL Scanner.
- Message Analyzer: type selector (SMS/WhatsApp/Email); a Sender field that appears
  only for Email; textarea; Check button; "Try a Sample Scam" and "Try a Safe
  Message" buttons. Result: animated score circle coloured by band, verdict,
  category chip, "ML signal: N% scam-like" chip, red-flag list with points and
  strength badges, advice list.
- Phishing URL Scanner: URL input, Scan button, one phishing sample and one safe
  sample button, result display like the analyzer, and a note that the URL is
  never opened.
- Security Dashboard: 4 stat cards (Total Analyses, Fraud/High-Risk Detected,
  URLs Scanned, Community Reports) from GET /api/stats, plus a pure-CSS bar chart
  of category_counts (no chart library).
- Report a Scam form (message, category dropdown, optional source) that refreshes
  Community Alerts and the dashboard on submit.
- Community Alerts: cards from GET /api/reports.
- Detection History: list from GET /api/history with date, type, score chip,
  verdict, category and preview; a search box; a per-item Delete button; an
  Export CSV button that downloads the history as a CSV file generated in the
  browser from the fetched data.
- Awareness: 8 cards (OTP Scam, UPI Fraud, Banking Scam, Fake Job Offer, Lottery
  Scam, KYC Scam, Fake Courier, Phishing) with 2-3 simple India-specific lines
  each, a Do / Don't list, and an "Already clicked or paid?" paragraph (call 1930,
  cybercrime.gov.in, contact your bank).
- Footer with a disclaimer (heuristic checker, not 100% perfect, URLs never opened).

Escape all user text before inserting it into the page (no HTML injection).
Handle server errors in the UI with a friendly message.
After creating all files, tell me how to run it: python server.py, then open
http://localhost:8000.
```

## Follow-up Prompt 1 — Styling polish

```
Improve the visual design of public/style.css only: keep the same HTML structure and
class names, keep the dark navy/charcoal theme with electric blue/cyan accents, make
cards and the dashboard chart cleaner, and verify everything on a 360px-wide mobile
screen. Do not add any external fonts, images or CDN links.
```

## Follow-up Prompt 2 — Extra awareness content

```
Add a "5 Signs of a Scam Message" numbered list at the top of the Awareness section
in public/index.html: unknown sender, urgency, secret (OTP/PIN) request, suspicious
link, and prize/fee trap — each with one simple India-specific example line. Add any
needed styles to public/style.css. Do not change the backend.
```

## Follow-up Prompt 3 — Testing

```
Test this project end to end and report the results: start the server, then
1) POST to /api/analyze a clear scam message (http bit.ly link, OTP request,
   account-block threat, lottery prize) — confirm a high score, a category and an
   ml_scam_probability value.
2) POST a normal delivery message with no link — confirm a low score.
3) POST to /api/scan-url the URL http://103.45.67.89/sbi-secure-login-verify —
   confirm a high score; then scan https://www.google.com — confirm a low score.
4) GET /api/history and confirm the test records are there; test ?q= search and
   DELETE one record.
5) GET /api/stats and confirm the counters moved.
6) POST a report to /api/report, then GET /api/reports and confirm it is first.
Fix any bug you find and re-run the failing test.
```
