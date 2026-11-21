"""
ScamShield - tiny Machine Learning signal (pure Python, standard library ONLY).

A Multinomial Naive Bayes text classifier implemented from scratch.
It is trained at startup on a small built-in labelled sample set
(no dataset file, no scikit-learn, no pip installs).

It returns a "scam probability" (0-100) used as a SUPPORTING signal.
The final ScamShield risk score stays rule-based (explainable) - see README.
"""
import math
import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# --------------------------------------------------------------------------
# Built-in training set: (message, label) - short samples written for this app.
# --------------------------------------------------------------------------
TRAINING_DATA = [
    # ---- scam samples ----
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
    # ---- safe samples ----
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


def _tokens(text):
    return _TOKEN_RE.findall(text.lower())


class NaiveBayesScamClassifier:
    """Multinomial Naive Bayes with Laplace (add-1) smoothing."""

    def __init__(self, training_data):
        self.doc_counts = {"scam": 0, "safe": 0}
        self.word_counts = {"scam": {}, "safe": {}}
        self.total_words = {"scam": 0, "safe": 0}
        vocab = set()
        for text, label in training_data:
            self.doc_counts[label] += 1
            for tok in _tokens(text):
                vocab.add(tok)
                self.word_counts[label][tok] = self.word_counts[label].get(tok, 0) + 1
                self.total_words[label] += 1
        self.vocab = vocab
        self.vocab_size = len(vocab)
        total_docs = sum(self.doc_counts.values())
        self.log_prior = {c: math.log(self.doc_counts[c] / total_docs) for c in self.doc_counts}

    def _log_likelihood(self, tokens, label):
        denom = self.total_words[label] + self.vocab_size
        counts = self.word_counts[label]
        return sum(math.log((counts.get(tok, 0) + 1) / denom) for tok in tokens)

    def scam_probability(self, text):
        """Return probability (0-100, rounded) that the text is a scam."""
        tokens = _tokens(text)
        if not tokens:
            return 0
        log_scam = self.log_prior["scam"] + self._log_likelihood(tokens, "scam")
        log_safe = self.log_prior["safe"] + self._log_likelihood(tokens, "safe")
        # Convert log-odds to a probability with a numerically stable sigmoid.
        diff = log_scam - log_safe
        if diff >= 0:
            prob = 1.0 / (1.0 + math.exp(-diff))
        else:
            e = math.exp(diff)
            prob = e / (1.0 + e)
        return round(prob * 100)


# Trained once at import / server startup.
MODEL = NaiveBayesScamClassifier(TRAINING_DATA)


def ml_scam_probability(text):
    return MODEL.scam_probability(text)
