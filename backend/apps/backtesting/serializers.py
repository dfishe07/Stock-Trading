from __future__ import annotations

from rest_framework import serializers

from apps.backtesting.catalog import get_stock_universe_catalog
from apps.backtesting.models import BacktestArtifact, BacktestMetricSnapshot, BacktestRun, BacktestTrade
from apps.backtesting.services import create_backtest_run, execute_backtest_run
from apps.strategies.models import StrategyVersion


class UniverseStockSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    name = serializers.CharField()
    sector = serializers.CharField()
    industry = serializers.CharField()


class BacktestTradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestTrade
        fields = "__all__"


class BacktestMetricSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestMetricSnapshot
        fields = "__all__"


class BacktestArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestArtifact
        fields = "__all__"


class BacktestRunSerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy_version.strategy.name", read_only=True)
    strategy_version_number = serializers.IntegerField(source="strategy_version.version_number", read_only=True)
    metrics = BacktestMetricSnapshotSerializer(source="metric_snapshots", many=True, read_only=True)
    artifacts = BacktestArtifactSerializer(many=True, read_only=True)
    trades = BacktestTradeSerializer(many=True, read_only=True)

    class Meta:
        model = BacktestRun
        fields = (
            "id",
            "run_name",
            "status",
            "strategy_version",
            "strategy_name",
            "strategy_version_number",
            "start_date",
            "end_date",
            "initial_cash",
            "benchmark_symbol",
            "universe_symbols",
            "run_parameters",
            "result_summary",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
            "metrics",
            "artifacts",
            "trades",
        )


class BacktestRunCreateSerializer(serializers.Serializer):
    strategy_version_id = serializers.UUIDField()
    run_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    initial_cash = serializers.DecimalField(max_digits=18, decimal_places=2, default="100000.00")
    benchmark_symbol = serializers.CharField(max_length=16, required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context["request"]
        try:
            strategy_version = StrategyVersion.objects.select_related("strategy", "strategy__organization").get(pk=attrs["strategy_version_id"])
        except StrategyVersion.DoesNotExist as exc:
            raise serializers.ValidationError({"strategy_version_id": "Strategy version not found."}) from exc

        if strategy_version.strategy.organization_id != request.organization.id:
            raise serializers.ValidationError({"strategy_version_id": "Strategy version is outside the active organization."})
        if attrs["start_date"] >= attrs["end_date"]:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})
        attrs["strategy_version"] = strategy_version
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        run = create_backtest_run(
            organization=request.organization,
            user=request.user,
            strategy_version=validated_data["strategy_version"],
            run_name=validated_data.get("run_name", ""),
            start_date=validated_data["start_date"],
            end_date=validated_data["end_date"],
            initial_cash=validated_data["initial_cash"],
            benchmark_symbol=validated_data.get("benchmark_symbol"),
        )
        return execute_backtest_run(run)


class BacktestUniverseSerializer(serializers.Serializer):
    items = UniverseStockSerializer(many=True)

    @staticmethod
    def build_payload():
        return {"items": get_stock_universe_catalog()}

