from __future__ import annotations

import re

DEFAULT_KEYWORDS = ["급등"]

DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b"),
    re.compile(r"\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b"),
    re.compile(r"\b\d{1,2}\s*월\s*\d{1,2}\s*일\b"),
]


def contains_date_keyword(title: str) -> bool:
    return any(p.search(title) for p in DATE_PATTERNS)


def match_title(title: str, keywords: list[str]) -> bool:
    normalized_title = title or ""
    return contains_date_keyword(normalized_title) or any(k in normalized_title for k in keywords)
