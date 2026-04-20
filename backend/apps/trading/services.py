from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.utils import timezone

from apps.backtesting.engine import calculate_indicator_series, evaluate_rule_node
from apps.backtesting.market_data import load_market_data
from apps.operations.services import record_audit_event
from apps.strategies.services import get_strategy_execution_readiness
from apps.trading.brokers import get_broker_adapter
from apps.trading.models import (
    BrokerAccount,
    BrokerEvent,
    HeartbeatStatusChoices,
    HeartbeatTriggerChoices,
    LiveDeployment,
    LiveHeartbeat,
    LiveSignal,
    Order,
    OrderStatusChoices,
    Portfolio,
    Position,
)


LOOKBACK_DAYS = 220
SUPPORTED_DEPLOYMENT_SCHEDULES = ["15m", "1h", "4h", "1d"]


def _to_decimal(value, places: str = "0.01") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places))


def _floor_quantity(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_DOWN)


def compute_next_run_at(schedule_expression: str, from_dt=None):
    reference = from_dt or timezone.now()
    normalized = (schedule_expression or "").strip().lower()
    if normalized == "15m":
        return reference + timedelta(minutes=15)
    if normalized == "1h":
        return reference + timedelta(hours=1)
    if normalized == "4h":
        return reference + timedelta(hours=4)
    return reference + timedelta(days=1)


def ensure_portfolio_balances(portfolio: Portfolio) -> Portfolio:
    expected_starting_cash = portfolio.starting_cash or Decimal("100000.00")
    changed_fields: list[str] = []
    if portfolio.cash_balance is None:
        portfolio.cash_balance = expected_starting_cash
        changed_fields.append("cash_balance")
    if portfolio.equity_value is None:
        portfolio.equity_value = portfolio.cash_balance
        changed_fields.append("equity_value")
    if changed_fields:
        portfolio.save(update_fields=[*changed_fields, "updated_at"])
    return portfolio


def create_broker_event(*, broker_account: BrokerAccount, event_type: str, message: str, portfolio=None, deployment=None, order=None, payload=None):
    return BrokerEvent.objects.create(
        broker_account=broker_account,
        portfolio=portfolio,
        deployment=deployment,
        order=order,
        event_type=event_type,
        message=message,
        payload=payload or {},
    )


def _target_order_quantity(*, definition: dict, current_equity: Decimal, cash_balance: Decimal, current_price: Decimal) -> Decimal:
    sizing = definition["sizing"]
    risk = definition["risk"]
    execution = definition["execution"]

    if sizing["method"] == "fixed_amount":
        target_notional = Decimal(str(sizing["value"]))
    else:
        target_notional = current_equity * Decimal(str(sizing["value"]))

    max_position_notional = current_equity * Decimal(str(risk.get("maxPositionExposure", 1)))
    target_notional = min(target_notional, max_position_notional, cash_balance)
    if target_notional <= 0 or current_price <= 0:
        return Decimal("0")

    quantity = target_notional / current_price
    if not execution.get("allowFractional", False):
        quantity = _floor_quantity(quantity)
    return quantity.quantize(Decimal("0.000001"))


def _update_position_marks(*, portfolio: Portfolio, prices_by_symbol: dict[str, Decimal]):
    unrealized_total = Decimal("0")
    for position in portfolio.positions.all():
        latest_price = prices_by_symbol.get(position.symbol, position.last_price or position.average_price or Decimal("0"))
        position.last_price = latest_price
        if position.quantity > 0:
            position.market_value = (position.quantity * latest_price).quantize(Decimal("0.01"))
            position.unrealized_pnl = ((latest_price - position.average_price) * position.quantity).quantize(Decimal("0.01"))
            position.closed_at = None
        else:
            position.market_value = Decimal("0.00")
            position.unrealized_pnl = Decimal("0.00")
            if position.closed_at is None:
                position.closed_at = timezone.now()
        unrealized_total += position.unrealized_pnl
        position.save(update_fields=["last_price", "market_value", "unrealized_pnl", "closed_at", "updated_at"])

    portfolio.unrealized_pnl = unrealized_total.quantize(Decimal("0.01"))
    portfolio.realized_pnl = portfolio.positions.aggregate_total_realized_pnl() if hasattr(portfolio.positions, "aggregate_total_realized_pnl") else sum(
        (position.realized_pnl for position in portfolio.positions.all()),
        Decimal("0"),
    )
    portfolio.equity_value = (portfolio.cash_balance + sum((position.market_value for position in portfolio.positions.all()), Decimal("0"))).quantize(Decimal("0.01"))
    portfolio.last_synced_at = timezone.now()
    portfolio.save(update_fields=["unrealized_pnl", "realized_pnl", "equity_value", "last_synced_at", "updated_at"])


