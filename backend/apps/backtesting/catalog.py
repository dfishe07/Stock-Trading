from __future__ import annotations

from copy import deepcopy


MVP_STOCK_UNIVERSE = [
    {"symbol": "AAPL", "name": "Apple", "sector": "Technology", "industry": "Consumer Electronics"},
    {"symbol": "MSFT", "name": "Microsoft", "sector": "Technology", "industry": "Software"},
    {"symbol": "JPM", "name": "JPMorgan Chase", "sector": "Financials", "industry": "Banks"},
    {"symbol": "XOM", "name": "Exxon Mobil", "sector": "Energy", "industry": "Integrated Oil & Gas"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"symbol": "CAT", "name": "Caterpillar", "sector": "Industrials", "industry": "Machinery"},
    {"symbol": "COST", "name": "Costco", "sector": "Consumer Staples", "industry": "Retail"},
    {"symbol": "AMZN", "name": "Amazon", "sector": "Consumer Discretionary", "industry": "Internet Retail"},
    {"symbol": "NFLX", "name": "Netflix", "sector": "Communication Services", "industry": "Entertainment"},
    {"symbol": "NEE", "name": "NextEra Energy", "sector": "Utilities", "industry": "Utilities - Regulated Electric"},
]


def get_stock_universe_catalog():
    return deepcopy(MVP_STOCK_UNIVERSE)


def find_stock(symbol: str):
    normalized = symbol.upper()
    return next((item for item in MVP_STOCK_UNIVERSE if item["symbol"] == normalized), None)

