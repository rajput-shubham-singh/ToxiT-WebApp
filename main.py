"""
ToxiTrack AI v3 - Multilingual Conversation Risk Analyzer
==========================================================
- English / Hindi / Hinglish / Roman Hindi toxicity detection
- Single-comment analyzer + Live Chat (per-user) analyzer
- Emotion / Intent / Drift / Aggression / Escalation Chance
- Main Aggressor + Victim Pressure + Mutual Toxicity
- Optional Google Gemini blend (lazy-loaded)
"""

import os
import re
import json
from collections import Counter
from flask import Flask, render_template, request, jsonify

try:
    import google.generativeai as genai

    _GEMINI_AVAILABLE = True
except Exception:
    _GEMINI_AVAILABLE = False

app = Flask(__name__)

# Hardcoded Gemini key — replace with your actual key.
# Leave as-is to use local AI only.
GEMINI_API_KEY = "AIzaSyAllYZnvjO6zmL4r9SxYTWWbm5dCCycAKo"

# ============================================================
# 1. MULTILINGUAL LEXICONS
# ============================================================

# --- ENGLISH ---
EN_SEVERE = {
    "idiot",
    "stupid",
    "dumb",
    "moron",
    "dumbass",
    "loser",
    "trash",
    "garbage",
    "pathetic",
    "worthless",
    "scum",
    "freak",
    "useless",
    "shameful",
    "disgusting",
    "horrible",
    "nasty",
    "asshole",
    "bastard",
    "jerk",
    "fool",
    "ugly",
    "fraud",
    "clown",
    "retard",
    "annoying",
}
EN_PROFANITY = {
    "damn",
    "hell",
    "crap",
    "shut up",
    "screw you",
    "piss off",
    "fuck",
    "shit",
    "bitch",
    "fucking",
    "motherfucker",
}
EN_AGGRESSIVE = {
    "hate",
    "kill",
    "destroy",
    "fight",
    "die",
    "attack",
    "threat",
    "punch",
    "smash",
    "ruin",
    "burn",
}
EN_HATE = {
    "kill yourself",
    "go die",
    "nobody likes you",
    "hate you",
    "you are nothing",
    "piece of trash",
    "get lost",
}
EN_BULLYING = {
    "nobody wants you",
    "tu unwanted",
    "you are unwanted",
    "cry more",
    "attention seeker",
    "embarrassing person",
    "sab tere pe haste hain",
    "everyone laughs at you",
}

# --- HINDI / HINGLISH / ROMAN HINDI ---
HI_ABUSIVE_SEVERE = {
    "madarchod",
    "bhenchod",
    "behenchod",
    "bhanchod",
    "chutiya",
    "chutiye",
    "chutiyaa",
    "chutya",
    "lodu",
    "lawde",
    "lavde",
    "lund",
    "land",
    "gaand",
    "gandu",
    "gaandu",
    "randi",
    "raand",
    "bhosdi",
    "bhosdike",
    "bhosadike",
    "bhosdiwale",
    "bsdk",
    "mkc",
    "bkl",
    "bc",
    "mc",
    "wtf",
    "stfu",
    "jhant",
    "jhantu",
    "jhatu",
}
HI_INSULT_SEVERE = {
    "harami",
    "haraami",
    "kutte",
    "kutta",
    "kutti",
    "sale",
    "saala",
    "saale",
    "kameena",
    "kamina",
    "kameene",
    "kaminey",
    "ghatiya",
    "ghattiya",
    "bakchod",
    "bakchodi",
    "chapri",
}
HI_INSULT_MEDIUM = {
    "pagal",
    "paagal",
    "bewakoof",
    "bewakuf",
    "bevakoof",
    "gadha",
    "gadhe",
    "ulloo",
    "ullu",
    "nikamma",
    "nalayak",
    "nalaayak",
    "bakwas",
    "faltu",
    "faaltu",
    "bekar",
    "bekaar",
    "ghamandi",
    "ghissu",
    "lallu",
    "lalu",
    "dhakkan",
    "tharki",
    "tharak",
    "neech",
    "ganda",
}
HI_AGGRESSIVE = {
    "maar",
    "maarunga",
    "marunga",
    "marungi",
    "peetunga",
    "peetungi",
    "thoko",
    "todunga",
    "phod dunga",
    "phodunga",
    "phorenge",
    "mar ja",
    "jaa ke mar",
    "mar dunga",
}

