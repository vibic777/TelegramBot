"""Keyword routing for the character emotion sticker set."""

from __future__ import annotations

import re

EMOTION_LABELS = {
    "sad": "Грустное",
    "happy": "Счастливое",
    "angry": "Злое",
    "aggressive": "Агрессивное",
    "kind": "Доброе",
    "joyful": "Радостное",
    "sorrowful": "Печальное",
    "tongue_out": "Показывает язык",
}

_PATTERNS = (
    ("tongue_out", re.compile(r"язык\w*(?:\s+\w+){0,2}\s+показыва\w*|показыва\w*(?:\s+\w+){0,2}\s+язык\w*|высун\w*.{0,12}язык|язык.{0,12}высун\w*|дразн\w*|tongue.{0,18}(?:out|stick)|stick.{0,18}tongue|show\w*\s+(?:the\s+)?tongue|tongue-out", re.I)),
    ("aggressive", re.compile(r"агрессив\w*|ярост\w*|бешен\w*|aggress\w*|furious|rage|berserk", re.I)),
    ("angry", re.compile(r"зл\w*|сердит\w*|гнев\w*|angry|anger|mad", re.I)),
    ("sorrowful", re.compile(r"печаль\w*|скорб\w*|тоск\w*|sorrowful|melanchol\w*", re.I)),
    ("sad", re.compile(r"груст\w*|уныл\w*|sad(?:ness)?", re.I)),
    ("happy", re.compile(r"счастлив\w*|happy|happier|happiness", re.I)),
    ("kind", re.compile(r"добр\w*|ласков\w*|нежн\w*|kind|gentle|tender", re.I)),
    ("joyful", re.compile(r"радост\w*|весел\w*|ликующ\w*|joy(?:ful)?|cheerful", re.I)),
)

EMOJI_REQUEST_PATTERN = re.compile(r"(?<![а-яa-z])(?:эмодзи|emoji|эмоци\w*)(?![а-яa-z])", re.I)


def requested_emotion(text: str) -> str | None:
    normalized = text.casefold().replace("ё", "е")
    return next((emotion for emotion, pattern in _PATTERNS if pattern.search(normalized)), None)


def requests_emotion_emoji(text: str) -> bool:
    return bool(EMOJI_REQUEST_PATTERN.search(text.casefold().replace("ё", "е")))
