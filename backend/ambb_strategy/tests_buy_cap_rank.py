"""Water-fill buy budget cap for MDIV rebalancing (even ending weights)."""
from decimal import Decimal
from django.test import TestCase
from ambb_strategy.services import AMBBStrategyService


class RankPriorityBuyCapTestCase(TestCase):
    def test_equal_starting_values_share_budget(self):
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
        self.assertEqual(by_ticker['TOP']['quantity_to_adjust'], 50)
        self.assertEqual(by_ticker['MID']['quantity_to_adjust'], 50)
        self.assertEqual(by_ticker['LOW']['quantity_to_adjust'], 50)

        total_spend = sum(
            Decimal(str(s['quantity_to_adjust'])) * Decimal(str(s['current_price']))
            for s in stocks_to_balance
        )
        self.assertEqual(total_spend, buy_budget)
        self.assertEqual(by_ticker['TOP']['difference'], 1000.0)
        self.assertEqual(by_ticker['LOW']['difference'], 1000.0)

    def test_water_fill_equalizes_ending_values_not_ticket_size(self):
        strategic = Decimal('1000')
        buy_budget = Decimal('800')
        stocks_to_balance = [
            {
                'ticker': 'NEW3',
                'ranking': 1,
                'current_value': 0.0,
                'current_price': 10.0,
                'quantity_to_adjust': 100,
            },
            {
                'ticker': 'HELD3',
                'ranking': 2,
                'current_value': 600.0,
                'current_price': 10.0,
                'quantity_to_adjust': 40,
            },
        ]
        formatted_buys = [
            {'ticker': 'NEW3', 'target_quantity': 100, 'target_value': 0.0},
        ]

        AMBBStrategyService._apply_rank_priority_buy_cap(
            buy_budget, strategic, stocks_to_balance, formatted_buys
        )

        by_ticker = {s['ticker']: s for s in stocks_to_balance}
        # Raise NEW3 to 600 (60 shares), remaining 200 lifts both by 100 -> 70 and 10.
        self.assertEqual(by_ticker['NEW3']['quantity_to_adjust'], 70)
        self.assertEqual(by_ticker['HELD3']['quantity_to_adjust'], 10)
        new_end = Decimal('70') * Decimal('10')
        held_end = Decimal('600') + Decimal('10') * Decimal('10')
        self.assertEqual(new_end, held_end)

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