def _record_signal(*, deployment: LiveDeployment, symbol: str, signal_type: str, strength: Decimal, context: dict):
    return LiveSignal.objects.create(
        deployment=deployment,
        symbol=symbol,
        signal_type=signal_type,
        strength=strength.quantize(Decimal("0.0001")),
        context=context,
    )


def _position_for_symbol(portfolio: Portfolio, symbol: str):
    return portfolio.positions.filter(symbol=symbol).first()


def _submit_order(*, deployment: LiveDeployment, portfolio: Portfolio, symbol: str, side: str, quantity: Decimal, market_price: Decimal, signal_type: str):
    order = Order.objects.create(
        portfolio=portfolio,
        broker_account=deployment.broker_account,
        deployment=deployment,
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type=deployment.strategy_version.definition["execution"].get("orderType", "market"),
        status=OrderStatusChoices.SUBMITTED,
        submitted_at=timezone.now(),
        requested_price=market_price,
        metadata={"signal_type": signal_type},
    )
    create_broker_event(
        broker_account=deployment.broker_account,
        portfolio=portfolio,
        deployment=deployment,
        order=order,
        event_type="order_submitted",
        message=f"{side.upper()} {symbol} submitted to paper broker.",
        payload={"quantity": str(quantity), "requested_price": str(market_price)},
    )
    return order