# Personal-attack patterns (raise score)
HI_ATTACK_PATTERNS = [
    r"\btu\s+\w+\s+hai\b",
    r"\btum\s+\w+\s+ho\b",
    r"\btu\s+kuch\s+nahi\s+hai\b",
    r"\bteri\s+(ma|maa|behen|bahen)\b",
    r"\btere\s+baap\b",
    r"\bchup\s+(reh|kar|raho|baith)\b",
    r"\bdimag\s+(kharab|kharaab)\b",
    r"\bdimaag\s+(kharab|kharaab)\b",
    r"\bbhag\s+ja\b",
    r"\bnikal\s+yaha[a]?\s+se\b",
    r"\bhat\s+ja\b",
    r"\bdafa\s+ho\b",
    r"\baukat\s+me\s+reh\b",
    r"\btere\s+se\s+na\s+ho\s+payega\b",
    r"\bchod\s+na\s+tujhe\b",
]

# Threat patterns
THREAT_MARKERS = [
    r"\bi\s+will\s+(kill|destroy|hurt|find)\b",
    r"\bkill\s+you\b",
    r"\bkill\s+u\b",
    r"\bmaar\s+dunga\b",
    r"\bmaar\s+dungi\b",
    r"\bjaan\s+le\s+lunga\b",
    r"\bdekh\s+lunga\b",
    r"\bdekh\s+lungi\b",
    r"\bdekhta\s+hu\s+tujhe\b",
    r"\btu\s+gaya\b",
    r"\bteri\s+to\b",
    r"\bteri\s+watt\s+laga\s+dunga\b",
    r"\btod\s+dunga\b",
    r"\btod\s+dungi\b",
    r"\bpit\s+dunga\b",
    r"\bghar\s+aa\b",
    r"\bmil\s+tu\b",
    r"\bwait\s+outside\b",
    r"\bdekh\s+lena\b",
]

# Passive-aggressive / sarcasm patterns
PASSIVE_AGG_PATTERNS = [
    r"\bwah\s+kya\s+genius\b",
    r"\bgreat\s+job\s+(idiot|stupid|moron)\b",
    r"\bclap\s+for\s+(yourself|urself)\b",
    r"\btu\s+rehne\s+de\b",
    r"\bsmart\s+ban\s+raha\s+hai\b",
    r"\bhaan\s+haan\s+tu\s+hi\s+sahi\b",
    r"\bwow\s+amazing\s+stupidity\b",
]

SARCASM_MARKERS = [
    r"\bwow\s+great\b",
    r"\boh\s+really\b",
    r"\bso\s+smart\b",
    r"\bkitna\s+intelligent\b",
    r"\bhaan\s+haan\b",
    r"\bjaroor\b.*\?",
    r"\bzaroor\b.*\?",
    r"/s$",
    r"\\\\s$",
]

# Bullying / humiliation patterns
BULLY_PATTERNS = [
    r"\bsab\s+tere\s+pe\s+haste\b",
    r"\bnobody\s+(likes|wants)\s+you\b",
    r"\btu\s+(loser|unwanted)\b",
    r"\btu\s+kuch\s+nahi\s+hai\b",
    r"\bcry\s+more\b",
]

# Apology / de-escalation markers (downweight conflict)
APOLOGY_MARKERS = [
    r"\bsorry\b",
    r"\bmaaf\s+(kar|karo|karna)\b",
    r"\bmera\s+(matlab|intent)\b",
    r"\bgussa\s+tha\b",
    r"\bcalm\s+down\b",
    r"\bshanti\b",
    r"\bbhul\s+ja\b",
    r"\bmy\s+bad\b",
    r"\bapologi[zs]e\b",
]

# Playful / positive offsets
PLAYFUL_PATTERNS = [
    r"\b\w+\s+level\s+(funny|cool|awesome|amazing|hilarious|mast|great|epic)\b",
    r"\bhaha+\b",
    r"\blol\b",
    r"\blmao\b",
    r"\brofl\b",
    r"\bkya\s+baat\b",
    r"\bwah+\b",
    r"\bshabaash\b",
    r"\bshabash\b",
    r"\bmast\b",
    r"\bzabardast\b",
    r"\bbahut\s+accha\b",
    r"\bbahut\s+badhiya\b",
    r"\bbadhiya\b",
    r"\bjokingly\b",
    r"\bjk\b",
    r"\bjust\s+kidding\b",
]

POSITIVE = {
    "good",
    "great",
    "love",
    "nice",
    "awesome",
    "amazing",
    "cool",
    "wonderful",
    "fantastic",
    "excellent",
    "thanks",
    "thank you",
    "appreciate",
    "kind",
    "happy",
    "best",
    "brilliant",
    "lovely",
    "respect",
    "agree",
    "supportive",
    "helpful",
    "accha",
    "achha",
    "achcha",
    "badhiya",
    "mast",
    "shandaar",
    "shabaash",
    "shabash",
    "wah",
    "zabardast",
    "kamaal",
    "pyaara",
    "pyara",
    "dhanyavaad",
    "shukriya",
}

