from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .krx_mapper import map_to_ticker, normalize_name

SEQUENCE_PATTERNS: dict[str, re.Pattern[str]] = {
    "first_stock": re.compile(r"(첫\s*번째\s*종목|첫번째\s*종목|첫째\s*종목|첫\s*종목)"),
    "second_stock": re.compile(r"(두\s*번째\s*종목|두번째\s*종목|둘째\s*종목|두\s*번째는|두번째는)"),
    "third_stock": re.compile(r"(세\s*번째\s*종목|세번째\s*종목|셋째\s*종목|마지막\s*종목|마지막으로)"),
    "next_stock": re.compile(r"(다음\s*종목|다음으로\s*볼\s*종목)"),
}

RECOMMENDATION_TITLE_HINTS = ("급등", "상한가", "추천", "유력", "임박", "3종목", "종목 공개")
EXPLANATION_HINTS = ("이유", "포인트", "실적", "수급", "차트", "매출", "모멘텀")
DISCLAIMER_HINTS = ("광고", "텔레그램", "구독", "좋아요", "유료", "리딩")
THEME_WORDS = {
    normalize_name(w)
    for w in (
        "로봇관련주",
        "원전",
        "우주항공",
        "바이오",
        "AI",
        "반도체",
        "전고체",
        "유리기판",
        "STO",
        "스테이블코인",
        "2차전지",
        "대장주",
    )
}


@dataclass
class InferredRecommendation:
    rec_rank: int
    stock_name: str
    ticker: str | None
    market: str | None
    confidence: str
    method: str
    evidence_text: str
    evidence_start_sec: float | None
    evidence_end_sec: float | None
    source_segment_label: str


@dataclass
class TranscriptLine:
    text: str
    start_sec: float | None


@dataclass
class Section:
    label: str
    rank: int
    start_idx: int
    end_idx: int
    has_marker: bool


def classify_recommendation_video(title: str) -> tuple[bool, int]:
    text = title or ""
    is_candidate = any(h in text for h in RECOMMENDATION_TITLE_HINTS)
    expected_count = 3 if "3종목" in text else 0
    top_match = re.search(r"(?:TOP|Top|top|베스트|BEST)\s*(\d)", text)
    if top_match:
        expected_count = int(top_match.group(1))
    return is_candidate, expected_count


def _parse_ts(chunk: str) -> float | None:
    m = re.match(r"\[?(\d{1,2}):(\d{2})(?::(\d{2}))?\]?", chunk)
    if not m:
        return None
    hh = 0
    mm = int(m.group(1))
    ss = int(m.group(2))
    if m.group(3) is not None:
        hh = mm
        mm = ss
        ss = int(m.group(3))
    return float(hh * 3600 + mm * 60 + ss)


def split_transcript_lines(transcript_text: str | None) -> list[TranscriptLine]:
    if not transcript_text:
        return []
    raw_lines = [x.strip() for x in re.split(r"\n+", transcript_text) if x.strip()]
    out: list[TranscriptLine] = []
    for line in raw_lines:
        ts = None
        ts_match = re.match(r"^\[?\d{1,2}:\d{2}(?::\d{2})?\]?", line)
        body = line
        if ts_match:
            ts = _parse_ts(ts_match.group(0))
            body = line[ts_match.end() :].strip(" -")
        out.append(TranscriptLine(text=body, start_sec=ts))
    return out


def detect_sequence_markers(lines: list[TranscriptLine]) -> list[tuple[int, str]]:
    markers: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        for label, pattern in SEQUENCE_PATTERNS.items():
            if pattern.search(line.text):
                markers.append((i, label))
                break
    return markers


