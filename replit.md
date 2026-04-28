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

- `GEMINI_API_KEY` (optional) — Enables Gemini AI blended scoring. Without it, the local rule-based engine is used. Set via Replit Secrets (never hardcode).

## Recent Changes

- 2026-04-27: Migrated to Replit. Removed hardcoded Gemini API key from `main.py` (now read from `GEMINI_API_KEY` env var only). Fixed a syntax error in `analyze_with_gemini`. Installed Python deps (flask, flask-sqlalchemy, gunicorn, psycopg2-binary, email-validator, google-generativeai) and confirmed the gunicorn workflow boots on port 5000.
- 2026-04-27: Gemini mode now uses Gemini's response directly (no 40/60 blend) when the toggle is on and a key is set; silent fallback to Local AI on failure.
- 2026-04-27: Final-label bands tuned to spec (0-10 Safe / 11-24 Low / 25-44 Mod / 45-69 High / 70-100 Critical). Added `HI_ABUSIVE_TIER_S` (madarchod-class) so only the most extreme abusives auto-floor to Critical; other severe abusives directed at a person floor to High instead. Expanded `EN_BULLYING`, `HI_AGGRESSIVE`, `THREAT_MARKERS`, `PASSIVE_AGG_PATTERNS` with workplace/relationship/sarcasm phrases. Bullying phrases now trigger the targeting amplifier so "You should be fired" / "No one likes you" surface above LOW. All 17 judge tests pass.
- 2026-04-27: Main "Demo" button cycles through 5 judge-spec sets (Safe → Mild → Formal → Threat → Escalation). Hinglish demo button kept. Footer now shows "Designed by Team Techvengers".
- 2026-04-28: Added `EN_MILD` lexicon (irritating, rude, immature, careless, boring, cringe, lazy, arrogant, selfish, fake person, toxic person, stupid behavior, ...) — single occurrence lands LOW, with target/intensifier bumps to MOD. Added missing formal phrases to `EN_BULLYING` (waste of company time, nobody likes working with you, poor attitude, waste of resources, replaceable employee). Stacked rude/bullying lines now trigger an additional aggregate boost (rude_msg_count >= 3 → +4..+10). Tiny card spacing polish (padding 30→32, header gap 16→18). 48/48 tests pass.

## Features

- English + Hindi/Hinglish/Roman Hindi toxicity detection
- Per-comment scoring with emotion/intent/reason classification
- Behavioral drift analysis (stable vs. escalating)
- Aggression score, escalation chance, threat level
- Main aggressor detection in multi-user chat mode
- Safe reply suggestions and toxic comment rewrites
- Interactive trend charts via Chart.js
