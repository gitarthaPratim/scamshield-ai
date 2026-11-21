"""
ScamShield AI - Machine Learning engine (pure Python, standard library ONLY).

v4 upgrade:
  * NLP preprocessing pipeline (cleaning, URL/number normalisation,
    tokenisation, stop-word removal, light stemming).
  * A larger labelled dataset (~430 messages) generated at startup from
    labelled templates with slot variation, plus handwritten samples.
    No dataset file, no scikit-learn, no pip installs.
  * THREE classifiers are trained and compared on a held-out test split:
        - Multinomial Naive Bayes
        - Logistic Regression (gradient descent, from scratch)
        - Random Forest (decision-tree ensemble, from scratch)
  * Proper evaluation: Accuracy, Precision, Recall, F1-score and a
    Confusion Matrix per model (see get_evaluation()).
  * The best-F1 model ("champion") provides the ML scam probability used
    as a SUPPORTING signal in the app. The final ScamShield risk score
    stays rule-based and explainable - see README.
"""
import math
import random
import re
import time

# ==========================================================================
# 1. NLP PREPROCESSING
# ==========================================================================
_URL_RE = re.compile(r"(https?://\S+|www\.\S+|\b[a-z0-9-]+\.(com|in|ly|gl|cc|io|net|org|info|xyz|top|site|online)(/\S*)?)")
_NUM_RE = re.compile(r"\d+")
_TOKEN_RE = re.compile(r"[a-z]+")

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "will", "would", "can",
    "could", "should", "to", "of", "in", "on", "at", "for", "with", "by",
    "from", "and", "or", "but", "if", "then", "so", "as", "it", "its",
    "this", "that", "these", "those", "you", "your", "yours", "we", "our",
    "they", "them", "their", "he", "she", "his", "her", "i", "me", "my",
    "am", "be", "been", "have", "has", "had", "do", "does", "did", "not",
    "no", "yes", "please", "dear", "sir", "madam", "hi", "hello", "thanks",
    "thank", "regards", "team", "per", "via", "into", "over", "under",
}

PREPROCESSING_STEPS = [
    "Lowercasing and cleaning of raw text",
    "URL normalisation (every link replaced by a single LINK token)",
    "Number normalisation (amounts, OTPs, phone numbers replaced by a NUM token)",
    "Tokenisation (splitting into words)",
    "Stop-word removal (the, is, your, please, ...)",
    "Light stemming (blocked -> block, charges -> charg, sharing -> shar)",
]


def _stem(word):
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 4 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def preprocess(text):
    """Full NLP pipeline: raw message -> list of clean feature tokens."""
    t = (text or "").lower()
    t = _URL_RE.sub(" link ", t)
    t = _NUM_RE.sub(" num ", t)
    tokens = _TOKEN_RE.findall(t)
    return [_stem(tok) for tok in tokens if tok not in STOPWORDS and len(tok) > 1]


# ==========================================================================
# 2. LARGER LABELLED DATASET (generated from templates + handwritten)
# ==========================================================================
_BANKS = ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "PNB", "Kotak Bank"]
_LINKS = ["http://bit.ly/sbi-kyc-verify", "http://tinyurl.com/update-kyc-now",
          "http://103.45.67.89/secure-login", "www.hdfc-verify-kyc.xyz/login",
          "http://rb.gy/claim-prize", "http://cutt.ly/pay-fee-now"]
_AMOUNTS = ["499", "999", "1499", "2500", "5000", "25740", "50000", "500000"]
_FEES = ["99", "199", "299", "499", "999"]
_ITEMS = ["parcel", "package", "order", "courier packet"]
_COMPANIES = ["Amazon", "Flipkart", "Myntra", "Meesho"]

