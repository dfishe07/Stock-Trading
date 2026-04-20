from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.backtesting.catalog import get_stock_universe_catalog
from apps.backtesting.engine import run_backtest_engine
from apps.backtesting.models import (
    BacktestArtifact,
    BacktestMetricSnapshot,
    BacktestRun,
    BacktestRunStatusChoices,
    BacktestTrade,
)
from apps.operations.services import record_audit_event
from apps.strategies.services import validate_strategy_definition


def get_universe_catalog():
    return get_stock_universe_catalog()


def _to_decimal(value: float, places: str = "0.0001"):
    return Decimal(str(value)).quantize(Decimal(places))


@transaction.atomic
def create_backtest_run(*, organization, user, strategy_version, run_name: str, start_date, end_date, initial_cash: Decimal, benchmark_symbol: str | None = None):
    definition = strategy_version.definition
    validation_errors = validate_strategy_definition(definition)
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    run = BacktestRun.objects.create(
        organization=organization,
        requested_by=user,
        strategy_version=strategy_version,
        status=BacktestRunStatusChoices.QUEUED,
        run_name=run_name,
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        benchmark_symbol=(benchmark_symbol or "").upper(),
        universe_symbols=[symbol.upper() for symbol in definition["universe"]["symbols"]],
        run_parameters={"schema_version": definition.get("schemaVersion", "1.0")},
    )
    record_audit_event(
        organization=organization,
        actor=user,
        category="backtest",
        verb="create-run",
        target_type="backtest-run",
        target_id=str(run.id),
        payload={"strategy_version": str(strategy_version.id)},
    )
    return run


@transaction.atomic
def execute_backtest_run(run: BacktestRun):
    run.status = BacktestRunStatusChoices.RUNNING
    run.started_at = timezone.now()
    run.error_message = ""
    run.save(update_fields=["status", "started_at", "error_message", "updated_at"])

    try:
        result = run_backtest_engine(
            definition=run.strategy_version.definition,
            start_date=run.start_date,
            end_date=run.end_date,
            initial_cash=float(run.initial_cash),
            benchmark_symbol=run.benchmark_symbol or None,
        )
    except Exception as exc:
        run.status = BacktestRunStatusChoices.FAILED
        run.completed_at = timezone.now()
        run.error_message = str(exc)
        run.save(update_fields=["status", "completed_at", "error_message", "updated_at"])
        raise

    run.status = BacktestRunStatusChoices.COMPLETED
    run.completed_at = timezone.now()
    run.result_summary = result["summary"]
    run.save(update_fields=["status", "completed_at", "result_summary", "updated_at"])

    run.metric_snapshots.all().delete()
    run.artifacts.all().delete()
    run.trades.all().delete()

    for label, value in result["summary"].items():
        if isinstance(value, (int, float)) and value is not None:
            BacktestMetricSnapshot.objects.create(
                run=run,
                metric_type="summary",
                label=label,
                value=_to_decimal(float(value), "0.000001"),
            )

    for trade in result["trades"]:
        BacktestTrade.objects.create(
            run=run,
            symbol=trade["symbol"],
            side="long",
            entry_date=trade["entry_date"],
            exit_date=trade["exit_date"],
            entry_price=_to_decimal(trade["entry_price"], "0.0001"),
            exit_price=_to_decimal(trade["exit_price"], "0.0001"),
            quantity=_to_decimal(trade["quantity"], "0.000001"),
            gross_pnl=_to_decimal(trade["gross_pnl"], "0.01"),
            net_pnl=_to_decimal(trade["net_pnl"], "0.01"),
            return_pct=_to_decimal(trade["return_pct"], "0.0001"),
            exit_reason=trade["exit_reason"],
            metadata={
                "max_favorable_excursion_pct": round(trade["max_favorable_excursion"], 4),
                "max_adverse_excursion_pct": round(trade["max_adverse_excursion"], 4),
            },
        )

    BacktestArtifact.objects.create(run=run, artifact_type="equity_curve", payload={"points": result["equity_curve"]})
    BacktestArtifact.objects.create(run=run, artifact_type="signal_log", payload={"events": result["signal_log"][:250]})
    BacktestArtifact.objects.create(
        run=run,
        artifact_type="execution_readiness",
        payload={
            "engine_version": run.engine_version,
            "validated_at": timezone.now().isoformat(),
            "supports_live_transition": True,
            "notes": "The stored strategy definition is compatible with the shared indicator and rule engine used for backtests and future live execution.",
        },
    )

    record_audit_event(
        organization=run.organization,
        actor=run.requested_by,
        category="backtest",
        verb="complete-run",
        target_type="backtest-run",
        target_id=str(run.id),
        payload={"status": run.status, "total_trades": result["summary"]["total_trades"]},
    )
    return run

