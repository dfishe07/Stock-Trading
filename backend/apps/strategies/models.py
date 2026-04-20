from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.access.models import Organization
from apps.common.models import TimeStampedUUIDModel
from apps.strategies.definition_schema import get_default_strategy_definition


class StrategyStatusChoices(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class Strategy(TimeStampedUUIDModel):
    organization = models.ForeignKey(Organization, related_name="strategies", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=StrategyStatusChoices.choices, default=StrategyStatusChoices.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="created_strategies", null=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="updated_strategies", null=True, on_delete=models.SET_NULL)
    latest_version = models.ForeignKey(
        "StrategyVersion",
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["name"]
        unique_together = ("organization", "slug")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class StrategyVersion(TimeStampedUUIDModel):
    strategy = models.ForeignKey(Strategy, related_name="versions", on_delete=models.CASCADE)
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=255, blank=True)
    change_summary = models.TextField(blank=True)
    definition = models.JSONField(default=get_default_strategy_definition)
    schema_version = models.CharField(max_length=32, default="1.0")
    validation_errors = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="strategy_versions", null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-version_number", "-created_at"]
        unique_together = ("strategy", "version_number")

    def __str__(self) -> str:
        return f"{self.strategy.name} v{self.version_number}"

