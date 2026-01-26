"""
Script to calculate the total value of rebalancing recommendations
using actual current prices vs. Stocks in Reals recommendations.
"""
import requests
import json
from decimal import Decimal

# API base URL
API_BASE = "http://localhost:8000/api"

# User ID (Aurelio Avanzi)
USER_ID = "024.537.739-50"

def get_latest_recommendation(user_id):
    """Get the latest rebalancing recommendation for a user."""
    response = requests.get(f"{API_BASE}/rebalancing-recommendations/", params={"user_id": user_id})
    if response.status_code == 200:
        recommendations = response.json()
        if recommendations:
            # Get the most recent recommendation
            latest = max(recommendations, key=lambda x: x.get('recommendation_date', ''))
            return latest
    return None

def get_stock_current_price(ticker):
    """Get current price for a stock ticker."""
    response = requests.get(f"{API_BASE}/stocks/", params={"ticker": ticker, "is_active": "true"})
    if response.status_code == 200:
        stocks = response.json()
        if stocks:
            stock = stocks[0]
            return Decimal(str(stock.get('current_price', 0)))
    return Decimal('0')

def calculate_recommendation_totals(recommendation):
    """Calculate total buy and sell values using current prices."""
    actions = recommendation.get('actions', [])
    
    total_buys = Decimal('0')
    total_sells = Decimal('0')
    total_buys_reais = Decimal('0')
    total_sells_reais = Decimal('0')
    total_buys_dolares = Decimal('0')
    total_buys_crypto = Decimal('0')
    
    buy_details = []
    sell_details = []
    
    for action in actions:
        action_type = action.get('action_type')
        stock = action.get('stock')
        difference = Decimal(str(action.get('difference', 0)))
        quantity_to_buy = action.get('quantity_to_buy')
        quantity_to_sell = action.get('quantity_to_sell')
        current_value = Decimal(str(action.get('current_value', 0)))
        investment_subtype = action.get('investment_subtype')
        subtype_name = investment_subtype.get('name', '') if investment_subtype else ''
        
        if stock:
            ticker = stock.get('ticker')
            current_price = Decimal(str(stock.get('current_price', 0)))
            
            # Determine if this is "Ações em Reais" or "BDRs"
            is_bdr = 'BDR' in subtype_name.upper() if subtype_name else False
            is_acoes_reais = not is_bdr and stock.get('investment_type', {}).get('code') == 'RENDA_VARIAVEL_REAIS'
            
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
                if quantity_to_sell and quantity_to_sell > 0:
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
        elif not stock and ('crypto' in subtype_name.lower() or 'cripto' in subtype_name.lower()):
            if difference > 0:
                total_buys_crypto += difference
                buy_details.append({
                    'ticker': 'BTC',
                    'action': action.get('crypto_currency_symbol', 'Crypto'),
                    'price': 0,
                    'value': float(difference),
                    'type': 'Cripto'
                })
    
    return {
        'total_buys': float(total_buys),
        'total_sells': float(total_sells),
        'total_buys_reais': float(total_buys_reais),
        'total_sells_reais': float(total_sells_reais),
        'total_buys_dolares': float(total_buys_dolares),
        'total_buys_crypto': float(total_buys_crypto),
        'net_flow': float(total_buys - total_sells),
        'buy_details': buy_details,
        'sell_details': sell_details
    }

def main():
    print("=" * 80)
    print("CÁLCULO DO TOTAL DA RECOMENDAÇÃO DE REBALANCEAMENTO")
    print("=" * 80)
    print()
    
    # Get latest recommendation
    print(f"Buscando recomendação mais recente para usuário {USER_ID}...")
    recommendation = get_latest_recommendation(USER_ID)
    
    if not recommendation:
        print("❌ Nenhuma recomendação encontrada!")
        return
    
    print(f"✅ Recomendação encontrada: ID {recommendation.get('id')}")
    print(f"   Data: {recommendation.get('recommendation_date')}")
    print(f"   Status: {recommendation.get('status')}")
    print()
    
    # Calculate totals
    print("Calculando totais usando preços atuais...")
    totals = calculate_recommendation_totals(recommendation)
    
    print()
    print("=" * 80)
    print("RESUMO DA RECOMENDAÇÃO")
    print("=" * 80)
    print()
    
    print("📊 COMPRAS:")
    print(f"   Total Geral: R$ {totals['total_buys']:,.2f}")
    print(f"   - Ações em Reais: R$ {totals['total_buys_reais']:,.2f}")
    print(f"   - BDRs: R$ {totals['total_buys_dolares']:,.2f}")
    print(f"   - Cripto: R$ {totals['total_buys_crypto']:,.2f}")
    print()
    
    print("💰 VENDAS:")
    print(f"   Total Geral: R$ {totals['total_sells']:,.2f}")
    print(f"   - Ações em Reais: R$ {totals['total_sells_reais']:,.2f}")
    print()
    
    print("📈 FLUXO LÍQUIDO:")
    print(f"   Total: R$ {totals['net_flow']:,.2f}")
    print(f"   (Compras - Vendas)")
    print()
    
    print("=" * 80)
    print("DETALHES DAS COMPRAS")
    print("=" * 80)
    for detail in totals['buy_details']:
        print(f"   {detail['ticker']:8s} | {detail['action']:20s} | Preço: R$ {detail['price']:8.2f} | Valor: R$ {detail['value']:10.2f} | {detail['type']}")
    
    print()
    print("=" * 80)
    print("DETALHES DAS VENDAS")
    print("=" * 80)
    for detail in totals['sell_details']:
        print(f"   {detail['ticker']:8s} | {detail['action']:20s} | Preço: R$ {detail['price']:8.2f} | Valor: R$ {detail['value']:10.2f} | {detail['type']}")
    
    print()
    print("=" * 80)
    print("INFORMAÇÕES DA RECOMENDAÇÃO")
    print("=" * 80)
    print(f"   Vendas Já Realizadas no Mês: R$ {recommendation.get('previous_sales_this_month', 0):,.2f}")
    print(f"   Limite Disponível para Vendas: R$ {recommendation.get('sales_limit_remaining', 0):,.2f}")
    print(f"   Total Vendas na Recomendação: R$ {recommendation.get('total_sales_value', 0):,.2f}")
    print(f"   Vendas Completas: R$ {recommendation.get('total_complete_sales_value', 0):,.2f}")
    print(f"   Vendas Parciais: R$ {recommendation.get('total_partial_sales_value', 0):,.2f}")

if __name__ == "__main__":
    main()





