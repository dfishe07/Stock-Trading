from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.access.models import Organization
from apps.common.models import TimeStampedUUIDModel
from apps.strategies.models import StrategyVersion


class BacktestRunStatusChoices(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class BacktestRun(TimeStampedUUIDModel):
    organization = models.ForeignKey(Organization, related_name="backtest_runs", on_delete=models.CASCADE)
    strategy_version = models.ForeignKey(StrategyVersion, related_name="backtest_runs", on_delete=models.CASCADE)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="backtest_runs", null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=32, choices=BacktestRunStatusChoices.choices, default=BacktestRunStatusChoices.QUEUED)
    run_name = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    initial_cash = models.DecimalField(max_digits=18, decimal_places=2, default=100000)
    benchmark_symbol = models.CharField(max_length=16, blank=True)
    universe_symbols = models.JSONField(default=list, blank=True)
    run_parameters = models.JSONField(default=dict, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    engine_version = models.CharField(max_length=32, default="phase2-v1")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.run_name or f"Backtest {self.pk}"


class BacktestTrade(TimeStampedUUIDModel):
    run = models.ForeignKey(BacktestRun, related_name="trades", on_delete=models.CASCADE)
    symbol = models.CharField(max_length=16)
    side = models.CharField(max_length=8, default="long")
    entry_date = models.DateField()
    exit_date = models.DateField(null=True, blank=True)
    entry_price = models.DecimalField(max_digits=18, decimal_places=4)
    exit_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    gross_pnl = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_pnl = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    return_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    exit_reason = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["entry_date", "symbol"]


class BacktestMetricSnapshot(TimeStampedUUIDModel):
    run = models.ForeignKey(BacktestRun, related_name="metric_snapshots", on_delete=models.CASCADE)
    metric_type = models.CharField(max_length=64, default="summary")
    label = models.CharField(max_length=128)
    value = models.DecimalField(max_digits=18, decimal_places=6)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["metric_type", "label"]


class BacktestArtifact(TimeStampedUUIDModel):
    run = models.ForeignKey(BacktestRun, related_name="artifacts", on_delete=models.CASCADE)
    artifact_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["artifact_type"]

