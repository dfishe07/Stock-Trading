from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.access.models import Membership, Organization
from apps.backtesting.catalog import get_stock_universe_catalog
from apps.backtesting.engine import run_backtest_engine
from apps.backtesting.services import create_backtest_run, execute_backtest_run
from apps.strategies.definition_schema import get_default_strategy_definition
from apps.strategies.services import create_strategy

User = get_user_model()


class BacktestEngineTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Quant Lab", slug="quant-lab")
        self.user = User.objects.create_user(username="builder", email="builder@example.com", password="password123")
        Membership.objects.create(user=self.user, organization=self.organization, role="developer", is_default=True)

    def test_market_catalog_has_ten_cross_sector_symbols(self):
        catalog = get_stock_universe_catalog()
        self.assertEqual(len(catalog), 10)
        self.assertGreaterEqual(len({item["sector"] for item in catalog}), 8)

    def test_default_strategy_definition_executes(self):
        definition = get_default_strategy_definition()
        definition["universe"]["symbols"] = ["AAPL", "MSFT", "JPM"]
        result = run_backtest_engine(
            definition=definition,
            start_date=date(2023, 1, 3),
            end_date=date(2023, 12, 29),
            initial_cash=100000,
            benchmark_symbol="AAPL",
        )
        self.assertIn("summary", result)
        self.assertGreater(len(result["equity_curve"]), 50)
        self.assertIn("total_trades", result["summary"])

    def test_strategy_with_non_close_price_sources_executes(self):
        definition = get_default_strategy_definition()
        definition["universe"]["symbols"] = ["AAPL", "MSFT"]
        definition["indicators"][0]["params"]["source"] = "open"
        definition["indicators"][1]["params"]["source"] = "high"
        definition["entryRules"]["conditions"][0]["right"] = {"kind": "price", "value": "open"}
        definition["exitRules"]["conditions"][0]["right"] = {"kind": "price", "value": "low"}
        result = run_backtest_engine(
            definition=definition,
            start_date=date(2023, 1, 3),
            end_date=date(2023, 12, 29),
            initial_cash=100000,
            benchmark_symbol="MSFT",
        )
        self.assertIn("summary", result)
        self.assertGreater(len(result["equity_curve"]), 50)

    def test_backtest_run_persists_metrics_and_artifacts(self):
        strategy = create_strategy(
            organization=self.organization,
            user=self.user,
            name="Golden Cross",
            description="Test strategy",
        )
        run = create_backtest_run(
            organization=self.organization,
            user=self.user,
            strategy_version=strategy.latest_version,
            run_name="Integration Run",
            start_date=date(2023, 1, 3),
            end_date=date(2023, 6, 30),
            initial_cash=Decimal("100000.00"),
            benchmark_symbol="MSFT",
        )
        execute_backtest_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, "completed")
        self.assertTrue(run.result_summary)
        self.assertTrue(run.metric_snapshots.exists())
        self.assertTrue(run.artifacts.filter(artifact_type="equity_curve").exists())
