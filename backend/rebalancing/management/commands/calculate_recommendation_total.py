"""
Django management command to calculate the total value of rebalancing recommendations
using actual current prices vs. Stocks in Reals recommendations.
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from users.models import User
from rebalancing.models import RebalancingRecommendation, RebalancingAction
from stocks.models import Stock


class Command(BaseCommand):
    help = 'Calculate total value of rebalancing recommendations using current prices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            help='User ID to calculate recommendation for',
            default='024.537.739-50'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {user_id} not found!'))
            return
        
        # Get latest recommendation
        recommendation = RebalancingRecommendation.objects.filter(
            user=user,
            status='pending'
        ).order_by('-recommendation_date', '-created_at').first()
        
        if not recommendation:
            self.stdout.write(self.style.ERROR('No pending recommendation found!'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found recommendation: ID {recommendation.id}'))
        self.stdout.write(f'Date: {recommendation.recommendation_date}')
        self.stdout.write(f'Status: {recommendation.status}')
        self.stdout.write('')
        
        # Calculate totals
        actions = recommendation.actions.all().select_related('stock', 'stock__investment_type', 'investment_subtype')
        
        total_buys = Decimal('0')
        total_sells = Decimal('0')
        total_buys_reais = Decimal('0')
        total_sells_reais = Decimal('0')
        total_buys_dolares = Decimal('0')
        total_buys_crypto = Decimal('0')
        
        buy_details = []
        sell_details = []
        
        for action in actions:
            action_type = action.action_type
            stock = action.stock
            difference = action.difference
            quantity_to_buy = action.quantity_to_buy
            quantity_to_sell = action.quantity_to_sell
            investment_subtype = action.investment_subtype
            subtype_name = investment_subtype.name if investment_subtype else ''
            
            if stock:
                ticker = stock.ticker
                current_price = stock.current_price or Decimal('0')
                
                # Determine if this is "Ações em Reais" or "BDRs"
                is_bdr = 'BDR' in subtype_name.upper() if subtype_name else False
                is_acoes_reais = not is_bdr and stock.investment_type and stock.investment_type.code == 'RENDA_VARIAVEL_REAIS'
                
                if action_type == 'buy' or (action_type == 'rebalance' and difference > 0):
                    if quantity_to_buy and quantity_to_buy > 0:
                        buy_value = current_price * Decimal(str(quantity_to_buy))
                        total_buys += buy_value
                        
                        if is_acoes_reais:
                            total_buys_reais += buy_value
                        elif is_bdr:
                            total_buys_dolares += buy_value
                        
                        buy_details.append({
                            'ticker': ticker,
                            'action': f'Comprar {quantity_to_buy}',
                            'price': float(current_price),
                            'value': float(buy_value),
                            'type': 'Ações em Reais' if is_acoes_reais else 'BDRs'
                        })
                    elif difference > 0:
                        # Use difference as buy value
                        total_buys += difference
                        if is_acoes_reais:
                            total_buys_reais += difference
                        elif is_bdr:
                            total_buys_dolares += difference
                        
                        buy_details.append({
                            'ticker': ticker,
                            'action': f'Comprar (diff: {difference})',
                            'price': float(current_price),
                            'value': float(difference),
                            'type': 'Ações em Reais' if is_acoes_reais else 'BDRs'
                        })
                
                elif action_type == 'sell' or (action_type == 'rebalance' and difference < 0):
                    if quantity_to_sell and quantity_to_sell < 0:
                        sell_value = current_price * Decimal(str(abs(quantity_to_sell)))
                        total_sells += sell_value
                        
                        if is_acoes_reais:
                            total_sells_reais += sell_value
                        
                        sell_details.append({
                            'ticker': ticker,
                            'action': f'Vender {abs(quantity_to_sell)}',
                            'price': float(current_price),
                            'value': float(sell_value),
                            'type': 'Ações em Reais'
                        })
                    elif difference < 0:
                        # Use absolute difference as sell value
                        sell_value = abs(difference)
                        total_sells += sell_value
                        if is_acoes_reais:
                            total_sells_reais += sell_value
                        
                        sell_details.append({
                            'ticker': ticker,
                            'action': f'Vender (diff: {abs(difference)})',
                            'price': float(current_price),
                            'value': float(sell_value),
                            'type': 'Ações em Reais'
                        })
            
            # Handle crypto
            elif not stock and investment_subtype and ('crypto' in subtype_name.lower() or 'cripto' in subtype_name.lower()):
                if difference > 0:
                    total_buys_crypto += difference
                    buy_details.append({
                        'ticker': 'BTC',
                        'action': 'Comprar Crypto',
                        'price': 0,
                        'value': float(difference),
                        'type': 'Cripto'
                    })
        
        # Print results
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('RESUMO DA RECOMENDAÇÃO'))
        self.stdout.write('=' * 80)
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('📊 COMPRAS:'))
        self.stdout.write(f'   Total Geral: R$ {total_buys:,.2f}')
        self.stdout.write(f'   - Ações em Reais: R$ {total_buys_reais:,.2f}')
        self.stdout.write(f'   - BDRs: R$ {total_buys_dolares:,.2f}')
        self.stdout.write(f'   - Cripto: R$ {total_buys_crypto:,.2f}')
        self.stdout.write('')
        
        self.stdout.write(self.style.WARNING('💰 VENDAS:'))
        self.stdout.write(f'   Total Geral: R$ {total_sells:,.2f}')
        self.stdout.write(f'   - Ações em Reais: R$ {total_sells_reais:,.2f}')
        self.stdout.write('')
        
        net_flow = total_buys - total_sells
        self.stdout.write(self.style.SUCCESS('📈 FLUXO LÍQUIDO:'))
        self.stdout.write(f'   Total: R$ {net_flow:,.2f}')
        self.stdout.write(f'   (Compras - Vendas)')
        self.stdout.write('')
        
        self.stdout.write('=' * 80)
        self.stdout.write('DETALHES DAS COMPRAS')
        self.stdout.write('=' * 80)
        for detail in buy_details:
            self.stdout.write(f"   {detail['ticker']:8s} | {detail['action']:25s} | Preço: R$ {detail['price']:8.2f} | Valor: R$ {detail['value']:10.2f} | {detail['type']}")
        
        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write('DETALHES DAS VENDAS')
        self.stdout.write('=' * 80)
        for detail in sell_details:
            self.stdout.write(f"   {detail['ticker']:8s} | {detail['action']:25s} | Preço: R$ {detail['price']:8.2f} | Valor: R$ {detail['value']:10.2f} | {detail['type']}")
        
        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write('INFORMAÇÕES DA RECOMENDAÇÃO')
        self.stdout.write('=' * 80)
        self.stdout.write(f"   Vendas Já Realizadas no Mês: R$ {recommendation.previous_sales_this_month:,.2f}")
        self.stdout.write(f"   Limite Disponível para Vendas: R$ {recommendation.sales_limit_remaining:,.2f}")
        self.stdout.write(f"   Total Vendas na Recomendação: R$ {recommendation.total_sales_value:,.2f}")



