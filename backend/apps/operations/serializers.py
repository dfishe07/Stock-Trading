from rest_framework import serializers

from apps.operations.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditEvent
        fields = "__all__"

