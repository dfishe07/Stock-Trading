from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.trading.views import BrokerAccountViewSet, LiveDeploymentViewSet, PortfolioViewSet, TradingCatalogView, TradingDashboardView

router = DefaultRouter()
router.register("broker-accounts", BrokerAccountViewSet, basename="broker-account")
router.register("portfolios", PortfolioViewSet, basename="portfolio")
router.register("deployments", LiveDeploymentViewSet, basename="deployment")

urlpatterns = [
    path("catalog/", TradingCatalogView.as_view()),
    path("dashboard/", TradingDashboardView.as_view()),
    path("", include(router.urls)),
]
