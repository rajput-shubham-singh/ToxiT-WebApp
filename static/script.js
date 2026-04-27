/* =====================================================
   ToxiTrack AI v3 - Frontend
   ===================================================== */

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

const DEMO_CHAT_SAFE = [
  { user: "User1", text: "hello bhai" },
  { user: "User2", text: "hi, kaisa hai" },
  { user: "User1", text: "sab badhiya, tu bata" },
  { user: "User2", text: "haan mast, thanks" },
];
const DEMO_CHAT_MED = [
  { user: "User1", text: "tu pagal hai kya" },
  { user: "User2", text: "chup reh yaar" },
  { user: "User1", text: "kya bakwas kar raha hai" },
  { user: "User2", text: "bewakoof banda" },
];
const DEMO_CHAT_HIGH = [
  { user: "User1", text: "bc tu chutiya hai" },
  { user: "User2", text: "aa mil bahar dekh lunga tujhe" },
  { user: "User1", text: "teri watt laga dunga" },
  { user: "User2", text: "tod dunga tujhe" },
  { user: "User1", text: "sorry bhai gussa tha" },
];

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const els = {
  // Tabs
  tabs: $$(".tab"),
  panels: { single: $("#panel-single"), chat: $("#panel-chat") },
  // Single
  textarea: $("#commentsInput"),
  count: $("#commentCount"),
  analyzeBtn: $("#analyzeBtn"),
  demoBtn: $("#demoBtn"),
  demoHiBtn: $("#demoHiBtn"),
  resetBtn: $("#resetBtn"),
  // Chat
  chatBuilder: $("#chatBuilder"),
  addMsgBtn: $("#addMsgBtn"),
  chatCount: $("#chatCount"),
  analyzeChatBtn: $("#analyzeChatBtn"),
  chatDemoSafe: $("#chatDemoSafe"),
  chatDemoMed: $("#chatDemoMed"),
  chatDemoHigh: $("#chatDemoHigh"),
  chatResetBtn: $("#chatResetBtn"),
  // Dashboard
  dashboard: $("#dashboard"),
  toxicityValue: $("#toxicityValue"), toxicityBar: $("#toxicityBar"),
  aggressionValue: $("#aggressionValue"), aggressionBar: $("#aggressionBar"),
  driftValue: $("#driftValue"), driftBar: $("#driftBar"), driftHint: $("#driftHint"),
  escalationValue: $("#escalationValue"), escalationBar: $("#escalationBar"),
  riskBadge: $("#riskBadge"), riskHint: $("#riskHint"), riskCard: $("#riskCard"),
  emotionChip: $("#emotionChip"), emotionHint: $("#emotionHint"),
  intentChip: $("#intentChip"),
  threatBadge: $("#threatBadge"), threatHint: $("#threatHint"),
  engineChip: $("#engineChip"), engineSubHint: $("#engineSubHint"),
  actionCard: $("#actionCard"), actionText: $("#actionText"),
  moderatorAlert: $("#moderatorAlert"),
  explainList: $("#explainList"),
  breakdownList: $("#breakdownList"),
  trendCanvas: $("#trendChart"),
  gaugeArc: $("#gaugeArc"), gaugeNeedle: $("#gaugeNeedle"), gaugeValue: $("#gaugeValue"),
  driftTypeText: $("#driftTypeText"), driftTimeline: $("#driftTimeline"),
  healthArc: $("#healthArc"), healthValue: $("#healthValue"),
  rewriteBody: $("#rewriteBody"), safeReplyText: $("#safeReplyText"),
  // Chat-only
  chatOnlySection: $("#chatOnlySection"),
  aggressorAvatar: $("#aggressorAvatar"), aggressorName: $("#aggressorName"),
  victimPressureVal: $("#victimPressureVal"), mutualToxVal: $("#mutualToxVal"),
  patternList: $("#patternList"),
  usersGrid: $("#usersGrid"),
  chatReplay: $("#chatReplay"),
  // Misc
  toast: $("#toast"),
  exportBtn: $("#exportBtn"),
  settingsToggle: $("#settingsToggle"), settingsPanel: $("#settingsPanel"),
  geminiToggle: $("#geminiToggle"), geminiText: $("#geminiText"), geminiHint: $("#geminiHint"),
  strictToggle: $("#strictToggle"), hindiSeg: $("#hindiSeg"),
  enginePill: $("#enginePill"), engineLabel: $("#engineLabel"),
};

