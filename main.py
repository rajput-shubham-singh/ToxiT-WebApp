"""
ToxiTrack AI - Behavioral Drift & Toxicity Escalation Prediction
=================================================================
Multilingual (English + Hindi + Hinglish + Roman Hindi) toxicity engine
with optional Google Gemini fallback for deeper context analysis.
"""

import os
import re
import json
from flask import Flask, render_template, request, jsonify

# Optional Gemini integration - imported lazily so app still runs without it
try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except Exception:
    _GEMINI_AVAILABLE = False

app = Flask(__name__)

# ============================================================
# 1. MULTILINGUAL LEXICONS
# Weighted dictionaries: severe / abusive / medium / mild
# ============================================================

# --- ENGLISH severe & abusive ---
EN_SEVERE = {
    "idiot", "stupid", "moron", "dumbass", "loser", "trash", "garbage",
    "pathetic", "worthless", "scum", "freak", "useless", "shameful",
    "disgusting", "horrible", "nasty", "asshole", "bastard", "jerk",
    "fool", "ugly", "fraud",
}
EN_PROFANITY = {
    "damn", "hell", "crap", "shut up", "screw you", "piss off",
    "fuck", "shit", "bitch", "fucking", "motherfucker",
}
EN_AGGRESSIVE = {
    "hate", "kill", "destroy", "fight", "die", "attack",
    "threat", "punch", "smash", "ruin", "burn",
}

# --- HINDI / HINGLISH / ROMAN HINDI ---
# Severe abuse - always score high regardless of context
HI_ABUSIVE_SEVERE = {
    "madarchod", "bhenchod", "behenchod", "bhanchod", "chutiya",
    "chutiye", "chutiyaa", "chutya", "lodu", "lawde", "lavde",
    "lund", "land", "gaand", "gandu", "gaandu", "randi", "raand",
    "bhosdi", "bhosdike", "bhosadike", "bhosadike", "bhosdiwale",
    "bsdk", "mkc", "bkl", "bc", "mc", "wtf", "stfu",
}

# Medium-severity Hindi insults
HI_INSULT_SEVERE = {
    "harami", "haraami", "kutte", "kutta", "kutti", "sale", "saala",
    "saale", "kameena", "kamina", "kameene", "ghatiya", "ghattiya",
    "bakchod", "bakchodi",
}

# Mild/medium insults - context matters
HI_INSULT_MEDIUM = {
    "pagal", "paagal", "bewakoof", "bewakuf", "bevakoof", "gadha",
    "gadhe", "ulloo", "ullu", "nikamma", "nalayak", "nalaayak",
    "bakwas", "faltu", "faaltu", "bekar", "bekaar", "ghamandi",
    "ghissu", "lallu", "lalu", "dhakkan", "tharki", "tharak",
    "neech", "neech aadmi",
}

# Aggression / threat keywords (Hindi)
HI_AGGRESSIVE = {
    "maar", "maarunga", "marunga", "marungi", "peetunga", "peetungi",
    "thoko", "thok dunga", "jaan le", "katwa dunga", "uthwa lunga",
    "todunga", "phod dunga", "phodunga", "phorenge",
}

# Phrases that ATTACK a person (raise score significantly)
HI_ATTACK_PATTERNS = [
    r"\btu\s+\w+\s+hai\b",        # "tu pagal hai"
    r"\btum\s+\w+\s+ho\b",         # "tum pagal ho"
    r"\bteri\s+ma\b",              # "teri ma"
    r"\bteri\s+maa\b",
    r"\bteri\s+behen\b",
    r"\btere\s+baap\b",
    r"\bchup\s+(reh|kar|raho|baith)\b",  # "chup reh"
    r"\bdimag\s+(kharab|kharaab)\b",     # "dimag kharab"
    r"\bdimaag\s+(kharab|kharaab)\b",
    r"\bbhag\s+ja\b",              # "bhag ja"
    r"\bnikal\s+yahan\s+se\b",
    r"\bdafa\s+ho\b",
]

