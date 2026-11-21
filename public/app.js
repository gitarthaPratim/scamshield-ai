// ScamShield AI frontend — talks to the Python backend APIs (same origin).
const $ = (id) => document.getElementById(id);

const SAMPLE_SCAM = "URGENT! Dear Customer, your SBI account will be blocked today. Update your KYC immediately, click here http://bit.ly/sbi-kyc-verify and share the OTP sent to your mobile. You have also won a lottery prize of Rs. 500000. Pay Rs. 499 processing fee to claim it.";
const SAMPLE_SAFE = "Hi, your parcel from Amazon will be delivered tomorrow between 10 AM and 2 PM. Please keep your phone available so our delivery partner can reach you. Thank you for shopping with us.";
const SAMPLE_BAD_URL = "http://103.45.67.89/sbi-secure-login-verify";
const SAMPLE_GOOD_URL = "https://www.google.com";

function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }
function bandClass(score) { return score >= 75 ? "band-critical" : score >= 50 ? "band-high" : score >= 25 ? "band-moderate" : "band-low"; }
function verdictIcon(score) { return score >= 75 ? "🚨 " : score >= 50 ? "⛔ " : score >= 25 ? "⚠️ " : "✅ "; }

function animateScore(el, target) {
  let cur = 0;
  const step = Math.max(1, Math.round(target / 30));
  const timer = setInterval(() => {
    cur += step;
    if (cur >= target) { cur = target; clearInterval(timer); }
    el.textContent = cur;
  }, 25);
}

function reasonsHTML(reasons) {
  return reasons.map(r =>
    `<li><strong>${esc(r.rule)}</strong>${r.points ? `<span class="pts">+${r.points}</span>` : ""}` +
    `<span class="strength ${esc(r.strength || "warning")}">${r.strength === "strong" ? "Strong indicator" : "Warning"}</span>` +
    `<br><span class="muted">${esc(r.detail)}</span></li>`).join("");
}

/* ---------------- Safety Report (download / copy) ---------------- */
let lastMessageData = null, lastMessageContext = { message: "", type: "", sender: "" };
let lastUrlData = null;

function buildReport(kind, data, context) {
  const lines = [];
  lines.push("ScamShield AI - Safety Report");
  lines.push("=============================");
  lines.push("Generated: " + new Date().toLocaleString());
  lines.push("");
  if (kind === "message") {
    lines.push("Check type: Message (" + (context.type || "SMS") + ")");
    if (context.sender) lines.push("Sender: " + context.sender);
    lines.push("Message checked:");
    lines.push(context.message || "");
  } else {
    lines.push("Check type: Phishing URL scan (the URL was never opened)");
    lines.push("URL checked:");
    lines.push(data.url || "");
  }
  lines.push("");
  lines.push("RESULT: " + data.score + " / 100 - " + data.verdict);
  if (data.category) lines.push("Scam category: " + data.category);
  if (kind === "message" && data.ml_scam_probability != null)
    lines.push("ML signal (Naive Bayes): " + data.ml_scam_probability + "% scam-like");
  lines.push("");
  lines.push("Red flags found:");
  if (data.reasons && data.reasons.length) {
    data.reasons.forEach(r => lines.push("- " + r.rule + (r.points ? " (+" + r.points + " points, " + (r.strength === "strong" ? "strong indicator" : "warning") + ")" : "") + ": " + r.detail));
  } else {
    lines.push("- No strong red flags were detected in this check.");
  }
  lines.push("");
  lines.push("What you should do:");
  (data.advice || []).forEach(a => lines.push("- " + a));
  lines.push("");
  lines.push("Already clicked, paid or shared an OTP? Call 1930 (national cyber helpline)");
  lines.push("immediately and report at cybercrime.gov.in, then inform your bank.");
  lines.push("");
  lines.push("Note: ScamShield AI is a heuristic checker built for a hackathon. It explains");
  lines.push("its reasons, but no tool is 100% accurate - always verify through official");
  lines.push("apps, websites or phone numbers.");
  return lines.join("\n");
}

