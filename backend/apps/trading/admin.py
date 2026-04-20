from django.contrib import admin

from apps.trading.models import BrokerAccount, BrokerEvent, LiveDeployment, LiveHeartbeat, LiveSignal, Order, Portfolio, Position


@admin.register(BrokerAccount)
class BrokerAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "provider", "account_mode", "is_active")
    list_filter = ("provider", "account_mode", "organization")


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "broker_account", "base_currency", "is_active")
    list_filter = ("organization", "broker_account")


@admin.register(LiveDeployment)
class LiveDeploymentAdmin(admin.ModelAdmin):
    list_display = ("strategy_version", "portfolio", "broker_account", "status", "next_run_at")
    list_filter = ("status", "organization")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "symbol", "quantity", "market_value")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "symbol", "side", "quantity", "status", "submitted_at")
    list_filter = ("status", "broker_account")


@admin.register(LiveSignal)
class LiveSignalAdmin(admin.ModelAdmin):
    list_display = ("deployment", "symbol", "signal_type", "strength", "created_at")


@admin.register(LiveHeartbeat)
class LiveHeartbeatAdmin(admin.ModelAdmin):
    list_display = ("deployment", "trigger_type", "status", "started_at", "completed_at")
    list_filter = ("trigger_type", "status")


@admin.register(BrokerEvent)
class BrokerEventAdmin(admin.ModelAdmin):
    list_display = ("broker_account", "event_type", "message", "created_at")
    list_filter = ("event_type", "broker_account")