let trendChart = null;
let lastResult = null;
let chatRows = [];
const settings = { use_gemini: false, strict: false, sensitivity: "medium" };
const geminiReady = document.body.dataset.geminiReady === "true";
const USERS = ["User1", "User2", "User3", "User4"];

// ===== Helpers =====
function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("is-visible");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => els.toast.classList.remove("is-visible"), 2500);
}
function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function escapeRegex(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
function highlightToxic(text, toxicWords) {
  if (!toxicWords || !toxicWords.length) return escapeHtml(text);
  // Escape full text once, then replace toxic substrings inside escaped string
  let escaped = escapeHtml(text);
  // Sort longest-first to avoid partial overlaps
  const sorted = [...new Set(toxicWords)].sort((a, b) => b.length - a.length);
  for (const w of sorted) {
    const safe = escapeHtml(w);
    const re = new RegExp(escapeRegex(safe), "gi");
    escaped = escaped.replace(re, (m) => `<span class="hl-toxic">${m}</span>`);
  }
  return escaped;
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
function bubbleScoreClass(score) {
  if (score >= 65) return "bubble__score--high";
  if (score >= 35) return "bubble__score--med";
  return "bubble__score--low";
}

// ===== Tabs =====
els.tabs.forEach((t) => {
  t.addEventListener("click", () => {
    els.tabs.forEach((x) => x.classList.remove("is-active"));
    t.classList.add("is-active");
    Object.values(els.panels).forEach((p) => p.classList.remove("is-active"));
    els.panels[t.dataset.tab].classList.add("is-active");
  });
});

// ===== Settings =====
function syncGeminiUI() {
  if (!geminiReady) {
    els.geminiToggle.checked = false; els.geminiToggle.disabled = true;
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
els.geminiToggle.addEventListener("change", (e) => { settings.use_gemini = e.target.checked; syncGeminiUI(); });
els.strictToggle.addEventListener("change", (e) => { settings.strict = e.target.checked; });
els.hindiSeg.addEventListener("click", (e) => {
  const btn = e.target.closest(".seg__btn"); if (!btn) return;
  $$(".seg__btn").forEach((b) => b.classList.remove("is-active"));
  btn.classList.add("is-active");
  settings.sensitivity = btn.dataset.value;
});

// ===== Single comment counter =====
function updateCount() {
  const lines = els.textarea.value.split("\n").filter((l) => l.trim().length > 0);
  els.count.textContent = `${lines.length} comment${lines.length === 1 ? "" : "s"}`;
}

// ===== Chat builder =====
function renderChatBuilder() {
  els.chatBuilder.innerHTML = "";
  chatRows.forEach((row, i) => {
    const div = document.createElement("div");
    div.className = "chat-row";
    div.innerHTML = `
      <div class="chat-row__user-wrap">
        <span class="chat-row__dot" data-user="${row.user}"></span>
        <select class="chat-row__select" data-i="${i}">
          ${USERS.map((u) => `<option value="${u}" ${u === row.user ? "selected" : ""}>${u}</option>`).join("")}
        </select>
      </div>
      <input class="chat-row__input" data-i="${i}" type="text" value="${escapeHtml(row.text)}" placeholder="Type message..." />
      <button class="chat-row__del" data-i="${i}" type="button" title="Delete">×</button>
    `;
    els.chatBuilder.appendChild(div);
  });
  els.chatCount.textContent = `${chatRows.length} message${chatRows.length === 1 ? "" : "s"}`;
}
els.chatBuilder.addEventListener("input", (e) => {
  const target = e.target;
  const i = parseInt(target.dataset.i, 10);
  if (Number.isNaN(i)) return;
  if (target.classList.contains("chat-row__input")) {
    chatRows[i].text = target.value;
  } else if (target.classList.contains("chat-row__select")) {
    chatRows[i].user = target.value;
    const dot = target.parentElement.querySelector(".chat-row__dot");
    if (dot) dot.dataset.user = target.value;
  }
});
els.chatBuilder.addEventListener("click", (e) => {
  const btn = e.target.closest(".chat-row__del");
  if (!btn) return;
  const i = parseInt(btn.dataset.i, 10);
  chatRows.splice(i, 1);
  renderChatBuilder();
});
els.addMsgBtn.addEventListener("click", () => {
  const last = chatRows[chatRows.length - 1];
  const next = last ? (last.user === "User1" ? "User2" : "User1") : "User1";
  chatRows.push({ user: next, text: "" });
  renderChatBuilder();
  // focus the new input
  setTimeout(() => {
    const inputs = els.chatBuilder.querySelectorAll(".chat-row__input");
    if (inputs.length) inputs[inputs.length - 1].focus();
  }, 30);
});
function loadChatDemo(rows, label) {
  chatRows = rows.map((r) => ({ ...r }));
  renderChatBuilder();
  showToast(`${label} chat demo loaded.`);
}
els.chatDemoSafe.addEventListener("click", () => loadChatDemo(DEMO_CHAT_SAFE, "Safe"));
els.chatDemoMed.addEventListener("click", () => loadChatDemo(DEMO_CHAT_MED, "Medium"));
els.chatDemoHigh.addEventListener("click", () => loadChatDemo(DEMO_CHAT_HIGH, "High"));
els.chatResetBtn.addEventListener("click", () => {
  chatRows = [
    { user: "User1", text: "" }, { user: "User2", text: "" },
    { user: "User1", text: "" }, { user: "User2", text: "" },
  ];
  renderChatBuilder();
  els.dashboard.classList.add("hidden");
  showToast("Chat reset.");
});

// ===== Rendering =====
function renderBreakdown(rows, isChat) {
  els.breakdownList.innerHTML = "";
  rows.forEach((item, i) => {
    const row = document.createElement("div");
    row.className = "row";
    row.style.animation = `rise 0.4s ease both`;
    row.style.animationDelay = `${i * 40}ms`;
    const tagsHtml = item.tags.map((t) => `<span class="tag tag--${t}">${t}</span>`).join("");
    const userHtml = (isChat && item.user) ? `<div class="row__user" data-user="${escapeHtml(item.user)}">${escapeHtml(item.user)}</div>` : "";
    row.innerHTML = `
      <div class="row__index">#${item.index}</div>
      <div class="row__main">
        ${userHtml}
        <div class="row__text">${highlightToxic(item.comment, item.toxic_words)}</div>
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
      label: "Toxicity", data: series,
      borderColor: "#8b5cf6", backgroundColor: grad,
      borderWidth: 3, fill: true, tension: 0.4,
      pointBackgroundColor: "#22d3ee", pointBorderColor: "#0b0c1a",
      pointBorderWidth: 2, pointRadius: 5, pointHoverRadius: 8,
    }],
  };
  const options = {
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 900, easing: "easeOutCubic" },
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: "rgba(11, 12, 26, 0.95)", titleColor: "#e7e9ff", bodyColor: "#9aa0c8",
        borderColor: "rgba(139, 92, 246, 0.4)", borderWidth: 1, padding: 12, cornerRadius: 8 },
    },
    scales: {
      x: { grid: { color: "rgba(139, 92, 246, 0.08)" }, ticks: { color: "#6b7099", font: { family: "JetBrains Mono" } } },
      y: { beginAtZero: true, max: 100, grid: { color: "rgba(139, 92, 246, 0.08)" },
           ticks: { color: "#6b7099", font: { family: "JetBrains Mono" }, stepSize: 20 } },
    },
  };
  if (trendChart) { trendChart.data = data; trendChart.options = options; trendChart.update(); }
  else trendChart = new Chart(els.trendCanvas, { type: "line", data, options });
}

function applyRiskStyling(label, simpleRisk) {
  els.riskBadge.classList.remove("is-slight", "is-medium", "is-high", "is-critical");
  els.actionCard.classList.remove("is-medium", "is-high");
  els.moderatorAlert.classList.add("hidden");
  const l = (label || "").toLowerCase();
  if (l.includes("critical")) els.riskBadge.classList.add("is-critical");
  else if (l.includes("high")) els.riskBadge.classList.add("is-high");
  else if (l.includes("moderate")) els.riskBadge.classList.add("is-medium");
  else if (l.includes("slight")) els.riskBadge.classList.add("is-slight");

  if (simpleRisk === "MEDIUM") els.actionCard.classList.add("is-medium");
  else if (simpleRisk === "HIGH") {
    els.actionCard.classList.add("is-high");
    els.moderatorAlert.classList.remove("hidden");
  }
}
function applyThreatBadge(level) {
  els.threatBadge.classList.remove("is-low", "is-medium", "is-high");
  const l = (level || "NONE").toLowerCase();
  els.threatBadge.textContent = level;
  if (l === "low") els.threatBadge.classList.add("is-low");
  else if (l === "medium") els.threatBadge.classList.add("is-medium");
  else if (l === "high") els.threatBadge.classList.add("is-high");
  const hints = {
    NONE: "No threats found", LOW: "Mild attack signal",
    MEDIUM: "Aggressive language", HIGH: "Direct threats present",
  };
  els.threatHint.textContent = hints[level] || "—";
}

function updateGauge(value) {
  const arcLen = 251.2;
  els.gaugeArc.style.strokeDashoffset = arcLen * (1 - Math.min(100, value) / 100);
  const angle = -90 + (Math.min(100, value) / 100) * 180;
  els.gaugeNeedle.setAttribute("transform", `rotate(${angle} 100 110)`);
  animateNumber(els.gaugeValue, value);
}
function updateHealth(value) {
  const arcLen = 314.16;
  els.healthArc.style.strokeDashoffset = arcLen * (1 - Math.min(100, value) / 100);
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
    <div class="suggest-result">${escapeHtml(rewrite)}</div>`;
}

function renderChatExtras(result) {
  // Aggressor card
  const ag = result.main_aggressor || "None";
  els.aggressorName.textContent = ag;
  let avatarColor = "none", avatarText = "—";
  if (ag === "Both") { avatarColor = "both"; avatarText = "⚔"; }
  else if (ag.startsWith("User")) { avatarColor = ag.toLowerCase(); avatarText = ag.replace("User", "U"); }
  els.aggressorAvatar.dataset.color = avatarColor;
  els.aggressorAvatar.textContent = avatarText;

  els.victimPressureVal.textContent = result.victim_pressure || "Low";
  els.mutualToxVal.textContent = `${result.mutual_toxicity ?? 0}%`;

  // Patterns
  els.patternList.innerHTML = "";
  if (!result.patterns || !result.patterns.length) {
    els.patternList.innerHTML = `<span class="pattern-tag pattern-tag--empty">No notable patterns</span>`;
  } else {
    result.patterns.forEach((p) => {
      const span = document.createElement("span");
      span.className = "pattern-tag";
      span.textContent = p;
      els.patternList.appendChild(span);
    });
  }

  // Per-user grid
  els.usersGrid.innerHTML = "";
  result.user_summaries.forEach((u) => {
    let role = "Calm", roleCls = "is-calm";
    if (result.main_aggressor === u.user) { role = "Aggressor"; roleCls = "is-aggressor"; }
    else if (result.main_aggressor === "Both") { role = "Co-aggressor"; roleCls = "is-aggressor"; }
    else if (result.main_aggressor !== "None" && u.user !== result.main_aggressor) { role = "Recipient"; roleCls = "is-victim"; }
    const card = document.createElement("div");
    card.className = "user-card";
    card.innerHTML = `
      <div class="user-card__head">
        <div class="user-card__avatar" data-color="${u.user}">${u.user.replace("User", "U")}</div>
        <div>
          <div class="user-card__name">${u.user}</div>
          <div class="user-card__role ${roleCls}">${role}</div>
        </div>
      </div>
      <div class="user-card__metrics">
        <div class="user-card__metric"><div class="user-card__metric-label">Avg Score</div><div class="user-card__metric-value">${u.avg_score}</div></div>
        <div class="user-card__metric"><div class="user-card__metric-label">Peak</div><div class="user-card__metric-value">${u.peak_score}</div></div>
        <div class="user-card__metric"><div class="user-card__metric-label">Threats</div><div class="user-card__metric-value">${u.threats}</div></div>
        <div class="user-card__metric"><div class="user-card__metric-label">Attacks</div><div class="user-card__metric-value">${u.attacks}</div></div>
      </div>`;
    els.usersGrid.appendChild(card);
  });

  // Chat replay bubbles
  els.chatReplay.innerHTML = "";
  result.breakdown.forEach((row, i) => {
    const isRight = row.user === "User2";
    const wrap = document.createElement("div");
    wrap.className = "bubble-row" + (isRight ? " is-right" : "");
    wrap.style.animationDelay = `${i * 50}ms`;
    const isToxic = row.score >= 50;
    wrap.innerHTML = `
      <div class="bubble-avatar" data-color="${escapeHtml(row.user)}">${escapeHtml(row.user.replace("User", "U"))}</div>
      <div class="bubble ${isRight ? "is-right" : ""} ${isToxic ? "is-toxic" : ""}">
        <div class="bubble__head">
          <span class="bubble__user">${escapeHtml(row.user)}</span>
          <span class="bubble__score ${bubbleScoreClass(row.score)}">${row.score}</span>
        </div>
        <div class="bubble__text">${highlightToxic(row.comment, row.toxic_words)}</div>
      </div>`;
    els.chatReplay.appendChild(wrap);
  });
}

function renderResult(result) {
  lastResult = result;
  els.dashboard.classList.remove("hidden");

  // Engine pill
  if (result.engine === "Gemini") { els.enginePill.classList.add("is-gemini"); els.engineLabel.textContent = "Gemini Mode"; }
  else { els.enginePill.classList.remove("is-gemini"); els.engineLabel.textContent = "Local AI Mode"; }
  els.engineChip.textContent = result.engine;
  els.engineSubHint.textContent = result.engine === "Gemini" ? "Blended scoring (Gemini + local)" : "Rule-based scoring";

  // Top 5 metrics
  animateNumber(els.toxicityValue, result.toxicity_score);
  animateNumber(els.aggressionValue, result.aggression_score || 0);
  animateNumber(els.driftValue, result.drift_score);
  animateNumber(els.escalationValue, result.escalation_chance || 0);
  requestAnimationFrame(() => {
    els.toxicityBar.style.width = result.toxicity_score + "%";
    els.aggressionBar.style.width = (result.aggression_score || 0) + "%";
    els.driftBar.style.width = result.drift_score + "%";
    els.escalationBar.style.width = (result.escalation_chance || 0) + "%";
  });

  // Final risk label + threat badge
  els.riskBadge.textContent = result.final_label || result.risk_level;
  els.riskHint.textContent = `Confidence ${result.confidence}%`;
  applyRiskStyling(result.final_label, result.risk_level);
  applyThreatBadge(result.threat_level || "NONE");

  // Emotion / Intent / Hints
  els.emotionChip.textContent = result.dominant_emotion;
  els.emotionChip.dataset.emotion = result.dominant_emotion;
  els.intentChip.textContent = result.dominant_intent;
  els.intentChip.dataset.intent = result.dominant_intent;
  els.emotionHint.textContent = `${result.engine} · ${result.confidence}% confidence`;
  els.driftHint.textContent = `Trend: ${result.trend_label}`;

  // Action
  els.actionText.textContent = result.recommended_action;

  // Heat / Drift / Health
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

  // Chat-only sections
  const isChat = result.mode === "chat";
  els.chatOnlySection.classList.toggle("hidden", !isChat);
  if (isChat) renderChatExtras(result);

  // Breakdown + chart
  renderBreakdown(result.breakdown, isChat);
  renderTrendChart(result.trend_series);

  setTimeout(() => { els.dashboard.scrollIntoView({ behavior: "smooth", block: "start" }); }, 80);
}

// ===== Analyze =====
async function analyze() {
  const text = els.textarea.value.trim();
  if (!text) { showToast("Please enter at least one comment."); return; }
  els.analyzeBtn.classList.add("is-loading");
  try {
    const res = await fetch("/analyze", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        comments: text, sensitivity: settings.sensitivity,
        strict: settings.strict, use_gemini: settings.use_gemini && geminiReady,
      }),
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.error || "Something went wrong."); return; }
    renderResult(data);
  } catch (err) {
    showToast("Network error. Please try again.");
    console.error(err);
  } finally { els.analyzeBtn.classList.remove("is-loading"); }
}

async function analyzeChat() {
  const messages = chatRows.filter((r) => r.text.trim().length > 0);
  if (!messages.length) { showToast("Please add at least one message."); return; }
  els.analyzeChatBtn.classList.add("is-loading");
  try {
    const res = await fetch("/analyze_chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages, sensitivity: settings.sensitivity,
        strict: settings.strict, use_gemini: settings.use_gemini && geminiReady,
      }),
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.error || "Something went wrong."); return; }
    renderResult(data);
  } catch (err) {
    showToast("Network error. Please try again.");
    console.error(err);
  } finally { els.analyzeChatBtn.classList.remove("is-loading"); }
}

