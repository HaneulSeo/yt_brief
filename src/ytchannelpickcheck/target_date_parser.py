from __future__ import annotations

import re
from datetime import date, timedelta

from .schemas import ParsedTargetDate
from .utils_time import next_trading_day

WD_MAP = {
    "월요일": 0,
    "화요일": 1,
    "수요일": 2,
    "목요일": 3,
    "금요일": 4,
}


def _resolve_year(m: int, d: int, upload_date: date) -> date:
    candidate = date(upload_date.year, m, d)
    if candidate < upload_date - timedelta(days=180):
        candidate = date(upload_date.year + 1, m, d)
    return candidate


def parse_target_date(video_id: str, title: str, upload_date_kst: date, is_trading_day_fn=None) -> ParsedTargetDate:
    title = title or ""
    explicit = re.search(r"(?:(20\d{2}|\d{2})[./-])?(\d{1,2})[./-](\d{1,2})", title)
    if explicit:
        y, m, d = explicit.groups()
        m_i, d_i = int(m), int(d)
        if y:
            y_i = int(y)
            if y_i < 100:
                y_i += 2000
            target = date(y_i, m_i, d_i)
        else:
            target = _resolve_year(m_i, d_i, upload_date_kst)
        return ParsedTargetDate(
            video_id=video_id,
            target_date_type="explicit_date",
            target_date_kst=target,
            parser_confidence=0.98,
            parser_evidence=explicit.group(0),
        )

    if "내일" in title:
        return ParsedTargetDate(
            video_id=video_id,
            target_date_type="relative_tomorrow",
            target_date_kst=next_trading_day(upload_date_kst, is_trading_day_fn),
            parser_confidence=0.9,
            parser_evidence="내일",
        )

    if "다음주" in title or "다음 주" in title:
        delta = 7 - upload_date_kst.weekday()
        week_start = upload_date_kst + timedelta(days=delta)
        while week_start.weekday() >= 5:
            week_start += timedelta(days=1)
        return ParsedTargetDate(
            video_id=video_id,
            target_date_type="relative_next_week",
            target_date_kst=None,
            target_week_start_kst=week_start,
            parser_confidence=0.75,
            parser_evidence="다음주",
        )

    for token, wd in WD_MAP.items():
        if token in title:
            cur = upload_date_kst
            for _ in range(8):
                cur += timedelta(days=1)
                if cur.weekday() == wd:
                    return ParsedTargetDate(
                        video_id=video_id,
                        target_date_type="weekday_inferred",
                        target_date_kst=cur,
                        parser_confidence=0.8,
                        parser_evidence=token,
                    )

    inferred = next_trading_day(upload_date_kst, is_trading_day_fn)
    return ParsedTargetDate(
        video_id=video_id,
        target_date_type="upload_next_trading_day",
        target_date_kst=inferred,
        parser_confidence=0.35,
        parser_evidence="fallback_next_trading_day",
        parser_notes="inferred_low_confidence",
        status="inferred",
    )