# Phrases that DOWNWEIGHT the toxicity (playful / non-attack context)
PLAYFUL_PATTERNS = [
    r"\b\w+\s+level\s+(funny|cool|awesome|amazing|hilarious|mast|great|epic)\b",
    r"\bhaha+\b", r"\blol\b", r"\blmao\b", r"\brofl\b",
    r"\bkya\s+baat\b", r"\bwah+\b", r"\bshabaash\b", r"\bshabash\b",
    r"\bmast\b", r"\bzabardast\b", r"\bbahut\s+accha\b",
    r"\bbahut\s+badhiya\b", r"\bbadhiya\b",
    r"\bjokingly\b", r"\bjk\b", r"\bjust\s+kidding\b",
]

# Sarcasm markers
SARCASM_MARKERS = [
    r"\bwow\s+great\b", r"\bbahut\s+accha\.{2,}", r"\boh\s+really\b",
    r"\bso\s+smart\b", r"\bkitna\s+intelligent\b",
    r"\bhaan\s+haan\b", r"\bjaroor\b.*\?", r"\bzaroor\b.*\?",
    r"/s$", r"\\\\s$",
]

# Threat markers
THREAT_MARKERS = [
    r"\bi\s+will\s+(kill|destroy|hurt|find)\b",
    r"\bmaar\s+dunga\b", r"\bjaan\s+le\s+lunga\b",
    r"\bdekhta\s+hu\s+tujhe\b", r"\bdekh\s+lunga\b",
    r"\btu\s+gaya\b", r"\bteri\s+to\b",
]

# Positive sentiment offsets
POSITIVE = {
    "good", "great", "love", "nice", "awesome", "amazing", "cool",
    "wonderful", "fantastic", "excellent", "thanks", "thank you",
    "appreciate", "kind", "happy", "best", "brilliant", "lovely",
    "respect", "agree", "supportive", "helpful",
    # Hindi positives
    "accha", "achha", "achcha", "badhiya", "mast", "shandaar",
    "shabaash", "shabash", "wah", "zabardast", "kamaal", "pyaara",
    "pyara", "dhanyavaad", "shukriya",
}

# Question / playful tone markers (downweight)
QUESTION_TONE = [
    r"\?\s*$", r"\bkya\b\s+\w+\s+(hai|ho)\s*\?", r"\bho\s+kya\b",
]


# ============================================================
# 2. PHRASE-BASED REWRITE & SAFE REPLY MAPS
# ============================================================

REWRITE_MAP = {
    "tu pagal hai": "I think you're mistaken about this.",
    "tu paagal hai": "I think you're mistaken about this.",
    "pagal ho kya": "Could you reconsider that?",
    "tum pagal ho": "I respectfully disagree.",
    "chup reh": "Let's hear other perspectives too.",
    "chup kar": "Let's pause and listen for a moment.",
    "bakwas": "I don't think that's quite right.",
    "kya bakwas": "I'm not following the reasoning here.",
    "bewakoof": "I see this differently.",
    "gadha": "Let's try to think this through together.",
    "faltu": "This may not be the most useful angle.",
    "bekar": "I think this could be improved.",
    "ghatiya": "I'd respectfully disagree with that take.",
    "shut up": "Let's give everyone space to share.",
    "you are an idiot": "I think there's a misunderstanding here.",
    "you are stupid": "I see this differently.",
    "stupid": "unconvincing",
    "idiot": "person",
    "trash": "weak",
}

SAFE_REPLY_BANK = {
    "anger":      "Take a breath - let's keep the conversation respectful.",
    "sarcasm":    "I want to make sure I'm reading you right - can you clarify?",
    "mockery":    "Let's discuss this without targeting anyone personally.",
    "bullying":   "Everyone here deserves to feel safe. Let's reset the tone.",
    "threat":     "Threats aren't acceptable - this conversation will be reviewed.",
    "hate":       "Let's keep the discussion focused on ideas, not attacks.",
    "frustration":"I hear you - what's the underlying concern?",
    "playful":    "Glad you're enjoying it!",
    "neutral":    "Thanks for sharing your thoughts.",
}


# ============================================================
# 3. HELPERS
# ============================================================

def tokenize(text: str):
    return re.findall(r"[a-zA-Z\u0900-\u097F']+", text.lower())


def count_phrases(text_lower: str, phrases):
    """Count occurrences of words OR multi-word phrases."""
    total = 0
    for phrase in phrases:
        if " " in phrase:
            total += text_lower.count(phrase)
        else:
            total += len(re.findall(r"\b" + re.escape(phrase) + r"\b", text_lower))
    return total


