"""
ToxiTrack AI - Behavioral Drift and Toxicity Escalation Prediction
Flask backend that scores user comment history for toxicity and drift.
"""

import os
import re
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ----- Lexicons used by the rule based scorer -----
# Severe / abusive language - heaviest weights
SEVERE_TOXIC = {
    "idiot", "stupid", "moron", "dumb", "loser", "trash", "garbage",
    "pathetic", "worthless", "scum", "fool", "jerk", "ugly", "freak",
    "useless", "shameful", "disgusting", "horrible", "nasty", "fraud",
}

# Profanity - heavy weights (kept mild for a public demo)
PROFANITY = {
    "damn", "hell", "crap", "bastard", "dumbass", "asshole",
    "shut up", "screw you", "piss off",
}

# Aggressive / hostile speech patterns
AGGRESSIVE = {
    "hate", "kill", "destroy", "fight", "shut", "die", "attack",
    "threat", "punch", "smash", "ruin", "burn",
}

# Negative sentiment markers
NEGATIVE = {
    "bad", "worst", "awful", "terrible", "annoying", "boring",
    "wrong", "poor", "fail", "failure", "disappointing", "lame",
    "ridiculous", "pointless", "useless", "weak", "sad", "angry",
    "mad", "upset", "broken", "sick",
}

# Positive sentiment markers (used to offset, detect drift)
POSITIVE = {
    "good", "great", "love", "nice", "awesome", "amazing", "cool",
    "wonderful", "fantastic", "excellent", "thanks", "thank",
    "appreciate", "kind", "happy", "best", "brilliant", "lovely",
    "respect", "agree",
}


def tokenize(text: str):
    """Split a comment into lowercased word tokens."""
    return re.findall(r"[a-zA-Z']+", text.lower())


def count_phrases(text_lower: str, phrases):
    """Count occurrences of single words OR multi word phrases."""
    total = 0
    for phrase in phrases:
        if " " in phrase:
            total += text_lower.count(phrase)
        else:
            # word boundary match for single words
            total += len(re.findall(r"\b" + re.escape(phrase) + r"\b", text_lower))
    return total


def score_single_comment(comment: str):
    """Return a per comment breakdown of toxic signals."""
    text_lower = comment.lower()
    tokens = tokenize(comment)
    word_count = max(1, len(tokens))

    severe = count_phrases(text_lower, SEVERE_TOXIC)
    profanity = count_phrases(text_lower, PROFANITY)
    aggressive = count_phrases(text_lower, AGGRESSIVE)
    negative = count_phrases(text_lower, NEGATIVE)
    positive = count_phrases(text_lower, POSITIVE)

    # ALL CAPS shouting detection (only count words with 4+ letters)
    shout_words = sum(1 for t in tokens if len(t) >= 4 and t.upper() == t and any(c.isalpha() for c in t))
    caps_ratio = shout_words / word_count

    # Excessive punctuation = anger/aggression
    exclaim = comment.count("!")
    excessive_exclaim = max(0, exclaim - 1)

    # Weighted raw score
    raw = (
        severe * 22
        + profanity * 14
        + aggressive * 12
        + negative * 6
        + excessive_exclaim * 3
        + caps_ratio * 18
        - positive * 7
    )

    # Clamp to 0-100
    score = max(0, min(100, int(raw)))

    return {
        "comment": comment,
        "score": score,
        "severe": severe,
        "profanity": profanity,
        "aggressive": aggressive,
        "negative": negative,
        "positive": positive,
        "shouting": shout_words,
        "exclaim": exclaim,
    }


