"""
ScamShield AI - Fraud Message & Phishing URL Checker
Backend: Python 3 standard library ONLY (no pip packages, no Flask).
Serves the static frontend AND the JSON APIs. Data persists in data.json.

Run:  python server.py
Open: http://localhost:8000
"""
import json
import os
import re
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from ml_model import ml_scam_probability, get_evaluation, CHAMPION

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
PORT = int(os.environ.get("PORT", "8000"))

_lock = threading.Lock()

# ---------------------------------------------------------------- seed data
SEED_REPORTS = [
    {
        "id": 1,
        "message": "Dear Customer, your SBI YONO account will be blocked today. Update your KYC at the link sent and share the OTP to reactivate.",
        "category": "Bank KYC Fraud",
        "state": "Assam",
        "contact": "SMS from VM-SBIKYC",
        "timestamp": "2026-11-18T10:15:00+00:00",
    },
    {
        "id": 2,
        "message": "Your Aadhaar will be deactivated. Update Aadhaar details immediately on the link below and pay Rs. 10 verification fee.",
        "category": "Government Impersonation",
        "state": "Delhi",
        "contact": "WhatsApp unknown number",
        "timestamp": "2026-11-18T12:40:00+00:00",
    },
    {
        "id": 3,
        "message": "Your parcel is held at customs. Pay COD charges of Rs. 499 on this link to release your delivery today.",
        "category": "Delivery / COD Fraud",
        "state": "Maharashtra",
        "contact": "SMS from AD-DLVCOD",
        "timestamp": "2026-11-19T09:05:00+00:00",
    },
    {
        "id": 4,
        "message": "Congratulations! Work from home job offer. Earn Rs. 3000 daily by liking videos. Registration fee only Rs. 999, join now.",
        "category": "Fake Job Offer",
        "state": "Uttar Pradesh",
        "contact": "WhatsApp unknown number",
        "timestamp": "2026-11-19T16:22:00+00:00",
    },
    {
        "id": 5,
        "message": "Electricity bill overdue. Your connection will be cut tonight at 9 PM. Pay immediately on the link and call this number.",
        "category": "Electricity Bill Fraud",
        "state": "Karnataka",
        "contact": "SMS from unknown number",
        "timestamp": "2026-11-20T08:31:00+00:00",
    },
]

# Report-form category names -> analyzer category names (for the chart).
REPORT_CATEGORY_MAP = {
    "Bank KYC Fraud": "Banking/KYC Scam",
    "Government Impersonation": "Government Impersonation",
    "Delivery / COD Fraud": "Delivery/Courier Scam",
    "Fake Job Offer": "Job Offer Scam",
    "Lottery / Prize Fraud": "Lottery/Prize Scam",
    "Electricity Bill Fraud": "Other/Unknown",
    "Other Scam": "Other/Unknown",
}


def _fresh_data():
    return {
        "stats": {"total_checked": 0, "fraud_found": 0, "urls_scanned": 0},
        "reports": list(reversed(SEED_REPORTS)),  # newest first
        "history": [],                            # newest first
        "next_id": len(SEED_REPORTS) + 1,
        "next_history_id": 1,
    }


def load_data():
    if not os.path.exists(DATA_FILE):
        data = _fresh_data()
        save_data(data)
        return data
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = _fresh_data()
        save_data(data)
        return data
    # Migrate older (v1) files: fill in any missing keys.
    fresh = _fresh_data()
    for key, val in fresh.items():
        if key not in data:
            data[key] = val
    for key, val in fresh["stats"].items():
        if key not in data.get("stats", {}):
            data["stats"][key] = val
    return data


def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)


# ---------------------------------------------------------------- risk bands
def band_for(score):
    """Four risk bands used everywhere in v2."""
    if score >= 75:
        return "Critical Risk", "critical"
    if score >= 50:
        return "High Risk", "high"
    if score >= 25:
        return "Moderate Risk", "moderate"
    return "Low Risk", "low"


