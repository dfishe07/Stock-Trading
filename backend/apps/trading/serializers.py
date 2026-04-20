from rest_framework import serializers

from apps.backtesting.catalog import get_stock_universe_catalog
from apps.strategies.models import StrategyVersion
from apps.strategies.services import get_strategy_execution_readiness
from apps.trading.models import (
    BrokerAccount,
    BrokerEvent,
    LiveDeployment,
    LiveHeartbeat,
    LiveSignal,
    Order,
    Portfolio,
    Position,
)
from apps.trading.services import SUPPORTED_DEPLOYMENT_SCHEDULES, build_live_dashboard


class BrokerAccountSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    account_mode_label = serializers.CharField(source="get_account_mode_display", read_only=True)

    class Meta:
        model = BrokerAccount
        fields = (
            "id",
            "organization",
            "name",
            "provider",
            "provider_label",
            "account_mode",
            "account_mode_label",
            "external_account_id",
            "credentials_reference",
            "settings",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("organization", "created_at", "updated_at")

    def validate(self, attrs):
        if attrs.get("account_mode", getattr(self.instance, "account_mode", "paper")) != "paper":
            raise serializers.ValidationError({"account_mode": "Phase 3 only supports paper broker accounts."})
        return attrs


class PortfolioSerializer(serializers.ModelSerializer):
    broker_account_name = serializers.CharField(source="broker_account.name", read_only=True)

    class Meta:
        model = Portfolio
        fields = (
            "id",
            "organization",
            "broker_account",
            "broker_account_name",
            "name",
            "base_currency",
            "benchmark_symbol",
            "starting_cash",
            "cash_balance",
            "equity_value",
            "realized_pnl",
            "unrealized_pnl",
            "cash_reserve_percent",
            "last_synced_at",
            "metadata",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("organization", "created_at", "updated_at")

    def validate(self, attrs):
        request = self.context.get("request")
        broker_account = attrs.get("broker_account", getattr(self.instance, "broker_account", None))
        if request and broker_account and broker_account.organization_id != request.organization.id:
            raise serializers.ValidationError({"broker_account": "Broker account is outside the active organization."})
        return attrs


class PositionSerializer(serializers.ModelSerializer):
    portfolio_name = serializers.CharField(source="portfolio.name", read_only=True)

    class Meta:
        model = Position
        fields = (
            "id",
            "portfolio",
            "portfolio_name",
            "symbol",
            "quantity",
            "average_price",
            "last_price",
            "market_value",
            "realized_pnl",
            "unrealized_pnl",
            "opened_at",
            "closed_at",
            "created_at",
            "updated_at",
        )


class OrderSerializer(serializers.ModelSerializer):
    portfolio_name = serializers.CharField(source="portfolio.name", read_only=True)
    deployment_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "portfolio",
            "portfolio_name",
            "broker_account",
            "deployment",
            "deployment_name",
            "symbol",
            "side",
            "quantity",
            "order_type",
            "requested_price",
            "filled_price",
            "status",
            "submitted_at",
            "filled_at",
            "external_order_id",
            "rejection_reason",
            "metadata",
            "created_at",
            "updated_at",
        )

    def get_deployment_name(self, obj):
        if obj.deployment_id and obj.deployment and obj.deployment.strategy_version_id:
            return obj.deployment.strategy_version.strategy.name
        return None


class LiveSignalSerializer(serializers.ModelSerializer):
    deployment_name = serializers.SerializerMethodField()

    class Meta:
        model = LiveSignal
        fields = ("id", "deployment", "deployment_name", "symbol", "signal_type", "strength", "context", "created_at", "updated_at")

    def get_deployment_name(self, obj):
        return obj.deployment.strategy_version.strategy.name


class LiveHeartbeatSerializer(serializers.ModelSerializer):
    deployment_name = serializers.SerializerMethodField()

    class Meta:
        model = LiveHeartbeat
        fields = (
            "id",
            "deployment",
            "deployment_name",
            "trigger_type",
            "status",
            "started_at",
            "completed_at",
            "evaluated_symbols",
            "summary",
            "error_message",
            "created_at",
            "updated_at",
        )

    def get_deployment_name(self, obj):
        return obj.deployment.strategy_version.strategy.name


class BrokerEventSerializer(serializers.ModelSerializer):
    deployment_name = serializers.SerializerMethodField()
    portfolio_name = serializers.CharField(source="portfolio.name", read_only=True)

    class Meta:
        model = BrokerEvent
        fields = (
            "id",
            "broker_account",
            "portfolio",
            "portfolio_name",
            "deployment",
            "deployment_name",
            "order",
            "event_type",
            "message",
            "payload",
            "created_at",
            "updated_at",
        )

    def get_deployment_name(self, obj):
        if obj.deployment_id and obj.deployment:
            return obj.deployment.strategy_version.strategy.name
        return None


class LiveDeploymentSerializer(serializers.ModelSerializer):
    recent_signals = serializers.SerializerMethodField()
    recent_orders = serializers.SerializerMethodField()
    recent_heartbeats = serializers.SerializerMethodField()
    strategy_name = serializers.CharField(source="strategy_version.strategy.name", read_only=True)
    strategy_version_number = serializers.IntegerField(source="strategy_version.version_number", read_only=True)
    portfolio_name = serializers.CharField(source="portfolio.name", read_only=True)
    broker_account_name = serializers.CharField(source="broker_account.name", read_only=True)
    execution_readiness = serializers.SerializerMethodField()

    class Meta:
        model = LiveDeployment
        fields = (
            "id",
            "organization",
            "strategy_version",
            "strategy_name",
            "strategy_version_number",
            "portfolio",
            "portfolio_name",
            "broker_account",
            "broker_account_name",
            "status",
            "schedule_expression",
            "last_run_at",
            "next_run_at",
            "last_error",
            "created_by",
            "configuration",
            "recent_signals",
            "recent_orders",
            "recent_heartbeats",
            "execution_readiness",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "organization",
            "created_by",
            "created_at",
            "updated_at",
            "recent_signals",
            "recent_orders",
            "recent_heartbeats",
            "strategy_name",
            "strategy_version_number",
            "portfolio_name",
            "broker_account_name",
            "execution_readiness",
        )

    def get_recent_signals(self, obj):
        return LiveSignalSerializer(obj.signals.all()[:10], many=True).data

    def get_recent_orders(self, obj):
        return OrderSerializer(obj.orders.all()[:10], many=True).data

    def get_recent_heartbeats(self, obj):
        return LiveHeartbeatSerializer(obj.heartbeats.all()[:5], many=True).data

    def get_execution_readiness(self, obj):
        return get_strategy_execution_readiness(obj.strategy_version.definition)


class LiveDeploymentCreateSerializer(serializers.ModelSerializer):
    strategy_version = serializers.PrimaryKeyRelatedField(queryset=StrategyVersion.objects.select_related("strategy"))

    class Meta:
        model = LiveDeployment
        fields = ("strategy_version", "portfolio", "broker_account", "status", "schedule_expression", "configuration")

    def validate_schedule_expression(self, value):
        if value and value not in SUPPORTED_DEPLOYMENT_SCHEDULES:
            raise serializers.ValidationError(f"Schedule must be one of: {', '.join(SUPPORTED_DEPLOYMENT_SCHEDULES)}.")
        return value

    def validate(self, attrs):
        organization = self.context["request"].organization
        portfolio = attrs["portfolio"]
        broker_account = attrs["broker_account"]
        strategy_version = attrs["strategy_version"]
        if portfolio.organization_id != organization.id:
            raise serializers.ValidationError({"portfolio": "Portfolio is outside the active organization."})
        if broker_account.organization_id != organization.id:
            raise serializers.ValidationError({"broker_account": "Broker account is outside the active organization."})
        if strategy_version.strategy.organization_id != organization.id:
            raise serializers.ValidationError({"strategy_version": "Strategy version is outside the active organization."})
        if portfolio.broker_account_id != broker_account.id:
            raise serializers.ValidationError({"broker_account": "Portfolio must use the selected broker account."})
        readiness = get_strategy_execution_readiness(strategy_version.definition)
        if not readiness["is_ready"]:
            raise serializers.ValidationError({"strategy_version": readiness["errors"]})
        return attrs


class LiveDashboardSerializer(serializers.Serializer):
    summary = serializers.DictField()
    recent_events = BrokerEventSerializer(many=True)
    recent_heartbeats = LiveHeartbeatSerializer(many=True)
    open_positions = PositionSerializer(many=True)
    open_orders = OrderSerializer(many=True)

    @staticmethod
    def build_payload(organization):
        return build_live_dashboard(organization)


class TradingCatalogSerializer(serializers.Serializer):
    supported_schedules = serializers.ListField(child=serializers.CharField())
    stock_universe = serializers.ListField(child=serializers.DictField())
    supported_broker_providers = serializers.ListField(child=serializers.CharField())
    supported_account_modes = serializers.ListField(child=serializers.CharField())

    @staticmethod
    def build_payload():
        return {
            "supported_schedules": SUPPORTED_DEPLOYMENT_SCHEDULES,
            "stock_universe": get_stock_universe_catalog(),
            "supported_broker_providers": ["alpaca"],
            "supported_account_modes": ["paper"],
        }
