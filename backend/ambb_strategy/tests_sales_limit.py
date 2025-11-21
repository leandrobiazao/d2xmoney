"""
Test: Rebalancing Sales Limit - Stocks with ranking > 30 should be sold completely

This test verifies that when there's available sales limit, stocks with ranking > 30
(VAMO3, LAVV3, IGTI11) are correctly identified and added to the complete sales list.

Scenario:
- User has stocks VAMO3 (ranking 68), LAVV3 (ranking 73), IGTI11 (ranking 109) in portfolio
- Available sales limit: R$ 9,221.45
- Total value of these stocks: R$ 8,191.58 (within limit)
- Expected: All three stocks should appear in stocks_to_sell (complete sales)
"""
from decimal import Decimal
from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.models import User
from stocks.models import Stock
from portfolio_operations.models import PortfolioPosition
from configuration.models import InvestmentType
from ambb_strategy.services import AMBBStrategyService


class RebalancingSalesLimitTestCase(TestCase):
    """Test case for rebalancing sales limit logic."""
    
    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create(
            name="Test User Sales Limit",
            cpf="123.456.789-00",
            account_provider="XP Investimentos",
            account_number="12345-6"
        )
        
        # Create investment type "Ações em Reais"
        self.acoes_reais_type = InvestmentType.objects.create(
            code="ACOES_REAIS",
            name="Ações em Reais",
            is_active=True
        )
        
        # Create test stocks
        self.vamo3 = Stock.objects.create(
            ticker="VAMO3",
            name="Vamos Locação de Caminhões, Máquinas e Equipamentos S.A.",
            investment_type=self.acoes_reais_type,
            current_price=Decimal('3.64'),
            is_active=True
        )
        
        self.lavv3 = Stock.objects.create(
            ticker="LAVV3",
            name="Lavvi Empreendimentos Imobiliários S.A.",
            investment_type=self.acoes_reais_type,
            current_price=Decimal('5.90'),
            is_active=True
        )
        
        self.igti11 = Stock.objects.create(
            ticker="IGTI11",
            name="Iguatemi S.A.",
            investment_type=self.acoes_reais_type,
            current_price=Decimal('31.37'),
            is_active=True
        )
        
        # Expected values (defined before creating positions)
        self.vamo3_value = Decimal('3461.64')
        self.lavv3_value = Decimal('1593.00')
        self.igti11_value = Decimal('3137.00')
        self.total_value = self.vamo3_value + self.lavv3_value + self.igti11_value  # R$ 8,191.58
        self.available_limit = Decimal('9221.45')  # R$ 9,221.45
        
        # Create portfolio positions
        # PortfolioPosition uses user_id (string) and ticker (string), not ForeignKey
        self.vamo3_position = PortfolioPosition.objects.create(
            user_id=str(self.user.id),
            ticker='VAMO3',
            quantidade=951,
            preco_medio=Decimal('3.64'),
            valor_total_investido=self.vamo3_value
        )
        
        self.lavv3_position = PortfolioPosition.objects.create(
            user_id=str(self.user.id),
            ticker='LAVV3',
            quantidade=270,
            preco_medio=Decimal('5.90'),
            valor_total_investido=self.lavv3_value
        )
        
        self.igti11_position = PortfolioPosition.objects.create(
            user_id=str(self.user.id),
            ticker='IGTI11',
            quantidade=100,
            preco_medio=Decimal('31.37'),
            valor_total_investido=self.igti11_value
        )
        
        # Expected values
        self.vamo3_value = Decimal('3461.64')
        self.lavv3_value = Decimal('1593.00')
        self.igti11_value = Decimal('3137.00')
        self.total_value = self.vamo3_value + self.lavv3_value + self.igti11_value  # R$ 8,191.58
        self.available_limit = Decimal('9221.45')  # R$ 9,221.45
        
    @patch('ambb_strategy.services.ClubeDoValorService.get_current_stocks')
    def test_stocks_with_ranking_over_30_should_be_sold_completely(self, mock_get_current_stocks):
        """
        Test that stocks with ranking > 30 are sold completely when limit is available.
        """
        # Mock AMBB 2.0 data
        # VAMO3: ranking 68, LAVV3: ranking 73, IGTI11: ranking 109
        mock_get_current_stocks.return_value = [
            {
                'codigo': 'VAMO3',
                'nome': 'Vamos Locação de Caminhões, Máquinas e Equipamentos S.A.',
                'ranking': 68
            },
            {
                'codigo': 'LAVV3',
                'nome': 'Lavvi Empreendimentos Imobiliários S.A.',
                'ranking': 73
            },
            {
                'codigo': 'IGTI11',
                'nome': 'Iguatemi S.A.',
                'ranking': 109
            }
        ]
        
        # Generate recommendations with available limit
        recommendations = AMBBStrategyService.generate_rebalancing_recommendations(
            user=self.user,
            remaining_monthly_limit=self.available_limit
        )
        
        # Verify results
        stocks_to_sell = recommendations.get('stocks_to_sell', [])
        stocks_to_sell_tickers = [s['ticker'] for s in stocks_to_sell]
        
        # Print debug information
        print(f"\nDebug Information:")
        print(f"   Stocks to sell: {stocks_to_sell_tickers}")
        print(f"   Total sales value: {recommendations.get('total_sales_value', 0)}")
        print(f"   Available limit: {self.available_limit}")
        
        debug_info = recommendations.get('debug_info', {})
        if debug_info:
            print(f"   Remaining limit after complete sales: {debug_info.get('remaining_limit_after_complete_sales', 0)}")
            print(f"   Stocks in sell list: {debug_info.get('stocks_to_sell_list_count', 0)}")
            print(f"   Final stocks to sell: {debug_info.get('final_stocks_to_sell_count', 0)}")
            
            # Check target stocks info
            target_stocks_info = debug_info.get('target_stocks_info', [])
            for stock_info in target_stocks_info:
                if stock_info['ticker'] in ['VAMO3', 'LAVV3', 'IGTI11']:
                    print(f"\n   {stock_info['ticker']}:")
                    print(f"      in_portfolio: {stock_info['in_portfolio']}")
                    print(f"      in_ambb: {stock_info['in_ambb']}")
                    print(f"      ranking: {stock_info['ranking']}")
                    print(f"      in_stocks_to_keep: {stock_info['in_stocks_to_keep']}")
                    print(f"      in_stocks_to_sell_list: {stock_info['in_stocks_to_sell_list']}")
                    print(f"      in_final_stocks_to_sell: {stock_info['in_final_stocks_to_sell']}")
                    print(f"      current_value: {stock_info['current_value']}")
            
            # Check stocks_to_sell_list_details
            stocks_to_sell_list_details = debug_info.get('stocks_to_sell_list_details', [])
            print(f"\n   Stocks in sell list details:")
            for detail in stocks_to_sell_list_details:
                if detail['ticker'] in ['VAMO3', 'LAVV3', 'IGTI11']:
                    print(f"      {detail['ticker']}: ranking={detail['ranking']}, value={detail['current_value']}, in_final_sell={detail['in_final_sell']}")
        
        # All three stocks should be in the complete sales list
        self.assertIn('VAMO3', stocks_to_sell_tickers, 
                     f"VAMO3 should be in complete sales list. Found: {stocks_to_sell_tickers}")
        self.assertIn('LAVV3', stocks_to_sell_tickers,
                     "LAVV3 should be in complete sales list")
        self.assertIn('IGTI11', stocks_to_sell_tickers,
                     "IGTI11 should be in complete sales list")
        
        # Verify total sales value
        total_sales_value = Decimal(str(recommendations.get('total_sales_value', 0)))
        self.assertGreaterEqual(total_sales_value, self.total_value,
                               f"Total sales value ({total_sales_value}) should be >= {self.total_value}")
        
        # Verify sales don't exceed limit
        self.assertLessEqual(total_sales_value, self.available_limit,
                            f"Total sales value ({total_sales_value}) should be <= {self.available_limit}")
        
        # Verify debug info
        debug_info = recommendations.get('debug_info', {})
        self.assertIsNotNone(debug_info, "Debug info should be present")
        
        # Check target stocks info
        target_stocks_info = debug_info.get('target_stocks_info', [])
        for stock_info in target_stocks_info:
            if stock_info['ticker'] in ['VAMO3', 'LAVV3', 'IGTI11']:
                self.assertTrue(stock_info['in_portfolio'], 
                               f"{stock_info['ticker']} should be in portfolio")
                self.assertTrue(stock_info['in_ambb'],
                               f"{stock_info['ticker']} should be in AMBB 2.0")
                self.assertGreater(stock_info['ranking'], 30,
                                  f"{stock_info['ticker']} should have ranking > 30")
                self.assertFalse(stock_info['in_stocks_to_keep'],
                                f"{stock_info['ticker']} should NOT be in stocks_to_keep")
                self.assertTrue(stock_info['in_stocks_to_sell_list'],
                               f"{stock_info['ticker']} should be in stocks_to_sell_list")
                # If limit is available, it should be in final_stocks_to_sell
                if stock_info['current_value'] <= self.available_limit:
                    self.assertTrue(stock_info['in_final_stocks_to_sell'],
                                   f"{stock_info['ticker']} should be in final_stocks_to_sell (limit available)")
        
        print("\nTest passed: All stocks with ranking > 30 are in complete sales list")
        print(f"   Total sales value: R$ {total_sales_value}")
        print(f"   Available limit: R$ {self.available_limit}")
        print(f"   Stocks to sell: {stocks_to_sell_tickers}")
        
    @patch('ambb_strategy.services.ClubeDoValorService.get_current_stocks')
    def test_stocks_not_sold_when_limit_insufficient(self, mock_get_current_stocks):
        """
        Test that stocks are NOT sold completely when limit is insufficient.
        """
        # Mock AMBB 2.0 data
        mock_get_current_stocks.return_value = [
            {
                'codigo': 'VAMO3',
                'nome': 'Vamos Locação de Caminhões, Máquinas e Equipamentos S.A.',
                'ranking': 68
            },
            {
                'codigo': 'LAVV3',
                'nome': 'Lavvi Empreendimentos Imobiliários S.A.',
                'ranking': 73
            },
            {
                'codigo': 'IGTI11',
                'nome': 'Iguatemi S.A.',
                'ranking': 109
            }
        ]
        
        # Generate recommendations with insufficient limit (only R$ 1,000)
        insufficient_limit = Decimal('1000.00')
        recommendations = AMBBStrategyService.generate_rebalancing_recommendations(
            user=self.user,
            remaining_monthly_limit=insufficient_limit
        )
        
        # Verify results
        stocks_to_sell = recommendations.get('stocks_to_sell', [])
        stocks_to_sell_tickers = [s['ticker'] for s in stocks_to_sell]
        
        # With insufficient limit, some stocks may not be sold completely
        total_sales_value = Decimal(str(recommendations.get('total_sales_value', 0)))
        self.assertLessEqual(total_sales_value, insufficient_limit,
                            f"Total sales value ({total_sales_value}) should be <= {insufficient_limit}")
        
        print("\nTest passed: Sales respect the limit")
        print(f"   Total sales value: R$ {total_sales_value}")
        print(f"   Limit: R$ {insufficient_limit}")
        print(f"   Stocks to sell: {stocks_to_sell_tickers}")
        
    @patch('ambb_strategy.services.ClubeDoValorService.get_current_stocks')
    def test_stocks_to_sell_list_includes_all_ranking_over_30(self, mock_get_current_stocks):
        """
        Test that stocks_to_sell_list includes all stocks with ranking > 30.
        """
        # Mock AMBB 2.0 data with multiple stocks
        mock_get_current_stocks.return_value = [
            {
                'codigo': 'VAMO3',
                'nome': 'Vamos Locação de Caminhões, Máquinas e Equipamentos S.A.',
                'ranking': 68
            },
            {
                'codigo': 'LAVV3',
                'nome': 'Lavvi Empreendimentos Imobiliários S.A.',
                'ranking': 73
            },
            {
                'codigo': 'IGTI11',
                'nome': 'Iguatemi S.A.',
                'ranking': 109
            }
        ]
        
        # Generate recommendations
        recommendations = AMBBStrategyService.generate_rebalancing_recommendations(
            user=self.user,
            remaining_monthly_limit=self.available_limit
        )
        
        # Check debug info
        debug_info = recommendations.get('debug_info', {})
        stocks_to_sell_list_details = debug_info.get('stocks_to_sell_list_details', [])
        
        # All three stocks should be in stocks_to_sell_list_details
        sell_list_tickers = [s['ticker'] for s in stocks_to_sell_list_details]
        
        self.assertIn('VAMO3', sell_list_tickers,
                     "VAMO3 should be in stocks_to_sell_list_details")
        self.assertIn('LAVV3', sell_list_tickers,
                     "LAVV3 should be in stocks_to_sell_list_details")
        self.assertIn('IGTI11', sell_list_tickers,
                     "IGTI11 should be in stocks_to_sell_list_details")
        
        # Verify rankings
        for stock_detail in stocks_to_sell_list_details:
            if stock_detail['ticker'] in ['VAMO3', 'LAVV3', 'IGTI11']:
                self.assertGreater(stock_detail['ranking'], 30,
                                  f"{stock_detail['ticker']} should have ranking > 30")
        
        print("\nTest passed: All stocks with ranking > 30 are in stocks_to_sell_list")
        print(f"   Stocks in sell list: {sell_list_tickers}")

