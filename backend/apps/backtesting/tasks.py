from celery import shared_task

from apps.backtesting.models import BacktestRun
from apps.backtesting.services import execute_backtest_run


@shared_task
def execute_backtest_run_task(run_id: str):
    run = BacktestRun.objects.get(pk=run_id)
    execute_backtest_run(run)
    return str(run.id)

