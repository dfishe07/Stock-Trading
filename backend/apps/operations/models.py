from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.access.models import Organization
from apps.common.models import TimeStampedUUIDModel


class AuditEvent(TimeStampedUUIDModel):
    organization = models.ForeignKey(Organization, related_name="audit_events", null=True, blank=True, on_delete=models.SET_NULL)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="audit_events", null=True, blank=True, on_delete=models.SET_NULL)
    category = models.CharField(max_length=64)
    verb = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