def analyze_history(comments):
    """Run the full analysis pipeline on a list of comments."""
    cleaned = [c.strip() for c in comments if c and c.strip()]
    if not cleaned:
        return {"error": "Please enter at least one comment."}

    breakdown = [score_single_comment(c) for c in cleaned]
    scores = [b["score"] for b in breakdown]

    # Average toxicity = overall toxicity score
    toxicity_score = int(sum(scores) / len(scores))

    # Drift score = how much later half differs from earlier half
    drift_score = 0
    trend_label = "stable"
    if len(scores) >= 2:
        mid = len(scores) // 2
        first_half = scores[:mid] if mid > 0 else scores[:1]
        second_half = scores[mid:]
        first_avg = sum(first_half) / max(1, len(first_half))
        second_avg = sum(second_half) / max(1, len(second_half))
        delta = second_avg - first_avg
        # Map delta (-100..100) to drift 0..100 with rising weighted heavier
        drift_score = max(0, min(100, int((delta + 20) * 2)))
        if delta > 12:
            trend_label = "rapidly escalating"
        elif delta > 4:
            trend_label = "rising"
        elif delta < -12:
            trend_label = "calming"
        elif delta < -4:
            trend_label = "improving"
        else:
            trend_label = "stable"
    else:
        drift_score = min(100, scores[0])

    # Risk level computed from a blend
    risk_value = (toxicity_score * 0.6) + (drift_score * 0.4)
    if risk_value >= 65 or toxicity_score >= 70:
        risk_level = "HIGH"
        recommended_action = "Immediate moderation review recommended."
    elif risk_value >= 35 or toxicity_score >= 40:
        risk_level = "MEDIUM"
        recommended_action = "Monitor user closely for further escalation."
    else:
        risk_level = "LOW"
        recommended_action = "User behavior is currently safe. No action required."

    # Build a list of human readable explanations
    explanations = []
    total_severe = sum(b["severe"] for b in breakdown)
    total_profanity = sum(b["profanity"] for b in breakdown)
    total_aggressive = sum(b["aggressive"] for b in breakdown)
    total_negative = sum(b["negative"] for b in breakdown)
    total_positive = sum(b["positive"] for b in breakdown)
    total_shout = sum(b["shouting"] for b in breakdown)

    if trend_label == "rapidly escalating":
        explanations.append("Rapid escalation pattern detected across the comment timeline.")
    elif trend_label == "rising":
        explanations.append("Language became more aggressive over time.")
    elif trend_label == "calming":
        explanations.append("Conversation shows a clear de-escalation pattern.")
    elif trend_label == "improving":
        explanations.append("Tone improved across later comments.")
    else:
        explanations.append("Tone remained relatively stable across the timeline.")

    if total_severe >= 1:
        explanations.append(f"Detected {total_severe} severe toxic keyword(s) in the history.")
    if total_profanity >= 1:
        explanations.append(f"Profanity frequency is elevated ({total_profanity} hit(s)).")
    if total_aggressive >= 2:
        explanations.append("Multiple aggressive expressions detected.")
    if total_negative > total_positive and total_negative >= 2:
        explanations.append("Negative sentiment dominates the comment history.")
    if total_shout >= 2:
        explanations.append("Shouting (ALL CAPS) detected, suggesting heightened emotion.")
    if total_positive >= 2 and total_negative == 0:
        explanations.append("Mostly positive language - low inherent risk signal.")

    return {
        "toxicity_score": toxicity_score,
        "drift_score": drift_score,
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "trend_label": trend_label,
        "explanations": explanations,
        "breakdown": [
            {
                "index": i + 1,
                "comment": b["comment"],
                "score": b["score"],
                "tags": _tags_for(b),
            }
            for i, b in enumerate(breakdown)
        ],
        "trend_series": scores,
    }


def _tags_for(b):
    """Build readable tag chips for a single comment row."""
    tags = []
    if b["severe"]:
        tags.append("severe")
    if b["profanity"]:
        tags.append("profanity")
    if b["aggressive"]:
        tags.append("aggressive")
    if b["negative"] > b["positive"]:
        tags.append("negative")
    if b["shouting"]:
        tags.append("shouting")
    if b["positive"] and not b["negative"] and b["score"] < 20:
        tags.append("positive")
    if not tags:
        tags.append("neutral")
    return tags


@app.route("/")
def index():
    """Render the main single page UI."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """Receive comments JSON and return the analysis result."""
    data = request.get_json(silent=True) or {}
    comments = data.get("comments")

    # Accept either a list or a newline separated string
    if isinstance(comments, str):
        comments = comments.splitlines()
    if not isinstance(comments, list):
        return jsonify({"error": "Invalid input. Provide comments as a list or newline string."}), 400

    result = analyze_history(comments)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


if __name__ == "__main__":
    # Run on host 0.0.0.0 and port from environment so Replit can serve it.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
