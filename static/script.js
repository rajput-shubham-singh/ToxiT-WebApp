/* =====================================================
   ToxiTrack AI v2 - Frontend
   ===================================================== */

// Demo comment sets
const DEMO_EN = [
  "Nice post bro, really helpful",
  "I kind of disagree with this take",
  "This is pretty stupid honestly",
  "You are an absolute idiot",
  "SHUT UP you worthless loser, I hate you!"
];

const DEMO_HI = [
  "bahut accha post hai bhai",
  "haan thoda confusing tha",
  "tu pagal hai kya",
  "kya bakwas hai chup reh",
  "tu chutiya hai, dimag kharab hai tera"
];

// Helpers
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const els = {
  textarea: $("#commentsInput"),
  count: $("#commentCount"),
  analyzeBtn: $("#analyzeBtn"),
  demoBtn: $("#demoBtn"),
  demoHiBtn: $("#demoHiBtn"),
  resetBtn: $("#resetBtn"),
  dashboard: $("#dashboard"),

  toxicityValue: $("#toxicityValue"),
  toxicityBar: $("#toxicityBar"),
  driftValue: $("#driftValue"),
  driftBar: $("#driftBar"),
  driftHint: $("#driftHint"),

  emotionChip: $("#emotionChip"),
  emotionHint: $("#emotionHint"),
  intentChip: $("#intentChip"),

  riskBadge: $("#riskBadge"),
  riskHint: $("#riskHint"),
  riskCard: $("#riskCard"),

  actionCard: $("#actionCard"),
  actionText: $("#actionText"),
  moderatorAlert: $("#moderatorAlert"),

  explainList: $("#explainList"),
  breakdownList: $("#breakdownList"),
  trendCanvas: $("#trendChart"),

  gaugeArc: $("#gaugeArc"),
  gaugeNeedle: $("#gaugeNeedle"),
  gaugeValue: $("#gaugeValue"),

  driftTypeText: $("#driftTypeText"),
  driftTimeline: $("#driftTimeline"),

  healthArc: $("#healthArc"),
  healthValue: $("#healthValue"),

  rewriteBody: $("#rewriteBody"),
  safeReplyText: $("#safeReplyText"),

  toast: $("#toast"),

  settingsToggle: $("#settingsToggle"),
  settingsPanel: $("#settingsPanel"),
  geminiToggle: $("#geminiToggle"),
  geminiText: $("#geminiText"),
  geminiHint: $("#geminiHint"),
  strictToggle: $("#strictToggle"),
  hindiSeg: $("#hindiSeg"),
  enginePill: $("#enginePill"),
  engineLabel: $("#engineLabel"),
};

let trendChart = null;
const settings = {
  use_gemini: false,
  strict: false,
  sensitivity: "medium",
};
const geminiReady = document.body.dataset.geminiReady === "true";

// ----- Helpers -----
function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("is-visible");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => els.toast.classList.remove("is-visible"), 2500);
}

function updateCount() {
  const lines = els.textarea.value.split("\n").filter((l) => l.trim().length > 0);
  els.count.textContent = `${lines.length} comment${lines.length === 1 ? "" : "s"}`;
}

