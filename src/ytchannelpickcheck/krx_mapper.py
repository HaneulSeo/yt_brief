from __future__ import annotations

import re
from functools import lru_cache

from pykrx import stock


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name.strip()).upper()


@lru_cache(maxsize=1)
def get_krx_universe() -> dict[str, str]:
    tickers = stock.get_market_ticker_list(market="ALL")
    out = {}
    for t in tickers:
        n = stock.get_market_ticker_name(t)
        out[normalize_name(n)] = t
    return out


def map_to_ticker(name: str) -> tuple[str | None, str]:
    uni = get_krx_universe()
    norm = normalize_name(name)
    if norm in uni:
        return uni[norm], "normalized_exact"
    return None, "unmapped"
