from rest_framework import mixins
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import IsAdmin
from apps.access.views import OrganizationScopedViewSet
from apps.operations.models import AuditEvent
from apps.operations.serializers import AuditEventSerializer


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class AuditEventViewSet(mixins.ListModelMixin, OrganizationScopedViewSet):
    serializer_class = AuditEventSerializer

    def get_permissions(self):
        return [IsAdmin()]

    def get_queryset(self):
        organization = getattr(self.request, "organization", None)
        if not organization:
            return AuditEvent.objects.none()
        return AuditEvent.objects.filter(organization=organization)