function animateNumber(el, target) {
  const duration = 800;
  const start = performance.now();
  const from = parseInt(el.textContent, 10) || 0;
  function step(now) {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(from + (target - from) * eased);
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function scoreClass(score) {
  if (score >= 65) return "row__score--high";
  if (score >= 35) return "row__score--med";
  return "row__score--low";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ----- Settings ----- 
function syncGeminiUI() {
  if (!geminiReady) {
    els.geminiToggle.checked = false;
    els.geminiToggle.disabled = true;
    els.geminiText.textContent = "Gemini API (key required)";
    els.geminiHint.textContent = "Add GEMINI_API_KEY in Replit Secrets to enable.";
    els.enginePill.classList.remove("is-gemini");
    els.engineLabel.textContent = "Local AI Mode";
    return;
  }
  if (settings.use_gemini) {
    els.geminiText.textContent = "Gemini API (active)";
    els.geminiHint.textContent = "Gemini will analyze with multilingual context.";
    els.enginePill.classList.add("is-gemini");
    els.engineLabel.textContent = "Gemini Mode";
  } else {
    els.geminiText.textContent = "Use Gemini API";
    els.geminiHint.textContent = "Gemini key detected - toggle to enable.";
    els.enginePill.classList.remove("is-gemini");
    els.engineLabel.textContent = "Local AI Mode";
  }
}

els.settingsToggle.addEventListener("click", () => {
  const open = !els.settingsPanel.classList.contains("hidden");
  els.settingsPanel.classList.toggle("hidden", open);
  els.settingsToggle.setAttribute("aria-expanded", String(!open));
});

els.geminiToggle.addEventListener("change", (e) => {
  settings.use_gemini = e.target.checked;
  syncGeminiUI();
});

els.strictToggle.addEventListener("change", (e) => {
  settings.strict = e.target.checked;
});

els.hindiSeg.addEventListener("click", (e) => {
  const btn = e.target.closest(".seg__btn");
  if (!btn) return;
  $$(".seg__btn").forEach((b) => b.classList.remove("is-active"));
  btn.classList.add("is-active");
  settings.sensitivity = btn.dataset.value;
});

// ----- Rendering -----
function renderBreakdown(rows) {
  els.breakdownList.innerHTML = "";
  rows.forEach((item, i) => {
    const row = document.createElement("div");
    row.className = "row";
    row.style.animation = `rise 0.4s ease both`;
    row.style.animationDelay = `${i * 40}ms`;

    const tagsHtml = item.tags
      .map((t) => `<span class="tag tag--${t}">${t}</span>`).join("");

    row.innerHTML = `
      <div class="row__index">#${item.index}</div>
      <div class="row__main">
        <div class="row__text">${escapeHtml(item.comment)}</div>
        <div class="row__reason">${escapeHtml(item.reason || "")}</div>
      </div>
      <div class="row__emotion" data-emotion="${escapeHtml(item.emotion)}">${escapeHtml(item.emotion)}</div>
      <div class="row__tags">${tagsHtml}</div>
      <div class="row__score ${scoreClass(item.score)}">${item.score}</div>
    `;
    els.breakdownList.appendChild(row);
  });
}

function renderTrendChart(series) {
  const labels = series.map((_, i) => `#${i + 1}`);
  const ctx = els.trendCanvas.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 320);
  grad.addColorStop(0, "rgba(139, 92, 246, 0.55)");
  grad.addColorStop(1, "rgba(139, 92, 246, 0)");

  const data = {
    labels,
    datasets: [{
      label: "Toxicity",
      data: series,
      borderColor: "#8b5cf6",
      backgroundColor: grad,
      borderWidth: 3,
      fill: true,
      tension: 0.4,
      pointBackgroundColor: "#22d3ee",
      pointBorderColor: "#0b0c1a",
      pointBorderWidth: 2,
      pointRadius: 5,
      pointHoverRadius: 8,
    }],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 900, easing: "easeOutCubic" },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "rgba(11, 12, 26, 0.95)",
        titleColor: "#e7e9ff", bodyColor: "#9aa0c8",
        borderColor: "rgba(139, 92, 246, 0.4)", borderWidth: 1,
        padding: 12, cornerRadius: 8,
      },
    },
    scales: {
      x: { grid: { color: "rgba(139, 92, 246, 0.08)" },
           ticks: { color: "#6b7099", font: { family: "JetBrains Mono" } } },
      y: { beginAtZero: true, max: 100,
           grid: { color: "rgba(139, 92, 246, 0.08)" },
           ticks: { color: "#6b7099", font: { family: "JetBrains Mono" }, stepSize: 20 } },
    },
  };

  if (trendChart) {
    trendChart.data = data; trendChart.options = options; trendChart.update();
  } else {
    trendChart = new Chart(els.trendCanvas, { type: "line", data, options });
  }
}

function applyRiskStyling(level) {
  els.riskBadge.classList.remove("is-medium", "is-high");
  els.actionCard.classList.remove("is-medium", "is-high");
  els.moderatorAlert.classList.add("hidden");
  if (level === "MEDIUM") {
    els.riskBadge.classList.add("is-medium");
    els.actionCard.classList.add("is-medium");
  } else if (level === "HIGH") {
    els.riskBadge.classList.add("is-high");
    els.actionCard.classList.add("is-high");
    els.moderatorAlert.classList.remove("hidden");
  }
}

function updateGauge(value) {
  // Arc length = ~251.2 (half circle of r=80)
  const arcLen = 251.2;
  const offset = arcLen * (1 - Math.min(100, value) / 100);
  els.gaugeArc.style.strokeDashoffset = offset;
  // Needle: 0 -> -90deg, 100 -> +90deg
  const angle = -90 + (Math.min(100, value) / 100) * 180;
  els.gaugeNeedle.setAttribute("transform", `rotate(${angle} 100 110)`);
  animateNumber(els.gaugeValue, value);
}

function updateHealth(value) {
  const arcLen = 314.16;
  const offset = arcLen * (1 - Math.min(100, value) / 100);
  els.healthArc.style.strokeDashoffset = offset;
  animateNumber(els.healthValue, value);
}