# ---------------------------------------------------------------- scoring
SHORTENERS = ["bit.ly", "tinyurl.com", "t.co", "goo.gl", "rb.gy", "cutt.ly",
              "shorturl.at", "is.gd", "tiny.cc", "rebrand.ly", "ow.ly", "s.id"]
SUSPICIOUS_WORDS_IN_DOMAIN = ["verify", "kyc", "secure-login", "login-update",
                              "account-update", "sbi-", "hdfc-", "icici-",
                              "aadhaar-update", "refund-claim", "prize-claim"]
URL_KEYWORDS = ["verify", "login", "kyc", "secure", "update", "free", "prize",
                "claim", "bonus", "account", "banking", "confirm", "wallet"]
OFFICIAL_HINTS = ["sbi.co.in", "hdfcbank.com", "icicibank.com", "uidai.gov.in",
                  "india.gov.in", "amazon.in", "flipkart.com", "google.com"]
FREE_MAIL_DOMAINS = ["gmail.com", "yahoo.com", "yahoo.in", "hotmail.com",
                     "outlook.com", "rediffmail.com", "protonmail.com",
                     "gmx.com", "mail.com", "yandex.com"]


def _hits(text, patterns):
    found = []
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            found.append(m.group(0))
    return found


def classify_category(low):
    """Keyword-based scam category for a message (lowercased text)."""
    if _hits(low, [r"kyc", r"\bsbi\b", r"\bhdfc\b", r"\bicici\b", r"\brbi\b", r"reserve bank",
                   r"credit card", r"debit card", r"\bbank\b"]):
        return "Banking/KYC Scam"
    if _hits(low, [r"\bupi\b", r"paytm", r"phonepe", r"google pay", r"\bgpay\b",
                   r"collect request", r"payment request", r"enter.*pin to receive"]):
        return "UPI/Payment Scam"
    if _hits(low, [r"parcel", r"courier", r"delivery", r"customs", r"\bcod\b", r"shipment", r"redeliver"]):
        return "Delivery/Courier Scam"
    if _hits(low, [r"job offer", r"work from home", r"earn rs", r"earn ₹", r"part.?time job",
                   r"daily income", r"liking videos", r"hiring"]):
        return "Job Offer Scam"
    if _hits(low, [r"lottery", r"lucky draw", r"you (have )?won", r"prize", r"gift voucher"]):
        return "Lottery/Prize Scam"
    if _hits(low, [r"aadhaar", r"uidai", r"government", r"income tax", r"subsidy",
                   r"electricity board", r"\bpolice\b"]):
        return "Government Impersonation"
    return "Other/Unknown"


