from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.access.urls")),
    path("api/strategies/", include("apps.strategies.urls")),
    path("api/backtests/", include("apps.backtesting.urls")),
    path("api/trading/", include("apps.trading.urls")),
    path("api/operations/", include("apps.operations.urls")),
]