QUESTION_TONE = [
    r"\?\s*$",
    r"\bkya\b\s+\w+\s+(hai|ho)\s*\?",
    r"\bho\s+kya\b",
]


# ============================================================
# 2. REWRITE / SAFE REPLY MAPS
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
    "nobody likes you": "Let's try to be more inclusive.",
    "kill yourself": "Please be respectful — that kind of language isn't okay.",
    "stupid": "unconvincing",
    "idiot": "person",
    "trash": "weak",
}

SAFE_REPLY_BANK = {
    "anger": "Take a breath - let's keep the conversation respectful.",
    "sarcasm": "I want to make sure I'm reading you right - can you clarify?",
    "mockery": "Let's discuss this without targeting anyone personally.",
    "bullying": "Everyone here deserves to feel safe. Let's reset the tone.",
    "threat": "Threats aren't acceptable - this conversation will be reviewed.",
    "hate": "Let's keep the discussion focused on ideas, not attacks.",
    "frustration": "I hear you - what's the underlying concern?",
    "playful": "Glad you're enjoying it!",
    "neutral": "Thanks for sharing your thoughts.",
}


# ============================================================
# 3. CORE HELPERS
# ============================================================

ALL_TOXIC_WORDS = (
    HI_ABUSIVE_SEVERE
    | HI_INSULT_SEVERE
    | HI_INSULT_MEDIUM
    | HI_AGGRESSIVE
    | EN_SEVERE
    | EN_PROFANITY
    | EN_AGGRESSIVE
    | EN_HATE
    | EN_BULLYING
)


def tokenize(text: str):
    return re.findall(r"[a-zA-Z\u0900-\u097F']+", text.lower())


def count_phrases(text_lower: str, phrases):
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
    return bool(re.search(r"[\U0001F600-\U0001F64F]|😂|🤣|😅|😆|😜|😝|😛|🤪|❤|♥", text))


def find_toxic_words(text: str):
    """Return list of toxic substrings found in original casing."""
    text_lower = text.lower()
    found = []
    seen = set()
    for word in ALL_TOXIC_WORDS:
        wl = word.lower()
        if " " in wl:
            start = 0
            while True:
                i = text_lower.find(wl, start)
                if i == -1:
                    break
                snippet = text[i : i + len(wl)]
                if snippet.lower() not in seen:
                    found.append(snippet)
                    seen.add(snippet.lower())
                start = i + len(wl)
        else:
            for m in re.finditer(r"\b" + re.escape(wl) + r"\b", text_lower):
                snippet = text[m.start() : m.end()]
                if snippet.lower() not in seen:
                    found.append(snippet)
                    seen.add(snippet.lower())
    return found


# ============================================================
# 4. PER-COMMENT SCORING
# ============================================================


