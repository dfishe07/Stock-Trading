from django.contrib import admin

from apps.strategies.models import Strategy, StrategyVersion


class StrategyVersionInline(admin.TabularInline):
    model = StrategyVersion
    extra = 0
    readonly_fields = ("version_number", "created_by", "created_at")


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "status", "latest_version", "updated_at")
    list_filter = ("organization", "status")
    search_fields = ("name", "slug", "description")
    inlines = [StrategyVersionInline]


@admin.register(StrategyVersion)
class StrategyVersionAdmin(admin.ModelAdmin):
    list_display = ("strategy", "version_number", "is_published", "created_by", "created_at")
    list_filter = ("is_published", "strategy__organization")
    search_fields = ("strategy__name", "title", "change_summary")