def analyze_message(message, msg_type="SMS", sender=""):
    """Explainable, rule-based scoring + category + ML signal + sender check."""
    text = message.strip()
    low = text.lower()
    reasons = []
    score = 0

    def add(points, rule, detail, strength):
        nonlocal score
        score += points
        reasons.append({"rule": rule, "points": points, "detail": detail, "strength": strength})

    urls = re.findall(r"(https?://[^\s]+|www\.[^\s]+|[a-z0-9-]+\.[a-z]{2,}(?:/[^\s]*)?)", low)

    # --- Link rules -------------------------------------------------------
    real_urls = [u for u in urls if "." in u]
    if real_urls:
        add(10, "Contains a link", "The message asks you to open a link: " + real_urls[0][:60], "warning")
        for u in real_urls:
            host = re.sub(r"^https?://", "", u).split("/")[0]
            if u.startswith("http://"):
                add(15, "Insecure http link", "Real banks and government sites use https, not http.", "warning")
            if any(s in host for s in SHORTENERS):
                add(25, "Shortened link", "Short links like bit.ly hide the real destination.", "strong")
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
                add(30, "Link uses an IP address", "A raw IP address instead of a real website name is a strong fraud sign.", "strong")
            if any(w in host for w in SUSPICIOUS_WORDS_IN_DOMAIN) and host not in OFFICIAL_HINTS:
                add(20, "Suspicious look-alike domain", "The domain '" + host + "' looks made to imitate an official site.", "strong")
            if "xn--" in host:
                add(20, "Punycode / look-alike domain", "This domain uses tricks to look like a known brand.", "strong")

    # --- Secret request ---------------------------------------------------
    if _hits(low, [r"\botp\b", r"\bpin\b", r"\bcvv\b", r"password", r"card number", r"share.*code", r"send.*otp"]):
        add(35, "Asks for OTP / PIN / secret", "No bank, delivery company or government office ever asks for your OTP, PIN, CVV or password.", "strong")

    # --- KYC / verification request --------------------------------------
    if _hits(low, [r"update.*kyc", r"kyc.*update", r"kyc", r"verify your (account|identity|aadhaar)", r"aadhaar.*update", r"pan.*update"]):
        add(20, "KYC / verification pressure", "Fake KYC-update messages are one of the most common bank frauds in India.", "warning")

    # --- Threat / account block -------------------------------------------
    if _hits(low, [r"will be blocked", r"will be suspended", r"account.*(blocked|suspended|closed|deactivated)",
                   r"connection will be cut", r"legal action", r"arrest", r"will be deactivated"]):
        add(20, "Threat / account-block language", "Scammers create fear so you act without thinking.", "warning")

    # --- Urgency ------------------------------------------------------------
    urgency = _hits(low, [r"\burgent\b", r"immediately", r"within \d+ hours", r"today itself",
                          r"last chance", r"expires? (today|soon)", r"act now", r"tonight"])
    if urgency:
        add(15, "Urgency pressure", "Words like '" + urgency[0] + "' push you to hurry. Genuine notices give you time.", "warning")

    # --- Money / lottery / prize -------------------------------------------
    if _hits(low, [r"lottery", r"you (have )?won", r"prize", r"cashback.*rs", r"refund.*rs",
                   r"rs\.?\s?\d+.*(prize|reward|bonus)", r"free money", r"lucky draw"]):
        add(20, "Lottery / prize / money claim", "Unexpected prize or lottery winnings are almost always fake.", "warning")

    # --- Payment / fee request ----------------------------------------------
    if _hits(low, [r"pay (rs|inr|₹)", r"pay.*fee", r"registration fee", r"pay.*charges",
                   r"pay.*cod", r"processing fee"]):
        add(15, "Asks you to pay a fee", "Paying a small 'fee' or 'charge' to unlock money, a parcel or a job is a classic scam step.", "warning")

    # --- Impersonation -------------------------------------------------------
    impersonation = _hits(low, [r"\bsbi\b", r"\bhdfc\b", r"\bicici\b", r"\brbi\b", r"reserve bank",
                                r"aadhaar", r"uidai", r"government of india", r"income tax department",
                                r"electricity board", r"customs department"])
    action_words = _hits(low, [r"click", r"update", r"verify", r"pay", r"share", r"call (this|on)"])
    if impersonation and (real_urls or action_words):
        add(15, "Impersonates a trusted organisation", "The message claims to be from '" + impersonation[0].upper() + "' but comes with a link or an action request — always check the official app/website yourself.", "warning")

    # --- Fake job / reward claim ----------------------------------------------
    if _hits(low, [r"work from home.*earn", r"earn rs", r"earn ₹", r"liking videos", r"part.?time job offer", r"daily income"]):
        add(15, "Unrealistic earning claim", "Easy-money job offers that ask for a fee first are fake.", "warning")

    # --- Click / call pressure with a link --------------------------------------
    if real_urls and _hits(low, [r"click (here|now|the link)", r"tap here"]):
        add(10, "'Click here' pressure", "The message pushes you to click instead of using the official app.", "warning")

    # --- Email sender check -----------------------------------------------------
    sender = (sender or "").strip().lower()
    if msg_type == "Email" and sender:
        domain_match = re.search(r"@([a-z0-9.-]+\.[a-z]{2,})", sender)
        if domain_match:
            domain = domain_match.group(1)
            claims_org = impersonation or _hits(low, [r"\bbank\b", r"government", r"income tax", r"aadhaar"])
            if domain in FREE_MAIL_DOMAINS and claims_org:
                add(25, "Sender address does not match the organisation",
                    "The email claims to be from a bank/government body but was sent from free mail (@" + domain + "). Real organisations never email from Gmail/Yahoo-type addresses.", "strong")
            elif any(w in domain for w in SUSPICIOUS_WORDS_IN_DOMAIN) and domain not in OFFICIAL_HINTS:
                add(15, "Suspicious sender domain", "The sender domain '" + domain + "' looks made to imitate an official site.", "warning")

    score = max(0, min(100, score))
    verdict, band = band_for(score)
    category = classify_category(low)

    advice = [
        "Do not click any link in this message.",
        "Never share OTP, PIN, CVV or passwords with anyone.",
        "Open your bank's official app or website yourself — do not use the link sent to you.",
    ]
    if score >= 25:
        advice.append("Block and report the sender on SMS / WhatsApp / your email app.")
        advice.append("If you already clicked or paid, call the national cyber helpline 1930 and report at cybercrime.gov.in immediately.")
    else:
        advice.append("Even for safe-looking messages, confirm important actions inside the official app.")
    if not reasons:
        reasons.append({"rule": "No major red flags found", "points": 0, "strength": "warning",
                        "detail": "No suspicious link, secret request, threat, urgency or prize claim was detected. Still stay alert — no checker is 100% perfect."})

    return {
        "score": score,
        "verdict": verdict,          # v2 four-band label
        "band": band,                # low | moderate | high | critical
        "category": category,
        "message_type": msg_type,
        "ml_scam_probability": ml_scam_probability(text),  # supporting ML signal
        "ml_model": CHAMPION.name,  # champion model chosen by F1 on the test split
        "reasons": reasons,
        "advice": advice,
    }


