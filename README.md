# ScamShield AI — Fraud Detection & Phishing Prevention

**Domain: Cybersecurity** · PromptWars Hackathon

## The Problem
People in India receive fraudulent SMS, WhatsApp messages and emails every day — fake
bank KYC updates, Aadhaar warnings, delivery/COD charges, fake job offers, UPI refund
traps and electricity-bill threats. Many people, especially elderly users, cannot tell a
genuine message from a fraudulent one, and one wrong click can empty a bank account.

## Project Objectives
1. Let anyone check a suspicious **message** (SMS / WhatsApp / Email) in seconds.
2. Let anyone check a suspicious **URL** without ever opening it.
3. Explain **why** something is risky, in simple language — not just a yes/no answer.
4. Classify the scam type (Banking/KYC, UPI/Payment, Delivery, Job, Lottery,
   Government Impersonation, …) so users recognise the pattern next time.
5. Build community protection: reported scams warn everyone else.
6. Raise awareness of the most common India-specific scams and the 1930 helpline.

## The Solution
ScamShield AI is a full-stack web app (frontend + backend connected and working):

- **Message Analyzer** — paste a message, choose SMS / WhatsApp / Email (for Email you
  can add the sender address). You get a **risk score (0–100)**, a four-band verdict,
  the **scam category**, a **machine-learning signal**, every red flag with points and a
  strength label (**Strong indicator** = confirmed-type sign, **Warning** = heuristic
  sign), and clear advice.
- **Phishing URL Scanner** — paste a link. It is only parsed as text (**never opened or
  fetched**) and checked for IP hosts, http, shorteners, `@` tricks, punycode,
  look-alike subdomains, suspicious keywords and more.
- **Security Dashboard** — real counters from the app's own data (total analyses,
  high-risk detections, URLs scanned, community reports) plus a category distribution
  chart. No fake statistics.
- **Detection History** — every check is saved by the backend; you can search, delete
  records, and export them as CSV.
- **Safety Report download** — after every message check or URL scan, download a
  plain-text safety report (score, verdict, category, red flags and advice), or copy
  it to share with family members so they can be warned too.
- **Screenshot-based Scam Detection** — upload a screenshot of a suspicious
  message; OCR (Tesseract.js, in the browser) reads the text and fills the
  Analyzer automatically. If the OCR library cannot load, manual paste still works.
- **AI Explanation Assistant** — an "Explain Simply" button rewrites every result
  in very simple language: what the scam is, the trick, what can go wrong, and the
  safe action — with a one-line summary in Hinglish for family members.
- **ML Model Lab** — a live model-comparison section: dataset details, the NLP
  preprocessing pipeline, Accuracy / Precision / Recall / F1 for Naive Bayes vs
  Logistic Regression vs Random Forest, and the champion model's Confusion Matrix.
- **Scam Intelligence Map** — a schematic tile map of India that lights up from
  the states selected in community reports, showing where scams are reported from.
- **Report a Scam + Community Alerts** — reports are saved by the backend and shown
  live to warn everyone else.
- **Awareness section** — 8 India-specific scam cards (OTP, UPI, Banking, Fake Job,
  Lottery, KYC, Fake Courier, Phishing), a Do / Don't list and "Already clicked?"
  emergency steps (call **1930**).

### Risk bands (used everywhere)
| Score | Band | Colour |
|---|---|---|
| 0–24 | Low Risk | Green |
| 25–49 | Moderate Risk | Orange |
| 50–74 | High Risk | Orange-red |
| 75–100 | Critical Risk | Red |

## System Architecture
```
Browser (single page: public/index.html + style.css + app.js)
        |  fetch() JSON calls, same origin
        v
Python backend (server.py, standard library http.server only)
  |-- Rule engine     -> explainable score, reasons, category, advice
  |-- URL scanner     -> parses URL text, never fetches it
  |-- ML engine       -> ml_model.py, NLP preprocessing + Naive Bayes / Logistic Regression / Random Forest (champion signal)
  |-- Persistence     -> data.json (reports, history, counters; auto-seeded)
```
No framework, no database server, no build step: one Python process serves the
frontend and all APIs on http://localhost:8000.

## Machine Learning Approach
`ml_model.py` is a small ML engine written **from scratch in pure Python**
(no scikit-learn, so the project runs with zero installation):

- **NLP preprocessing:** lowercasing/cleaning, URL normalisation (every link →
  one LINK token), number normalisation (→ NUM token), tokenisation, stop-word
  removal, and light stemming.
- **Larger labelled dataset:** 480 labelled messages (286 scam / 194 safe),
  generated at startup from scam/safe templates with slot variation (bank names,
  amounts, links, fees) plus handwritten and deliberately hard borderline samples.
  No dataset file is needed.
- **Three models compared:** Multinomial **Naive Bayes**, **Logistic Regression**
  (gradient descent) and **Random Forest** (decision-tree ensemble) — all
  implemented from scratch.
- **Proper evaluation:** the models are compared on a held-out 20% test split
  (385 train / 95 test) with **Accuracy, Precision, Recall, F1-score and a
  Confusion Matrix** per model. Live results are shown in the app's **ML Model
  Lab** section and at `GET /svc/model-evaluation`. Current test results:

  | Model | Accuracy | Precision | Recall | F1 |
  |---|---|---|---|---|
  | Naive Bayes | 97.9% | 98.2% | 98.2% | 98.2% |
  | Logistic Regression | 98.9% | 98.3% | 100% | 99.1% |
  | Random Forest | 98.9% | 100% | 98.2% | 99.1% |