def count_pattern_hits(text_lower: str, patterns):
    return sum(1 for p in patterns if re.search(p, text_lower))


def has_emoji(text: str) -> bool:
    # Common laughing / playful emoji range
    return bool(re.search(r"[\U0001F600-\U0001F64F]|😂|🤣|😅|😆|😜|😝|😛|🤪|❤|♥", text))


# ============================================================
# 4. CORE LOCAL ENGINE - per-comment scoring
# ============================================================

def score_single_comment(comment: str, sensitivity: str = "medium", strict: bool = False):
    text_lower = comment.lower()
    tokens = tokenize(comment)
    word_count = max(1, len(tokens))

    # Lexicon hits
    en_severe = count_phrases(text_lower, EN_SEVERE)
    en_profanity = count_phrases(text_lower, EN_PROFANITY)
    en_aggressive = count_phrases(text_lower, EN_AGGRESSIVE)

    hi_abusive = count_phrases(text_lower, HI_ABUSIVE_SEVERE)
    hi_severe = count_phrases(text_lower, HI_INSULT_SEVERE)
    hi_medium = count_phrases(text_lower, HI_INSULT_MEDIUM)
    hi_aggro = count_phrases(text_lower, HI_AGGRESSIVE)

    positive = count_phrases(text_lower, POSITIVE)

    # Pattern hits
    attack_hits = count_pattern_hits(text_lower, HI_ATTACK_PATTERNS)
    playful_hits = count_pattern_hits(text_lower, PLAYFUL_PATTERNS)
    sarcasm_hits = count_pattern_hits(text_lower, SARCASM_MARKERS)
    threat_hits = count_pattern_hits(text_lower, THREAT_MARKERS)
    question_hits = count_pattern_hits(text_lower, QUESTION_TONE)
    emoji_playful = has_emoji(comment)

    # ALL CAPS shouting (English-only — Hindi script isn't case-sensitive)
    shout_words = sum(
        1 for t in tokens
        if len(t) >= 4 and t.upper() == t and re.match(r"^[a-z']+$", t.lower())
    )
    caps_ratio = shout_words / word_count

    excess_exclaim = max(0, comment.count("!") - 1)

    # Sensitivity multiplier for Hindi medium-severity insults
    hindi_mult = {"low": 0.6, "medium": 1.0, "high": 1.5}.get(sensitivity, 1.0)
    strict_bonus = 1.25 if strict else 1.0

    # Weighted score
    raw = (
        hi_abusive * 32                                # always severe
        + hi_severe * 22                               # harami / kutte / sale
        + hi_medium * 11 * hindi_mult                  # pagal / bewakoof
        + hi_aggro * 18
        + en_severe * 18
        + en_profanity * 14
        + en_aggressive * 12
        + attack_hits * 14                             # "tu X hai"
        + threat_hits * 22
        + sarcasm_hits * 6
        + excess_exclaim * 3
        + caps_ratio * 22
        - positive * 7
        - playful_hits * 14                            # "X level funny"
        - (10 if emoji_playful and hi_abusive == 0 and hi_severe == 0 else 0)
        - question_hits * 4                            # "ho kya?" tone
    )

    score = int(max(0, min(100, raw * strict_bonus)))

    # ----- Emotion / Intent classification -----
    emotion, intent, reason = classify_emotion_intent(
        score=score,
        hi_abusive=hi_abusive, hi_severe=hi_severe, hi_medium=hi_medium,
        en_severe=en_severe, en_profanity=en_profanity,
        attack_hits=attack_hits, threat_hits=threat_hits,
        sarcasm_hits=sarcasm_hits, playful_hits=playful_hits,
        emoji_playful=emoji_playful, positive=positive,
        caps_ratio=caps_ratio, excess_exclaim=excess_exclaim,
    )

    return {
        "comment": comment,
        "score": score,
        "emotion": emotion,
        "intent": intent,
        "reason": reason,
        "signals": {
            "abusive": hi_abusive,
            "severe": hi_severe + en_severe,
            "profanity": en_profanity,
            "aggressive": hi_aggro + en_aggressive,
            "attack": attack_hits,
            "threat": threat_hits,
            "sarcasm": sarcasm_hits,
            "playful": playful_hits,
            "shouting": shout_words,
            "positive": positive,
            "emoji_playful": int(emoji_playful),
        },
    }


