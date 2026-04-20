from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from statistics import mean, pstdev
from typing import Any

from apps.backtesting.market_data import PriceBar, load_market_data


def price_value(bar: PriceBar, source: str):
    if source == "open":
        return bar.open
    if source == "high":
        return bar.high
    if source == "low":
        return bar.low
    return bar.close


def simple_moving_average(values: list[float], period: int):
    output: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < period:
            output.append(None)
        else:
            window = values[index + 1 - period : index + 1]
            output.append(sum(window) / period)
    return output


def exponential_moving_average(values: list[float], period: int):
    output: list[float | None] = []
    multiplier = 2 / (period + 1)
    ema_value: float | None = None
    for index, value in enumerate(values):
        if index + 1 < period:
            output.append(None)
            continue
        if ema_value is None:
            ema_value = sum(values[index + 1 - period : index + 1]) / period
        else:
            ema_value = (value - ema_value) * multiplier + ema_value
        output.append(ema_value)
    return output


def relative_strength_index(values: list[float], period: int):
    output: list[float | None] = [None]
    gains: list[float] = []
    losses: list[float] = []
    avg_gain: float | None = None
    avg_loss: float | None = None
    for index in range(1, len(values)):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
        if index < period:
            output.append(None)
            continue
        if avg_gain is None or avg_loss is None:
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
        else:
            avg_gain = ((avg_gain * (period - 1)) + gains[-1]) / period
            avg_loss = ((avg_loss * (period - 1)) + losses[-1]) / period
        if avg_loss == 0:
            output.append(100.0)
            continue
        rs = avg_gain / avg_loss
        output.append(100 - (100 / (1 + rs)))
    return output


def macd(values: list[float], fast: int, slow: int, signal: int):
    fast_ema = exponential_moving_average(values, fast)
    slow_ema = exponential_moving_average(values, slow)
    line: list[float | None] = []
    compact_line: list[float] = []
    for fast_value, slow_value in zip(fast_ema, slow_ema):
        if fast_value is None or slow_value is None:
            line.append(None)
            continue
        macd_value = fast_value - slow_value
        line.append(macd_value)
        compact_line.append(macd_value)

    signal_line_compact = exponential_moving_average(compact_line, signal)
    signal_line: list[float | None] = []
    compact_index = 0
    for value in line:
        if value is None:
            signal_line.append(None)
            continue
        signal_line.append(signal_line_compact[compact_index])
        compact_index += 1

    histogram: list[float | None] = []
    for line_value, signal_value in zip(line, signal_line):
        if line_value is None or signal_value is None:
            histogram.append(None)
        else:
            histogram.append(line_value - signal_value)
    return line, signal_line, histogram


def calculate_indicator_series(bars: list[PriceBar], definition: dict[str, Any]):
    indicator_values: dict[str, list[float | None]] = {}
    for indicator in definition.get("indicators", []):
        indicator_id = indicator["id"]
        indicator_type = indicator["type"]
        params = indicator.get("params", {})
        source = str(params.get("source", "close"))
        price_series = [price_value(bar, source) for bar in bars]
        if indicator_type == "sma":
            indicator_values[indicator_id] = simple_moving_average(price_series, int(params["period"]))
        elif indicator_type == "ema":
            indicator_values[indicator_id] = exponential_moving_average(price_series, int(params["period"]))
        elif indicator_type == "rsi":
            indicator_values[indicator_id] = relative_strength_index(price_series, int(params["period"]))
        elif indicator_type == "macd":
            indicator_values[indicator_id], _, _ = macd(
                price_series,
                int(params["fast"]),
                int(params["slow"]),
                int(params["signal"]),
            )
        else:
            raise ValueError(f"Unsupported indicator type '{indicator_type}'.")
    return indicator_values


