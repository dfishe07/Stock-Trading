from celery import shared_task

from apps.trading.services import sync_due_live_deployments


@shared_task
def sync_live_deployments() -> str:
    processed = sync_due_live_deployments()
    return f"Processed {len(processed)} live deployments."
