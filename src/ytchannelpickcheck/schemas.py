from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    class BaseModel:  # minimal fallback
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def Field(default=None, **kwargs):
        return default


class ParsedTargetDate(BaseModel):
    video_id: str
    target_date_type: Literal[
        "explicit_date",
        "relative_tomorrow",
        "relative_next_week",
        "weekday_inferred",
        "upload_next_trading_day",
        "unknown",
    ]
    target_date_kst: date | None = None
    target_week_start_kst: date | None = None
    parser_confidence: float = Field(ge=0.0, le=1.0)
    parser_evidence: str
    parser_notes: str = ""
    status: str = "success"


class ExtractedPick(BaseModel):
    video_id: str
    pick_rank: int | None = None
    raw_mention: str
    normalized_name: str
    ticker: str | None = None
    extraction_method: Literal["rule", "dict", "llm", "hybrid"]
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_text: str
    is_primary_recommendation: bool = False


class BacktestResult(BaseModel):
    video_id: str
    ticker: str
    target_date_kst: date
    window_days: int
    target_prev_close: float | None = None
    target_open: float | None = None
    target_high: float | None = None
    target_low: float | None = None
    target_close: float | None = None
    ret_target_open: float | None = None
    ret_target_high: float | None = None
    ret_target_close: float | None = None
    hit_target_intraday: bool = False
    hit_target_close: bool = False
    week_window_start_date: date | None = None
    week_window_end_date: date | None = None
    week_max_high: float | None = None
    week_max_high_date: date | None = None
    week_max_close: float | None = None
    week_max_close_date: date | None = None
    ret_week_max_high: float | None = None
    ret_week_max_close: float | None = None
    hit_week_intraday: bool = False
    hit_week_close: bool = False
    first_hit_day_offset_intraday: int | None = None
    first_hit_day_offset_close: int | None = None
    backtest_status: str = "success"
    backtest_error: str | None = None
