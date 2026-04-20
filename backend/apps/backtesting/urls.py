from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.backtesting.views import BacktestRunViewSet, BacktestUniverseView

router = DefaultRouter()
router.register("runs", BacktestRunViewSet, basename="backtest-run")

urlpatterns = [
    path("universe/", BacktestUniverseView.as_view(), name="backtest-universe"),
    path("", include(router.urls)),
]

