from __future__ import annotations

from copy import deepcopy
from typing import Any

from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify

from apps.backtesting.catalog import get_stock_universe_catalog
from apps.strategies.definition_schema import (
    STRATEGY_FORM_SCHEMA,
    SUPPORTED_COMPARATORS,
    SUPPORTED_INDICATORS,
    SUPPORTED_LOGIC_OPERATORS,
    SUPPORTED_MARKET_SESSIONS,
    SUPPORTED_ORDER_TYPES,
    SUPPORTED_PRICE_SOURCES,
    SUPPORTED_SCHEDULES,
    SUPPORTED_SIZING_METHODS,
    SUPPORTED_TIMEFRAMES,
    get_default_strategy_definition,
)
from apps.strategies.models import Strategy, StrategyVersion


def _validate_indicator(indicator: dict[str, Any], errors: list[str]) -> None:
    indicator_type = indicator.get("type")
    if indicator_type not in SUPPORTED_INDICATORS:
        errors.append(f"Unsupported indicator type '{indicator_type}'.")
        return

    params = indicator.get("params", {})
    expected_params = SUPPORTED_INDICATORS[indicator_type]
    for key, value_type in expected_params.items():
        if key not in params:
            errors.append(f"Indicator '{indicator.get('id', indicator_type)}' is missing param '{key}'.")
            continue
        if value_type == "integer" and not isinstance(params[key], int):
            errors.append(f"Indicator param '{key}' must be an integer.")
        if value_type == "string" and not isinstance(params[key], str):
            errors.append(f"Indicator param '{key}' must be a string.")
    if "source" in params and params["source"] not in SUPPORTED_PRICE_SOURCES:
        errors.append(f"Indicator source '{params['source']}' is not supported.")


def _validate_operand(operand: dict[str, Any], errors: list[str], indicator_ids: set[str]) -> None:
    kind = operand.get("kind")
    value = operand.get("value")
    if kind == "indicator" and value not in indicator_ids:
        errors.append(f"Operand references unknown indicator '{value}'.")
    elif kind == "literal" and not isinstance(value, (int, float)):
        errors.append("Literal operands must use numeric values.")
    elif kind == "price" and value not in SUPPORTED_PRICE_SOURCES:
        errors.append(f"Price operand source '{value}' is not supported.")
    elif kind not in {"indicator", "literal", "price"}:
        errors.append(f"Unsupported operand kind '{kind}'.")


def _validate_rule_node(node: dict[str, Any], errors: list[str], indicator_ids: set[str], path: str = "rule") -> None:
    node_type = node.get("type")
    if node_type == "group":
        operator = node.get("operator")
        if operator not in SUPPORTED_LOGIC_OPERATORS:
            errors.append(f"{path}: unsupported logic operator '{operator}'.")
        conditions = node.get("conditions", [])
        if not isinstance(conditions, list) or not conditions:
            errors.append(f"{path}: grouped rules must include at least one condition.")
            return
        for index, condition in enumerate(conditions):
            _validate_rule_node(condition, errors, indicator_ids, f"{path}.conditions[{index}]")
        return

    if node_type != "condition":
        errors.append(f"{path}: unsupported rule node type '{node_type}'.")
        return

    operator = node.get("operator")
    if operator not in SUPPORTED_COMPARATORS:
        errors.append(f"{path}: unsupported comparator '{operator}'.")
    _validate_operand(node.get("left", {}), errors, indicator_ids)
    _validate_operand(node.get("right", {}), errors, indicator_ids)


