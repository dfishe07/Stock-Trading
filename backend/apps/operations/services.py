from apps.operations.models import AuditEvent


def record_audit_event(*, organization=None, actor=None, category: str, verb: str, target_type: str, target_id: str = "", payload=None):
    return AuditEvent.objects.create(
        organization=organization,
        actor=actor,
        category=category,
        verb=verb,
        target_type=target_type,
        target_id=target_id,
        payload=payload or {},
    )