def score_single_comment(
    comment: str, sensitivity: str = "medium", strict: bool = False
):
    text_lower = comment.lower()
    tokens = tokenize(comment)
    word_count = max(1, len(tokens))

    en_severe = count_phrases(text_lower, EN_SEVERE)
    en_profanity = count_phrases(text_lower, EN_PROFANITY)
    en_aggressive = count_phrases(text_lower, EN_AGGRESSIVE)
    en_hate = count_phrases(text_lower, EN_HATE)
    en_bullying = count_phrases(text_lower, EN_BULLYING)

    hi_abusive = count_phrases(text_lower, HI_ABUSIVE_SEVERE)
    hi_severe = count_phrases(text_lower, HI_INSULT_SEVERE)
    hi_medium = count_phrases(text_lower, HI_INSULT_MEDIUM)
    hi_aggro = count_phrases(text_lower, HI_AGGRESSIVE)

    # Smart context: bc/mc/wtf/stfu used as filler ("bc yaar net slow hai")
    # are downweighted unless paired with attack/insult/threat context.
    casual_filler_hits = len(re.findall(r"\b(bc|mc|wtf|stfu)\b", text_lower))
    if casual_filler_hits:
        has_attack_context = (
            count_pattern_hits(text_lower, HI_ATTACK_PATTERNS)
            + count_pattern_hits(text_lower, THREAT_MARKERS)
            + count_pattern_hits(text_lower, BULLY_PATTERNS)
            + count_phrases(text_lower, HI_INSULT_SEVERE)
            + count_phrases(text_lower, HI_INSULT_MEDIUM)
            + count_phrases(text_lower, EN_SEVERE)
            + count_phrases(text_lower, EN_HATE)
            + count_phrases(text_lower, HI_AGGRESSIVE)
        ) > 0
        if not has_attack_context:
            # treat fillers as casual venting, not personal attack
            hi_abusive = max(0, hi_abusive - casual_filler_hits)

    positive = count_phrases(text_lower, POSITIVE)

    attack_hits = count_pattern_hits(text_lower, HI_ATTACK_PATTERNS)
    playful_hits = count_pattern_hits(text_lower, PLAYFUL_PATTERNS)
    sarcasm_hits = count_pattern_hits(text_lower, SARCASM_MARKERS)
    passive_agg_hits = count_pattern_hits(text_lower, PASSIVE_AGG_PATTERNS)
    threat_hits = count_pattern_hits(text_lower, THREAT_MARKERS)
    bully_hits = count_pattern_hits(text_lower, BULLY_PATTERNS)
    apology_hits = count_pattern_hits(text_lower, APOLOGY_MARKERS)
    question_hits = count_pattern_hits(text_lower, QUESTION_TONE)
    emoji_playful = has_emoji(comment)

    shout_words = sum(
        1
        for t in tokens
        if len(t) >= 4 and t.upper() == t and re.match(r"^[a-z']+$", t.lower())
    )
    caps_ratio = shout_words / word_count
    excess_exclaim = max(0, comment.count("!") - 1)

    hindi_mult = {"low": 0.6, "medium": 1.0, "high": 1.5}.get(sensitivity, 1.0)
    strict_bonus = 1.25 if strict else 1.0

    raw = (
        hi_abusive * 32
        + hi_severe * 22
        + hi_medium * 11 * hindi_mult
        + hi_aggro * 18
        + en_severe * 18
        + en_profanity * 14
        + en_aggressive * 12
        + en_hate * 30
        + en_bullying * 18
        + attack_hits * 14
        + threat_hits * 24
        + bully_hits * 16
        + passive_agg_hits * 12
        + sarcasm_hits * 6
        + excess_exclaim * 3
        + caps_ratio * 22
        - positive * 7
        - playful_hits * 14
        - apology_hits * 16
        - (10 if emoji_playful and hi_abusive == 0 and hi_severe == 0 else 0)
        - question_hits * 4
    )

    score = int(max(0, min(100, raw * strict_bonus)))

    emotion, intent, reason = classify_emotion_intent(
        score=score,
        hi_abusive=hi_abusive,
        hi_severe=hi_severe,
        hi_medium=hi_medium,
        en_severe=en_severe,
        en_profanity=en_profanity,
        en_hate=en_hate,
        attack_hits=attack_hits,
        threat_hits=threat_hits,
        sarcasm_hits=sarcasm_hits,
        passive_agg_hits=passive_agg_hits,
        bully_hits=bully_hits,
        apology_hits=apology_hits,
        playful_hits=playful_hits,
        emoji_playful=emoji_playful,
        positive=positive,
        caps_ratio=caps_ratio,
        excess_exclaim=excess_exclaim,
        aggressive=hi_aggro + en_aggressive,
    )

    return {
        "comment": comment,
        "score": score,
        "emotion": emotion,
        "intent": intent,
        "reason": reason,
        "toxic_words": find_toxic_words(comment),
        "signals": {
            "abusive": hi_abusive,
            "severe": hi_severe + en_severe,
            "profanity": en_profanity,
            "aggressive": hi_aggro + en_aggressive,
            "hate": en_hate,
            "bullying": en_bullying + bully_hits,
            "attack": attack_hits,
            "threat": threat_hits,
            "sarcasm": sarcasm_hits,
            "passive_aggressive": passive_agg_hits,
            "apology": apology_hits,
            "playful": playful_hits,
            "shouting": shout_words,
            "positive": positive,
            "emoji_playful": int(emoji_playful),
        },
    }


def classify_emotion_intent(**s):
    score = s["score"]
    hi_abusive, hi_severe = s["hi_abusive"], s["hi_severe"]
    en_severe = s["en_severe"]
    en_hate = s["en_hate"]
    attack_hits = s["attack_hits"]
    threat_hits = s["threat_hits"]
    sarcasm_hits = s["sarcasm_hits"]
    passive_agg_hits = s["passive_agg_hits"]
    bully_hits = s["bully_hits"]
    apology_hits = s["apology_hits"]
    playful_hits = s["playful_hits"]
    emoji_playful = s["emoji_playful"]
    caps_ratio, excess_exclaim = s["caps_ratio"], s["excess_exclaim"]
    positive = s["positive"]

    if threat_hits >= 1:
        return "Threat", "threat", "Threatening language detected."
    if en_hate >= 1:
        return "Angry", "hate", "Hate-speech phrase detected."
    if hi_abusive >= 1:
        return "Angry", "bullying", "Severe abusive Hindi/Hinglish phrase detected."
    if bully_hits >= 1:
        return "Angry", "bullying", "Bullying / humiliation pattern detected."
    if apology_hits >= 1 and score < 40:
        return "Calm", "supportive", "Apologetic / de-escalating tone."
    if (hi_severe + en_severe) >= 2 or (
        attack_hits >= 1 and (hi_severe + en_severe + s["hi_medium"]) >= 1
    ):
        return "Angry", "bullying", "Multiple insults targeting a person."
    if passive_agg_hits >= 1:
        return "Sarcastic", "mockery", "Passive-aggressive tone detected."
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
# 5. REWRITE / SAFE REPLY
# ============================================================