SCAM_TEMPLATES = [
    "Dear customer your {bank} account will be blocked today update KYC immediately click {link} and share the OTP sent to your mobile",
    "URGENT your {bank} account has been suspended verify your identity and password at {link} within {hrs} hours",
    "Congratulations you won a lottery prize of Rs {amt} pay a processing fee of Rs {fee} at {link} to claim your prize money",
    "You are the lucky draw winner claim Rs {amt} within 24 hours pay tax fee Rs {fee} on {link}",
    "Your {item} is held at customs pay COD charges of Rs {fee} on {link} to release the delivery today",
    "Delivery failed your {item} is waiting pay redelivery charges Rs {fee} at {link} or it will be returned",
    "Work from home earn Rs {amt} daily by liking videos registration fee only Rs {fee} join now on {link}",
    "Part time job offer easy daily income no experience needed pay joining fee Rs {fee} and start earning today",
    "Your Aadhaar will be deactivated update Aadhaar details immediately and pay Rs {fee} verification fee at {link}",
    "Government subsidy of Rs {amt} is approved for you share your Aadhaar and bank details at {link} to receive the money",
    "Income tax refund of Rs {amt} is pending share your bank account number and OTP at {link} to get the refund",
    "Electricity bill overdue your connection will be cut tonight pay Rs {amt} immediately at {link} and call this number",
    "Your SIM will be blocked today complete KYC verification now share the OTP sent to your phone",
    "You have received a UPI collect request approve it with your PIN to get cashback refund of Rs {amt}",
    "Refund initiated enter your UPI PIN at {link} to receive Rs {amt} in your account",
    "Your credit card will be blocked share the CVV and card number at {link} to reactivate it",
    "Free recharge offer click {link} and enter your mobile number and OTP to get Rs {amt} talktime free",
    "Investment offer double your money in 7 days guaranteed profit of Rs {amt} join our WhatsApp group now",
    "Loan of Rs {amt} approved instantly without documents pay processing fee Rs {fee} first at {link}",
    "Your {bank} account will be closed and legal action will be taken call this number immediately to stop it",
    "Claim your free gift voucher of Rs {amt} click {link} and enter your card details and CVV",
    "Your WhatsApp account will be deactivated verify now share the 6 digit code sent to you",
    "KYC pending your wallet account will be frozen update KYC on {link} right now to avoid block",
    "Bank alert unusual login detected verify your password immediately at {link} secure your account",
    "Pay Rs {fee} courier charges to receive your prize parcel of Rs {amt} claim at {link} today",
    "Selected for a government job pay application fee Rs {fee} at {link} last date today hurry",
    "Your pension amount of Rs {amt} is stuck complete verification share OTP and Aadhaar at {link}",
    "Crypto investment plan earn Rs {amt} every week guaranteed returns deposit Rs {fee} to start",
    "Your {bank} debit card has expired renew it at {link} and share the OTP to activate the new card",
    "Police notice a case is registered against your Aadhaar pay Rs {fee} fine at {link} to avoid arrest",
    "Customs department your foreign parcel needs clearance fee Rs {fee} pay at {link} within {hrs} hours",
    "Share market tip guaranteed profit invest Rs {amt} today and get double returns in one week join {link}",
    "Your mobile number won Rs {amt} in a lucky draw pay Rs {fee} charges at {link} to claim the amount",
    "Account verification required your {bank} net banking will be locked login at {link} with password",
]

SAFE_TEMPLATES = [
    "Your {item} from {company} will be delivered tomorrow between 10 AM and 2 PM please keep your phone available",
    "Dear customer Rs {amt} was debited from your {bank} account for a purchase your available balance is Rs {amt}",
    "Rs {amt} has been credited to your {bank} account as salary for this month view details in the official app",
    "Your OTP for login is a secret code never share this code with anyone not even bank staff",
    "Your appointment is confirmed for Monday at 11 AM please arrive 10 minutes early with your reports",
    "Your electricity bill for this month is Rs {amt} due date is the 15th pay safely via the official app",
    "Your train ticket is confirmed and the train departs at 6 PM from platform 3 have a safe journey",
    "Your {item} has been delivered successfully thank you for shopping with {company} rate your experience in the app",
    "Reminder your mobile recharge plan expires in 3 days recharge anytime from the official app",
    "Your monthly bank statement is ready download it securely from the official {bank} mobile app",
    "The meeting is rescheduled to 3 PM tomorrow in conference room B please update your calendar",
    "Your order has been shipped and will arrive by Friday track it inside the orders section of the app",
    "School will remain closed tomorrow due to heavy rain classes will resume on Monday as usual",
    "Your exam admit card is available on the university portal login with your roll number to download",
    "Water supply will be unavailable on Sunday from 9 AM to 12 PM due to maintenance work in your area",
    "Your flight booking is confirmed departure at 8 30 AM please reach the airport 2 hours early",
    "Rs {amt} cashback has been credited to your wallet for your last order thank you for shopping",
    "Your subscription renews next week you can manage or cancel it anytime in the settings",
    "Your report card is ready please collect it from the school office on Saturday morning",
    "Dear customer your fixed deposit matures next month visit your {bank} branch for renewal options",
    "The library book you issued is due next Tuesday please return or renew it on time",
    "Your parcel is out for delivery today our delivery partner will call you before reaching your address",
    "Payment of Rs {amt} to {company} was successful your transaction receipt is available in the app",
    "Your {bank} credit card statement is generated total due Rs {amt} pay before the due date to avoid charges",
    "Reminder your vehicle insurance expires next month renew it at any branch or on the official website",
    "Your leave application for next week has been approved by your manager enjoy your break",
    "The blood donation camp will be held on Sunday at the community hall all are welcome to join",
    "Your gym membership renewal is due this week pay at the front desk during your next visit",
    "Class test for mathematics is postponed to next Wednesday study well and best of luck",
    "Your hotel booking is confirmed check in after 12 PM and carry a valid ID card for verification at the desk",
]

