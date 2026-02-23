from datetime import date

from ytchannelpickcheck.backtest import compute_backtest


def test_backtest_hits():
    rows = [
        {"date": date(2025, 1, 2), "open": 100, "high": 102, "low": 99, "close": 100},
        {"date": date(2025, 1, 3), "open": 105, "high": 112, "low": 103, "close": 108},
        {"date": date(2025, 1, 6), "open": 110, "high": 120, "low": 107, "close": 115},
        {"date": date(2025, 1, 7), "open": 108, "high": 111, "low": 105, "close": 109},
    ]
    r = compute_backtest("v1", "005930", date(2025, 1, 3), rows, window_days=3)
    assert r.hit_target_intraday is True
    assert r.hit_week_intraday is True