function downloadTextFile(filename, text) {
  const blob = new Blob([text], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function copyReportText(text) {
  try {
    await navigator.clipboard.writeText(text);
    alert("Report copied - paste it anywhere to share and warn others.");
  } catch (e) {
    alert("Copy was blocked by the browser. Use the Download button instead.");
  }
}

/* ---------------- Message Analyzer ---------------- */
$("sampleScamBtn").addEventListener("click", () => { $("msgInput").value = SAMPLE_SCAM; });
$("sampleSafeBtn").addEventListener("click", () => { $("msgInput").value = SAMPLE_SAFE; });
$("msgType").addEventListener("change", () => {
  $("senderWrap").classList.toggle("hidden", $("msgType").value !== "Email");
});

$("analyzeBtn").addEventListener("click", async () => {
  const message = $("msgInput").value.trim();
  $("analyzeError").textContent = "";
  if (message.length < 5) { $("analyzeError").textContent = "Please paste a message first."; return; }
  try {
    const res = await fetch("/svc/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, type: $("msgType").value, sender: $("senderInput").value.trim() })
    });
    const data = await res.json();
    if (!res.ok) { $("analyzeError").textContent = data.error || "Something went wrong."; return; }
    lastMessageContext = { message, type: $("msgType").value, sender: $("senderInput").value.trim() };
    showResult(data);
    loadStats(); loadHistory();
  } catch (e) {
    $("analyzeError").textContent = "Could not reach the server. Is server.py running?";
  }
});

function showResult(data) {
  lastMessageData = data;
  $("result").classList.remove("hidden");
  const bc = bandClass(data.score);
  const circle = $("scoreCircle"), verdict = $("verdictText");
  circle.className = "score-circle " + bc;
  verdict.className = "verdict " + bc;
  verdict.textContent = verdictIcon(data.score) + data.verdict;
  $("categoryChip").textContent = "Category: " + data.category;
  $("mlChip").textContent = "ML signal (" + (data.ml_model || "ML model") + "): " + data.ml_scam_probability + "% scam-like";
  animateScore($("scoreNum"), data.score);
  $("reasonsList").innerHTML = reasonsHTML(data.reasons);
  $("adviceList").innerHTML = data.advice.map(a => `<li>${esc(a)}</li>`).join("");
  $("result").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ---------------- URL Scanner ---------------- */
$("sampleBadUrlBtn").addEventListener("click", () => { $("urlInput").value = SAMPLE_BAD_URL; });
$("sampleGoodUrlBtn").addEventListener("click", () => { $("urlInput").value = SAMPLE_GOOD_URL; });

$("scanBtn").addEventListener("click", async () => {
  const url = $("urlInput").value.trim();
  $("urlError").textContent = "";
  if (!url) { $("urlError").textContent = "Please paste a URL first."; return; }
  try {
    const res = await fetch("/svc/scan-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await res.json();
    if (!res.ok) { $("urlError").textContent = data.error || "Something went wrong."; return; }
    showUrlResult(data);
    loadStats(); loadHistory();
  } catch (e) {
    $("urlError").textContent = "Could not reach the server. Is server.py running?";
  }
});

function showUrlResult(data) {
  lastUrlData = data;
  $("urlResult").classList.remove("hidden");
  const bc = bandClass(data.score);
  const circle = $("urlScoreCircle"), verdict = $("urlVerdictText");
  circle.className = "score-circle " + bc;
  verdict.className = "verdict " + bc;
  verdict.textContent = verdictIcon(data.score) + data.verdict;
  $("urlEcho").textContent = "Scanned address (never opened): " + data.url;
  animateScore($("urlScoreNum"), data.score);
  $("urlReasonsList").innerHTML = reasonsHTML(data.reasons);
  $("urlAdviceList").innerHTML = data.advice.map(a => `<li>${esc(a)}</li>`).join("");
  $("urlResult").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

$("downloadMsgReportBtn").addEventListener("click", () => {
  if (lastMessageData) downloadTextFile("scamshield-message-report.txt", buildReport("message", lastMessageData, lastMessageContext));
});
$("copyMsgReportBtn").addEventListener("click", () => {
  if (lastMessageData) copyReportText(buildReport("message", lastMessageData, lastMessageContext));
});
$("downloadUrlReportBtn").addEventListener("click", () => {
  if (lastUrlData) downloadTextFile("scamshield-url-report.txt", buildReport("url", lastUrlData, {}));
});
$("copyUrlReportBtn").addEventListener("click", () => {
  if (lastUrlData) copyReportText(buildReport("url", lastUrlData, {}));
});

/* ---------------- Report a Scam ---------------- */
$("reportForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("reportOk").textContent = ""; $("reportError").textContent = "";
  try {
    const res = await fetch("/svc/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: $("reportMsg").value.trim(),
        category: $("reportCategory").value,
        state: $("reportState").value,
        contact: $("reportContact").value.trim()
      })
    });
    const data = await res.json();
    if (!res.ok) { $("reportError").textContent = data.error || "Could not submit."; return; }
    $("reportOk").textContent = "Thank you! Your report is now live in Community Alerts.";
    $("reportForm").reset();
    loadAlerts(); loadStats();
  } catch (err) {
    $("reportError").textContent = "Could not reach the server. Is server.py running?";
  }
});

