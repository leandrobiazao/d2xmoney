"""Rank-priority buy budget cap for AMBB rebalancing."""
from decimal import Decimal
from django.test import TestCase
from ambb_strategy.services import AMBBStrategyService


class RankPriorityBuyCapTestCase(TestCase):
    def test_funds_best_ranks_first_and_stops_at_budget(self):
        strategic = Decimal('1000')
        buy_budget = Decimal('1500')
        stocks_to_balance = [
            {
                'ticker': 'LOW',
                'ranking': 20,
                'current_value': 0.0,
                'current_price': 10.0,
                'quantity_to_adjust': 100,
            },
            {
                'ticker': 'TOP',
                'ranking': 3,
                'current_value': 0.0,
                'current_price': 10.0,
                'quantity_to_adjust': 100,
            },
            {
                'ticker': 'MID',
                'ranking': 10,
                'current_value': 0.0,
                'current_price': 10.0,
                'quantity_to_adjust': 100,
            },
        ]
        formatted_buys = [
            {'ticker': 'TOP', 'target_quantity': 100, 'target_value': 0.0},
            {'ticker': 'MID', 'target_quantity': 100, 'target_value': 0.0},
            {'ticker': 'LOW', 'target_quantity': 100, 'target_value': 0.0},
        ]

        AMBBStrategyService._apply_rank_priority_buy_cap(
            buy_budget, strategic, stocks_to_balance, formatted_buys
        )

        by_ticker = {s['ticker']: s for s in stocks_to_balance}
        self.assertEqual(by_ticker['TOP']['quantity_to_adjust'], 100)
        self.assertEqual(by_ticker['MID']['quantity_to_adjust'], 50)
        self.assertEqual(by_ticker['LOW']['quantity_to_adjust'], 0)

        total_spend = sum(
            Decimal(str(s['quantity_to_adjust'])) * Decimal(str(s['current_price']))
            for s in stocks_to_balance
        )
        self.assertLessEqual(total_spend, buy_budget)
        self.assertEqual(by_ticker['TOP']['difference'], 1000.0)
        self.assertEqual(by_ticker['LOW']['difference'], 1000.0)

    def test_existing_position_uses_headroom(self):
        strategic = Decimal('1000')
        buy_budget = Decimal('500')
        stocks_to_balance = [
            {
                'ticker': 'AAA3',
                'ranking': 1,
                'current_value': 800.0,
                'current_price': 10.0,
                'quantity_to_adjust': 50,
            },
        ]
        formatted_buys = []

        AMBBStrategyService._apply_rank_priority_buy_cap(
            buy_budget, strategic, stocks_to_balance, formatted_buys
        )

        # headroom = 200, budget = 500 -> buy 20 shares (R$ 200)
        self.assertEqual(stocks_to_balance[0]['quantity_to_adjust'], 20)
        self.assertEqual(stocks_to_balance[0]['difference'], 200.0)