def scan_url(raw_url):
    """Phishing URL scanner. The URL is only parsed as text - NEVER opened/fetched."""
    url = raw_url.strip()
    reasons = []
    score = 0

    def add(points, rule, detail, strength):
        nonlocal score
        score += points
        reasons.append({"rule": rule, "points": points, "detail": detail, "strength": strength})

    has_scheme = "://" in url
    to_parse = url if has_scheme else "http://" + url
    parsed = urlparse(to_parse)
    host = (parsed.hostname or "").lower()
    full_low = url.lower()

    if not has_scheme:
        add(5, "No scheme (http/https) given", "The address was pasted without http:// or https://, which hides how it will open.", "warning")
    elif parsed.scheme == "http":
        add(15, "Uses http, not https", "Login, bank and payment pages must use https. An http page sends your details unprotected.", "warning")

    if "@" in url.split("://", 1)[-1].split("/")[0] or "@" in parsed.netloc:
        add(20, "'@' symbol in the address", "Everything before '@' is ignored by the browser — a classic trick to hide the real site.", "strong")

    is_ip_host = bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host))
    if is_ip_host:
        add(30, "IP address instead of a domain name", "Real companies use names like sbi.co.in, never a raw number address.", "strong")

    if any(host == s or host.endswith("." + s) for s in SHORTENERS):
        add(25, "URL shortening service", "Short links hide the real destination. Never log in or pay after opening one from a message.", "strong")

    if "xn--" in host:
        add(20, "Punycode domain", "Punycode (xn--) domains are often used to imitate famous brands with look-alike letters.", "strong")

    subdomains = host.split(".")[:-2] if (len(host.split(".")) > 2 and not is_ip_host) else []
    if len(subdomains) >= 2:
        add(15, "Many subdomains", "Long chains of subdomains are used to make a fake address look official.", "warning")
    brand_in_subdomain = [b for b in ["sbi", "hdfc", "icici", "paypal", "amazon", "aadhaar", "gov"] if subdomains and b in ".".join(subdomains)]
    if brand_in_subdomain and host not in OFFICIAL_HINTS:
        add(20, "Brand name hidden in subdomain", "A trusted name appears as a subdomain, but the real domain is something else.", "strong")

    if host.count("-") >= 3:
        add(10, "Hyphen-heavy domain", "Domains stuffed with hyphens (like secure-login-verify-update) are typical of throwaway phishing sites.", "warning")

    kw_hits = [w for w in URL_KEYWORDS if w in full_low]
    if kw_hits:
        add(15, "Suspicious keywords in URL", "The address contains words like '" + "', '".join(kw_hits[:3]) + "' that phishing pages use to look like login/verification pages.", "warning")

    if len(url) > 75:
        add(10, "Very long URL", "Unusually long addresses are used to hide the real destination.", "warning")

    if host in OFFICIAL_HINTS and parsed.scheme == "https" and score <= 15:
        reasons.append({"rule": "Known official domain over https", "points": 0, "strength": "warning",
                        "detail": "This is a recognised official domain using https. Still type addresses yourself instead of trusting links in messages."})

    score = max(0, min(100, score))
    verdict, band = band_for(score)
    if not reasons:
        reasons.append({"rule": "No major red flags found", "points": 0, "strength": "warning",
                        "detail": "No IP host, shortener, '@' trick, punycode or suspicious keyword was detected. Still open important sites by typing the address yourself."})

    advice = [
        "Never log in or pay on a page that arrived through a message link.",
        "Type the official address yourself (for example sbi.co.in) or use the official app.",
        "Check the exact spelling of the domain — one wrong letter means a fake site.",
    ]
    if score >= 50:
        advice.append("Close the page if it is open, and do not enter OTP, PIN or card details.")
        advice.append("If you entered any details, change your password and call your bank / 1930 immediately.")

    return {
        "score": score,
        "verdict": verdict,
        "band": band,
        "category": "Phishing URL",
        "url": url,
        "reasons": reasons,
        "advice": advice,
    }