/* ---------------- Community Alerts ---------------- */
async function loadAlerts() {
  try {
    const res = await fetch("/svc/reports");
    const data = await res.json();
    if (!data.reports.length) { $("alertsList").innerHTML = '<p class="muted">No reports yet.</p>'; return; }
    $("alertsList").innerHTML = data.reports.map(r => {
      const when = r.timestamp ? new Date(r.timestamp).toLocaleString() : "";
      return `<div class="alert"><span class="cat">${esc(r.category)}</span>
        <div class="meta">${r.state ? "📍 " + esc(r.state) + " · " : ""}${esc(r.contact || "Reported by a user")} · ${esc(when)}</div>
        <p>${esc(r.message)}</p></div>`;
    }).join("");
  } catch (e) { $("alertsList").innerHTML = '<p class="muted">Could not load alerts. Is server.py running?</p>'; }
}

/* ---------------- Dashboard / Stats ---------------- */
async function loadStats() {
  try {
    const res = await fetch("/svc/stats");
    const s = await res.json();
    $("statChecked").textContent = s.total_checked;
    $("statHigh").textContent = (s.high_risk_count != null ? s.high_risk_count : s.fraud_found);
    $("statUrls").textContent = s.urls_scanned;
    $("statReports").textContent = s.reports_count;
    renderMap(s.state_counts || {});
    const counts = s.category_counts || {};
    const cats = Object.keys(counts);
    if (!cats.length) { $("catChart").innerHTML = '<p class="muted">No data yet — run a check or a scan.</p>'; return; }
    const max = Math.max(...cats.map(c => counts[c]));
    $("catChart").innerHTML = cats.map(c =>
      `<div class="bar-row"><span>${esc(c)}</span>
       <div class="bar-track"><div class="bar-fill" style="width:${Math.round(counts[c] / max * 100)}%"></div></div>
       <span class="bar-count">${counts[c]}</span></div>`).join("");
  } catch (e) { /* server not up yet */ }
}

/* ---------------- History ---------------- */
async function loadHistory() {
  const q = $("historySearch").value.trim();
  try {
    const res = await fetch("/svc/history" + (q ? "?q=" + encodeURIComponent(q) : ""));
    const data = await res.json();
    if (!data.history.length) { $("historyList").innerHTML = '<p class="muted">No history records found.</p>'; return; }
    $("historyList").innerHTML = data.history.map(h => {
      const when = h.timestamp ? new Date(h.timestamp).toLocaleString() : "";
      return `<div class="hitem">
        <span class="score-chip ${bandClass(h.score)}">${h.score}</span>
        <div class="main">
          <span class="type-chip">${esc(h.type)}</span> <strong>${esc(h.verdict)}</strong> · ${esc(h.category)}
          <div class="preview">${esc(h.input_preview)}</div>
          <div class="meta">${esc(when)}</div>
        </div>
        <button class="del" data-del="${h.id}">Delete</button>
      </div>`;
    }).join("");
    document.querySelectorAll("[data-del]").forEach(btn =>
      btn.addEventListener("click", () => deleteHistory(btn.getAttribute("data-del"))));
  } catch (e) { $("historyList").innerHTML = '<p class="muted">Could not load history. Is server.py running?</p>'; }
}

