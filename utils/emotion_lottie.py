"""Utilities to normalize emotion labels and map them to frontend Lottie keys/files.

This module intentionally keeps the mapping small and deterministic. Frontend
lottie assets are expected in `frontend/public/lotties` and named like:
`happy.json`, `sad.json`, `angry.json`, `love.json`, `fearful.json`, `neutral.json`.

Helpers:
- `to_canonical(label)` -> canonical emotion string (one of: happy, sad, angry, love, fearful, neutral)
- `lottie_key(label)` -> canonical key (same as to_canonical)
- `lottie_filename(label, ext='.json')` -> filename for the lottie asset
- `lottie_url(label, base='/public/lotties')` -> URL/path for the frontend asset
"""

from __future__ import annotations

from typing import Optional

CANONICAL = ("happy", "sad", "angry", "love", "fearful", "neutral")

# common synonyms -> canonical
SYNONYMS = {
    "joy": "happy",
    "happiness": "happy",
    "smile": "happy",
    "cheerful": "happy",
    "cheery": "happy",
    "joyful": "happy",
    "delighted": "happy",
    "excited": "happy",
    "positive": "happy",
    "celebration": "happy",
    "depressed": "sad",
    "sorrow": "sad",
    "empathetic": "sad",
    "compassionate": "sad",
    "comforting": "sad",
    "anger": "angry",
    "mad": "angry",
    "frustration": "angry",
    "frustrated": "angry",
    "irritated": "angry",
    "fear": "fearful",
    "afraid": "fearful",
    "scared": "fearful",
    "anxious": "fearful",
    "anxiety": "fearful",
    "nervous": "fearful",
    "like": "love",
    "liked": "love",
    "warm": "love",
    "warmth": "love",
    "affectionate": "love",
    "loving": "love",
    "lovely": "love",
    "affection": "love",
    # handle some misspellings/casing
    "fearful": "fearful",
    "neutral": "neutral",
    "gentle": "neutral",
    "friendly": "neutral",
    "understanding": "neutral",
    "sympathetic": "neutral",
    # Korean tokens (stems to allow substring matching)
    "행복": "happy",
    "기쁘": "happy",
    "고맙": "happy",
    "감사": "happy",
    "슬프": "sad",
    "우울": "sad",
    "눈물": "sad",
    "상처": "sad",
    "화나": "angry",
    "열받": "angry",
    "분노": "angry",
    "짜증": "angry",
    "불쾌": "angry",
    "무서": "fearful",
    "두렵": "fearful",
    "겁": "fearful",
    "공포": "fearful",
    "불안": "fearful",
    "사랑": "love",
    "보고 싶": "love",
    "좋아해": "love",
}


def to_canonical(label: Optional[str]) -> str:
    """Return a canonical emotion label for given free-text label.

    If the input is None or cannot be mapped, returns "neutral".
    """
    if not label or not isinstance(label, str):
        return "neutral"
    l = label.strip().lower()
    if l in CANONICAL:
        return l
    if l in SYNONYMS:
        return SYNONYMS[l]
    # if label contains a canonical token, prefer that
    for token in CANONICAL:
        if token in l:
            return token
    # check synonyms tokens
    for syn, canon in SYNONYMS.items():
        if syn in l:
            return canon
    return "neutral"


def lottie_key(label: Optional[str]) -> str:
    """Return the lottie key (canonical emotion) for given label."""
    return to_canonical(label)


def lottie_filename(label: Optional[str], ext: str = ".json") -> str:
    """Return the lottie filename (e.g. 'happy.json')."""
    key = lottie_key(label)
    return f"{key}{ext}"


def lottie_url(label: Optional[str], base: str = "/public/lotties") -> str:
    """Return the lottie url/path combining base and filename.

    Example: lottie_url('happy') -> '/public/lotties/happy.json'
    """
    base = base.rstrip("/")
    return f"{base}/{lottie_filename(label)}"
