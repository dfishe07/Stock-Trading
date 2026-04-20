from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.access.models import Membership, Organization
from apps.access.services import issue_token
from apps.strategies.definition_schema import get_default_strategy_definition
from apps.strategies.services import create_strategy
from apps.trading.models import BrokerAccount, LiveDeployment, Portfolio
from apps.trading.services import evaluate_live_deployment

User = get_user_model()


class TradingPhaseThreeTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Paper Lab", slug="paper-lab")
        self.user = User.objects.create_user(username="developer", email="developer@example.com", password="password123", default_organization=self.organization)
        Membership.objects.create(user=self.user, organization=self.organization, role="developer", is_default=True)
        token = issue_token(user=self.user, created_by=self.user, label="test-login")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.key}", HTTP_X_ORGANIZATION_SLUG=self.organization.slug)

        broker = BrokerAccount.objects.create(
            organization=self.organization,
            name="Alpaca Paper",
            provider="alpaca",
            account_mode="paper",
            credentials_reference="paper-key",
        )
        self.portfolio = Portfolio.objects.create(
            organization=self.organization,
            broker_account=broker,
            name="Core Portfolio",
            benchmark_symbol="AAPL",
            starting_cash=Decimal("100000.00"),
            cash_balance=Decimal("100000.00"),
            equity_value=Decimal("100000.00"),
            cash_reserve_percent=Decimal("5.00"),
        )

        definition = deepcopy(get_default_strategy_definition())
        definition["universe"]["symbols"] = ["AAPL", "MSFT"]
        definition["entryRules"] = {
            "type": "group",
            "operator": "and",
            "conditions": [
                {
                    "type": "condition",
                    "left": {"kind": "price", "value": "close"},
                    "operator": "gt",
                    "right": {"kind": "literal", "value": 0},
                }
            ],
        }
        definition["exitRules"] = {
            "type": "group",
            "operator": "and",
            "conditions": [
                {
                    "type": "condition",
                    "left": {"kind": "price", "value": "close"},
                    "operator": "lt",
                    "right": {"kind": "literal", "value": 0},
                }
            ],
        }
        strategy = create_strategy(
            organization=self.organization,
            user=self.user,
            name="Always In",
            description="Deterministic strategy for paper trading tests.",
            definition=definition,
        )
        self.deployment = LiveDeployment.objects.create(
            organization=self.organization,
            strategy_version=strategy.latest_version,
            portfolio=self.portfolio,
            broker_account=broker,
            status="active",
            schedule_expression="1d",
            created_by=self.user,
        )

    def test_evaluate_live_deployment_creates_orders_positions_and_heartbeat(self):
        heartbeat = evaluate_live_deployment(deployment=self.deployment)
        self.portfolio.refresh_from_db()
        self.assertEqual(heartbeat.status, "completed")
        self.assertEqual(self.deployment.orders.count(), 2)
        self.assertEqual(self.deployment.signals.count(), 2)
        self.assertEqual(self.portfolio.positions.filter(quantity__gt=0).count(), 2)
        self.assertLess(self.portfolio.cash_balance, Decimal("100000.00"))
        self.assertGreater(self.portfolio.equity_value, Decimal("0"))

    def test_dashboard_endpoint_returns_live_summary(self):
        evaluate_live_deployment(deployment=self.deployment)
        response = self.client.get("/api/trading/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["deployments_active"], 1)
        self.assertGreaterEqual(response.data["summary"]["positions_open"], 1)

    def test_run_now_endpoint_executes_deployment(self):
        response = self.client.post(f"/api/trading/deployments/{self.deployment.id}/run_now/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "active")
        self.assertGreaterEqual(len(response.data["recent_heartbeats"]), 1)