HANDWRITTEN = [
    ("Dear customer your SBI account will be blocked today update KYC immediately click link share OTP", "scam"),
    ("Congratulations you won lottery prize Rs 500000 pay processing fee to claim", "scam"),
    ("Your parcel is held at customs pay COD charges Rs 499 on this link to release delivery", "scam"),
    ("Work from home earn Rs 3000 daily liking videos registration fee Rs 999 join now", "scam"),
    ("Aadhaar will be deactivated update Aadhaar details immediately pay verification fee", "scam"),
    ("Electricity bill overdue connection will be cut tonight pay immediately call this number", "scam"),
    ("URGENT your bank account has been suspended verify your identity and password here", "scam"),
    ("You have received a UPI collect request approve with your PIN to get cashback refund", "scam"),
    ("Income tax refund of Rs 25740 is pending share your bank account number and OTP", "scam"),
    ("Your credit card will be blocked share CVV and card number to reactivate", "scam"),
    ("Free recharge offer click this link and enter your mobile number and OTP", "scam"),
    ("Part time job offer easy money daily income no experience join on telegram registration fee", "scam"),
    ("KYC pending your Paytm account will be frozen update KYC on this link now", "scam"),
    ("You are selected lucky draw winner claim prize money within 24 hours pay tax fee", "scam"),
    ("Delivery failed your package is waiting pay redelivery charges on this link", "scam"),
    ("Bank alert unusual login verify password immediately secure login update", "scam"),
    ("Government subsidy of Rs 10000 approved share Aadhaar and bank details to receive", "scam"),
    ("Your SIM will be blocked today complete KYC verification share OTP", "scam"),
    ("Refund initiated enter UPI PIN to receive money in your account", "scam"),
    ("Investment offer double your money in 7 days guaranteed profit join WhatsApp group", "scam"),
    ("Loan approved instantly no documents pay processing fee first", "scam"),
    ("Your account will be closed legal action will be taken call this number immediately", "scam"),
    ("Claim your free gift voucher click link enter card details and CVV", "scam"),
    ("WhatsApp will be deactivated verify your account share the 6 digit code sent to you", "scam"),
    ("Your parcel will be delivered tomorrow between 10 AM and 2 PM please keep your phone available", "safe"),
    ("Dear customer Rs 500 debited from your account for purchase at store your balance is Rs 12450", "safe"),
    ("Your OTP for login is 483920 do not share this code with anyone team", "safe"),
    ("Your appointment with Dr Sharma is confirmed for Monday 11 AM please arrive 10 minutes early", "safe"),
    ("Your electricity bill for this month is Rs 860 due date is 15th pay via the official app", "safe"),
    ("Your train ticket is confirmed PNR 8527413690 train departs at 6 PM from platform 3", "safe"),
    ("Salary of Rs 45000 has been credited to your account for this month", "safe"),
    ("Your package has been delivered thank you for shopping with us rate your experience", "safe"),
    ("Reminder your mobile recharge plan expires in 3 days recharge from the official app", "safe"),
    ("Your bank statement for last month is ready download it from the official mobile app", "safe"),
    ("Meeting rescheduled to 3 PM tomorrow in conference room B please update your calendar", "safe"),
    ("Your order has been shipped and will arrive by Friday track it in the orders section of the app", "safe"),
    ("Happy birthday we wish you a wonderful year ahead from all of us at the office", "safe"),
    ("Your exam admit card is available on the university portal login with your roll number", "safe"),
    ("Water supply will be unavailable on Sunday from 9 AM to 12 PM due to maintenance", "safe"),
    ("Your flight booking is confirmed departure at 8 30 AM please reach the airport 2 hours early", "safe"),
    ("Rs 200 cashback has been credited to your wallet for your last order thank you", "safe"),
    ("Your subscription renews next week manage it anytime in settings", "safe"),
    ("School will remain closed tomorrow due to heavy rain classes resume on Monday", "safe"),
    ("Your report card is ready please collect it from the school office on Saturday", "safe"),
    ("Dear customer your fixed deposit matures next month visit your branch for renewal options", "safe"),
    ("The library book you issued is due next Tuesday please return or renew it in time", "safe"),
]