@transaction.atomic
def evaluate_live_deployment(*, deployment: LiveDeployment, trigger_type: str = HeartbeatTriggerChoices.MANUAL):
    deployment = (
        LiveDeployment.objects.select_related("portfolio", "broker_account", "strategy_version", "organization", "created_by")
        .prefetch_related("portfolio__positions", "orders", "signals")
        .get(pk=deployment.pk)
    )
    portfolio = ensure_portfolio_balances(deployment.portfolio)
    definition = deployment.strategy_version.definition
    readiness = get_strategy_execution_readiness(definition)
    if not readiness["is_ready"]:
        deployment.last_error = "; ".join(readiness["errors"])
        deployment.last_run_at = timezone.now()
        deployment.next_run_at = compute_next_run_at(deployment.schedule_expression or definition["metadata"]["schedule"]["value"])
        deployment.save(update_fields=["last_error", "last_run_at", "next_run_at", "updated_at"])
        raise ValueError(deployment.last_error)

    heartbeat = LiveHeartbeat.objects.create(
        deployment=deployment,
        trigger_type=trigger_type,
        status=HeartbeatStatusChoices.RUNNING,
        evaluated_symbols=[symbol.upper() for symbol in definition["universe"]["symbols"]],
    )
    create_broker_event(
        broker_account=deployment.broker_account,
        portfolio=portfolio,
        deployment=deployment,
        event_type="evaluation_started",
        message=f"Deployment evaluation started via {trigger_type}.",
        payload={"heartbeat_id": str(heartbeat.id)},
    )

    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    symbols = [symbol.upper() for symbol in definition["universe"]["symbols"]]
    market_data = load_market_data(symbols, start_date, end_date)
    prices_by_symbol = {symbol: Decimal(str(bars[-1].close)) for symbol, bars in market_data.items()}
    indicator_map = {symbol: calculate_indicator_series(bars, definition) for symbol, bars in market_data.items()}
    current_equity = portfolio.equity_value or portfolio.cash_balance
    reserve_ratio = Decimal(str(portfolio.cash_reserve_percent or 0)) / Decimal("100")
    reserve_cash = (current_equity * reserve_ratio).quantize(Decimal("0.01"))

    signals_created = 0
    orders_created = 0
    adapter = get_broker_adapter(deployment.broker_account)
    trade_fee = Decimal(str(definition["execution"].get("feesPerTrade", 0)))
    slippage_bps = Decimal(str(definition["execution"].get("slippageBps", 0)))

    try:
        for symbol, bars in market_data.items():
            index = len(bars) - 1
            indicators = indicator_map[symbol]
            position = _position_for_symbol(portfolio, symbol)
            has_position = position is not None and position.quantity > 0
            entry_signal = evaluate_rule_node(definition["entryRules"], index, bars, indicators)
            exit_signal = evaluate_rule_node(definition["exitRules"], index, bars, indicators)
            current_price = prices_by_symbol[symbol]

            if has_position and exit_signal:
                order = _submit_order(
                    deployment=deployment,
                    portfolio=portfolio,
                    symbol=symbol,
                    side="sell",
                    quantity=position.quantity,
                    market_price=current_price,
                    signal_type="exit",
                )
                fill = adapter.submit_market_order(order=order, market_price=current_price, slippage_bps=slippage_bps)
                proceeds = (fill.filled_price * position.quantity).quantize(Decimal("0.01"))
                gross_pnl = ((fill.filled_price - position.average_price) * position.quantity).quantize(Decimal("0.01"))
                net_pnl = (gross_pnl - trade_fee).quantize(Decimal("0.01"))
                portfolio.cash_balance = (portfolio.cash_balance + proceeds - trade_fee).quantize(Decimal("0.01"))
                position.realized_pnl = (position.realized_pnl + net_pnl).quantize(Decimal("0.01"))
                position.quantity = Decimal("0.000000")
                position.market_value = Decimal("0.00")
                position.last_price = fill.filled_price
                position.closed_at = fill.filled_at
                position.save(update_fields=["realized_pnl", "quantity", "market_value", "last_price", "closed_at", "updated_at"])
                _record_signal(
                    deployment=deployment,
                    symbol=symbol,
                    signal_type="exit",
                    strength=Decimal("1"),
                    context={"price": str(fill.filled_price), "reason": "rule_exit"},
                )
                signals_created += 1
                orders_created += 1
                continue

            if has_position:
                _record_signal(
                    deployment=deployment,
                    symbol=symbol,
                    signal_type="hold",
                    strength=Decimal("0.2500"),
                    context={"price": str(current_price), "position": "open"},
                )
                signals_created += 1
                continue

            available_cash = max(portfolio.cash_balance - reserve_cash, Decimal("0"))
            quantity = _target_order_quantity(
                definition=definition,
                current_equity=current_equity,
                cash_balance=available_cash,
                current_price=current_price,
            )
            if entry_signal and quantity > 0:
                order = _submit_order(
                    deployment=deployment,
                    portfolio=portfolio,
                    symbol=symbol,
                    side="buy",
                    quantity=quantity,
                    market_price=current_price,
                    signal_type="entry",
                )
                fill = adapter.submit_market_order(order=order, market_price=current_price, slippage_bps=slippage_bps)
                cost = (fill.filled_price * quantity).quantize(Decimal("0.01"))
                portfolio.cash_balance = (portfolio.cash_balance - cost - trade_fee).quantize(Decimal("0.01"))
                Position.objects.update_or_create(
                    portfolio=portfolio,
                    symbol=symbol,
                    defaults={
                        "quantity": quantity,
                        "average_price": fill.filled_price,
                        "last_price": fill.filled_price,
                        "market_value": cost,
                        "opened_at": fill.filled_at,
                        "closed_at": None,
                    },
                )
                _record_signal(
                    deployment=deployment,
                    symbol=symbol,
                    signal_type="entry",
                    strength=Decimal("1"),
                    context={"price": str(fill.filled_price), "quantity": str(quantity)},
                )
                signals_created += 1
                orders_created += 1
            elif entry_signal:
                _record_signal(
                    deployment=deployment,
                    symbol=symbol,
                    signal_type="skip",
                    strength=Decimal("0.5000"),
                    context={"reason": "insufficient_cash", "price": str(current_price)},
                )
                signals_created += 1

        portfolio.save(update_fields=["cash_balance", "updated_at"])
        _update_position_marks(portfolio=portfolio, prices_by_symbol=prices_by_symbol)
        deployment.last_run_at = timezone.now()
        deployment.next_run_at = compute_next_run_at(deployment.schedule_expression or definition["metadata"]["schedule"]["value"], deployment.last_run_at)
        deployment.last_error = ""
        deployment.save(update_fields=["last_run_at", "next_run_at", "last_error", "updated_at"])
        heartbeat.status = HeartbeatStatusChoices.COMPLETED
        heartbeat.completed_at = timezone.now()
        heartbeat.summary = {
            "signals_created": signals_created,
            "orders_created": orders_created,
            "cash_balance": str(portfolio.cash_balance),
            "equity_value": str(portfolio.equity_value),
        }
        heartbeat.save(update_fields=["status", "completed_at", "summary", "updated_at"])
        create_broker_event(
            broker_account=deployment.broker_account,
            portfolio=portfolio,
            deployment=deployment,
            event_type="evaluation_completed",
            message="Deployment evaluation completed successfully.",
            payload=heartbeat.summary,
        )
        record_audit_event(
            organization=deployment.organization,
            actor=deployment.created_by,
            category="trading",
            verb="evaluate-deployment",
            target_type="deployment",
            target_id=str(deployment.id),
            payload={"trigger_type": trigger_type, **heartbeat.summary},
        )
        return heartbeat
    except Exception as exc:
        heartbeat.status = HeartbeatStatusChoices.FAILED
        heartbeat.completed_at = timezone.now()
        heartbeat.error_message = str(exc)
        heartbeat.save(update_fields=["status", "completed_at", "error_message", "updated_at"])
        deployment.last_error = str(exc)
        deployment.last_run_at = timezone.now()
        deployment.next_run_at = compute_next_run_at(deployment.schedule_expression or definition["metadata"]["schedule"]["value"], deployment.last_run_at)
        deployment.save(update_fields=["last_error", "last_run_at", "next_run_at", "updated_at"])
        create_broker_event(
            broker_account=deployment.broker_account,
            portfolio=portfolio,
            deployment=deployment,
            event_type="evaluation_failed",
            message="Deployment evaluation failed.",
            payload={"error": str(exc)},
        )
        raise