function renderDriftDisplay(driftType, series) {
  els.driftTypeText.textContent = driftType;
  const cls = els.driftTypeText.classList;
  cls.remove("is-rapid", "is-slow", "is-recovery");
  if (driftType === "Rapid Escalation") cls.add("is-rapid");
  else if (driftType === "Slowly Negative") cls.add("is-slow");
  else if (driftType === "Recovery") cls.add("is-recovery");

  els.driftTimeline.innerHTML = "";
  series.forEach((s, i) => {
    const tick = document.createElement("div");
    tick.className = "drift-tick";
    const fill = document.createElement("div");
    fill.className = "drift-tick__fill";
    fill.style.height = "0%";
    tick.appendChild(fill);
    els.driftTimeline.appendChild(tick);
    setTimeout(() => { fill.style.height = `${s}%`; }, 60 + i * 60);
  });
}

function renderRewrite(comment, rewrite) {
  if (!comment || !rewrite) {
    els.rewriteBody.innerHTML = `<div class="suggest-empty">No toxic comment detected — nothing to rewrite.</div>`;
    return;
  }
  els.rewriteBody.innerHTML = `
    <div class="suggest-quote">${escapeHtml(comment)}</div>
    <div class="suggest-arrow">↓</div>
    <div class="suggest-result">${escapeHtml(rewrite)}</div>
  `;
}

function renderResult(result) {
  els.dashboard.classList.remove("hidden");

  // Engine pill
  if (result.engine === "Gemini") {
    els.enginePill.classList.add("is-gemini");
    els.engineLabel.textContent = "Gemini Mode";
  } else {
    els.enginePill.classList.remove("is-gemini");
    els.engineLabel.textContent = "Local AI Mode";
  }

  // Top metrics
  animateNumber(els.toxicityValue, result.toxicity_score);
  animateNumber(els.driftValue, result.drift_score);
  requestAnimationFrame(() => {
    els.toxicityBar.style.width = result.toxicity_score + "%";
    els.driftBar.style.width = result.drift_score + "%";
  });

  els.emotionChip.textContent = result.dominant_emotion;
  els.emotionChip.dataset.emotion = result.dominant_emotion;
  els.intentChip.textContent = result.dominant_intent;
  els.intentChip.dataset.intent = result.dominant_intent;
  els.emotionHint.textContent = `${result.engine} · ${result.confidence}% confidence`;
  els.driftHint.textContent = `Trend: ${result.trend_label}`;

  // Risk
  els.riskBadge.textContent = result.risk_level;
  applyRiskStyling(result.risk_level);
  els.riskHint.textContent = `Confidence ${result.confidence}%`;
  els.actionText.textContent = result.recommended_action;

  // Heat gauge + Drift display + Health ring
  updateGauge(result.toxicity_score);
  renderDriftDisplay(result.drift_type, result.trend_series);
  updateHealth(result.community_health);

  // Explanations
  els.explainList.innerHTML = "";
  result.explanations.forEach((line, i) => {
    const li = document.createElement("li");
    li.textContent = line;
    li.style.animation = `rise 0.4s ease both`;
    li.style.animationDelay = `${i * 60}ms`;
    els.explainList.appendChild(li);
  });

  // Rewrite + Safe reply
  renderRewrite(result.riskiest_comment, result.rewrite_suggestion);
  els.safeReplyText.textContent = result.safe_reply || "—";

  // Breakdown + chart
  renderBreakdown(result.breakdown);
  renderTrendChart(result.trend_series);

  // Smooth scroll
  setTimeout(() => {
    els.dashboard.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 80);
}

async function analyze() {
  const text = els.textarea.value.trim();
  if (!text) {
    showToast("Please enter at least one comment.");
    return;
  }
  els.analyzeBtn.classList.add("is-loading");
  try {
    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        comments: text,
        sensitivity: settings.sensitivity,
        strict: settings.strict,
        use_gemini: settings.use_gemini && geminiReady,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Something went wrong.");
      return;
    }
    renderResult(data);
  } catch (err) {
    showToast("Network error. Please try again.");
    console.error(err);
  } finally {
    els.analyzeBtn.classList.remove("is-loading");
  }
}

function loadDemoEN() {
  els.textarea.value = DEMO_EN.join("\n"); updateCount();
  showToast("English demo loaded.");
}
function loadDemoHI() {
  els.textarea.value = DEMO_HI.join("\n"); updateCount();
  showToast("Hinglish demo loaded.");
}
function reset() {
  els.textarea.value = ""; updateCount();
  els.dashboard.classList.add("hidden");
  if (trendChart) { trendChart.destroy(); trendChart = null; }
  showToast("Reset complete.");
  els.textarea.focus();
}

// Wire up events
els.textarea.addEventListener("input", updateCount);
els.analyzeBtn.addEventListener("click", analyze);
els.demoBtn.addEventListener("click", loadDemoEN);
els.demoHiBtn.addEventListener("click", loadDemoHI);
els.resetBtn.addEventListener("click", reset);
els.textarea.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault(); analyze();
  }
});

syncGeminiUI();
updateCount();
