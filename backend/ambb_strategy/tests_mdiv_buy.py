"""MDIV top-10 buy / top-20 keep (replaces AMBB 2.0 for Ações em Reais)."""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from ambb_strategy.services import AMBBStrategyService
from configuration.models import InvestmentType
from portfolio_operations.models import PortfolioPosition
from stocks.models import Stock
from users.models import User


class MDIVBuyTransitionTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name="MDIV Buy Test",
            cpf="111.222.333-44",
            account_provider="XP Investimentos",
            account_number="99999-9",
        )
        self.acoes_reais_type, _ = InvestmentType.objects.get_or_create(
            code="RENDA_VARIAVEL_REAIS",
            defaults={
                "name": "Renda Variável em Reais",
                "is_active": True,
            },
        )
        self.mdiv_top = [
            {"codigo": f"MDV{i}", "nome": f"MDIV Rank {i}", "ranking": i}
            for i in range(1, 16)
        ]
        self.mdiv_top.append({"codigo": "MDV21", "nome": "MDIV Rank 21", "ranking": 21})
        self.ambb_only = [
            {"codigo": "AMB1", "nome": "AMBB Rank 1", "ranking": 1},
            {"codigo": "AMB2", "nome": "AMBB Rank 2", "ranking": 2},
        ]
        for i in list(range(1, 16)) + [21]:
            ticker = f"MDV{i}"
            Stock.objects.get_or_create(
                ticker=ticker,
                defaults={
                    "name": f"MDIV Rank {i}",
                    "investment_type": self.acoes_reais_type,
                    "current_price": Decimal("10.00"),
                    "is_active": True,
                },
            )
        for ticker, name in [("AMB1", "AMBB Rank 1"), ("AMB2", "AMBB Rank 2")]:
            Stock.objects.get_or_create(
                ticker=ticker,
                defaults={
                    "name": name,
                    "investment_type": self.acoes_reais_type,
                    "current_price": Decimal("10.00"),
                    "is_active": True,
                },
            )

    def _mock_strategy_stocks(self, strategy_type):
        if strategy_type == "MDIV":
            return self.mdiv_top
        if strategy_type == "AMBB2":
            return self.ambb_only
        return []

    @patch("allocation_strategies.services.AllocationStrategyService.get_current_allocation")
    @patch("stocks.services.StockService.refresh_prices_for_tickers")
    @patch("ambb_strategy.services.ClubeDoValorService.get_current_stocks")
    def test_new_buys_use_mdiv_top_ten_not_ambb(
        self, mock_get_stocks, mock_refresh_prices, mock_allocation
    ):
        mock_get_stocks.side_effect = self._mock_strategy_stocks
        mock_allocation.return_value = {"total_value": Decimal("100000")}

        recommendations = AMBBStrategyService.generate_rebalancing_recommendations(self.user)
        buy_tickers = [b["ticker"] for b in recommendations.get("stocks_to_buy", [])]

        self.assertEqual(
            buy_tickers,
            [f"MDV{i}" for i in range(1, 11)],
        )
        self.assertNotIn("AMB1", buy_tickers)
        self.assertNotIn("AMB2", buy_tickers)
        self.assertNotIn("MDV11", buy_tickers)
        self.assertNotIn("MDV15", buy_tickers)

        debug = recommendations.get("debug_info", {})
        self.assertEqual(debug.get("mdiv_buy_rank_limit"), 10)
        self.assertEqual(AMBBStrategyService.RANK_THRESHOLD, 20)
        self.assertEqual(AMBBStrategyService.EQUAL_WEIGHT_DIVISOR, 10)
        self.assertAlmostEqual(
            recommendations.get("target_value_per_stock", 0),
            3000.0,
            places=2,
        )

    @patch("allocation_strategies.services.AllocationStrategyService.get_current_allocation")
    @patch("stocks.services.StockService.refresh_prices_for_tickers")
    @patch("ambb_strategy.services.ClubeDoValorService.get_current_stocks")
    def test_held_ambb_only_ticker_is_sold(
        self, mock_get_stocks, mock_refresh_prices, mock_allocation
    ):
        mock_get_stocks.side_effect = self._mock_strategy_stocks
        mock_allocation.return_value = {"total_value": Decimal("100000")}
        PortfolioPosition.objects.create(
            user_id=str(self.user.id),
            ticker="AMB1",
            quantidade=10,
            preco_medio=Decimal("10.00"),
            valor_total_investido=Decimal("100.00"),
        )

        recommendations = AMBBStrategyService.generate_rebalancing_recommendations(self.user)
        sells = {s["ticker"]: s for s in recommendations.get("stocks_to_sell", [])}

        self.assertIn("AMB1", sells)
        self.assertEqual(sells["AMB1"]["reason"], "Not in MDIV ranking")
        self.assertNotIn("AMB1", [b["ticker"] for b in recommendations.get("stocks_to_buy", [])])

    @patch("allocation_strategies.services.AllocationStrategyService.get_current_allocation")
    @patch("stocks.services.StockService.refresh_prices_for_tickers")
    @patch("ambb_strategy.services.ClubeDoValorService.get_current_stocks")
    def test_held_mdiv_rank_15_is_kept_without_buy(
        self, mock_get_stocks, mock_refresh_prices, mock_allocation
    ):
        mock_get_stocks.side_effect = self._mock_strategy_stocks
        mock_allocation.return_value = {"total_value": Decimal("100000")}
        PortfolioPosition.objects.create(
            user_id=str(self.user.id),
            ticker="MDV15",
            quantidade=5,
            preco_medio=Decimal("10.00"),
            valor_total_investido=Decimal("50.00"),
        )

        recommendations = AMBBStrategyService.generate_rebalancing_recommendations(self.user)
        sell_tickers = [s["ticker"] for s in recommendations.get("stocks_to_sell", [])]
        self.assertNotIn("MDV15", sell_tickers)

        held = next(
            (b for b in recommendations.get("stocks_to_balance", []) if b["ticker"] == "MDV15"),
            None,
        )
        self.assertIsNotNone(held)
        self.assertEqual(held["ranking"], 15)
        self.assertEqual(int(held.get("quantity_to_adjust") or 0), 0)
        self.assertNotIn("MDV15", [b["ticker"] for b in recommendations.get("stocks_to_buy", [])])

    @patch("allocation_strategies.services.AllocationStrategyService.get_current_allocation")
    @patch("stocks.services.StockService.refresh_prices_for_tickers")
    @patch("ambb_strategy.services.ClubeDoValorService.get_current_stocks")
    def test_leftover_limit_partial_sells_exit_below_equal_weight_slot(
        self, mock_get_stocks, mock_refresh_prices, mock_allocation
    ):
        """Exit names smaller than the 1/10 slot still consume leftover sales limit."""
        mock_get_stocks.side_effect = self._mock_strategy_stocks
        mock_allocation.return_value = {"total_value": Decimal("100000")}
        for ticker, name in [("BIG1", "Big Exit"), ("SEER3", "Ser Educacional")]:
            Stock.objects.get_or_create(
                ticker=ticker,
                defaults={
                    "name": name,
                    "investment_type": self.acoes_reais_type,
                    "current_price": Decimal("10.00"),
                    "is_active": True,
                },
            )
        PortfolioPosition.objects.create(
            user_id=str(self.user.id),
            ticker="BIG1",
            quantidade=1700,
            preco_medio=Decimal("10.00"),
            valor_total_investido=Decimal("17000.00"),
        )
        PortfolioPosition.objects.create(
            user_id=str(self.user.id),
            ticker="SEER3",
            quantidade=250,
            preco_medio=Decimal("10.00"),
            valor_total_investido=Decimal("2500.00"),
        )

        recommendations = AMBBStrategyService.generate_rebalancing_recommendations(
            self.user, remaining_monthly_limit=Decimal("19000.00")
        )
        sell_tickers = [s["ticker"] for s in recommendations.get("stocks_to_sell", [])]
        self.assertIn("BIG1", sell_tickers)
        self.assertNotIn("SEER3", sell_tickers)

        seer = next(
            (b for b in recommendations.get("stocks_to_balance", []) if b["ticker"] == "SEER3"),
            None,
        )
        self.assertIsNotNone(seer)
        self.assertLess(int(seer.get("quantity_to_adjust") or 0), 0)
        partial = Decimal(str(abs(int(seer["quantity_to_adjust"])))) * Decimal("10.00")
        self.assertLessEqual(Decimal("17000.00") + partial, Decimal("19000.00"))