def validate_strategy_definition(definition: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(definition, dict):
        return ["Strategy definition must be an object."]

    universe = definition.get("universe", {})
    available_symbols = {item["symbol"] for item in get_stock_universe_catalog()}
    if universe.get("type") != "symbols" or not universe.get("symbols"):
        errors.append("Universe must define at least one symbol.")
    else:
        for symbol in universe.get("symbols", []):
            if symbol.upper() not in available_symbols:
                errors.append(f"Universe symbol '{symbol}' is not in the supported MVP stock universe.")

    metadata = definition.get("metadata", {})
    if metadata.get("timeframe") not in SUPPORTED_TIMEFRAMES:
        errors.append("Metadata timeframe is not supported.")
    if metadata.get("schedule", {}).get("value") not in SUPPORTED_SCHEDULES:
        errors.append("Metadata schedule is not supported.")
    if metadata.get("marketSession") not in SUPPORTED_MARKET_SESSIONS:
        errors.append("Metadata market session is not supported.")

    indicators = definition.get("indicators", [])
    if not indicators:
        errors.append("At least one indicator is required.")
    indicator_ids = {indicator.get("id") for indicator in indicators if indicator.get("id")}
    if len(indicator_ids) != len(indicators):
        errors.append("Each indicator must include a unique 'id'.")

    for indicator in indicators:
        _validate_indicator(indicator, errors)

    for section in ("entryRules", "exitRules"):
        _validate_rule_node(definition.get(section, {}), errors, indicator_ids, section)

    risk = definition.get("risk", {})
    for key in ("maxPositionExposure", "maxPortfolioExposure", "stopLossPercent", "takeProfitPercent"):
        value = risk.get(key)
        if value is None or not isinstance(value, (int, float)):
            errors.append(f"Risk setting '{key}' must be numeric.")

    sizing = definition.get("sizing", {})
    if sizing.get("method") not in SUPPORTED_SIZING_METHODS:
        errors.append("Sizing method must be one of 'fixed_fraction' or 'fixed_amount'.")
    if not isinstance(sizing.get("value"), (int, float)):
        errors.append("Sizing value must be numeric.")

    execution = definition.get("execution", {})
    if execution.get("orderType") not in SUPPORTED_ORDER_TYPES:
        errors.append("Execution order type is not supported.")

    return errors


def get_strategy_execution_readiness(definition: dict[str, Any]):
    errors = validate_strategy_definition(definition)
    return {
        "is_ready": len(errors) == 0,
        "errors": errors,
        "engine_version": "phase2-v1",
        "supports_backtests": len(errors) == 0,
        "supports_live_transition": len(errors) == 0,
    }


def get_strategy_builder_schema():
    return deepcopy(STRATEGY_FORM_SCHEMA)


def unique_strategy_slug(organization, name: str) -> str:
    base_slug = slugify(name) or "strategy"
    slug = base_slug
    counter = 2
    while Strategy.objects.filter(organization=organization, slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


@transaction.atomic
def create_strategy(*, organization, user, name: str, description: str = "", definition: dict[str, Any] | None = None, change_summary: str = ""):
    strategy = Strategy.objects.create(
        organization=organization,
        name=name,
        slug=unique_strategy_slug(organization, name),
        description=description,
        created_by=user,
        updated_by=user,
    )
    version = create_strategy_version(
        strategy=strategy,
        user=user,
        title="Initial version",
        change_summary=change_summary or "Initial strategy definition.",
        definition=definition or get_default_strategy_definition(),
    )
    strategy.latest_version = version
    strategy.save(update_fields=["latest_version", "updated_at"])
    from apps.operations.services import record_audit_event

    record_audit_event(
        organization=organization,
        actor=user,
        category="strategy",
        verb="create",
        target_type="strategy",
        target_id=str(strategy.id),
        payload={"name": strategy.name, "version": version.version_number},
    )
    return strategy


@transaction.atomic
def create_strategy_version(*, strategy: Strategy, user, title: str, change_summary: str, definition: dict[str, Any]):
    version_number = (strategy.versions.aggregate(current_max=Max("version_number"))["current_max"] or 0) + 1
    errors = validate_strategy_definition(definition)
    version = StrategyVersion.objects.create(
        strategy=strategy,
        version_number=version_number,
        title=title,
        change_summary=change_summary,
        definition=definition,
        schema_version=definition.get("schemaVersion", "1.0"),
        validation_errors=errors,
        created_by=user,
    )
    strategy.latest_version = version
    strategy.updated_by = user
    strategy.save(update_fields=["latest_version", "updated_by", "updated_at"])
    from apps.operations.services import record_audit_event

    record_audit_event(
        organization=strategy.organization,
        actor=user,
        category="strategy",
        verb="create-version",
        target_type="strategy-version",
        target_id=str(version.id),
        payload={"strategy": str(strategy.id), "version": version.version_number},
    )
    return version


@transaction.atomic
def publish_strategy_version(*, version: StrategyVersion, actor=None):
    version.strategy.versions.update(is_published=False)
    version.is_published = True
    version.save(update_fields=["is_published", "updated_at"])
    version.strategy.status = "active"
    version.strategy.latest_version = version
    version.strategy.save(update_fields=["status", "latest_version", "updated_at"])
    from apps.operations.services import record_audit_event

    record_audit_event(
        organization=version.strategy.organization,
        actor=actor or version.created_by,
        category="strategy",
        verb="publish-version",
        target_type="strategy-version",
        target_id=str(version.id),
        payload={"strategy": str(version.strategy_id), "version": version.version_number},
    )
    return version