SCAM_EXTRAS = ["", " Hurry up.", " Do not ignore this message.",
               " Act now to avoid problems.", " This is your final notice.",
               " Offer valid only for today."]
SAFE_EXTRAS = ["", " Thank you.", " Have a nice day.",
               " For help, visit the nearest branch or the official app.",
               " Ignore this message if already done.", " Stay safe."]

# Deliberately hard / borderline samples, so evaluation stays realistic:
# safe messages that contain scary words, and scams that use no link at all.
HARD_SAMPLES = [
    ("Call our bank officer on this number to unblock your account and share the code received on your phone", "scam"),
    ("Madam your account shows a suspicious transaction tell the OTP to our officer quickly to cancel it", "scam"),
    ("You won a gift in our store draw call back today and pay a small courier charge to receive it", "scam"),
    ("Your electricity bill is due tomorrow pay via the official app only to avoid a late fee", "safe"),
    ("Verify your email address by opening the official app settings we never ask for your password", "safe"),
    ("Your account password was changed if this was not you call the bank helpline printed on your card", "safe"),
    ("Urgent weather warning heavy rain is expected today please stay indoors and stay safe", "safe"),
    ("Your prize for the office quiz is ready collect it from the HR desk with your employee ID card", "safe"),
    ("Please pay the school fees at the office counter before Friday to avoid a late fine", "safe"),
    ("Your account will be charged a small annual fee this month as per the schedule shared by email", "safe"),
]


def _generate_dataset():
    rng = random.Random(20261121)
    samples = []

    def fill(tpl, extras):
        return tpl.format(
            bank=rng.choice(_BANKS), link=rng.choice(_LINKS),
            amt=rng.choice(_AMOUNTS), fee=rng.choice(_FEES),
            item=rng.choice(_ITEMS), company=rng.choice(_COMPANIES),
            hrs=rng.choice(["2", "4", "12", "24"]),
        ) + rng.choice(extras)

    for tpl in SCAM_TEMPLATES:
        for _ in range(8):
            samples.append((fill(tpl, SCAM_EXTRAS), "scam"))
    for tpl in SAFE_TEMPLATES:
        for _ in range(8):
            samples.append((fill(tpl, SAFE_EXTRAS), "safe"))
    samples.extend(HANDWRITTEN)
    samples.extend(HARD_SAMPLES)
    # De-duplicate (same text+label), keep order stable.
    seen, unique = set(), []
    for text, label in samples:
        key = (text, label)
        if key not in seen:
            seen.add(key)
            unique.append((text, label))
    return unique


ALL_DATA = _generate_dataset()


def _split(data, seed=7, test_ratio=0.2):
    rng = random.Random(seed)
    scam = [d for d in data if d[1] == "scam"]
    safe = [d for d in data if d[1] == "safe"]
    rng.shuffle(scam)
    rng.shuffle(safe)
    n_scam = max(1, int(len(scam) * test_ratio))
    n_safe = max(1, int(len(safe) * test_ratio))
    test = scam[:n_scam] + safe[:n_safe]
    train = scam[n_scam:] + safe[n_safe:]
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


