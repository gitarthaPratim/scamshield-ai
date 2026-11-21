# ScamShield AI — Project Overview

**Domain:** Cybersecurity · **Event:** PromptWars Hackathon

## What it is
A full-stack web app that helps users identify fraudulent SMS, WhatsApp messages,
emails and phishing URLs that impersonate banks, delivery services and government
organisations — and explains the risk in simple language.

## How it works (one paragraph)
The user pastes a message or a URL into the single-page frontend. The Python
(standard-library only) backend scores it with weighted, explainable rules
(OTP requests, shortened/IP links, urgency, threats, look-alike domains, sender
mismatch, URL tricks) and, for messages, adds a supporting machine-learning
signal from a pure-Python ML engine: after NLP preprocessing (cleaning, URL/number
normalisation, tokenisation, stop-word removal, stemming), three from-scratch
classifiers — Naive Bayes, Logistic Regression and Random Forest — are trained on
a 480-sample labelled dataset and compared on a held-out test split with Accuracy,
Precision, Recall, F1 and Confusion Matrix (shown live in the ML Model Lab); the
best-F1 champion provides the signal. The app also offers screenshot-based
detection (browser OCR reads the message text from an image), an AI Explanation
Assistant that rewrites results in very simple language, downloadable safety
reports, and a Scam Intelligence Map built from the states in community reports.
The result is a 0–100 score in four bands — Low, Moderate,
High, Critical — with reasons labelled *strong indicator* or *warning*, a scam
category, and clear next steps. Every check is stored in a detection history,
community scam reports are persisted, and the dashboard shows only real data
recorded by the app itself.

## Key facts
- Zero installation beyond Python 3: no Flask, no scikit-learn, no CDN.
- Suspicious URLs are parsed as text only — never opened or fetched.
- Data persists in a local `data.json` (auto-seeded on first run).
- Whole repository is far below the 10 MB submission limit; single `main` branch.

## Future scope
QR-code URL extraction, training the same models on a large public spam dataset,
SQLite storage, and optional external URL-reputation APIs.