// ===== Demo loaders / reset (single) =====
function loadDemoEN() { els.textarea.value = DEMO_EN.join("\n"); updateCount(); showToast("English demo loaded."); }
function loadDemoHI() { els.textarea.value = DEMO_HI.join("\n"); updateCount(); showToast("Hinglish demo loaded."); }
function reset() {
  els.textarea.value = ""; updateCount();
  els.dashboard.classList.add("hidden");
  if (trendChart) { trendChart.destroy(); trendChart = null; }
  showToast("Reset complete.");
  els.textarea.focus();
}

// ===== Export TXT =====
function exportReport() {
  if (!lastResult) { showToast("Run an analysis first."); return; }
  const r = lastResult;
  const lines = [];
  const sep = "=".repeat(60);
  lines.push("ToxiTrack AI - Conversation Risk Report");
  lines.push(sep);
  lines.push(`Generated: ${new Date().toLocaleString()}`);
  lines.push(`Engine:    ${r.engine}`);
  lines.push(`Mode:      ${r.mode === "chat" ? "Live Chat" : "Comment Analyzer"}`);
  lines.push("");
  lines.push("--- SCORES ---");
  lines.push(`Toxicity:          ${r.toxicity_score}/100`);
  lines.push(`Aggression:        ${r.aggression_score || 0}/100`);
  lines.push(`Drift:             ${r.drift_score}/100  (${r.drift_type})`);
  lines.push(`Escalation Chance: ${r.escalation_chance || 0}/100`);
  lines.push(`Conversation Health: ${r.community_health}/100`);
  lines.push(`Threat Level:      ${r.threat_level}`);
  lines.push(`Final Risk:        ${r.final_label}  (confidence ${r.confidence}%)`);
  lines.push(`Dominant Emotion:  ${r.dominant_emotion}`);
  lines.push(`Dominant Intent:   ${r.dominant_intent}`);
  lines.push("");
  if (r.mode === "chat") {
    lines.push("--- WHO IS RESPONSIBLE ---");
    lines.push(`Main Aggressor:   ${r.main_aggressor}`);
    lines.push(`Victim Pressure:  ${r.victim_pressure}`);
    lines.push(`Mutual Toxicity:  ${r.mutual_toxicity}%`);
    lines.push(`Patterns:         ${(r.patterns || []).join(", ") || "None"}`);
    lines.push("");
    lines.push("--- PER USER ---");
    r.user_summaries.forEach((u) => {
      lines.push(`${u.user} | msgs ${u.messages} | avg ${u.avg_score} | peak ${u.peak_score} | threats ${u.threats} | attacks ${u.attacks}`);
    });
    lines.push("");
  }
  lines.push("--- AI EXPLANATION ---");
  r.explanations.forEach((e) => lines.push("• " + e));
  lines.push("");
  lines.push("--- RECOMMENDED ACTION ---");
  lines.push(r.recommended_action);
  lines.push("");
  if (r.rewrite_suggestion && r.riskiest_comment) {
    lines.push("--- REWRITE SUGGESTION ---");
    lines.push(`Original: ${r.riskiest_comment}`);
    lines.push(`Polite:   ${r.rewrite_suggestion}`);
    lines.push("");
  }
  lines.push("--- SAFE REPLY ---");
  lines.push(r.safe_reply || "—");
  lines.push("");
  lines.push("--- MESSAGE BREAKDOWN ---");
  r.breakdown.forEach((row) => {
    const u = row.user ? `${row.user} | ` : "";
    lines.push(`#${row.index} | ${u}score ${row.score} | ${row.emotion} (${row.intent})`);
    lines.push(`     "${row.comment}"`);
    lines.push(`     ${row.reason}`);
    if (row.toxic_words && row.toxic_words.length) lines.push(`     toxic: ${row.toxic_words.join(", ")}`);
  });
  lines.push("");
  lines.push(sep);
  lines.push("ToxiTrack AI v3.0 · AI for Safer Communities");
  const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  a.download = `toxitrack-report-${ts}.txt`;
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 100);
  showToast("Report downloaded.");
}

// ===== Wire up =====
els.textarea.addEventListener("input", updateCount);
els.analyzeBtn.addEventListener("click", analyze);
els.demoBtn.addEventListener("click", loadDemoEN);
els.demoHiBtn.addEventListener("click", loadDemoHI);
els.resetBtn.addEventListener("click", reset);
els.textarea.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); analyze(); }
});
els.analyzeChatBtn.addEventListener("click", analyzeChat);
els.exportBtn.addEventListener("click", exportReport);

// Initialize
chatRows = [
  { user: "User1", text: "" }, { user: "User2", text: "" },
  { user: "User1", text: "" }, { user: "User2", text: "" },
];
renderChatBuilder();
syncGeminiUI();
updateCount();