TRAIN_DATA, TEST_DATA = _split(ALL_DATA)

# Shared vocabulary from the training split (top words by frequency).
def _build_vocab(train, max_features=400):
    freq = {}
    for text, _ in train:
        for tok in set(preprocess(text)):
            freq[tok] = freq.get(tok, 0) + 1
    words = sorted(freq.items(), key=lambda kv: -kv[1])
    return [w for w, _ in words[:max_features]]


VOCAB = _build_vocab(TRAIN_DATA)
VOCAB_SET = set(VOCAB)


def _features(text):
    toks = preprocess(text)
    return toks, (set(toks) & VOCAB_SET)


# ==========================================================================
# 3. MODEL 1 - MULTINOMIAL NAIVE BAYES
# ==========================================================================
class NaiveBayes:
    name = "Naive Bayes"

    def __init__(self, train):
        self.doc_counts = {"scam": 0, "safe": 0}
        self.word_counts = {"scam": {}, "safe": {}}
        self.total_words = {"scam": 0, "safe": 0}
        vocab = set()
        for text, label in train:
            self.doc_counts[label] += 1
            for tok in preprocess(text):
                vocab.add(tok)
                self.word_counts[label][tok] = self.word_counts[label].get(tok, 0) + 1
                self.total_words[label] += 1
        self.vocab_size = len(vocab)
        total = sum(self.doc_counts.values())
        self.log_prior = {c: math.log(self.doc_counts[c] / total) for c in self.doc_counts}

    def predict_proba(self, text):
        toks, _ = _features(text)
        if not toks:
            return 0.0
        out = {}
        for label in ("scam", "safe"):
            denom = self.total_words[label] + self.vocab_size
            counts = self.word_counts[label]
            out[label] = self.log_prior[label] + sum(
                math.log((counts.get(t, 0) + 1) / denom) for t in toks)
        diff = out["scam"] - out["safe"]
        if diff >= 0:
            return 1.0 / (1.0 + math.exp(-diff))
        e = math.exp(diff)
        return e / (1.0 + e)


# ==========================================================================
# 4. MODEL 2 - LOGISTIC REGRESSION (gradient descent, from scratch)
# ==========================================================================
class LogisticRegression:
    name = "Logistic Regression"

    def __init__(self, train, epochs=220, lr=0.5, l2=0.01):
        self.w = {word: 0.0 for word in VOCAB}
        self.b = 0.0
        rng = random.Random(99)
        data = [(set(preprocess(t)) & VOCAB_SET, 1 if lab == "scam" else 0)
                for t, lab in train]
        for _ in range(epochs):
            rng.shuffle(data)
            for feats, y in data:
                z = self.b + sum(self.w[f] for f in feats)
                p = 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))
                grad = p - y
                for f in feats:
                    self.w[f] -= lr * (grad + l2 * self.w[f])
                self.b -= lr * grad

    def predict_proba(self, text):
        _, feats = _features(text)
        z = self.b + sum(self.w[f] for f in feats)
        if z >= 0:
            return 1.0 / (1.0 + math.exp(-z))
        e = math.exp(z)
        return e / (1.0 + e)


# ==========================================================================
# 5. MODEL 3 - RANDOM FOREST (decision-tree ensemble, from scratch)
# ==========================================================================
def _gini(n_scam, n_total):
    if n_total == 0:
        return 0.0
    p = n_scam / n_total
    return 1.0 - p * p - (1 - p) * (1 - p)


