from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone

from apps.operations.services import record_audit_event
from apps.trading.models import BrokerAccount, BrokerEvent, Order, OrderStatusChoices


@dataclass
class FillResult:
    requested_price: Decimal
    filled_price: Decimal
    filled_at: object
    external_order_id: str


class PaperBrokerAdapter:
    def __init__(self, broker_account: BrokerAccount):
        self.broker_account = broker_account

    def submit_market_order(self, *, order: Order, market_price: Decimal, slippage_bps: Decimal) -> FillResult:
        raise NotImplementedError


class AlpacaPaperBrokerAdapter(PaperBrokerAdapter):
    def submit_market_order(self, *, order: Order, market_price: Decimal, slippage_bps: Decimal) -> FillResult:
        direction = Decimal("1") if order.side == "buy" else Decimal("-1")
        price_adjustment = Decimal("1") + ((slippage_bps / Decimal("10000")) * direction)
        filled_price = (market_price * price_adjustment).quantize(Decimal("0.0001"))
        filled_at = timezone.now()
        external_order_id = f"alpaca-paper-{uuid4()}"

        order.status = OrderStatusChoices.FILLED
        order.requested_price = market_price
        order.filled_price = filled_price
        order.submitted_at = filled_at
        order.filled_at = filled_at
        order.external_order_id = external_order_id
        order.rejection_reason = ""
        order.save(
            update_fields=[
                "status",
                "requested_price",
                "filled_price",
                "submitted_at",
                "filled_at",
                "external_order_id",
                "rejection_reason",
                "updated_at",
            ]
        )

        BrokerEvent.objects.create(
            broker_account=self.broker_account,
            portfolio=order.portfolio,
            deployment=order.deployment,
            order=order,
            event_type="order_filled",
            message=f"{order.side.upper()} {order.symbol} filled via Alpaca paper adapter.",
            payload={
                "quantity": str(order.quantity),
                "requested_price": str(market_price),
                "filled_price": str(filled_price),
                "external_order_id": external_order_id,
            },
        )
        record_audit_event(
            organization=self.broker_account.organization,
            actor=order.deployment.created_by if order.deployment else None,
            category="trading",
            verb="paper-fill",
            target_type="order",
            target_id=str(order.id),
            payload={"symbol": order.symbol, "side": order.side, "filled_price": str(filled_price)},
        )
        return FillResult(
            requested_price=market_price,
            filled_price=filled_price,
            filled_at=filled_at,
            external_order_id=external_order_id,
        )


def get_broker_adapter(broker_account: BrokerAccount) -> PaperBrokerAdapter:
    if broker_account.provider == "alpaca":
        return AlpacaPaperBrokerAdapter(broker_account)
    raise ValueError(f"Unsupported broker provider '{broker_account.provider}'.")