# ---------------------------------------------------------------- stats
def compute_stats(data):
    history = data.get("history", [])
    high_risk_count = sum(1 for h in history if h.get("score", 0) >= 50)
    category_counts = {}
    for h in history:
        cat = h.get("category", "Other/Unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    for r in data.get("reports", []):
        cat = REPORT_CATEGORY_MAP.get(r.get("category", ""), r.get("category", "Other/Unknown"))
        category_counts[cat] = category_counts.get(cat, 0) + 1
    state_counts = {}
    for r in data.get("reports", []):
        st = r.get("state") or "Unknown"
        state_counts[st] = state_counts.get(st, 0) + 1
    stats = dict(data["stats"])
    stats["state_counts"] = dict(sorted(state_counts.items(), key=lambda kv: -kv[1]))
    stats["reports_count"] = len(data.get("reports", []))
    stats["high_risk_count"] = high_risk_count
    stats["fraud_found"] = sum(1 for h in history if h.get("score", 0) >= 75)  # critical = fraud
    stats["category_counts"] = dict(sorted(category_counts.items(), key=lambda kv: -kv[1]))
    return stats


def add_history(data, rec_type, preview, result):
    record = {
        "id": data["next_history_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": rec_type,
        "input_preview": preview[:120],
        "score": result["score"],
        "verdict": result["verdict"],
        "category": result.get("category", "Other/Unknown"),
    }
    data["next_history_id"] += 1
    data["history"].insert(0, record)
    return record


# ---------------------------------------------------------------- handler
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep console clean
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/reports":
            with _lock:
                data = load_data()
            return self._json(200, {"reports": data["reports"][:20]})
        if path == "/api/stats":
            with _lock:
                data = load_data()
            return self._json(200, compute_stats(data))
        if path == "/api/history":
            q = (parse_qs(parsed.query).get("q", [""])[0] or "").strip().lower()
            with _lock:
                data = load_data()
            history = data.get("history", [])
            if q:
                history = [h for h in history
                           if q in h.get("input_preview", "").lower()
                           or q in h.get("category", "").lower()
                           or q in h.get("verdict", "").lower()
                           or q in h.get("type", "").lower()]
            return self._json(200, {"history": history[:100]})
        if path == "/api/model-evaluation":
            return self._json(200, get_evaluation())
        if path == "/api/health":
            return self._json(200, {"status": "ok"})
        return self._static(path)

    def do_DELETE(self):
        path = urlparse(self.path).path
        m = re.match(r"^/api/history/(\d+)$", path)
        if not m:
            return self._json(404, {"error": "not found"})
        hid = int(m.group(1))
        with _lock:
            data = load_data()
            before = len(data.get("history", []))
            data["history"] = [h for h in data.get("history", []) if h.get("id") != hid]
            if len(data["history"]) == before:
                return self._json(404, {"error": "history record not found"})
            save_data(data)
        return self._json(200, {"ok": True, "deleted": hid})

    def _static(self, path):
        if path == "/":
            path = "/index.html"
        rel = path.lstrip("/")
        full = os.path.normpath(os.path.join(PUBLIC_DIR, rel))
        if not full.startswith(os.path.normpath(PUBLIC_DIR)) or not os.path.isfile(full):
            return self._json(404, {"error": "not found"})
        ctype = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                 ".js": "application/javascript; charset=utf-8"}.get(os.path.splitext(full)[1], "application/octet-stream")
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        payload = self._read_json()
        if path == "/api/analyze":
            message = str(payload.get("message", "")).strip()
            if len(message) < 5:
                return self._json(400, {"error": "Please paste a longer message to check."})
            msg_type = str(payload.get("type", payload.get("message_type", "SMS"))).strip()
            if msg_type not in ("SMS", "WhatsApp", "Email"):
                msg_type = "SMS"
            sender = str(payload.get("sender", "")).strip()
            result = analyze_message(message, msg_type, sender)
            with _lock:
                data = load_data()
                data["stats"]["total_checked"] += 1
                add_history(data, "email" if msg_type == "Email" else "message", message, result)
                save_data(data)
            return self._json(200, result)
        if path == "/api/scan-url":
            raw_url = str(payload.get("url", "")).strip()
            if len(raw_url) < 4 or "." not in raw_url:
                return self._json(400, {"error": "Please enter a valid-looking URL (it must contain a dot, e.g. example.com)."})
            result = scan_url(raw_url)
            with _lock:
                data = load_data()
                data["stats"]["total_checked"] += 1
                data["stats"]["urls_scanned"] += 1
                add_history(data, "url", raw_url, result)
                save_data(data)
            return self._json(200, result)
        if path == "/api/report":
            message = str(payload.get("message", "")).strip()
            category = str(payload.get("category", "Other Scam")).strip()[:60] or "Other Scam"
            state = str(payload.get("state", "Unknown")).strip()[:40] or "Unknown"
            contact = str(payload.get("contact", "")).strip()[:80]
            if len(message) < 5:
                return self._json(400, {"error": "Please paste the scam message you received."})
            with _lock:
                data = load_data()
                report = {
                    "id": data["next_id"],
                    "message": message[:500],
                    "category": category,
                    "state": state,
                    "contact": contact,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                data["next_id"] += 1
                data["reports"].insert(0, report)
                save_data(data)
            return self._json(201, {"ok": True, "report": report})
        return self._json(404, {"error": "not found"})


if __name__ == "__main__":
    load_data()  # create / seed data.json on first run
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"ScamShield AI is running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