class _Tree:
    def __init__(self, max_depth=7, min_samples=5, n_candidates=26, rng=None):
        self.max_depth = max_depth
        self.min_samples = min_samples
        self.n_candidates = n_candidates
        self.rng = rng or random.Random(0)
        self.root = None

    def fit(self, samples):  # samples: list of (feature_set, y)
        self.root = self._build(samples, 0)
        return self

    def _build(self, samples, depth):
        n = len(samples)
        n_scam = sum(y for _, y in samples)
        prob = n_scam / n if n else 0.0
        if n_scam == 0 or n_scam == n or depth >= self.max_depth or n < self.min_samples:
            return {"prob": prob}
        base = _gini(n_scam, n)
        best_gain, best_feat = 0.001, None
        candidates = self.rng.sample(VOCAB, min(self.n_candidates, len(VOCAB)))
        for feat in candidates:
            left_scam = left_n = 0
            for feats, y in samples:
                if feat in feats:
                    left_n += 1
                    left_scam += y
            if left_n == 0 or left_n == n:
                continue
            right_n = n - left_n
            right_scam = n_scam - left_scam
            gain = base - (left_n / n) * _gini(left_scam, left_n) \
                        - (right_n / n) * _gini(right_scam, right_n)
            if gain > best_gain:
                best_gain, best_feat = gain, feat
        if best_feat is None:
            return {"prob": prob}
        left = [s for s in samples if best_feat in s[0]]
        right = [s for s in samples if best_feat not in s[0]]
        return {"feature": best_feat,
                "left": self._build(left, depth + 1),
                "right": self._build(right, depth + 1)}

    def predict_proba(self, feats):
        node = self.root
        while "feature" in node:
            node = node["left"] if node["feature"] in feats else node["right"]
        return node["prob"]


class RandomForest:
    name = "Random Forest"

    def __init__(self, train, n_trees=21):
        data = [(set(preprocess(t)) & VOCAB_SET, 1 if lab == "scam" else 0)
                for t, lab in train]
        rng = random.Random(123)
        self.trees = []
        n = len(data)
        for i in range(n_trees):
            bootstrap = [data[rng.randrange(n)] for _ in range(n)]
            tree = _Tree(rng=random.Random(1000 + i)).fit(bootstrap)
            self.trees.append(tree)

    def predict_proba(self, text):
        _, feats = _features(text)
        return sum(t.predict_proba(feats) for t in self.trees) / len(self.trees)


# ==========================================================================
# 6. TRAIN ALL MODELS + PROPER EVALUATION ON THE HELD-OUT TEST SPLIT
# ==========================================================================
def _metrics(model, test):
    tp = tn = fp = fn = 0
    for text, label in test:
        pred_scam = model.predict_proba(text) >= 0.5
        if label == "scam" and pred_scam:
            tp += 1
        elif label == "scam":
            fn += 1
        elif pred_scam:
            fp += 1
        else:
            tn += 1
    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "model": model.name,
        "accuracy": round(accuracy * 100, 1),
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "f1_score": round(f1 * 100, 1),
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


_t0 = time.time()
MODELS = [NaiveBayes(TRAIN_DATA), LogisticRegression(TRAIN_DATA), RandomForest(TRAIN_DATA)]
_EVAL_ROWS = [_metrics(m, TEST_DATA) for m in MODELS]
_CHAMPION_IDX = max(range(len(MODELS)),
                    key=lambda i: (_EVAL_ROWS[i]["f1_score"], _EVAL_ROWS[i]["accuracy"]))
CHAMPION = MODELS[_CHAMPION_IDX]
for row in _EVAL_ROWS:
    row["is_champion"] = row["model"] == CHAMPION.name
_TRAIN_SECONDS = round(time.time() - _t0, 2)

EVALUATION = {
    "dataset": {
        "total_samples": len(ALL_DATA),
        "train_samples": len(TRAIN_DATA),
        "test_samples": len(TEST_DATA),
        "scam_samples": sum(1 for _, l in ALL_DATA if l == "scam"),
        "safe_samples": sum(1 for _, l in ALL_DATA if l == "safe"),
        "vocabulary_size": len(VOCAB),
        "source": "Labelled samples generated at startup from scam/safe message "
                  "templates with slot variation, plus handwritten samples. "
                  "No external dataset file is used.",
    },
    "preprocessing": PREPROCESSING_STEPS,
    "models": _EVAL_ROWS,
    "champion_model": CHAMPION.name,
    "note": "Metrics are computed on a held-out 20% test split that the models "
            "never trained on. The champion model (best F1-score) provides the "
            "ML signal in the app; the final risk score remains rule-based.",
    "training_time_seconds": _TRAIN_SECONDS,
}


def ml_scam_probability(text):
    """Scam probability (0-100) from the champion model."""
    return round(CHAMPION.predict_proba(text) * 100)


def get_evaluation():
    return EVALUATION
