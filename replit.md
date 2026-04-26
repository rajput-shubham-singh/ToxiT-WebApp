# ToxiTrack AI

## Overview

A hackathon-ready Flask web app that predicts toxicity escalation and behavioral drift from a user's recent comment history. Pure rule-based scoring engine — no paid APIs required.

## Stack

- **Backend**: Python 3.11 + Flask
- **Frontend**: HTML, CSS, vanilla JS
- **Charts**: Chart.js (CDN)
- **Fonts**: Space Grotesk + JetBrains Mono (Google Fonts)

## File Structure

```
main.py                  # Flask backend + scoring engine
templates/index.html     # Single-page UI (hero, analyzer, dashboard)
static/style.css         # Dark futuristic glassmorphism styles
static/script.js         # UI interactions + Chart.js trend chart
```

## How It Works

1. User pastes comments (one per line) into the analyzer textarea.
2. Frontend POSTs JSON to `/analyze`.
3. Backend (`analyze_history` in `main.py`) computes:
   - **toxicity_score** (0-100) — weighted average across all comments
   - **drift_score** (0-100) — change in hostility from earlier to later comments
   - **escalation_risk** — LOW / MEDIUM / HIGH classification
   - Per-comment breakdown with signal tags
4. Dashboard renders metric cards, AI explanation, recommended action, trend chart, and breakdown.

## How to Run on Replit

1. Open the project on Replit.
2. The `Start application` workflow runs `python main.py` automatically.
3. Flask binds to `0.0.0.0:5000` (uses `PORT` env var if set).
4. The preview pane displays the live UI — click **Demo Data** to populate sample comments, then **Analyze Behavior**.

To run manually from a shell:

```
python main.py
```
