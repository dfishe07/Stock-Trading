from __future__ import annotations

from copy import deepcopy

from apps.backtesting.catalog import get_stock_universe_catalog


SUPPORTED_INDICATORS = {
    "sma": {"period": "integer", "source": "string"},
    "ema": {"period": "integer", "source": "string"},
    "rsi": {"period": "integer", "source": "string"},
    "macd": {"fast": "integer", "slow": "integer", "signal": "integer"},
}

SUPPORTED_COMPARATORS = {
    "gt",
    "gte",
    "lt",
    "lte",
    "eq",
    "crosses_above",
    "crosses_below",
}

SUPPORTED_LOGIC_OPERATORS = {"and", "or"}
SUPPORTED_TIMEFRAMES = ["15m", "1H", "4H", "1D"]
SUPPORTED_SCHEDULES = ["15m", "1h", "4h", "1d"]
SUPPORTED_MARKET_SESSIONS = ["regular", "extended"]
SUPPORTED_PRICE_SOURCES = ["open", "high", "low", "close"]
SUPPORTED_SIZING_METHODS = ["fixed_fraction", "fixed_amount"]
SUPPORTED_ORDER_TYPES = ["market", "limit"]


DEFAULT_STRATEGY_DEFINITION = {
    "schemaVersion": "1.0",
    "metadata": {
        "timeframe": "1D",
        "schedule": {"type": "interval", "value": "1d"},
        "marketSession": "regular",
        "notes": "",
    },
    "universe": {
        "type": "symbols",
        "symbols": ["AAPL", "MSFT"],
    },
    "indicators": [
        {"id": "fast_sma", "type": "sma", "params": {"period": 20, "source": "close"}},
        {"id": "slow_sma", "type": "sma", "params": {"period": 50, "source": "close"}},
    ],
    "entryRules": {
        "type": "group",
        "operator": "and",
        "conditions": [
            {
                "type": "condition",
                "left": {"kind": "indicator", "value": "fast_sma"},
                "operator": "crosses_above",
                "right": {"kind": "indicator", "value": "slow_sma"},
            }
        ],
    },
    "exitRules": {
        "type": "group",
        "operator": "or",
        "conditions": [
            {
                "type": "condition",
                "left": {"kind": "indicator", "value": "fast_sma"},
                "operator": "crosses_below",
                "right": {"kind": "indicator", "value": "slow_sma"},
            }
        ],
    },
    "sizing": {"method": "fixed_fraction", "value": 0.1, "minCash": 0},
    "risk": {
        "maxPositionExposure": 0.2,
        "maxPortfolioExposure": 1.0,
        "stopLossPercent": 0.05,
        "takeProfitPercent": 0.12,
        "reEntryCooldownBars": 3,
        "dailyLossLimitPercent": 0.03,
    },
    "execution": {
        "orderType": "market",
        "allowFractional": False,
        "slippageBps": 5,
        "feesPerTrade": 0,
    },
}


def get_default_strategy_definition():
    return deepcopy(DEFAULT_STRATEGY_DEFINITION)


STRATEGY_FORM_SCHEMA = {
    "schemaVersion": "1.0",
    "supportedIndicators": SUPPORTED_INDICATORS,
    "supportedComparators": sorted(SUPPORTED_COMPARATORS),
    "supportedLogicOperators": sorted(SUPPORTED_LOGIC_OPERATORS),
    "supportedTimeframes": SUPPORTED_TIMEFRAMES,
    "supportedSchedules": SUPPORTED_SCHEDULES,
    "supportedMarketSessions": SUPPORTED_MARKET_SESSIONS,
    "supportedPriceSources": SUPPORTED_PRICE_SOURCES,
    "supportedSizingMethods": SUPPORTED_SIZING_METHODS,
    "supportedOrderTypes": SUPPORTED_ORDER_TYPES,
    "stockUniverse": get_stock_universe_catalog(),
    "sections": [
        {
            "id": "metadata",
            "title": "Strategy Basics",
            "fields": [
                {"key": "name", "type": "text", "label": "Strategy Name", "required": True},
                {"key": "description", "type": "textarea", "label": "Description", "required": False},
                {
                    "key": "metadata.timeframe",
                    "type": "select",
                    "label": "Timeframe",
                    "options": SUPPORTED_TIMEFRAMES,
                    "required": True,
                },
                {
                    "key": "metadata.schedule.value",
                    "type": "select",
                    "label": "Evaluation Schedule",
                    "options": SUPPORTED_SCHEDULES,
                    "required": True,
                },
                {
                    "key": "metadata.marketSession",
                    "type": "select",
                    "label": "Market Session",
                    "options": SUPPORTED_MARKET_SESSIONS,
                    "required": True,
                },
            ],
        },
        {
            "id": "universe",
            "title": "Universe",
            "fields": [
                {
                    "key": "universe.symbols",
                    "type": "stock-search",
                    "label": "Symbols",
                    "required": True,
                    "placeholder": "Search AAPL, MSFT, JPM...",
                }
            ],
        },
        {
            "id": "execution",
            "title": "Execution",
            "fields": [
                {
                    "key": "sizing.method",
                    "type": "select",
                    "label": "Sizing Method",
                    "options": SUPPORTED_SIZING_METHODS,
                },
                {
                    "key": "execution.orderType",
                    "type": "select",
                    "label": "Order Type",
                    "options": SUPPORTED_ORDER_TYPES,
                },
                {
                    "key": "sizing.value",
                    "type": "number",
                    "label": "Target Allocation",
                },
                {
                    "key": "execution.slippageBps",
                    "type": "number",
                    "label": "Slippage (bps)",
                },
            ],
        },
        {
            "id": "risk",
            "title": "Risk Controls",
            "fields": [
                {"key": "risk.maxPositionExposure", "type": "number", "label": "Max Position Exposure"},
                {"key": "risk.maxPortfolioExposure", "type": "number", "label": "Max Portfolio Exposure"},
                {"key": "risk.stopLossPercent", "type": "number", "label": "Stop Loss Percent"},
                {"key": "risk.takeProfitPercent", "type": "number", "label": "Take Profit Percent"},
                {"key": "risk.reEntryCooldownBars", "type": "number", "label": "Re-entry Cooldown Bars"},
                {"key": "risk.dailyLossLimitPercent", "type": "number", "label": "Daily Loss Limit Percent"},
            ],
        },
    ],
}