def rewrite_toxic(comment: str) -> str:
    text = comment
    lower = text.lower()
    for bad, good in REWRITE_MAP.items():
        if " " in bad and bad in lower:
            return good
    new_words = []
    for w in re.findall(r"\S+|\s+", text):
        bare = re.sub(r"[^\w\u0900-\u097F]", "", w).lower()
        if bare in REWRITE_MAP and " " not in REWRITE_MAP[bare]:
            new_words.append(
                w.replace(re.search(r"\w+", w).group(), REWRITE_MAP[bare], 1)
            )
        else:
            new_words.append(w)
    rewritten = "".join(new_words)
    if rewritten.lower() == text.lower():
        return "I see this differently — let's discuss it respectfully."
    return rewritten


def safe_reply_for(emotion: str) -> str:
    key = emotion.lower()
    mapping = {
        "angry": "anger",
        "threat": "threat",
        "sarcastic": "sarcasm",
        "negative": "frustration",
        "frustrated": "frustration",
        "playful": "playful",
        "positive": "neutral",
        "calm": "neutral",
        "neutral": "neutral",
    }
    return SAFE_REPLY_BANK.get(mapping.get(key, "neutral"), SAFE_REPLY_BANK["neutral"])


# ============================================================
# 6. AGGREGATE METRICS
# ============================================================


def _signal_total(breakdown, key):
    return sum(b["signals"].get(key, 0) for b in breakdown)


def aggression_score_for(breakdown):
    n = max(1, len(breakdown))
    raw = (
        _signal_total(breakdown, "threat") * 30
        + _signal_total(breakdown, "attack") * 16
        + _signal_total(breakdown, "aggressive") * 12
        + _signal_total(breakdown, "abusive") * 22
        + _signal_total(breakdown, "shouting") * 5
        + _signal_total(breakdown, "bullying") * 14
        + _signal_total(breakdown, "hate") * 26
    ) / n
    return int(max(0, min(100, raw)))


