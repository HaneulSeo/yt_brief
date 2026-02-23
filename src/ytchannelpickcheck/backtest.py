from __future__ import annotations

from datetime import date
from typing import Any

from .schemas import BacktestResult


def _to_rows(ohlcv: Any) -> list[dict]:
    if hasattr(ohlcv, "iterrows"):
        rows = []
        for idx, row in ohlcv.iterrows():
            d = idx if isinstance(idx, date) else idx.date()
            rows.append({"date": d, "open": float(row["open"]), "high": float(row["high"]), "low": float(row["low"]), "close": float(row["close"])})
        return sorted(rows, key=lambda x: x["date"])
    return sorted(list(ohlcv), key=lambda x: x["date"])


def compute_backtest(
    video_id: str,
    ticker: str,
    target_date: date,
    ohlcv: Any,
    window_days: int = 5,
    intraday_hit: float = 0.10,
    close_hit: float = 0.05,
) -> BacktestResult:
    rows = _to_rows(ohlcv)
    dates = [r["date"] for r in rows]
    if target_date not in dates:
        return BacktestResult(video_id=video_id, ticker=ticker, target_date_kst=target_date, window_days=window_days, backtest_status="failed", backtest_error="missing_target_ohlcv")
    t_i = dates.index(target_date)
    if t_i == 0:
        return BacktestResult(video_id=video_id, ticker=ticker, target_date_kst=target_date, window_days=window_days, backtest_status="failed", backtest_error="no_prev_close")

    prev_close = float(rows[t_i - 1]["close"])
    row = rows[t_i]
    ret_open = row["open"] / prev_close - 1
    ret_high = row["high"] / prev_close - 1
    ret_close = row["close"] / prev_close - 1

    window = rows[t_i : t_i + window_days]
    week_max_high_row = max(window, key=lambda x: x["high"])
    week_max_close_row = max(window, key=lambda x: x["close"])
    ret_week_high = week_max_high_row["high"] / prev_close - 1
    ret_week_close = week_max_close_row["close"] / prev_close - 1

    intraday_offsets = [i for i, x in enumerate(window) if x["high"] / prev_close - 1 >= intraday_hit]
    close_offsets = [i for i, x in enumerate(window) if x["close"] / prev_close - 1 >= close_hit]

    return BacktestResult(
        video_id=video_id,
        ticker=ticker,
        target_date_kst=target_date,
        window_days=window_days,
        target_prev_close=prev_close,
        target_open=row["open"],
        target_high=row["high"],
        target_low=row["low"],
        target_close=row["close"],
        ret_target_open=ret_open,
        ret_target_high=ret_high,
        ret_target_close=ret_close,
        hit_target_intraday=ret_high >= intraday_hit,
        hit_target_close=ret_close >= close_hit,
        week_window_start_date=window[0]["date"],
        week_window_end_date=window[-1]["date"],
        week_max_high=week_max_high_row["high"],
        week_max_high_date=week_max_high_row["date"],
        week_max_close=week_max_close_row["close"],
        week_max_close_date=week_max_close_row["date"],
        ret_week_max_high=ret_week_high,
        ret_week_max_close=ret_week_close,
        hit_week_intraday=ret_week_high >= intraday_hit,
        hit_week_close=ret_week_close >= close_hit,
        first_hit_day_offset_intraday=intraday_offsets[0] if intraday_offsets else None,
        first_hit_day_offset_close=close_offsets[0] if close_offsets else None,
    )
