from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
UTC = timezone.utc


def parse_ymd(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def utc_to_kst(utc_dt: datetime) -> datetime:
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC)
    return utc_dt.astimezone(KST)


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def next_weekday(d: date) -> date:
    cur = d + timedelta(days=1)
    while is_weekend(cur):
        cur += timedelta(days=1)
    return cur


def next_trading_day(d: date, is_trading_day_fn=None) -> date:
    cur = d + timedelta(days=1)
    while True:
        if is_weekend(cur):
            cur += timedelta(days=1)
            continue
        if is_trading_day_fn is not None and not is_trading_day_fn(cur):
            cur += timedelta(days=1)
            continue
        return cur


def ensure_trading_day(d: date, is_trading_day_fn=None) -> tuple[date, str | None]:
    if not is_weekend(d) and (is_trading_day_fn is None or is_trading_day_fn(d)):
        return d, None
    shifted = d
    while is_weekend(shifted) or (is_trading_day_fn is not None and not is_trading_day_fn(shifted)):
        shifted += timedelta(days=1)
    return shifted, "shifted_to_next_trading_day"
