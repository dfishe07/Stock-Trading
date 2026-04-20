from celery import shared_task


@shared_task
def heartbeat() -> str:
    return "ok"
