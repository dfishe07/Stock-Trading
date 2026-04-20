from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.access.permissions import IsDeveloperOrAdmin
from apps.access.views import OrganizationScopedAPIView, OrganizationScopedViewSet
from apps.trading.models import BrokerAccount, LiveDeployment, Portfolio
from apps.trading.serializers import (
    BrokerAccountSerializer,
    LiveDashboardSerializer,
    LiveDeploymentCreateSerializer,
    LiveDeploymentSerializer,
    PortfolioSerializer,
    TradingCatalogSerializer,
)
from apps.trading.services import HeartbeatTriggerChoices, compute_next_run_at, evaluate_live_deployment


class TradingCatalogView(OrganizationScopedAPIView):
    def get(self, request):
        return Response(TradingCatalogSerializer.build_payload())


class TradingDashboardView(OrganizationScopedAPIView):
    def get(self, request):
        payload = LiveDashboardSerializer.build_payload(request.organization)
        return Response(LiveDashboardSerializer(payload).data)


class OrganizationTradingViewSet(OrganizationScopedViewSet):
    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "activate", "pause", "stop", "run_now"}:
            return [IsDeveloperOrAdmin()]
        return super().get_permissions()


class BrokerAccountViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    OrganizationTradingViewSet,
):
    queryset = BrokerAccount.objects.all()
    serializer_class = BrokerAccountSerializer

    def get_queryset(self):
        organization = self.request.organization
        if not organization:
            return self.queryset.none()
        return self.queryset.filter(organization=organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)


class PortfolioViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    OrganizationTradingViewSet,
):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        organization = self.request.organization
        if not organization:
            return self.queryset.none()
        return self.queryset.filter(organization=organization).select_related("broker_account")

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)


class LiveDeploymentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    OrganizationTradingViewSet,
):
    queryset = LiveDeployment.objects.all()
    serializer_class = LiveDeploymentSerializer

    def get_queryset(self):
        organization = self.request.organization
        if not organization:
            return self.queryset.none()
        return self.queryset.filter(organization=organization).select_related(
            "portfolio",
            "strategy_version",
            "strategy_version__strategy",
            "broker_account",
        ).prefetch_related("signals", "orders", "heartbeats")

    def get_serializer_class(self):
        if self.action == "create":
            return LiveDeploymentCreateSerializer
        return LiveDeploymentSerializer

    def perform_create(self, serializer):
        schedule_expression = serializer.validated_data.get(
            "schedule_expression",
            serializer.validated_data["strategy_version"].definition["metadata"]["schedule"]["value"],
        )
        serializer.save(
            organization=self.request.organization,
            created_by=self.request.user,
            next_run_at=compute_next_run_at(schedule_expression),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        deployment = serializer.save(
            organization=request.organization,
            created_by=request.user,
            next_run_at=compute_next_run_at(
                serializer.validated_data.get(
                    "schedule_expression",
                    serializer.validated_data["strategy_version"].definition["metadata"]["schedule"]["value"],
                )
            ),
        )
        return Response(LiveDeploymentSerializer(deployment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        deployment = self.get_object()
        deployment.status = "active"
        deployment.next_run_at = compute_next_run_at(
            deployment.schedule_expression or deployment.strategy_version.definition["metadata"]["schedule"]["value"]
        )
        deployment.last_error = ""
        deployment.save(update_fields=["status", "next_run_at", "last_error", "updated_at"])
        return Response(LiveDeploymentSerializer(deployment).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        deployment = self.get_object()
        deployment.status = "paused"
        deployment.save(update_fields=["status", "updated_at"])
        return Response(LiveDeploymentSerializer(deployment).data)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        deployment = self.get_object()
        deployment.status = "stopped"
        deployment.next_run_at = None
        deployment.save(update_fields=["status", "next_run_at", "updated_at"])
        return Response(LiveDeploymentSerializer(deployment).data)

    @action(detail=True, methods=["post"], permission_classes=[IsDeveloperOrAdmin])
    def run_now(self, request, pk=None):
        deployment = self.get_object()
        evaluate_live_deployment(deployment=deployment, trigger_type=HeartbeatTriggerChoices.MANUAL)
        deployment.refresh_from_db()
        return Response(LiveDeploymentSerializer(deployment).data)