async function deleteHistory(id) {
  try {
    const res = await fetch("/svc/history/" + id, { method: "DELETE" });
    if (!res.ok) { const d = await res.json(); alert(d.error || "Could not delete."); return; }
    loadHistory(); loadStats();
  } catch (e) { alert("Could not reach the server. Is server.py running?"); }
}

$("historySearchBtn").addEventListener("click", loadHistory);
$("historySearch").addEventListener("keydown", (e) => { if (e.key === "Enter") loadHistory(); });

$("exportBtn").addEventListener("click", async () => {
  try {
    const res = await fetch("/svc/history");
    const data = await res.json();
    const rows = [["id", "timestamp", "type", "score", "verdict", "category", "input_preview"]];
    data.history.forEach(h => rows.push([h.id, h.timestamp, h.type, h.score, h.verdict, h.category, h.input_preview]));
    const csv = rows.map(r => r.map(v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "scamshield-history.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) { alert("Could not export. Is server.py running?"); }
});

/* ---------------- Screenshot-based Scam Detection (OCR) ---------------- */
$("shotInput").addEventListener("change", async () => {
  const file = $("shotInput").files[0];
  if (!file) return;
  const status = $("ocrStatus");
  if (typeof Tesseract === "undefined") {
    status.textContent = "OCR library could not load (it needs internet once). Please paste the message text manually instead.";
    return;
  }
  status.textContent = "Reading your screenshot… please wait a few seconds.";
  try {
    const { data } = await Tesseract.recognize(file, "eng");
    const text = (data.text || "").trim();
    if (text.length < 5) {
      status.textContent = "Could not read clear text from that image. Try a sharper screenshot, or paste the text manually.";
      return;
    }
    $("msgInput").value = text;
    status.textContent = "✅ Text extracted from your screenshot and filled in the box above. Now press “Check This Message”.";
  } catch (e) {
    status.textContent = "OCR failed on this image. Please paste the message text manually instead.";
  }
});

/* ---------------- AI Explanation Assistant ---------------- */
const SIMPLE_EXPLAIN = {
  "Banking/KYC Scam": {
    what: "This message is pretending to be from your bank.",
    trick: "It scares you (account will be blocked, KYC pending) and pushes you to click a link or share an OTP quickly, before you can think.",
    danger: "If you share the OTP or log in on their fake page, the scammer can empty your bank account within minutes.",
    safe: "Do nothing in the message. Open your bank's official app yourself, or visit the branch. A real bank never asks for OTP, PIN or KYC through a link."
  },
  "UPI/Payment Scam": {
    what: "This message is pretending you will RECEIVE money.",
    trick: "It asks you to approve a collect request or enter your UPI PIN to 'receive' a refund or cashback.",
    danger: "Entering your PIN always SENDS money. You would pay the scammer instead of receiving anything.",
    safe: "Remember one rule: receiving money never needs a PIN. Decline the request and check your balance only in your own UPI app."
  },
  "Delivery/Courier Scam": {
    what: "This message is pretending your parcel is stuck.",
    trick: "It asks for a small 'customs' or 'redelivery' payment on a link, so the amount feels too small to worry about.",
    danger: "The payment page steals your card details, and bigger amounts can be taken later.",
    safe: "Track parcels only on the courier's official website or app. Couriers never collect charges through random message links."
  },
  "Job Offer Scam": {
    what: "This message is pretending to offer an easy job.",
    trick: "It promises high daily income for simple tasks, then asks for a small registration or joining fee first.",
    danger: "After the fee, more fees are demanded ('unlock level', 'withdrawal charge') and the 'job' disappears with your money.",
    safe: "A real employer never charges money to hire you. Never pay any fee for a job offer received on WhatsApp or Telegram."
  },
  "Lottery/Prize Scam": {
    what: "This message is pretending you won something.",
    trick: "It announces a lottery, lucky draw or prize you never entered, then asks for a tax or processing fee to release it.",
    danger: "There is no prize. Only the fee is real, and paying once brings demands for more fees.",
    safe: "If you did not enter a draw, you cannot win it. Ignore the message and never pay to 'claim' a prize."
  },
  "Government Impersonation": {
    what: "This message is pretending to be from a government office.",
    trick: "It uses fear of Aadhaar deactivation, legal action or a fake refund/subsidy to make you share details or pay.",
    danger: "Your Aadhaar, bank details or money can be misused for fraud in your name.",
    safe: "Government departments never collect fees or OTPs through message links. Verify on the official .gov.in website or office."
  },
  "Phishing URL": {
    what: "This link is pretending to be a real website.",
    trick: "It copies a famous name using tricks — an IP address, a shortened link, extra words or a look-alike spelling — so you trust it.",
    danger: "The fake page records your password, card number or OTP and the scammer uses them immediately.",
    safe: "Never log in from a link in a message. Type the official address yourself (like sbi.co.in) or use the official app."
  },
  "default": {
    what: "This message or link is trying to make you act fast.",
    trick: "It uses urgency, fear or greed — the three levers almost every scam pulls.",
    danger: "Acting in a hurry can cost you money or your personal details.",
    safe: "Pause. Verify through the official app, website or phone number yourself, and never share OTP, PIN or passwords."
  }
};

function explainHTML(kind, data) {
  const t = SIMPLE_EXPLAIN[data.category] || SIMPLE_EXPLAIN["default"];
  const level = data.score >= 75 ? "This is VERY dangerous — do not touch it."
    : data.score >= 50 ? "This is dangerous — stay away from it."
    : data.score >= 25 ? "This looks suspicious — be careful."
    : "This looks mostly safe, but stay alert.";
  const topFlags = (data.reasons || []).filter(r => r.points > 0).slice(0, 3)
    .map(r => esc(r.rule)).join("; ");
  return `<h4>🤖 Simple explanation</h4>
    <p><strong>${level}</strong> (Risk score: ${data.score}/100)</p>
    <p><strong>What is this?</strong> ${t.what}</p>
    <p><strong>The trick:</strong> ${t.trick}</p>
    ${topFlags ? `<p><strong>Main warning signs we found:</strong> ${topFlags}.</p>` : ""}
    <p><strong>What can go wrong:</strong> ${t.danger}</p>
    <p><strong>What you should do:</strong> ${t.safe}</p>
    <p class="muted">Seedha matlab: ye aapko thagne ki koshish hai. Link par click mat karo, OTP mat do, aur paisa mat bhejo. Shak ho toh pehle 1930 par report karo.</p>`;
}

$("explainMsgBtn").addEventListener("click", () => {
  if (!lastMessageData) return;
  const box = $("explainBox");
  box.innerHTML = explainHTML("message", lastMessageData);
  box.classList.remove("hidden");
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
});
$("explainUrlBtn").addEventListener("click", () => {
  if (!lastUrlData) return;
  const box = $("urlExplainBox");
  box.innerHTML = explainHTML("url", lastUrlData);
  box.classList.remove("hidden");
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
});

/* ---------------- Scam Intelligence Map (tile map) ---------------- */
const TILE_STATES = [
  { n: "Jammu & Kashmir", r: 1, c: 2 }, { n: "Punjab", r: 2, c: 2 },
  { n: "Himachal Pradesh", r: 2, c: 3 }, { n: "Uttarakhand", r: 2, c: 4 },
  { n: "Rajasthan", r: 3, c: 2 }, { n: "Haryana", r: 3, c: 3 },
  { n: "Delhi", r: 3, c: 4 }, { n: "Uttar Pradesh", r: 3, c: 5 },
  { n: "Bihar", r: 3, c: 7 }, { n: "Sikkim", r: 2, c: 8 },
  { n: "Arunachal Pradesh", r: 2, c: 9 }, { n: "Assam", r: 3, c: 8 },
  { n: "Nagaland", r: 3, c: 9 }, { n: "West Bengal", r: 4, c: 7 },
  { n: "Jharkhand", r: 4, c: 6 }, { n: "Madhya Pradesh", r: 4, c: 4 },
  { n: "Meghalaya", r: 4, c: 8 }, { n: "Manipur", r: 4, c: 9 },
  { n: "Gujarat", r: 4, c: 2 }, { n: "Chhattisgarh", r: 5, c: 5 },
  { n: "Odisha", r: 5, c: 7 }, { n: "Tripura", r: 5, c: 8 },
  { n: "Mizoram", r: 5, c: 9 }, { n: "Maharashtra", r: 5, c: 3 },
  { n: "Karnataka", r: 6, c: 4 }, { n: "Telangana", r: 6, c: 5 },
  { n: "Andhra Pradesh", r: 6, c: 6 }, { n: "Goa", r: 6, c: 3 },
  { n: "Kerala", r: 7, c: 4 }, { n: "Tamil Nadu", r: 7, c: 5 }
];

function renderMap(stateCounts) {
  const map = $("tileMap");
  if (!map) return;
  const max = Math.max(1, ...Object.values(stateCounts));
  map.innerHTML = TILE_STATES.map(s => {
    const count = stateCounts[s.n] || 0;
    const ratio = count / max;
    const lvl = count === 0 ? "" : ratio > 0.66 ? "lvl4" : ratio > 0.4 ? "lvl3" : ratio > 0.2 ? "lvl2" : "lvl1";
    return `<div class="tile ${lvl}" style="grid-row:${s.r};grid-column:${s.c}" title="${esc(s.n)}: ${count} report(s)">
      <span>${esc(s.n)}</span><b>${count}</b></div>`;
  }).join("");
  const total = Object.values(stateCounts).reduce((a, b) => a + b, 0);
  const top = Object.keys(stateCounts).sort((a, b) => stateCounts[b] - stateCounts[a])[0];
  $("mapNote").textContent = total
    ? `Total reports mapped: ${total}. Most reports so far: ${top} (${stateCounts[top]}). Report a scam with your state to light up your tile.`
    : "No reports yet — be the first to report a scam.";
}

/* ---------------- ML Model Lab ---------------- */
async function loadEvaluation() {
  try {
    const res = await fetch("/svc/model-evaluation");
    const ev = await res.json();
    const d = ev.dataset;
    $("datasetInfo").innerHTML =
      `Dataset: <strong>${d.total_samples}</strong> labelled messages ` +
      `(${d.scam_samples} scam, ${d.safe_samples} safe) · Train: ${d.train_samples} · Test: ${d.test_samples} · ` +
      `Vocabulary: ${d.vocabulary_size} words · All 3 models trained in ${ev.training_time_seconds}s at server start.<br>` +
      `<span class="muted">${esc(d.source)}</span>`;
    const rows = ev.models.map(m =>
      `<tr><td>${esc(m.model)}${m.is_champion ? '<span class="badge">CHAMPION</span>' : ""}</td>` +
      `<td>${m.accuracy}%</td><td>${m.precision}%</td><td>${m.recall}%</td><td><strong>${m.f1_score}%</strong></td></tr>`).join("");
    $("modelTableWrap").innerHTML =
      `<table class="mtable"><tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1-score</th></tr>${rows}</table>`;
    const champ = ev.models.find(m => m.is_champion) || ev.models[0];
    const cm = champ.confusion_matrix;
    $("confMatrix").innerHTML =
      `<p class="muted">Champion: <strong>${esc(champ.model)}</strong> — how its ${d.test_samples} test predictions break down:</p>
       <div class="cm">
         <div class="head"></div><div class="head">Predicted SCAM</div><div class="head">Predicted SAFE</div>
         <div class="head">Actually SCAM</div><div><b>${cm.tp}</b>caught correctly (TP)</div><div><b>${cm.fn}</b>missed (FN)</div>
         <div class="head">Actually SAFE</div><div><b>${cm.fp}</b>false alarm (FP)</div><div><b>${cm.tn}</b>correctly cleared (TN)</div>
       </div>`;
    $("preprocessList").innerHTML = ev.preprocessing.map(s => `<li>${esc(s)}</li>`).join("");
    $("evalNote").textContent = ev.note;
  } catch (e) {
    $("datasetInfo").textContent = "Could not load evaluation. Is server.py running?";
  }
}

loadAlerts();
loadStats();
loadHistory();
loadEvaluation();
