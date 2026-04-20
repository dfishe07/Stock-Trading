from __future__ import annotations

from rest_framework import serializers

from apps.strategies.definition_schema import get_default_strategy_definition
from apps.strategies.models import Strategy, StrategyVersion
from apps.strategies.services import (
    create_strategy,
    create_strategy_version,
    get_strategy_execution_readiness,
    validate_strategy_definition,
)


class StrategyVersionSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.username", read_only=True)
    execution_readiness = serializers.SerializerMethodField()

    class Meta:
        model = StrategyVersion
        fields = (
            "id",
            "version_number",
            "title",
            "change_summary",
            "definition",
            "schema_version",
            "validation_errors",
            "execution_readiness",
            "is_published",
            "created_by",
            "created_at",
        )
        read_only_fields = ("validation_errors", "schema_version", "created_by", "created_at")

    def get_execution_readiness(self, obj):
        return get_strategy_execution_readiness(obj.definition)


class StrategySerializer(serializers.ModelSerializer):
    latest_version = StrategyVersionSerializer(read_only=True)
    latest_validation_errors = serializers.SerializerMethodField()

    class Meta:
        model = Strategy
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "status",
            "latest_version",
            "latest_validation_errors",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("slug", "latest_version", "created_at", "updated_at")

    def get_latest_validation_errors(self, obj):
        return obj.latest_version.validation_errors if obj.latest_version else []


class StrategyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    change_summary = serializers.CharField(required=False, allow_blank=True)
    definition = serializers.JSONField(required=False)

    def validate_definition(self, value):
        errors = validate_strategy_definition(value)
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def create(self, validated_data):
        request = self.context["request"]
        return create_strategy(
            organization=request.organization,
            user=request.user,
            name=validated_data["name"],
            description=validated_data.get("description", ""),
            change_summary=validated_data.get("change_summary", ""),
            definition=validated_data.get("definition", get_default_strategy_definition()),
        )


class StrategyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Strategy
        fields = ("name", "description", "status")


class StrategyVersionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    change_summary = serializers.CharField(required=False, allow_blank=True)
    definition = serializers.JSONField()

    def validate_definition(self, value):
        errors = validate_strategy_definition(value)
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def create(self, validated_data):
        request = self.context["request"]
        return create_strategy_version(
            strategy=self.context["strategy"],
            user=request.user,
            title=validated_data.get("title", ""),
            change_summary=validated_data.get("change_summary", ""),
            definition=validated_data["definition"],
        )