def sync_due_live_deployments():
    now = timezone.now()
    processed: list[str] = []
    queryset = LiveDeployment.objects.filter(status="active").select_related("portfolio", "broker_account", "strategy_version")
    for deployment in queryset:
        if deployment.next_run_at and deployment.next_run_at > now:
            continue
        try:
            evaluate_live_deployment(deployment=deployment, trigger_type=HeartbeatTriggerChoices.SCHEDULED)
            processed.append(str(deployment.id))
        except Exception:
            processed.append(f"{deployment.id}:failed")
    return processed


def build_live_dashboard(organization):
    broker_accounts = BrokerAccount.objects.filter(organization=organization).order_by("name")
    portfolios = Portfolio.objects.filter(organization=organization).prefetch_related("positions", "orders").order_by("name")
    deployments = (
        LiveDeployment.objects.filter(organization=organization)
        .select_related("portfolio", "broker_account", "strategy_version", "strategy_version__strategy")
        .prefetch_related("signals", "orders", "heartbeats", "events")
        .order_by("-created_at")
    )
    events = BrokerEvent.objects.filter(broker_account__organization=organization).select_related("deployment", "portfolio", "order")[:30]
    heartbeats = LiveHeartbeat.objects.filter(deployment__organization=organization).select_related("deployment")[:20]

    active_positions = Position.objects.filter(portfolio__organization=organization, quantity__gt=0).select_related("portfolio")
    open_orders = Order.objects.filter(portfolio__organization=organization).exclude(status=OrderStatusChoices.FILLED).select_related("portfolio", "deployment")[:20]

    total_equity = sum((portfolio.equity_value for portfolio in portfolios), Decimal("0"))
    total_cash = sum((portfolio.cash_balance for portfolio in portfolios), Decimal("0"))
    return {
        "summary": {
            "broker_accounts": broker_accounts.count(),
            "portfolios": portfolios.count(),
            "deployments_total": deployments.count(),
            "deployments_active": deployments.filter(status="active").count(),
            "positions_open": active_positions.count(),
            "orders_open": open_orders.count(),
            "total_equity": str(total_equity.quantize(Decimal("0.01"))),
            "total_cash": str(total_cash.quantize(Decimal("0.01"))),
        },
        "recent_events": list(events),
        "recent_heartbeats": list(heartbeats),
        "open_positions": list(active_positions),
        "open_orders": list(open_orders),
    }
