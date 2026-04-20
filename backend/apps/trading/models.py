from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.access.models import Organization
from apps.common.models import TimeStampedUUIDModel
from apps.strategies.models import StrategyVersion


class BrokerProviderChoices(models.TextChoices):
    ALPACA = "alpaca", "Alpaca"


class BrokerAccountModeChoices(models.TextChoices):
    PAPER = "paper", "Paper"
    LIVE = "live", "Live"


class BrokerAccount(TimeStampedUUIDModel):
    organization = models.ForeignKey(Organization, related_name="broker_accounts", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=64, choices=BrokerProviderChoices.choices, default=BrokerProviderChoices.ALPACA)
    account_mode = models.CharField(max_length=32, choices=BrokerAccountModeChoices.choices, default=BrokerAccountModeChoices.PAPER)
    external_account_id = models.CharField(max_length=255, blank=True)
    credentials_reference = models.CharField(max_length=255, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Portfolio(TimeStampedUUIDModel):
    organization = models.ForeignKey(Organization, related_name="portfolios", on_delete=models.CASCADE)
    broker_account = models.ForeignKey(BrokerAccount, related_name="portfolios", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    base_currency = models.CharField(max_length=8, default="USD")
    benchmark_symbol = models.CharField(max_length=16, blank=True)
    starting_cash = models.DecimalField(max_digits=18, decimal_places=2, default=100000)
    cash_balance = models.DecimalField(max_digits=18, decimal_places=2, default=100000)
    equity_value = models.DecimalField(max_digits=18, decimal_places=2, default=100000)
    realized_pnl = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    cash_reserve_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class DeploymentStatusChoices(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    STOPPED = "stopped", "Stopped"


class LiveDeployment(TimeStampedUUIDModel):
    organization = models.ForeignKey(Organization, related_name="live_deployments", on_delete=models.CASCADE)
    strategy_version = models.ForeignKey(StrategyVersion, related_name="deployments", on_delete=models.CASCADE)
    portfolio = models.ForeignKey(Portfolio, related_name="deployments", on_delete=models.CASCADE)
    broker_account = models.ForeignKey(BrokerAccount, related_name="deployments", on_delete=models.CASCADE)
    status = models.CharField(max_length=32, choices=DeploymentStatusChoices.choices, default=DeploymentStatusChoices.DRAFT)
    schedule_expression = models.CharField(max_length=64, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="live_deployments", null=True, on_delete=models.SET_NULL)
    configuration = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Position(TimeStampedUUIDModel):
    portfolio = models.ForeignKey(Portfolio, related_name="positions", on_delete=models.CASCADE)
    symbol = models.CharField(max_length=16)
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    average_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    last_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    market_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("portfolio", "symbol")
        ordering = ["symbol"]


class OrderStatusChoices(models.TextChoices):
    PENDING = "pending", "Pending"
    SUBMITTED = "submitted", "Submitted"
    FILLED = "filled", "Filled"
    CANCELLED = "cancelled", "Cancelled"
    REJECTED = "rejected", "Rejected"


class Order(TimeStampedUUIDModel):
    portfolio = models.ForeignKey(Portfolio, related_name="orders", on_delete=models.CASCADE)
    broker_account = models.ForeignKey(BrokerAccount, related_name="orders", on_delete=models.CASCADE)
    deployment = models.ForeignKey(LiveDeployment, related_name="orders", null=True, blank=True, on_delete=models.SET_NULL)
    symbol = models.CharField(max_length=16)
    side = models.CharField(max_length=16)
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    order_type = models.CharField(max_length=16, default="market")
    requested_price = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    filled_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=32, choices=OrderStatusChoices.choices, default=OrderStatusChoices.PENDING)
    submitted_at = models.DateTimeField(null=True, blank=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    external_order_id = models.CharField(max_length=255, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class LiveSignal(TimeStampedUUIDModel):
    deployment = models.ForeignKey(LiveDeployment, related_name="signals", on_delete=models.CASCADE)
    symbol = models.CharField(max_length=16)
    signal_type = models.CharField(max_length=64)
    strength = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class HeartbeatTriggerChoices(models.TextChoices):
    MANUAL = "manual", "Manual"
    SCHEDULED = "scheduled", "Scheduled"
    EVENT = "event", "Event"


class HeartbeatStatusChoices(models.TextChoices):
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class LiveHeartbeat(TimeStampedUUIDModel):
    deployment = models.ForeignKey(LiveDeployment, related_name="heartbeats", on_delete=models.CASCADE)
    trigger_type = models.CharField(max_length=32, choices=HeartbeatTriggerChoices.choices, default=HeartbeatTriggerChoices.MANUAL)
    status = models.CharField(max_length=32, choices=HeartbeatStatusChoices.choices, default=HeartbeatStatusChoices.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    evaluated_symbols = models.JSONField(default=list, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]


class BrokerEvent(TimeStampedUUIDModel):
    broker_account = models.ForeignKey(BrokerAccount, related_name="events", on_delete=models.CASCADE)
    portfolio = models.ForeignKey(Portfolio, related_name="events", null=True, blank=True, on_delete=models.SET_NULL)
    deployment = models.ForeignKey(LiveDeployment, related_name="events", null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey(Order, related_name="events", null=True, blank=True, on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=64)
    message = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
