# ToxiTrack AI

A multilingual (English, Hindi, Hinglish, Roman Hindi) toxicity and behavioral drift analyzer. Predicts rising hostility and escalation risk in user comment histories or chat conversations.

## Stack

- **Backend**: Python 3.11 / Flask (gunicorn in production)
- **Frontend**: Vanilla JS + Chart.js (single HTML page served via Flask templates)
- **Optional AI**: Google Gemini 1.5 Flash (user-provided API key, gracefully degrades to rule-based engine)

## Key Files

- `main.py` — Flask app with all scoring logic, routes, and multilingual lexicons
- `templates/index.html` — Single-page frontend UI
- `static/style.css` — Glassmorphism dark theme styles
- `static/script.js` — Frontend logic, Chart.js dashboards, API calls

## API Routes

- `GET /` — Renders the main UI
- `POST /analyze` — Accepts `{comments: [...], sensitivity, strict, use_gemini, gemini_key}`, returns toxicity analysis
- `POST /analyze_chat` — Accepts `{messages: [{user, text},...]}`, returns per-user chat analysis
- `GET /status` — Returns `{gemini_available, gemini_key_set}`

## Running

The app runs via gunicorn using the virtual environment at `.pythonlibs/`:

```
.pythonlibs/bin/gunicorn --bind 0.0.0.0:5000 --reload main:app
```

## Environment Variables

- `GEMINI_API_KEY` (optional) — Enables Gemini AI blended scoring. Without it, the local rule-based engine is used.

## Features

- English + Hindi/Hinglish/Roman Hindi toxicity detection
- Per-comment scoring with emotion/intent/reason classification
- Behavioral drift analysis (stable vs. escalating)
- Aggression score, escalation chance, threat level
- Main aggressor detection in multi-user chat mode
- Safe reply suggestions and toxic comment rewrites
- Interactive trend charts via Chart.js
