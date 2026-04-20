from __future__ import annotations

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import IsDeveloperOrAdmin
from apps.access.views import OrganizationScopedAPIView, OrganizationScopedViewSet
from apps.strategies.models import Strategy
from apps.strategies.serializers import (
    StrategyCreateSerializer,
    StrategySerializer,
    StrategyUpdateSerializer,
    StrategyVersionCreateSerializer,
    StrategyVersionSerializer,
)
from apps.strategies.services import get_strategy_builder_schema, publish_strategy_version


class StrategySchemaView(OrganizationScopedAPIView):
    def get(self, request):
        return Response(get_strategy_builder_schema())


class StrategyViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    OrganizationScopedViewSet,
):
    queryset = Strategy.objects.all().select_related("latest_version").prefetch_related("versions")

    def get_queryset(self):
        organization = self.request.organization
        if not organization:
            return self.queryset.none()
        return self.queryset.filter(organization=organization)

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "publish"}:
            return [IsDeveloperOrAdmin()]
        if self.action == "versions" and self.request.method.lower() == "post":
            return [IsDeveloperOrAdmin()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return StrategyCreateSerializer
        if self.action in {"update", "partial_update"}:
            return StrategyUpdateSerializer
        return StrategySerializer

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="versions")
    def versions(self, request, pk=None):
        strategy = self.get_object()
        if request.method.lower() == "get":
            serializer = StrategyVersionSerializer(strategy.versions.all(), many=True)
            return Response(serializer.data)

        serializer = StrategyVersionCreateSerializer(
            data=request.data,
            context={"request": request, "strategy": strategy},
        )
        serializer.is_valid(raise_exception=True)
        version = serializer.save()
        return Response(StrategyVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="publish/(?P<version_id>[^/.]+)")
    def publish(self, request, pk=None, version_id=None):
        strategy = self.get_object()
        version = strategy.versions.filter(pk=version_id).first()
        if not version:
            return Response({"detail": "Version not found."}, status=status.HTTP_404_NOT_FOUND)
        publish_strategy_version(version=version, actor=request.user)
        return Response(StrategyVersionSerializer(version).data)
