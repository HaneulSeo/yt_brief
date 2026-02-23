from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from pykrx import stock


class PriceClient:
    def is_trading_day(self, d: date) -> bool:
        df = stock.get_market_ohlcv_by_date(d.strftime("%Y%m%d"), d.strftime("%Y%m%d"), "005930")
        return not df.empty

    def get_ohlcv(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        df = stock.get_market_ohlcv_by_date(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker)
        if df.empty:
            return df
        df = df.rename(columns={"시가": "open", "고가": "high", "저가": "low", "종가": "close"})
        df.index = pd.to_datetime(df.index).date
        return df

    def get_trading_days(self, start: date, n: int) -> list[date]:
        days = []
        cur = start
        safety = 0
        while len(days) < n and safety < 60:
            if self.is_trading_day(cur):
                days.append(cur)
            cur += timedelta(days=1)
            safety += 1
        return days
