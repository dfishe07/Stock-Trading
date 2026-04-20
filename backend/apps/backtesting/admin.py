from django.contrib import admin

from apps.backtesting.models import BacktestArtifact, BacktestMetricSnapshot, BacktestRun, BacktestTrade


class BacktestTradeInline(admin.TabularInline):
    model = BacktestTrade
    extra = 0
    readonly_fields = ("symbol", "entry_date", "exit_date", "net_pnl")


@admin.register(BacktestRun)
class BacktestRunAdmin(admin.ModelAdmin):
    list_display = ("run_name", "strategy_version", "status", "start_date", "end_date", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("run_name", "strategy_version__strategy__name")
    inlines = [BacktestTradeInline]


@admin.register(BacktestTrade)
class BacktestTradeAdmin(admin.ModelAdmin):
    list_display = ("run", "symbol", "entry_date", "exit_date", "net_pnl", "exit_reason")
    list_filter = ("symbol", "exit_reason")


@admin.register(BacktestMetricSnapshot)
class BacktestMetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ("run", "metric_type", "label", "value")
    list_filter = ("metric_type",)


@admin.register(BacktestArtifact)
class BacktestArtifactAdmin(admin.ModelAdmin):
    list_display = ("run", "artifact_type", "created_at")