def operand_value(operand: dict[str, Any], index: int, bars: list[PriceBar], indicators: dict[str, list[float | None]]):
    kind = operand["kind"]
    value = operand["value"]
    if kind == "indicator":
        return indicators[str(value)][index]
    if kind == "literal":
        return float(value)
    if kind == "price":
        return price_value(bars[index], str(value))
    raise ValueError(f"Unsupported operand kind '{kind}'.")


def comparator_result(operator: str, previous_left, previous_right, current_left, current_right):
    if current_left is None or current_right is None:
        return False
    if operator == "gt":
        return current_left > current_right
    if operator == "gte":
        return current_left >= current_right
    if operator == "lt":
        return current_left < current_right
    if operator == "lte":
        return current_left <= current_right
    if operator == "eq":
        return math.isclose(current_left, current_right, rel_tol=1e-9)
    if operator == "crosses_above":
        return previous_left is not None and previous_right is not None and previous_left <= previous_right and current_left > current_right
    if operator == "crosses_below":
        return previous_left is not None and previous_right is not None and previous_left >= previous_right and current_left < current_right
    raise ValueError(f"Unsupported comparator '{operator}'.")


def evaluate_rule_node(node: dict[str, Any], index: int, bars: list[PriceBar], indicators: dict[str, list[float | None]]):
    if node["type"] == "group":
        child_results = [evaluate_rule_node(child, index, bars, indicators) for child in node["conditions"]]
        return all(child_results) if node["operator"] == "and" else any(child_results)

    previous_index = max(index - 1, 0)
    current_left = operand_value(node["left"], index, bars, indicators)
    current_right = operand_value(node["right"], index, bars, indicators)
    previous_left = operand_value(node["left"], previous_index, bars, indicators) if index > 0 else None
    previous_right = operand_value(node["right"], previous_index, bars, indicators) if index > 0 else None
    return comparator_result(node["operator"], previous_left, previous_right, current_left, current_right)


@dataclass
class ClosedTrade:
    symbol: str
    entry_date: date
    exit_date: date
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    net_pnl: float
    return_pct: float
    exit_reason: str
    max_favorable_excursion: float
    max_adverse_excursion: float


