from datetime import date

from ytchannelpickcheck.utils_time import next_trading_day


def test_next_trading_day_weekend():
    d = date(2025, 1, 3)  # Fri
    assert next_trading_day(d) == date(2025, 1, 6)
