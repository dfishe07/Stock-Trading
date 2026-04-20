from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from apps.backtesting.catalog import find_stock


@dataclass
class PriceBar:
    session_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


def trading_days(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            yield current
        current += timedelta(days=1)


def generate_symbol_bars(symbol: str, start_date: date, end_date: date) -> list[PriceBar]:
    stock = find_stock(symbol)
    if stock is None:
        raise ValueError(f"Unsupported symbol '{symbol}'.")

    seed = sum(ord(char) for char in symbol.upper())
    sector_bias = sum(ord(char) for char in stock["sector"]) % 9
    base_price = 40 + (seed % 140)
    drift = 0.00035 + sector_bias * 0.00003
    volatility = 0.008 + (seed % 5) * 0.0015

    bars: list[PriceBar] = []
    prev_close = float(base_price)
    for index, session_date in enumerate(trading_days(start_date, end_date)):
        cyclical = math.sin(index / 12 + seed / 17) * volatility
        secondary = math.cos(index / 29 + sector_bias) * (volatility / 2)
        daily_return = drift + cyclical + secondary
        open_price = max(5.0, prev_close * (1 + daily_return / 3))
        close_price = max(5.0, prev_close * (1 + daily_return))
        intraday_spread = max(0.004, abs(daily_return) + volatility * 0.9)
        high_price = max(open_price, close_price) * (1 + intraday_spread / 2)
        low_price = min(open_price, close_price) * (1 - intraday_spread / 2)
        volume = int(750000 + ((seed * (index + 7)) % 2_750_000))
        bars.append(
            PriceBar(
                session_date=session_date,
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=volume,
            )
        )
        prev_close = close_price
    return bars


def load_market_data(symbols: list[str], start_date: date, end_date: date):
    return {symbol: generate_symbol_bars(symbol, start_date, end_date) for symbol in symbols}

