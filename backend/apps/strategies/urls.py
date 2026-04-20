from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.strategies.views import StrategySchemaView, StrategyViewSet

router = DefaultRouter()
router.register("", StrategyViewSet, basename="strategy")

urlpatterns = [
    path("schema/", StrategySchemaView.as_view(), name="strategy-schema"),
    path("", include(router.urls)),
]

