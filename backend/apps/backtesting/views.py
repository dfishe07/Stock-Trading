from rest_framework import mixins, status
from rest_framework.response import Response

from apps.access.permissions import IsDeveloperOrAdmin
from apps.access.views import OrganizationScopedAPIView, OrganizationScopedViewSet
from apps.backtesting.catalog import get_stock_universe_catalog
from apps.backtesting.models import BacktestRun
from apps.backtesting.serializers import BacktestRunCreateSerializer, BacktestRunSerializer


class BacktestUniverseView(OrganizationScopedAPIView):
    def get(self, request):
        return Response({"items": get_stock_universe_catalog()})


class BacktestRunViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, OrganizationScopedViewSet):
    queryset = BacktestRun.objects.all().select_related("strategy_version", "strategy_version__strategy")

    def get_permissions(self):
        if self.action == "create":
            return [IsDeveloperOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        organization = self.request.organization
        if not organization:
            return self.queryset.none()
        return self.queryset.filter(organization=organization).prefetch_related("metric_snapshots", "artifacts", "trades")

    def get_serializer_class(self):
        if self.action == "create":
            return BacktestRunCreateSerializer
        return BacktestRunSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        run = serializer.save()
        return Response(BacktestRunSerializer(run).data, status=status.HTTP_201_CREATED)