- **Champion model:** the best-F1 model (currently Logistic Regression) provides
  the **ML signal** shown next to the rule-based score. The final risk score
  stays **rule-based** — stable and fully explainable for judges.
- **Limits:** the dataset is template-generated for the hackathon, so metrics
  reflect that distribution; training on a large public SMS-spam corpus is the
  natural next step (see Future Improvements).

## Tech Stack
- **Backend:** Python 3 standard library only (`http.server`) — zero pip installs
- **Frontend:** Vanilla HTML, CSS, JavaScript — no external fonts; the only CDN use is
  the optional Tesseract.js OCR library for screenshot detection, which degrades
  gracefully (manual paste) when offline
- **ML:** Naive Bayes + Logistic Regression + Random Forest, all implemented from
  scratch in pure Python (`ml_model.py`), with NLP preprocessing and full evaluation
- **Storage:** A local JSON file (`data.json`) created and seeded automatically on first run

## How to Run (Windows)
1. Make sure Python 3 is installed (`python --version` in Command Prompt).
2. **Easiest:** double-click **`start.bat`** — it starts the server and opens the browser.
3. Or manually: open Command Prompt in this folder and run:
   ```
   python server.py
   ```
   Then open **http://localhost:8000** in your browser.
4. To stop the server, press `Ctrl + C` in the server window.

No API keys are required. See `.env.example` for the optional settings documentation.

## APIs
| Method | Endpoint | What it does |
|---|---|---|
| POST | `/svc/analyze` | Body `{"message": "...", "type": "SMS\|WhatsApp\|Email", "sender": "..."}` → `{score, verdict, band, category, ml_scam_probability, reasons[{rule, points, detail, strength}], advice[]}` |
| POST | `/svc/scan-url` | Body `{"url": "..."}` → `{score, verdict, band, category, reasons[], advice[]}` (URL is never fetched) |
| POST | `/svc/report` | Body `{"message": "...", "category": "...", "contact": "..."}` → saves a community report |
| GET | `/svc/reports` | Latest community alerts |
| GET | `/svc/history` | Detection history, latest first; optional `?q=text` search |
| DELETE | `/svc/history/<id>` | Deletes one history record |
| GET | `/svc/stats` | `{total_checked, fraud_found, urls_scanned, high_risk_count, reports_count, category_counts}` — all from real app data |
| GET | `/svc/model-evaluation` | Dataset info, NLP preprocessing steps, and Accuracy / Precision / Recall / F1 + Confusion Matrix for all 3 ML models, with the champion marked |
| GET | `/svc/health` | `{"status": "ok"}` |

## How the Message Scoring Works (for judges / viva)
Each rule adds explainable points, capped at 100:
- Asks for **OTP / PIN / CVV / password** → +35 (strong)
- **Shortened link** (bit.ly etc.) → +25 (strong) · **IP-address link** → +30 (strong) · **look-alike / punycode domain** → +20 (strong) · **http link** → +15 · any link → +10
- **Email sender mismatch** (claims to be a bank/government but sent from free Gmail/Yahoo) → +25 (strong)
- **KYC / verification pressure** → +20 · **threat / account-block language** → +20
- **Lottery / prize claim** → +20 · **urgency words** → +15 · **fee/payment request** → +15
- **Impersonation** of a trusted brand combined with a link or action request → +15
- **Unrealistic earning / fake job claim** → +15 · **"click here" pressure with a link** → +10

The URL scanner uses its own rule set: IP host +30, shortener +25, `@` trick +20,
punycode +20, brand hidden in subdomain +20, http +15, many subdomains +15,
suspicious keywords +15, hyphen-heavy domain +10, very long URL +10.

## Screenshots
<!-- Add screenshots here after running the app: Analyzer result, URL Scanner result, Dashboard. -->
_Screenshots placeholder — capture the Analyzer, URL Scanner and Dashboard sections after running the app._

## Project Structure
```
scamshield/
├── server.py              # backend: static hosting + all APIs + rule engines + persistence
├── ml_model.py            # ML engine: NLP preprocessing, 480-sample dataset, Naive Bayes + Logistic Regression + Random Forest, evaluation
├── public/
│   ├── index.html         # one-page app (Analyzer, URL Scanner, Dashboard, History, Alerts, Awareness)
│   ├── style.css          # dark navy / electric-blue cybersecurity theme
│   └── app.js             # calls the backend APIs
├── docs/
│   └── project_overview.md
├── start.bat              # double-click to run on Windows
├── start.sh               # same for Mac/Linux
├── .env.example           # documents that no API keys are required
└── data.json              # auto-created on first run (seeded community reports)
```

## Future Improvements
- QR-code image → URL extraction + scanning (screenshot OCR is already implemented)
- Train the same three models on a large public SMS-spam dataset (e.g. UCI SMS Spam
  Collection) and compare against the built-in template dataset
- SQLite database instead of the JSON file for larger deployments
- Optional external URL-reputation checks (Google Safe Browsing / VirusTotal) behind API keys
- Browser extension / WhatsApp share integration for one-tap checking

## Disclaimer
ScamShield AI is a heuristic checker built for a hackathon and for awareness. It
explains its reasons, but no automated tool is 100% accurate. Never rely on it alone
for financial decisions — when in doubt, verify through official apps, websites or
phone numbers, and report fraud to **1930** / **cybercrime.gov.in**.
