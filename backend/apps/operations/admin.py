from django.contrib import admin

from apps.operations.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("category", "verb", "target_type", "actor", "organization", "created_at")
    list_filter = ("category", "verb", "organization")
    search_fields = ("target_type", "target_id", "actor__username")