def build_sections(lines: list[TranscriptLine], expected_count: int = 3) -> list[Section]:
    markers = detect_sequence_markers(lines)
    ranked_labels = ["first_stock", "second_stock", "third_stock"]
    ranked_markers = [(i, lbl) for i, lbl in markers if lbl in ranked_labels]
    if ranked_markers:
        sections: list[Section] = []
        for idx, (start_idx, label) in enumerate(ranked_markers[: max(expected_count, 1)]):
            end_idx = (ranked_markers[idx + 1][0] - 1) if idx + 1 < len(ranked_markers) else (len(lines) - 1)
            rank = ranked_labels.index(label) + 1
            sections.append(Section(label=label, rank=rank, start_idx=start_idx, end_idx=max(start_idx, end_idx), has_marker=True))
        return sections

    if not lines:
        return []

    section_count = expected_count or 3
    span = max(1, len(lines) // section_count)
    coarse: list[Section] = []
    for i in range(section_count):
        start_idx = i * span
        end_idx = len(lines) - 1 if i == section_count - 1 else min(len(lines) - 1, ((i + 1) * span) - 1)
        coarse.append(Section(label=f"fallback_{i + 1}", rank=i + 1, start_idx=start_idx, end_idx=end_idx, has_marker=False))
    return coarse


def _clean_candidate_token(token: str) -> str:
    cleaned = token.strip()
    for suf in ("입니다", "입니다만", "종목", "기업", "추천", "은", "는", "이", "가", "을", "를", "도", "와", "과"):
        if cleaned.endswith(suf) and len(cleaned) - len(suf) >= 2:
            cleaned = cleaned[: -len(suf)]
            break
    return cleaned


def _extract_candidates_from_line(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for token in set(re.findall(r"[가-힣A-Za-z]{2,12}", text)):
        candidate = _clean_candidate_token(token)
        norm = normalize_name(candidate)
        if norm in THEME_WORDS:
            continue
        ticker, quality = map_to_ticker(candidate)
        if ticker and quality != "unmapped":
            found.append((candidate, ticker))
    return found


def _score_candidate(line: TranscriptLine, line_idx: int, section: Section, in_seed_mentions: bool) -> float:
    score = 1.0
    if line_idx <= section.start_idx + 2:
        score += 1.2
    section_size = max(1, section.end_idx - section.start_idx + 1)
    score += max(0.0, 1.0 - ((line_idx - section.start_idx) / section_size))
    if any(x in line.text for x in EXPLANATION_HINTS):
        score += 0.8
    if any(x in line.text for x in DISCLAIMER_HINTS):
        score -= 1.0
    if in_seed_mentions:
        score += 0.5
    return score


def infer_recommendations(
    title: str,
    transcript_text: str | None,
    extracted_mentions: list[str] | None = None,
    expected_count: int | None = None,
) -> tuple[list[InferredRecommendation], dict[str, Any]]:
    is_reco_video, hinted_count = classify_recommendation_video(title)
    count = expected_count or hinted_count or 3
    lines = split_transcript_lines(transcript_text)
    sections = build_sections(lines, expected_count=count)
    seed_mentions = {normalize_name(x) for x in (extracted_mentions or [])}

    picks: list[InferredRecommendation] = []
    marker_section_count = 0

    for section in sections:
        if section.rank > count:
            continue
        candidates: dict[str, dict[str, Any]] = {}
        for line_idx in range(section.start_idx, min(section.end_idx + 1, len(lines))):
            line = lines[line_idx]
            for raw_name, ticker in _extract_candidates_from_line(line.text):
                norm = normalize_name(raw_name)
                info = candidates.setdefault(
                    norm,
                    {
                        "raw_name": raw_name,
                        "ticker": ticker,
                        "score": 0.0,
                        "first_idx": line_idx,
                        "evidence_text": line.text,
                        "start_sec": line.start_sec,
                    },
                )
                info["score"] += _score_candidate(line, line_idx, section, norm in seed_mentions)
        if not candidates:
            continue

        best = sorted(candidates.values(), key=lambda x: (x["score"], -x["first_idx"]), reverse=True)[0]
        marker_section_count += 1 if section.has_marker else 0
        method = "rule_sequence" if section.has_marker else "fallback_density"
        confidence = "high" if section.has_marker and best["score"] >= 3.0 and best["ticker"] else "medium"
        if not section.has_marker:
            confidence = "low" if not is_reco_video else "medium"

        picks.append(
            InferredRecommendation(
                rec_rank=section.rank,
                stock_name=best["raw_name"],
                ticker=best["ticker"],
                market="KOSPI/KOSDAQ" if best["ticker"] else None,
                confidence=confidence,
                method=method,
                evidence_text=best["evidence_text"][:220],
                evidence_start_sec=best["start_sec"],
                evidence_end_sec=None,
                source_segment_label=section.label,
            )
        )

    picks = sorted(picks, key=lambda x: x.rec_rank)[:count]
    if not picks:
        return [], {"expected_count": count, "is_recommendation_video": is_reco_video, "inferred_count": 0, "confidence_summary": "low"}

    confidence_order = {"high": 3, "medium": 2, "low": 1}
    avg = sum(confidence_order[p.confidence] for p in picks) / len(picks)
    summary = "high" if avg >= 2.7 and marker_section_count >= 2 else "medium" if avg >= 1.8 else "low"
    return picks, {
        "expected_count": count,
        "is_recommendation_video": is_reco_video,
        "inferred_count": len(picks),
        "confidence_summary": summary,
    }