def classify_emotion_intent(**s):
    """Classify a comment into an emotion + intent + reason string."""
    score = s["score"]
    hi_abusive, hi_severe = s["hi_abusive"], s["hi_severe"]
    en_severe, attack_hits = s["en_severe"], s["attack_hits"]
    threat_hits = s["threat_hits"]
    sarcasm_hits, playful_hits = s["sarcasm_hits"], s["playful_hits"]
    emoji_playful = s["emoji_playful"]
    caps_ratio, excess_exclaim = s["caps_ratio"], s["excess_exclaim"]
    positive = s["positive"]

    # Threat dominates everything
    if threat_hits >= 1:
        return "Threat", "threat", "Threatening language detected."

    if hi_abusive >= 1:
        return "Angry", "bullying", "Severe abusive Hindi/Hinglish phrase detected."

    if (hi_severe + en_severe) >= 2 or (attack_hits >= 1 and (hi_severe + en_severe + s["hi_medium"]) >= 1):
        return "Angry", "bullying", "Multiple insults targeting a person."

    if caps_ratio > 0.4 or excess_exclaim >= 2:
        if score >= 40:
            return "Angry", "anger", "Shouting / aggressive punctuation."
        return "Frustrated", "frustration", "Heightened tone with caps or punctuation."

    if sarcasm_hits >= 1 and score >= 25:
        return "Sarcastic", "mockery", "Sarcastic tone detected."

    if playful_hits >= 1 or (emoji_playful and score < 35):
        return "Playful", "playful", "Playful or joking tone."

    if score >= 60:
        return "Angry", "anger", "Hostile language pattern."
    if score >= 35:
        return "Negative", "frustration", "Negative tone toward subject."
    if positive >= 1 and score < 20:
        return "Positive", "supportive", "Positive sentiment expressed."
    return "Neutral", "neutral", "No strong toxicity signals."


# ============================================================
# 5. REWRITE / SAFE REPLY HELPERS
# ============================================================

def rewrite_toxic(comment: str) -> str:
    """Produce a polite version of a toxic comment using a substitution map."""
    text = comment
    lower = text.lower()
    # Try full-phrase rewrites first
    for bad, good in REWRITE_MAP.items():
        if " " in bad and bad in lower:
            return good
    # Word-level substitutions
    new_words = []
    for w in re.findall(r"\S+|\s+", text):
        bare = re.sub(r"[^\w\u0900-\u097F]", "", w).lower()
        if bare in REWRITE_MAP and " " not in REWRITE_MAP[bare]:
            new_words.append(w.replace(re.search(r"\w+", w).group(), REWRITE_MAP[bare], 1))
        else:
            new_words.append(w)
    rewritten = "".join(new_words)
    # Final cleanup — if nothing changed but score was high, fall back to template
    if rewritten.lower() == text.lower():
        return "I see this differently — let's discuss it respectfully."
    return rewritten


def safe_reply_for(emotion: str) -> str:
    key = emotion.lower()
    mapping = {
        "angry": "anger", "threat": "threat", "sarcastic": "sarcasm",
        "negative": "frustration", "frustrated": "frustration",
        "playful": "playful", "positive": "neutral", "neutral": "neutral",
    }
    return SAFE_REPLY_BANK.get(mapping.get(key, "neutral"), SAFE_REPLY_BANK["neutral"])


# ============================================================
# 6. AGGREGATE ANALYSIS - drift, risk, explanations, health
# ============================================================