def escalation_chance_for(breakdown, drift_score, threat_count):
    scores = [b["score"] for b in breakdown]
    if len(scores) < 2:
        delta = 0
    else:
        mid = max(1, len(scores) // 2)
        early = sum(scores[:mid]) / mid
        recent = sum(scores[mid:]) / max(1, len(scores) - mid)
        delta = recent - early
    raw = drift_score * 0.5 + max(0, delta) * 1.5 + threat_count * 18
    if recent_max := max(scores[-3:] if len(scores) >= 3 else scores):
        raw += max(0, recent_max - 50) * 0.4
    return int(max(0, min(100, raw)))


def threat_level_for(breakdown):
    threats = _signal_total(breakdown, "threat")
    abusive = _signal_total(breakdown, "abusive")
    attacks = _signal_total(breakdown, "attack")
    if threats >= 2 or (threats >= 1 and abusive >= 1):
        return "HIGH"
    if threats >= 1 or attacks >= 3:
        return "MEDIUM"
    if attacks >= 1 or abusive >= 1:
        return "LOW"
    return "NONE"


def final_label_for(toxicity, drift_score, aggression, threats):
    composite = toxicity * 0.5 + aggression * 0.3 + drift_score * 0.2
    if threats >= 2 or composite >= 80:
        return "Critical Risk"
    if composite >= 60 or threats >= 1:
        return "High Risk"
    if composite >= 40:
        return "Moderate Risk"
    if composite >= 22:
        return "Slightly Risky"
    return "Safe"


# ============================================================
# 7. AGGREGATE ANALYSIS
# ============================================================


def analyze_history(
    comments, sensitivity="medium", strict=False, use_gemini=False, gemini_key=None
):
    cleaned = [c.strip() for c in comments if c and c.strip()]
    if not cleaned:
        return {"error": "Please enter at least one comment."}

    gemini_result = None
    used_engine = "Local AI"
    effective_key = (
        gemini_key
        or os.environ.get("GEMINI_API_KEY")
        or (GEMINI_API_KEY if GEMINI_API_KEY != "PASTE_KEY_HERE" else None)
    )
    if use_gemini and _GEMINI_AVAILABLE and effective_key:
        gemini_result = analyze_with_gemini(cleaned, api_key=effective_key)
        if gemini_result:
            used_engine = "Gemini"

    breakdown = [score_single_comment(c, sensitivity, strict) for c in cleaned]

    if gemini_result:
        for i, item in enumerate(breakdown):
            if i < len(gemini_result.get("comments", [])):
                g = gemini_result["comments"][i]
                item["score"] = int(
                    item["score"] * 0.4 + g.get("score", item["score"]) * 0.6
                )
                item["emotion"] = g.get("emotion", item["emotion"])
                item["intent"] = g.get("intent", item["intent"])
                item["reason"] = g.get("reason", item["reason"])

    scores = [b["score"] for b in breakdown]
    toxicity_score = int(sum(scores) / len(scores))

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

    threat_count = _signal_total(breakdown, "threat")
    aggression_score = aggression_score_for(breakdown)
    escalation_chance = escalation_chance_for(breakdown, drift_score, threat_count)
    threat_level = threat_level_for(breakdown)
    final_label = final_label_for(
        toxicity_score, drift_score, aggression_score, threat_count
    )

    total = {
        k: _signal_total(breakdown, k)
        for k in [
            "abusive",
            "severe",
            "profanity",
            "aggressive",
            "hate",
            "bullying",
            "attack",
            "threat",
            "sarcasm",
            "playful",
            "shouting",
            "positive",
            "passive_aggressive",
            "apology",
        ]
    }

    emotions = [b["emotion"] for b in breakdown]
    intents = [b["intent"] for b in breakdown]
    dominant_emotion = max(set(emotions), key=emotions.count)
    dominant_intent = max(set(intents), key=intents.count)

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

    signal_density = sum(total.values()) / max(1, len(cleaned))
    confidence = int(min(98, 55 + signal_density * 6 + min(20, len(cleaned) * 2)))

    community_health = max(
        0,
        min(
            100,
            int(
                100
                - (toxicity_score * 0.55 + aggression_score * 0.25 + drift_score * 0.2)
            ),
        ),
    )

    explanations = []
    if drift_type == "Rapid Escalation":
        explanations.append("Rapid escalation pattern detected across the timeline.")
    elif drift_type == "Slowly Negative":
        explanations.append("Conversation is slowly drifting toward negativity.")
    elif drift_type == "Recovery":
        explanations.append("User is de-escalating - tone is improving over time.")
    else:
        explanations.append("Tone has remained relatively stable.")

    if total["threat"] >= 1:
        explanations.append("Threatening language detected - escalate immediately.")
    if total["abusive"] >= 1:
        explanations.append(
            f"Detected {total['abusive']} severe abusive Hindi/Hinglish phrase(s)."
        )
    if total["hate"] >= 1:
        explanations.append("Hate-speech phrasing detected.")
    if total["attack"] >= 1:
        explanations.append(
            "Personal attack patterns detected (e.g. 'tu ... hai', 'chup reh')."
        )
    if total["bullying"] >= 1:
        explanations.append("Bullying / humiliation patterns detected.")
    if total["passive_aggressive"] >= 1:
        explanations.append("Passive-aggressive tone detected.")
    if total["severe"] >= 2:
        explanations.append(
            f"Multiple severe insults across comments ({total['severe']} hits)."
        )
    if total["sarcasm"] >= 2:
        explanations.append("Recurrent sarcastic / mocking tone.")
    if total["shouting"] >= 2:
        explanations.append("Repeated shouting (ALL CAPS) suggests heightened emotion.")
    if total["apology"] >= 1:
        explanations.append("Apology / de-escalation phrase detected.")
    if total["playful"] >= 2 and total["abusive"] == 0:
        explanations.append("Predominantly playful tone - low actual hostility.")

    rows = []
    for i, b in enumerate(breakdown):
        rewrite = rewrite_toxic(b["comment"]) if b["score"] >= 40 else None
        rows.append(
            {
                "index": i + 1,
                "comment": b["comment"],
                "score": b["score"],
                "emotion": b["emotion"],
                "intent": b["intent"],
                "reason": b["reason"],
                "tags": _tags_for(b),
                "toxic_words": b["toxic_words"],
                "rewrite": rewrite,
            }
        )

    riskiest = max(breakdown, key=lambda x: x["score"])
    safe_reply = safe_reply_for(riskiest["emotion"])
    rewrite_top = (
        rewrite_toxic(riskiest["comment"]) if riskiest["score"] >= 40 else None
    )

    return {
        "engine": used_engine,
        "toxicity_score": toxicity_score,
        "drift_score": drift_score,
        "drift_type": drift_type,
        "trend_label": trend_label,
        "aggression_score": aggression_score,
        "escalation_chance": escalation_chance,
        "threat_level": threat_level,
        "final_label": final_label,
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
    if s["threat"]:
        tags.append("threat")
    if s["abusive"]:
        tags.append("abusive")
    if s["hate"]:
        tags.append("hate")
    if s["severe"]:
        tags.append("severe")
    if s["bullying"]:
        tags.append("bullying")
    if s["profanity"]:
        tags.append("profanity")
    if s["aggressive"]:
        tags.append("aggressive")
    if s["attack"]:
        tags.append("attack")
    if s["passive_aggressive"]:
        tags.append("passive-agg")
    if s["sarcasm"]:
        tags.append("sarcasm")
    if s["shouting"]:
        tags.append("shouting")
    if s["apology"]:
        tags.append("apology")
    if s["playful"]:
        tags.append("playful")
    if s["positive"] and not (s["abusive"] or s["severe"]):
        tags.append("positive")
    if not tags:
        tags.append("neutral")
    return tags


# ============================================================
# 8. CHAT (MULTI-USER) ANALYSIS
# ============================================================


def analyze_chat(
    messages, sensitivity="medium", strict=False, use_gemini=False, gemini_key=None
):
    """messages = [{user, text}, ...]"""
    cleaned = [m for m in messages if m.get("text", "").strip()]
    if not cleaned:
        return {"error": "Please add at least one message."}

    texts = [m["text"].strip() for m in cleaned]
    base = analyze_history(
        texts,
        sensitivity=sensitivity,
        strict=strict,
        use_gemini=use_gemini,
        gemini_key=gemini_key,
    )
    if "error" in base:
        return base

    # Stamp each row with its user
    for i, row in enumerate(base["breakdown"]):
        row["user"] = cleaned[i].get("user", f"User{(i % 2) + 1}")

    # Per-user aggregates
    per_user = {}
    for row in base["breakdown"]:
        u = row["user"]
        if u not in per_user:
            per_user[u] = {
                "user": u,
                "messages": 0,
                "scores": [],
                "threats": 0,
                "abusive": 0,
                "attacks": 0,
                "apologies": 0,
                "bullying": 0,
            }
        per_user[u]["messages"] += 1
        per_user[u]["scores"].append(row["score"])

    # Re-derive per-user signals from local breakdown (uses raw signals before Gemini blend)
    raw_breakdown = [score_single_comment(t, sensitivity, strict) for t in texts]
    for i, b in enumerate(raw_breakdown):
        u = cleaned[i].get("user", f"User{(i % 2) + 1}")
        per_user[u]["threats"] += b["signals"]["threat"]
        per_user[u]["abusive"] += b["signals"]["abusive"]
        per_user[u]["attacks"] += b["signals"]["attack"]
        per_user[u]["apologies"] += b["signals"]["apology"]
        per_user[u]["bullying"] += b["signals"]["bullying"]

    user_summaries = []
    for u, data in per_user.items():
        avg = int(sum(data["scores"]) / max(1, len(data["scores"])))
        peak = max(data["scores"]) if data["scores"] else 0
        user_summaries.append(
            {
                "user": u,
                "messages": data["messages"],
                "avg_score": avg,
                "peak_score": peak,
                "threats": data["threats"],
                "abusive": data["abusive"],
                "attacks": data["attacks"],
                "apologies": data["apologies"],
                "bullying": data["bullying"],
            }
        )
    user_summaries.sort(key=lambda x: x["avg_score"], reverse=True)

    # Main aggressor / victim pressure / mutual toxicity
    main_aggressor = "None"
    victim_pressure = "Low"
    mutual_toxicity = 0

    if len(user_summaries) >= 2:
        top, second = user_summaries[0], user_summaries[1]
        gap = top["avg_score"] - second["avg_score"]
        max_score = max(top["avg_score"], 1)
        mutual_toxicity = int(
            min(top["avg_score"], second["avg_score"]) / max_score * 100
        )

        if top["avg_score"] < 22 and second["avg_score"] < 22:
            main_aggressor = "None"
        elif gap < 10 and top["avg_score"] >= 30 and second["avg_score"] >= 30:
            main_aggressor = "Both"
        elif gap >= 10:
            main_aggressor = top["user"]
        elif top["avg_score"] >= 35:
            main_aggressor = top["user"]
        else:
            main_aggressor = "None"

        # Victim pressure = attacks received by the lower-scoring user
        attacks_received = top["attacks"] + top["threats"] + top["bullying"]
        if attacks_received >= 4 or top["threats"] >= 1:
            victim_pressure = "High"
        elif attacks_received >= 2:
            victim_pressure = "Medium"
        else:
            victim_pressure = "Low"
    elif user_summaries:
        only = user_summaries[0]
        if only["avg_score"] >= 40:
            main_aggressor = only["user"]
            victim_pressure = "Medium"

    # Conversation pattern flags
    patterns = []
    all_threats = sum(u["threats"] for u in user_summaries)
    all_apologies = sum(u["apologies"] for u in user_summaries)
    if base["drift_type"] == "Rapid Escalation":
        patterns.append("Rapid escalation")
    if main_aggressor == "Both":
        patterns.append("Mutual fighting")
    if all_threats >= 1:
        patterns.append("Threat language")
    if all_apologies >= 1:
        patterns.append("Apology / de-escalation")
    if any(u["bullying"] >= 1 for u in user_summaries):
        patterns.append("Bullying / humiliation")
    repeated = sum(1 for r in base["breakdown"] if r["score"] >= 40)
    if repeated >= 3:
        patterns.append("Repeated insults")

    base.update(
        {
            "mode": "chat",
            "user_summaries": user_summaries,
            "main_aggressor": main_aggressor,
            "victim_pressure": victim_pressure,
            "mutual_toxicity": mutual_toxicity,
            "patterns": patterns,
        }
    )
    return base


# ============================================================
# 9. OPTIONAL GEMINI MODE
# ============================================================

GEMINI_PROMPT = """You are a multilingual toxicity classifier for English, Hindi,
Hinglish and Roman Hindi comments. For EACH comment in the JSON list below,
return a JSON object with these exact keys:
  - score (0-100 toxicity score)
  - emotion (one of: Neutral, Positive, Playful, Frustrated, Negative, Sarcastic, Angry, Threat, Calm)
  - intent (one of: neutral, supportive, playful, frustration, mockery, anger, bullying, threat, hate)
  - reason (one short English sentence)
Return ONLY a JSON object: {"comments": [ ... ]} - no prose, no markdown.
Comments:
"""


def analyze_with_gemini(comments, api_key=None):
    try:
        api_key = api_key or GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        payload = json.dumps(comments, ensure_ascii=False)
        resp = model.generate_content(GEMINI_PROMPT + payload)
        text = (resp.text or "").strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("comments"), list):
            return data
    except Exception:
        return None
    return None


# ============================================================
# 10. ROUTES
# ============================================================


@app.route("/")
def index():
    # Engine is "ready" if the lib is installed; user can paste a key from the UI.
    gemini_ready = bool(_GEMINI_AVAILABLE)
    env_key_set = (
        bool(os.environ.get("GEMINI_API_KEY")) or GEMINI_API_KEY != "PASTE_KEY_HERE"
    )
    return render_template(
        "index.html", gemini_ready=gemini_ready, env_key_set=env_key_set
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    comments = data.get("comments")
    sensitivity = (data.get("sensitivity") or "medium").lower()
    strict = bool(data.get("strict"))
    _key_available = (
        bool(os.environ.get("GEMINI_API_KEY")) or GEMINI_API_KEY != "PASTE_KEY_HERE"
    )
    use_gemini = data.get("use_gemini", _key_available)
    gemini_key = (data.get("gemini_key") or "").strip() or None

    if isinstance(comments, str):
        comments = comments.splitlines()
    if not isinstance(comments, list):
        return jsonify(
            {"error": "Invalid input. Provide comments as a list or string."}
        ), 400

    result = analyze_history(
        comments,
        sensitivity=sensitivity,
        strict=strict,
        use_gemini=use_gemini,
        gemini_key=gemini_key,
    )
    if "error" in result:
        return jsonify(result), 400
    result["mode"] = "single"
    return jsonify(result)


@app.route("/analyze_chat", methods=["POST"])
def analyze_chat_route():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages")
    sensitivity = (data.get("sensitivity") or "medium").lower()
    strict = bool(data.get("strict"))
    _key_available = (
        bool(os.environ.get("GEMINI_API_KEY")) or GEMINI_API_KEY != "PASTE_KEY_HERE"
    )
    use_gemini = data.get("use_gemini", _key_available)
    gemini_key = (data.get("gemini_key") or "").strip() or None

    if not isinstance(messages, list):
        return jsonify(
            {"error": "Invalid input. Provide a list of {user, text} messages."}
        ), 400

    result = analyze_chat(
        messages,
        sensitivity=sensitivity,
        strict=strict,
        use_gemini=use_gemini,
        gemini_key=gemini_key,
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/status")
def status():
    return jsonify(
        {
            "gemini_available": _GEMINI_AVAILABLE,
            "gemini_key_set": bool(os.environ.get("GEMINI_API_KEY"))
            or GEMINI_API_KEY != "PASTE_KEY_HERE",
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
