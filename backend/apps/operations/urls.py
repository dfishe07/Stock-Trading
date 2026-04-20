from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.operations.views import AuditEventViewSet, HealthView

router = DefaultRouter()
router.register("audit-events", AuditEventViewSet, basename="audit-event")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("", include(router.urls)),
]