def analyze_history(comments, sensitivity="medium", strict=False, use_gemini=False):
    cleaned = [c.strip() for c in comments if c and c.strip()]
    if not cleaned:
        return {"error": "Please enter at least one comment."}

    # Try Gemini first if requested + available + key set
    gemini_result = None
    used_engine = "Local AI"
    if use_gemini and _GEMINI_AVAILABLE and os.environ.get("GEMINI_API_KEY"):
        gemini_result = analyze_with_gemini(cleaned)
        if gemini_result:
            used_engine = "Gemini"

    # Always run local engine for breakdown / consistency
    breakdown = [score_single_comment(c, sensitivity, strict) for c in cleaned]

    # If Gemini provided overall scores, blend them in
    if gemini_result:
        for i, item in enumerate(breakdown):
            if i < len(gemini_result.get("comments", [])):
                g = gemini_result["comments"][i]
                # Blend 60% Gemini / 40% local
                item["score"] = int(item["score"] * 0.4 + g.get("score", item["score"]) * 0.6)
                item["emotion"] = g.get("emotion", item["emotion"])
                item["intent"] = g.get("intent", item["intent"])
                item["reason"] = g.get("reason", item["reason"])

    scores = [b["score"] for b in breakdown]
    toxicity_score = int(sum(scores) / len(scores))

    # Drift calculation - first half vs second half average
    drift_score = 0
    drift_type = "Stable"
    trend_label = "stable"
    if len(scores) >= 2:
        mid = max(1, len(scores) // 2)
        first_avg = sum(scores[:mid]) / mid
        second_avg = sum(scores[mid:]) / max(1, len(scores) - mid)
        delta = second_avg - first_avg
        drift_score = max(0, min(100, int((delta + 25) * 2)))

        if delta > 25:
            drift_type, trend_label = "Rapid Escalation", "rapidly escalating"
        elif delta > 10:
            drift_type, trend_label = "Slowly Negative", "rising"
        elif delta < -15:
            drift_type, trend_label = "Recovery", "calming"
        else:
            drift_type, trend_label = "Stable", "stable"
    else:
        drift_score = min(100, scores[0])

    # Aggregate signal totals (for explanations)
    total = {k: sum(b["signals"].get(k, 0) for b in breakdown) for k in
             ["abusive", "severe", "profanity", "aggressive",
              "attack", "threat", "sarcasm", "playful", "shouting", "positive"]}

    # Dominant emotion + intent
    emotions = [b["emotion"] for b in breakdown]
    intents = [b["intent"] for b in breakdown]
    dominant_emotion = max(set(emotions), key=emotions.count)
    dominant_intent = max(set(intents), key=intents.count)

    # Risk classification
    risk_value = (toxicity_score * 0.55) + (drift_score * 0.30) + (max(scores) * 0.15)
    if total["threat"] >= 1 or risk_value >= 65 or toxicity_score >= 65:
        risk_level = "HIGH"
        recommended_action = "Immediate moderation review recommended."
    elif risk_value >= 35 or toxicity_score >= 35:
        risk_level = "MEDIUM"
        recommended_action = "Monitor user closely for further escalation."
    else:
        risk_level = "LOW"
        recommended_action = "User behavior is currently safe. No action required."

    # Confidence — based on signal density and comment count
    signal_density = sum(total.values()) / max(1, len(cleaned))
    confidence = int(min(98, 55 + signal_density * 6 + min(20, len(cleaned) * 2)))

    # Community health = inverse of risk, weighted
    community_health = max(0, min(100, int(100 - (toxicity_score * 0.7 + drift_score * 0.3))))

    # Explanations
    explanations = []
    if drift_type == "Rapid Escalation":
        explanations.append("Rapid escalation pattern detected across the timeline.")
    elif drift_type == "Slowly Negative":
        explanations.append("Conversation is slowly drifting toward negativity.")
    elif drift_type == "Recovery":
        explanations.append("User is de-escalating - tone is improving over time.")
    else:
        explanations.append("Tone has remained relatively stable.")

    if total["abusive"] >= 1:
        explanations.append(f"Detected {total['abusive']} severe abusive Hindi/Hinglish phrase(s).")
    if total["attack"] >= 1:
        explanations.append("Personal attack patterns detected (e.g. 'tu ... hai', 'chup reh').")
    if total["threat"] >= 1:
        explanations.append("Threatening language detected - escalate immediately.")
    if total["severe"] >= 2:
        explanations.append(f"Multiple severe insults across comments ({total['severe']} hits).")
    if total["sarcasm"] >= 2:
        explanations.append("Recurrent sarcastic / mocking tone.")
    if total["shouting"] >= 2:
        explanations.append("Repeated shouting (ALL CAPS) suggests heightened emotion.")
    if total["playful"] >= 2 and total["abusive"] == 0:
        explanations.append("Predominantly playful tone - low actual hostility.")

    # Per-row enrichment: tags, rewrite suggestion for high-score ones
    rows = []
    for i, b in enumerate(breakdown):
        rewrite = rewrite_toxic(b["comment"]) if b["score"] >= 40 else None
        rows.append({
            "index": i + 1,
            "comment": b["comment"],
            "score": b["score"],
            "emotion": b["emotion"],
            "intent": b["intent"],
            "reason": b["reason"],
            "tags": _tags_for(b),
            "rewrite": rewrite,
        })

    # Top safe-reply suggestion based on dominant emotion of riskiest comment
    riskiest = max(breakdown, key=lambda x: x["score"])
    safe_reply = safe_reply_for(riskiest["emotion"])
    rewrite_top = rewrite_toxic(riskiest["comment"]) if riskiest["score"] >= 40 else None

    return {
        "engine": used_engine,
        "toxicity_score": toxicity_score,
        "drift_score": drift_score,
        "drift_type": drift_type,
        "trend_label": trend_label,
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "dominant_emotion": dominant_emotion,
        "dominant_intent": dominant_intent,
        "confidence": confidence,
        "community_health": community_health,
        "explanations": explanations,
        "breakdown": rows,
        "trend_series": scores,
        "safe_reply": safe_reply,
        "rewrite_suggestion": rewrite_top,
        "riskiest_comment": riskiest["comment"] if rewrite_top else None,
    }


def _tags_for(b):
    tags = []
    s = b["signals"]
    if s["threat"]: tags.append("threat")
    if s["abusive"]: tags.append("abusive")
    if s["severe"]: tags.append("severe")
    if s["profanity"]: tags.append("profanity")
    if s["aggressive"]: tags.append("aggressive")
    if s["attack"]: tags.append("attack")
    if s["sarcasm"]: tags.append("sarcasm")
    if s["shouting"]: tags.append("shouting")
    if s["playful"]: tags.append("playful")
    if s["positive"] and not (s["abusive"] or s["severe"]): tags.append("positive")
    if not tags: tags.append("neutral")
    return tags


# ============================================================
# 7. OPTIONAL GEMINI MODE
# ============================================================

GEMINI_PROMPT = """You are a multilingual toxicity classifier for English, Hindi,
Hinglish and Roman Hindi comments. For EACH comment in the JSON list below,
return a JSON object with these exact keys:
  - score (0-100 toxicity score)
  - emotion (one of: Neutral, Positive, Playful, Frustrated, Negative, Sarcastic, Angry, Threat)
  - intent (one of: neutral, supportive, playful, frustration, mockery, anger, bullying, threat, hate)
  - reason (one short English sentence)
Return ONLY a JSON object: {"comments": [ ... ]} - no prose, no markdown.
Comments:
"""


def analyze_with_gemini(comments):
    """Best-effort Gemini analysis. Returns None on any failure."""
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        payload = json.dumps(comments, ensure_ascii=False)
        resp = model.generate_content(GEMINI_PROMPT + payload)
        text = (resp.text or "").strip()
        # Strip markdown fences if present
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("comments"), list):
            return data
    except Exception:
        return None
    return None


# ============================================================
# 8. ROUTES
# ============================================================

@app.route("/")
def index():
    gemini_ready = bool(_GEMINI_AVAILABLE and os.environ.get("GEMINI_API_KEY"))
    return render_template("index.html", gemini_ready=gemini_ready)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    comments = data.get("comments")
    sensitivity = (data.get("sensitivity") or "medium").lower()
    strict = bool(data.get("strict"))
    use_gemini = bool(data.get("use_gemini"))

    if isinstance(comments, str):
        comments = comments.splitlines()
    if not isinstance(comments, list):
        return jsonify({"error": "Invalid input. Provide comments as a list or string."}), 400

    result = analyze_history(comments, sensitivity=sensitivity,
                             strict=strict, use_gemini=use_gemini)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/status")
def status():
    return jsonify({
        "gemini_available": _GEMINI_AVAILABLE,
        "gemini_key_set": bool(os.environ.get("GEMINI_API_KEY")),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