def run_backtest_engine(definition: dict[str, Any], start_date: date, end_date: date, initial_cash: float, benchmark_symbol: str | None = None):
    symbols = [symbol.upper() for symbol in definition["universe"]["symbols"]]
    market_data = load_market_data(symbols + ([benchmark_symbol.upper()] if benchmark_symbol else []), start_date, end_date)
    symbol_data = {symbol: market_data[symbol] for symbol in symbols}
    indicator_map = {symbol: calculate_indicator_series(bars, definition) for symbol, bars in symbol_data.items()}
    sessions = [bar.session_date for bar in next(iter(symbol_data.values()))]

    cash = float(initial_cash)
    risk = definition["risk"]
    sizing = definition["sizing"]
    execution = definition["execution"]
    allow_fractional = bool(execution.get("allowFractional", False))
    stop_loss = float(risk.get("stopLossPercent", 0))
    take_profit = float(risk.get("takeProfitPercent", 0))
    reentry_cooldown = int(risk.get("reEntryCooldownBars", 0))
    slippage_bps = float(execution.get("slippageBps", 0))
    trade_fee = float(execution.get("feesPerTrade", 0))

    positions: dict[str, dict[str, Any]] = {}
    last_exit_index: dict[str, int] = {}
    closed_trades: list[ClosedTrade] = []
    signal_log: list[dict[str, Any]] = []
    equity_curve: list[dict[str, float | str]] = []

    for index, session_date in enumerate(sessions):
        prices_for_day = {symbol: bars[index].close for symbol, bars in symbol_data.items()}
        equity = cash + sum(position["quantity"] * prices_for_day[symbol] for symbol, position in positions.items())
        peak_equity_before = max([point["equity"] for point in equity_curve], default=equity)
        daily_loss_limit = float(risk.get("dailyLossLimitPercent", 0))
        allow_new_entries = True
        if peak_equity_before > 0 and daily_loss_limit:
            intraday_drawdown = (equity - peak_equity_before) / peak_equity_before
            if intraday_drawdown <= -daily_loss_limit:
                allow_new_entries = False

        for symbol, bars in symbol_data.items():
            current_price = bars[index].close
            indicators = indicator_map[symbol]
            position = positions.get(symbol)

            if position:
                mfe = max(position["max_favorable_excursion"], (current_price - position["entry_price"]) / position["entry_price"])
                mae = min(position["max_adverse_excursion"], (current_price - position["entry_price"]) / position["entry_price"])
                position["max_favorable_excursion"] = mfe
                position["max_adverse_excursion"] = mae
                exit_reason = ""
                if stop_loss and current_price <= position["entry_price"] * (1 - stop_loss):
                    exit_reason = "stop_loss"
                elif take_profit and current_price >= position["entry_price"] * (1 + take_profit):
                    exit_reason = "take_profit"
                elif evaluate_rule_node(definition["exitRules"], index, bars, indicators):
                    exit_reason = "rule_exit"

                if exit_reason:
                    exit_price = current_price * (1 - slippage_bps / 10000)
                    gross_pnl = (exit_price - position["entry_price"]) * position["quantity"]
                    net_pnl = gross_pnl - trade_fee
                    cash += (exit_price * position["quantity"]) - trade_fee
                    closed_trades.append(
                        ClosedTrade(
                            symbol=symbol,
                            entry_date=position["entry_date"],
                            exit_date=session_date,
                            entry_price=position["entry_price"],
                            exit_price=exit_price,
                            quantity=position["quantity"],
                            gross_pnl=gross_pnl,
                            net_pnl=net_pnl,
                            return_pct=(net_pnl / max(position["entry_price"] * position["quantity"], 1e-9)) * 100,
                            exit_reason=exit_reason,
                            max_favorable_excursion=position["max_favorable_excursion"] * 100,
                            max_adverse_excursion=position["max_adverse_excursion"] * 100,
                        )
                    )
                    signal_log.append({"date": session_date.isoformat(), "symbol": symbol, "action": "exit", "reason": exit_reason})
                    last_exit_index[symbol] = index
                    del positions[symbol]
                    equity = cash + sum(open_position["quantity"] * prices_for_day[open_symbol] for open_symbol, open_position in positions.items())
                    continue

            if position or not allow_new_entries:
                continue

            if symbol in last_exit_index and index - last_exit_index[symbol] <= reentry_cooldown:
                continue

            if not evaluate_rule_node(definition["entryRules"], index, bars, indicators):
                continue

            max_position_cash = equity * float(risk.get("maxPositionExposure", 0.2))
            desired_cash = equity * float(sizing.get("value", 0.1)) if sizing.get("method") == "fixed_fraction" else float(sizing.get("value", 0))
            cash_to_deploy = min(cash, desired_cash, max_position_cash)
            if cash_to_deploy <= 0:
                continue
            entry_price = current_price * (1 + slippage_bps / 10000)
            quantity = cash_to_deploy / entry_price
            if not allow_fractional:
                quantity = math.floor(quantity)
            if quantity <= 0:
                continue
            order_cost = quantity * entry_price + trade_fee
            if order_cost > cash:
                continue
            cash -= order_cost
            positions[symbol] = {
                "quantity": quantity,
                "entry_price": entry_price,
                "entry_date": session_date,
                "max_favorable_excursion": 0.0,
                "max_adverse_excursion": 0.0,
            }
            signal_log.append({"date": session_date.isoformat(), "symbol": symbol, "action": "entry", "reason": "rule_entry"})

        ending_equity = cash + sum(position["quantity"] * prices_for_day[symbol] for symbol, position in positions.items())
        exposure = 0.0 if ending_equity <= 0 else sum(position["quantity"] * prices_for_day[symbol] for symbol, position in positions.items()) / ending_equity
        equity_curve.append(
            {
                "date": session_date.isoformat(),
                "equity": round(ending_equity, 2),
                "cash": round(cash, 2),
                "exposure": round(exposure, 4),
            }
        )

    if equity_curve and positions:
        final_date = sessions[-1]
        final_prices = {symbol: bars[-1].close for symbol, bars in symbol_data.items()}
        for symbol, position in list(positions.items()):
            exit_price = final_prices[symbol]
            gross_pnl = (exit_price - position["entry_price"]) * position["quantity"]
            net_pnl = gross_pnl - trade_fee
            cash += (exit_price * position["quantity"]) - trade_fee
            closed_trades.append(
                ClosedTrade(
                    symbol=symbol,
                    entry_date=position["entry_date"],
                    exit_date=final_date,
                    entry_price=position["entry_price"],
                    exit_price=exit_price,
                    quantity=position["quantity"],
                    gross_pnl=gross_pnl,
                    net_pnl=net_pnl,
                    return_pct=(net_pnl / max(position["entry_price"] * position["quantity"], 1e-9)) * 100,
                    exit_reason="end_of_test",
                    max_favorable_excursion=position["max_favorable_excursion"] * 100,
                    max_adverse_excursion=position["max_adverse_excursion"] * 100,
                )
            )
            signal_log.append({"date": final_date.isoformat(), "symbol": symbol, "action": "exit", "reason": "end_of_test"})

        equity_curve[-1]["equity"] = round(cash, 2)
        equity_curve[-1]["cash"] = round(cash, 2)
        equity_curve[-1]["exposure"] = 0.0

    returns = []
    for index in range(1, len(equity_curve)):
        previous = float(equity_curve[index - 1]["equity"])
        current = float(equity_curve[index]["equity"])
        if previous > 0:
            returns.append((current - previous) / previous)

    peak = float(equity_curve[0]["equity"]) if equity_curve else initial_cash
    max_drawdown = 0.0
    for point in equity_curve:
        equity = float(point["equity"])
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, (equity - peak) / peak)

    ending_equity = float(equity_curve[-1]["equity"]) if equity_curve else float(initial_cash)
    total_return = ((ending_equity - initial_cash) / initial_cash) * 100 if initial_cash else 0.0
    annualized_return = 0.0
    if equity_curve and len(equity_curve) > 1 and initial_cash > 0:
        annualized_return = ((ending_equity / initial_cash) ** (252 / len(equity_curve)) - 1) * 100

    sharpe_ratio = 0.0
    if returns and pstdev(returns) > 0:
        sharpe_ratio = (mean(returns) / pstdev(returns)) * math.sqrt(252)

    winning_trades = [trade for trade in closed_trades if trade.net_pnl > 0]
    benchmark_return = None
    if benchmark_symbol:
        benchmark_bars = market_data[benchmark_symbol.upper()]
        if benchmark_bars:
            benchmark_return = ((benchmark_bars[-1].close - benchmark_bars[0].close) / benchmark_bars[0].close) * 100

    summary = {
        "initial_cash": round(initial_cash, 2),
        "ending_equity": round(ending_equity, 2),
        "total_return_pct": round(total_return, 4),
        "annualized_return_pct": round(annualized_return, 4),
        "max_drawdown_pct": round(abs(max_drawdown) * 100, 4),
        "win_rate_pct": round((len(winning_trades) / len(closed_trades)) * 100, 4) if closed_trades else 0.0,
        "sharpe_ratio": round(sharpe_ratio, 4),
        "total_trades": len(closed_trades),
        "benchmark_return_pct": round(benchmark_return, 4) if benchmark_return is not None else None,
        "symbols_tested": symbols,
    }

    return {
        "summary": summary,
        "equity_curve": equity_curve,
        "signal_log": signal_log,
        "trades": [trade.__dict__ for trade in closed_trades],
    }
