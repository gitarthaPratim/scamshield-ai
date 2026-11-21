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
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, type: $("msgType").value, sender: $("senderInput").value.trim() })
    });
    const data = await res.json();
    if (!res.ok) { $("analyzeError").textContent = data.error || "Something went wrong."; return; }
    showResult(data);
    loadStats(); loadHistory();
  } catch (e) {
    $("analyzeError").textContent = "Could not reach the server. Is server.py running?";
  }
});

function showResult(data) {
  $("result").classList.remove("hidden");
  const bc = bandClass(data.score);
  const circle = $("scoreCircle"), verdict = $("verdictText");
  circle.className = "score-circle " + bc;
  verdict.className = "verdict " + bc;
  verdict.textContent = verdictIcon(data.score) + data.verdict;
  $("categoryChip").textContent = "Category: " + data.category;
  $("mlChip").textContent = "ML signal: " + data.ml_scam_probability + "% scam-like";
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
    const res = await fetch("/api/scan-url", {
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

/* ---------------- Report a Scam ---------------- */
$("reportForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("reportOk").textContent = ""; $("reportError").textContent = "";
  try {
    const res = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: $("reportMsg").value.trim(),
        category: $("reportCategory").value,
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
    const res = await fetch("/api/reports");
    const data = await res.json();
    if (!data.reports.length) { $("alertsList").innerHTML = '<p class="muted">No reports yet.</p>'; return; }
    $("alertsList").innerHTML = data.reports.map(r => {
      const when = r.timestamp ? new Date(r.timestamp).toLocaleString() : "";
      return `<div class="alert"><span class="cat">${esc(r.category)}</span>
        <div class="meta">${esc(r.contact || "Reported by a user")} · ${esc(when)}</div>
        <p>${esc(r.message)}</p></div>`;
    }).join("");
  } catch (e) { $("alertsList").innerHTML = '<p class="muted">Could not load alerts. Is server.py running?</p>'; }
}

/* ---------------- Dashboard / Stats ---------------- */
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const s = await res.json();
    $("statChecked").textContent = s.total_checked;
    $("statHigh").textContent = (s.high_risk_count != null ? s.high_risk_count : s.fraud_found);
    $("statUrls").textContent = s.urls_scanned;
    $("statReports").textContent = s.reports_count;
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
    const res = await fetch("/api/history" + (q ? "?q=" + encodeURIComponent(q) : ""));
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
    const res = await fetch("/api/history/" + id, { method: "DELETE" });
    if (!res.ok) { const d = await res.json(); alert(d.error || "Could not delete."); return; }
    loadHistory(); loadStats();
  } catch (e) { alert("Could not reach the server. Is server.py running?"); }
}

$("historySearchBtn").addEventListener("click", loadHistory);
$("historySearch").addEventListener("keydown", (e) => { if (e.key === "Enter") loadHistory(); });

$("exportBtn").addEventListener("click", async () => {
  try {
    const res = await fetch("/api/history");
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

loadAlerts();
loadStats();
loadHistory();
