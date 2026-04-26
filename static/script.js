/* =====================================================
   ToxiTrack AI - Frontend interactions and chart rendering
   ===================================================== */

// Sample comments shown when "Demo Data" is clicked
const DEMO_COMMENTS = [
  "Nice post bro, really helpful",
  "I kind of disagree with this take",
  "This is pretty stupid honestly",
  "You are an absolute idiot",
  "SHUT UP you worthless loser, I hate you!"
];

// Grab DOM nodes once at load time
const $ = (sel) => document.querySelector(sel);
const els = {
  textarea: $("#commentsInput"),
  count: $("#commentCount"),
  analyzeBtn: $("#analyzeBtn"),
  demoBtn: $("#demoBtn"),
  resetBtn: $("#resetBtn"),
  dashboard: $("#dashboard"),
  toxicityValue: $("#toxicityValue"),
  toxicityBar: $("#toxicityBar"),
  driftValue: $("#driftValue"),
  driftBar: $("#driftBar"),
  driftHint: $("#driftHint"),
  riskBadge: $("#riskBadge"),
  riskHint: $("#riskHint"),
  actionCard: $("#actionCard"),
  actionText: $("#actionText"),
  explainList: $("#explainList"),
  breakdownList: $("#breakdownList"),
  trendCanvas: $("#trendChart"),
  toast: $("#toast"),
};

let trendChart = null; // Chart.js instance

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

function renderBreakdown(breakdown) {
  els.breakdownList.innerHTML = "";
  breakdown.forEach((item, i) => {
    const row = document.createElement("div");
    row.className = "row";
    row.style.animation = `rise 0.4s ease both`;
    row.style.animationDelay = `${i * 40}ms`;

    const tagsHtml = item.tags
      .map((t) => `<span class="tag tag--${t}">${t}</span>`)
      .join("");

    row.innerHTML = `
      <div class="row__index">#${item.index}</div>
      <div class="row__text">${escapeHtml(item.comment)}</div>
      <div class="row__tags">${tagsHtml}</div>
      <div class="row__score ${scoreClass(item.score)}">${item.score}</div>
    `;
    els.breakdownList.appendChild(row);
  });
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderTrendChart(series) {
  const labels = series.map((_, i) => `#${i + 1}`);

  // Create gradient fill for the chart
  const ctx = els.trendCanvas.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 320);
  grad.addColorStop(0, "rgba(139, 92, 246, 0.55)");
  grad.addColorStop(1, "rgba(139, 92, 246, 0)");

  const data = {
    labels,
    datasets: [
      {
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
        pointHoverRadius: 7,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 900, easing: "easeOutCubic" },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "rgba(11, 12, 26, 0.95)",
        titleColor: "#e7e9ff",
        bodyColor: "#9aa0c8",
        borderColor: "rgba(139, 92, 246, 0.4)",
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
      },
    },
    scales: {
      x: {
        grid: { color: "rgba(139, 92, 246, 0.08)" },
        ticks: { color: "#6b7099", font: { family: "JetBrains Mono" } },
      },
      y: {
        beginAtZero: true,
        max: 100,
        grid: { color: "rgba(139, 92, 246, 0.08)" },
        ticks: { color: "#6b7099", font: { family: "JetBrains Mono" }, stepSize: 20 },
      },
    },
  };

  if (trendChart) {
    trendChart.data = data;
    trendChart.options = options;
    trendChart.update();
  } else {
    trendChart = new Chart(els.trendCanvas, { type: "line", data, options });
  }
}

function applyRiskStyling(level) {
  els.riskBadge.classList.remove("is-medium", "is-high");
  els.actionCard.classList.remove("is-medium", "is-high");
  if (level === "MEDIUM") {
    els.riskBadge.classList.add("is-medium");
    els.actionCard.classList.add("is-medium");
  } else if (level === "HIGH") {
    els.riskBadge.classList.add("is-high");
    els.actionCard.classList.add("is-high");
  }
}

function renderResult(result) {
  // Reveal dashboard if hidden
  els.dashboard.classList.remove("hidden");

  // Animated metric values
  animateNumber(els.toxicityValue, result.toxicity_score);
  animateNumber(els.driftValue, result.drift_score);

  // Bar widths
  requestAnimationFrame(() => {
    els.toxicityBar.style.width = result.toxicity_score + "%";
    els.driftBar.style.width = result.drift_score + "%";
  });

  // Risk
  els.riskBadge.textContent = result.risk_level;
  applyRiskStyling(result.risk_level);
  els.riskHint.textContent = `Trend: ${result.trend_label}`;
  els.driftHint.textContent = `Trend: ${result.trend_label}`;

  // Action
  els.actionText.textContent = result.recommended_action;

  // Explanations
  els.explainList.innerHTML = "";
  result.explanations.forEach((line, i) => {
    const li = document.createElement("li");
    li.textContent = line;
    li.style.animation = `rise 0.4s ease both`;
    li.style.animationDelay = `${i * 60}ms`;
    els.explainList.appendChild(li);
  });

  // Breakdown + chart
  renderBreakdown(result.breakdown);
  renderTrendChart(result.trend_series);

  // Smooth scroll to dashboard
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
      body: JSON.stringify({ comments: text }),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Something went wrong.");
      return;
    }
    renderResult(data);
  } catch (err) {
    showToast("Network error. Please try again.");
    // eslint-disable-next-line no-console
    console.error(err);
  } finally {
    els.analyzeBtn.classList.remove("is-loading");
  }
}

function loadDemo() {
  els.textarea.value = DEMO_COMMENTS.join("\n");
  updateCount();
  showToast("Demo comments loaded.");
}

function reset() {
  els.textarea.value = "";
  updateCount();
  els.dashboard.classList.add("hidden");
  if (trendChart) {
    trendChart.destroy();
    trendChart = null;
  }
  showToast("Reset complete.");
  els.textarea.focus();
}

// ----- Wire up events -----
els.textarea.addEventListener("input", updateCount);
els.analyzeBtn.addEventListener("click", analyze);
els.demoBtn.addEventListener("click", loadDemo);
els.resetBtn.addEventListener("click", reset);

// Allow Ctrl/Cmd+Enter to trigger analysis
els.textarea.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    analyze();
  }
});

updateCount();
