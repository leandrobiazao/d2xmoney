"""
Portfolio service for managing aggregated portfolio summaries.
This service manages portfolio summaries per user per ticker, including realized profit calculations using FIFO method.
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import re
from django.db import transaction
from .models import PortfolioPosition, CorporateEvent
from brokerage_notes.services import BrokerageNoteHistoryService


class PortfolioService:
    """Service for managing portfolio summaries using Django ORM."""
    
    @staticmethod
    def is_fii(ticker: str) -> bool:
        """
        Check if a ticker is a FII (Fundo Imobiliário).
        FIIs typically end with '11' in Brazilian market.
        """
        if not ticker:
            return False
        ticker_upper = ticker.strip().upper()
        return ticker_upper.endswith('11')
    
    @staticmethod
    def get_portfolio_file_path():
        """Legacy method - kept for backward compatibility."""
        # This method is no longer used but kept for compatibility
        pass
    
    @staticmethod
    def load_portfolio() -> Dict[str, List[Dict]]:
        """Load portfolio from database."""
        positions = PortfolioPosition.objects.all()
        
        portfolio = {}
        for position in positions:
            user_id = position.user_id
            if user_id not in portfolio:
                portfolio[user_id] = []
            
            portfolio[user_id].append({
                'titulo': position.ticker,
                'quantidade': position.quantidade,
                'precoMedio': float(position.preco_medio),
                'valorTotalInvestido': float(position.valor_total_investido),
                'lucroRealizado': float(position.lucro_realizado),
            })
        
        # Sort each user's positions by ticker
        for user_id in portfolio:
            portfolio[user_id].sort(key=lambda x: x['titulo'])
        
        return portfolio
    
    @staticmethod
    def save_portfolio(portfolio: Dict[str, List[Dict]]) -> None:
        """Save portfolio to database."""
        # Delete all existing positions
        PortfolioPosition.objects.all().delete()
        
        # Create new positions
        for user_id, ticker_summaries in portfolio.items():
            for summary in ticker_summaries:
                PortfolioPosition.objects.create(
                    user_id=user_id,
                    ticker=summary.get('titulo', ''),
                    quantidade=summary.get('quantidade', 0),
                    preco_medio=summary.get('precoMedio', 0.0),
                    valor_total_investido=summary.get('valorTotalInvestido', 0.0),
                    lucro_realizado=summary.get('lucroRealizado', 0.0),
                )
    
    @staticmethod
    def get_user_portfolio(user_id: str) -> List[Dict]:
        """Get ticker summaries for a user."""
        positions = PortfolioPosition.objects.filter(user_id=user_id).order_by('ticker')
        
        return [
            {
                'titulo': position.ticker,
                'quantidade': position.quantidade,
                'precoMedio': float(position.preco_medio),
                'valorTotalInvestido': float(position.valor_total_investido),
                'lucroRealizado': float(position.lucro_realizado),
            }
            for position in positions
        ]
    
    @staticmethod
    def parse_date(date_str: str) -> Tuple[int, int, int]:
        """Parse date string DD/MM/YYYY to (year, month, day) for sorting."""
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                return (year, month, day)
        except (ValueError, IndexError):
            pass
        return (0, 0, 0)
    
    @staticmethod
    def calculate_fifo_profit(sale_quantity: int, sale_price: float, purchase_queue: List[Dict]) -> Tuple[float, List[Dict]]:
        """
        Calculate realized profit using FIFO method.
        
        Args:
            sale_quantity: Quantity being sold
            sale_price: Price per unit of sale
            purchase_queue: List of purchase records [{quantidade, preco, data, ordem}, ...]
        
        Returns:
            Tuple of (realized_profit, updated_purchase_queue)
        """
        realized_profit = 0.0
        remaining_sale_quantity = sale_quantity
        updated_queue = []
        
        for purchase in purchase_queue:
            if remaining_sale_quantity <= 0:
                # All sold, keep remaining purchases
                updated_queue.append(purchase)
                continue
            
            purchase_quantity = purchase.get('quantidade', 0)
            purchase_price = purchase.get('preco', 0.0)
            
            if purchase_quantity <= remaining_sale_quantity:
                # Sell entire purchase lot
                profit = (sale_price - purchase_price) * purchase_quantity
                realized_profit += profit
                remaining_sale_quantity -= purchase_quantity
            else:
                # Partial sale of this purchase lot
                profit = (sale_price - purchase_price) * remaining_sale_quantity
                realized_profit += profit
                
                # Keep remaining quantity in queue
                updated_queue.append({
                    'quantidade': purchase_quantity - remaining_sale_quantity,
                    'preco': purchase_price,
                    'data': purchase.get('data'),
                    'ordem': purchase.get('ordem')
                })
                remaining_sale_quantity = 0
        
        if remaining_sale_quantity > 0:
            # Sale exceeds holdings - this shouldn't happen but handle gracefully
            print(f"Warning: Sale quantity {sale_quantity} exceeds available holdings")
        
        return (realized_profit, updated_queue)
    
    @staticmethod
    def calculate_average_cost_profit(sale_quantity: int, sale_price: float, average_cost: float) -> float:
        """
        Calculate realized profit using Average Cost method.
        
        Args:
            sale_quantity: Quantity being sold
            sale_price: Price per unit of sale
            average_cost: Current weighted average cost per unit
        
        Returns:
            Realized profit (sale_price - average_cost) × sale_quantity
        """
        if average_cost <= 0:
            # No average cost, assume zero cost basis
            return 0.0
        
        realized_profit = (sale_price - average_cost) * sale_quantity
        return realized_profit
    
    @staticmethod
    def process_operations_average_cost(operations: List[Dict]) -> Dict[str, Dict]:
        """
        Process operations using Average Cost method and return ticker summaries.
        
        Average Cost method uses the current weighted average price for all sales,
        regardless of which specific purchases are being sold.
        
        Args:
            operations: List of operations sorted chronologically
        
        Returns:
            Dict mapping ticker to summary: {ticker: {quantidade, precoMedio, valorTotalInvestido, lucroRealizado}}
        """
        ticker_summaries = {}  # {ticker: {quantidade, precoMedio, valorTotalInvestido, lucroRealizado}}
        
        for operation in operations:
            ticker = operation.get('titulo', '').strip()
            if not ticker:
                continue
            
            tipo_operacao = operation.get('tipoOperacao', '').upper()
            quantidade = abs(operation.get('quantidade', 0))
            preco = operation.get('preco', 0.0)
            valor_operacao = operation.get('valorOperacao', 0.0)
            
            # Initialize ticker summary if not exists
            if ticker not in ticker_summaries:
                ticker_summaries[ticker] = {
                    'quantidade': 0,
                    'precoMedio': 0.0,
                    'valorTotalInvestido': 0.0,
                    'lucroRealizado': 0.0,
                }
            
            summary = ticker_summaries[ticker]
            
            if tipo_operacao == 'C':  # Purchase
                # Calculate new weighted average price
                current_quantity = summary['quantidade']
                current_value = summary['valorTotalInvestido']
                
                new_quantity = current_quantity + quantidade
                
                # If closing a short position (going from negative to zero or positive)
                if current_quantity < 0:
                    if new_quantity <= 0:
                        # Still short or exactly zero - reduce short position
                        short_closing_qty = min(quantidade, abs(current_quantity))
                        if short_closing_qty > 0:
                            closing_profit = (summary['precoMedio'] - preco) * short_closing_qty
                            summary['lucroRealizado'] += closing_profit
                        
                        summary['quantidade'] = new_quantity
                        summary['valorTotalInvestido'] = 0.0
                        
                        if new_quantity < 0:
                            # Still short - update average short price
                            old_abs_qty = abs(current_quantity)
                            old_price = summary['precoMedio']
                            new_abs_qty = abs(new_quantity)
                            if old_abs_qty > 0:
                                total_short_value = old_abs_qty * old_price - short_closing_qty * preco
                                summary['precoMedio'] = total_short_value / new_abs_qty if new_abs_qty > 0 else 0.0
                            else:
                                summary['precoMedio'] = preco
                        else:
                            # Exactly zero - close short position completely
                            summary['precoMedio'] = 0.0
                    else:
                        # Closing short and going long
                        short_closing_profit = (summary['precoMedio'] - preco) * abs(current_quantity)
                        summary['lucroRealizado'] += short_closing_profit
                        remaining_qty = new_quantity
                        summary['quantidade'] = remaining_qty
                        summary['valorTotalInvestido'] = remaining_qty * preco
                        summary['precoMedio'] = preco
                else:
                    # Normal purchase (from zero or positive)
                    new_value = current_value + valor_operacao
                    summary['quantidade'] = new_quantity
                    summary['valorTotalInvestido'] = new_value
                    summary['precoMedio'] = new_value / new_quantity if new_quantity > 0 else 0.0
                    if new_quantity == 0:
                        summary['valorTotalInvestido'] = 0.0
                        summary['precoMedio'] = 0.0
                
            elif tipo_operacao == 'V':  # Sale
                # Calculate realized profit using current average cost
                current_average_cost = summary['precoMedio']
                current_quantity = summary['quantidade']
                
                # Calculate realized profit for the full sale quantity
                # Allow selling more than available (short position)
                if current_quantity > 0:
                    realized_profit = PortfolioService.calculate_average_cost_profit(
                        quantidade, preco, current_average_cost
                    )
                    
                    # Recalculate value invested (proportional reduction)
                    reduction_ratio = quantidade / current_quantity
                    summary['valorTotalInvestido'] *= (1 - reduction_ratio)
                    if summary['valorTotalInvestido'] < 0:
                        summary['valorTotalInvestido'] = 0.0
                else:
                    # Selling more than available (short position or negative quantity)
                    if current_quantity < 0:
                        # Already in short position
                        realized_profit = PortfolioService.calculate_average_cost_profit(
                            quantidade, preco, current_average_cost
                        )
                    else:
                        # Going from positive/zero to negative
                        realized_profit = 0.0
                    summary['valorTotalInvestido'] = 0.0
                
                # Update realized profit (cumulative)
                summary['lucroRealizado'] += realized_profit
                
                # Update quantity - allow negative values
                summary['quantidade'] = current_quantity - quantidade
                
                # If quantity reached zero, zero out invested value
                if summary['quantidade'] == 0:
                    summary['valorTotalInvestido'] = 0.0
                    summary['precoMedio'] = 0.0
                elif summary['quantidade'] > 0:
                    # Positive quantity - update average cost
                    if summary['valorTotalInvestido'] > 0:
                        summary['precoMedio'] = summary['valorTotalInvestido'] / summary['quantidade']
                    else:
                        summary['precoMedio'] = 0.0
                else:
                    # Negative quantity (short position)
                    # Calculate weighted average of short positions
                    old_abs_qty = abs(current_quantity) if current_quantity < 0 else 0
                    old_price = summary['precoMedio'] if current_quantity < 0 and summary['precoMedio'] > 0 else 0.0
                    
                    new_abs_qty = abs(summary['quantidade'])
                    if old_abs_qty > 0:
                        # Weighted average
                        total_short_value = old_abs_qty * old_price + quantidade * preco
                        summary['precoMedio'] = total_short_value / new_abs_qty
                    else:
                        # First time going short
                        summary['precoMedio'] = preco
                    summary['valorTotalInvestido'] = 0.0
                
                print(f"  [VENDA] {ticker} {operation_date_str}: -{quantidade} -> Total: {summary['quantidade']}")
        
        return ticker_summaries
    
    @staticmethod
    def process_operations_fifo(operations: List[Dict]) -> Dict[str, Dict]:
        """
        Process operations using FIFO method and return ticker summaries.
        
        Args:
            operations: List of operations sorted chronologically
        
        Returns:
            Dict mapping ticker to summary: {ticker: {quantidade, precoMedio, valorTotalInvestido, lucroRealizado}}
        """
        ticker_summaries = {}  # {ticker: {quantidade, precoMedio, valorTotalInvestido, lucroRealizado, purchase_queue}}
        
        for operation in operations:
            ticker = operation.get('titulo', '').strip()
            if not ticker:
                continue
            
            tipo_operacao = operation.get('tipoOperacao', '').upper()
            quantidade = abs(operation.get('quantidade', 0))
            preco = operation.get('preco', 0.0)
            valor_operacao = operation.get('valorOperacao', 0.0)
            data = operation.get('data', '')
            ordem = operation.get('ordem', 0)
            
            # Initialize ticker summary if not exists
            if ticker not in ticker_summaries:
                ticker_summaries[ticker] = {
                    'quantidade': 0,
                    'precoMedio': 0.0,
                    'valorTotalInvestido': 0.0,
                    'lucroRealizado': 0.0,
                    'purchase_queue': []  # Internal: FIFO queue of purchases
                }
            
            summary = ticker_summaries[ticker]
            
            if tipo_operacao == 'C':  # Purchase
                # Add to FIFO purchase queue
                summary['purchase_queue'].append({
                    'quantidade': quantidade,
                    'preco': preco,
                    'data': data,
                    'ordem': ordem
                })
                
                # Update quantity
                summary['quantidade'] += quantidade
                
                # Recalculate weighted average price
                total_value = sum(p['quantidade'] * p['preco'] for p in summary['purchase_queue'])
                total_quantity = sum(p['quantidade'] for p in summary['purchase_queue'])
                summary['precoMedio'] = total_value / total_quantity if total_quantity > 0 else 0.0
                summary['valorTotalInvestido'] = total_value
                
            elif tipo_operacao == 'V':  # Sale
                # Calculate realized profit using FIFO
                current_quantity = summary['quantidade']
                
                if current_quantity > 0 and len(summary['purchase_queue']) > 0:
                    # Normal FIFO processing when we have shares
                    realized_profit, updated_queue = PortfolioService.calculate_fifo_profit(
                        quantidade, preco, summary['purchase_queue']
                    )
                    summary['purchase_queue'] = updated_queue
                else:
                    # Short position or no shares - no FIFO queue to process
                    if current_quantity < 0:
                        # Already short, calculate profit based on current average
                        realized_profit = PortfolioService.calculate_average_cost_profit(
                            quantidade, preco, summary['precoMedio']
                        )
                    else:
                        # Going short for the first time
                        realized_profit = 0.0
                    summary['purchase_queue'] = []  # No purchase queue for short positions
                
                # Update realized profit
                summary['lucroRealizado'] += realized_profit
                
                # Update quantity - allow negative values
                summary['quantidade'] = current_quantity - quantidade
                
                # Recalculate weighted average price
                if summary['quantidade'] > 0 and len(summary['purchase_queue']) > 0:
                    # Long position - calculate from purchase queue
                    total_value = sum(p['quantidade'] * p['preco'] for p in summary['purchase_queue'])
                    total_quantity = sum(p['quantidade'] for p in summary['purchase_queue'])
                    summary['precoMedio'] = total_value / total_quantity if total_quantity > 0 else 0.0
                    summary['valorTotalInvestido'] = total_value
                elif summary['quantidade'] < 0:
                    # Short position - update average short price
                    old_abs_qty = abs(current_quantity) if current_quantity < 0 else 0
                    old_price = summary['precoMedio'] if current_quantity < 0 and summary['precoMedio'] > 0 else 0.0
                    
                    new_abs_qty = abs(summary['quantidade'])
                    if old_abs_qty > 0:
                        total_short_value = old_abs_qty * old_price + quantidade * preco
                        summary['precoMedio'] = total_short_value / new_abs_qty
                    else:
                        summary['precoMedio'] = preco
                    summary['valorTotalInvestido'] = 0.0
                else:
                    # Zero quantity
                    summary['precoMedio'] = 0.0
                    summary['valorTotalInvestido'] = 0.0
        
        # Clean up: remove purchase_queue from final summaries (it's internal)
        for ticker in ticker_summaries:
            if 'purchase_queue' in ticker_summaries[ticker]:
                del ticker_summaries[ticker]['purchase_queue']
        
        return ticker_summaries
    
    @staticmethod
    def process_operations_with_corporate_events(operations: List[Dict], events_by_ticker: Dict[str, List[CorporateEvent]]) -> Dict[str, Dict]:
        """
        Process operations chronologically and apply corporate events when appropriate.
        
        When processing reaches an operation date that is equal to or after a corporate event's ex_date,
        the accumulated positions for that ticker are adjusted before processing that operation.
        
        Args:
            operations: List of operations sorted chronologically
            events_by_ticker: Dict mapping ticker to list of CorporateEvent objects (sorted by ex_date)
        
        Returns:
            Dict mapping ticker to summary: {ticker: {quantidade, precoMedio, valorTotalInvestido, lucroRealizado}}
        """
        from datetime import datetime
        
        ticker_summaries = {}  # {ticker: {quantidade, precoMedio, valorTotalInvestido, lucroRealizado}}
        applied_events = {}  # Track which events have been applied per ticker: {ticker: [event_id, ...]}
        
        for operation in operations:
            ticker = operation.get('titulo', '').strip().upper()
            if not ticker:
                continue
            
            operation_date_str = operation.get('data', '')
            if not operation_date_str:
                continue
            
            # Parse operation date (DD/MM/YYYY)
            try:
                parts = operation_date_str.split('/')
                if len(parts) == 3:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    operation_date = datetime(year, month, day).date()
                else:
                    operation_date = None
            except (ValueError, IndexError):
                operation_date = None
            
            # Check for corporate events that should be applied before this operation
            if ticker in events_by_ticker and operation_date:
                for event in events_by_ticker[ticker]:
                    # Skip if event already applied
                    if ticker in applied_events and event.id in applied_events[ticker]:
                        continue
                    
                    # Apply event if operation date is >= ex_date
                    if operation_date >= event.ex_date:
                        # Initialize ticker summary if needed
                        if ticker not in ticker_summaries:
                            ticker_summaries[ticker] = {
                                'quantidade': 0,
                                'precoMedio': 0.0,
                                'valorTotalInvestido': 0.0,
                                'lucroRealizado': 0.0,
                            }
                        
                        # Apply corporate event adjustment
                        PortfolioService._apply_corporate_event_to_summary(
                            ticker_summaries[ticker], event
                        )
                        
                        # Mark event as applied
                        if ticker not in applied_events:
                            applied_events[ticker] = []
                        applied_events[ticker].append(event.id)
            
            # Process the operation
            tipo_operacao = operation.get('tipoOperacao', '').upper()
            quantidade = abs(operation.get('quantidade', 0))
            preco = operation.get('preco', 0.0)
            valor_operacao = operation.get('valorOperacao', 0.0)
            
            # Initialize ticker summary if not exists
            if ticker not in ticker_summaries:
                ticker_summaries[ticker] = {
                    'quantidade': 0,
                    'precoMedio': 0.0,
                    'valorTotalInvestido': 0.0,
                    'lucroRealizado': 0.0,
                }
            
            summary = ticker_summaries[ticker]
            
            if tipo_operacao == 'C':  # Purchase
                # Calculate new weighted average price
                current_quantity = summary['quantidade']
                current_value = summary['valorTotalInvestido']
                
                new_quantity = current_quantity + quantidade
                
                # If closing a short position (going from negative to zero or positive)
                if current_quantity < 0:
                    if new_quantity <= 0:
                        # Still short or exactly zero - reduce short position
                        short_closing_qty = min(quantidade, abs(current_quantity))
                        if short_closing_qty > 0:
                            closing_profit = (summary['precoMedio'] - preco) * short_closing_qty
                            summary['lucroRealizado'] += closing_profit
                        
                        summary['quantidade'] = new_quantity
                        summary['valorTotalInvestido'] = 0.0
                        
                        if new_quantity < 0:
                            # Still short - update average short price
                            old_abs_qty = abs(current_quantity)
                            old_price = summary['precoMedio']
                            new_abs_qty = abs(new_quantity)
                            if old_abs_qty > 0:
                                total_short_value = old_abs_qty * old_price - short_closing_qty * preco
                                summary['precoMedio'] = total_short_value / new_abs_qty if new_abs_qty > 0 else 0.0
                            else:
                                summary['precoMedio'] = preco
                        else:
                            # Exactly zero - close short position completely
                            summary['precoMedio'] = 0.0
                    else:
                        # Closing short and going long
                        short_closing_profit = (summary['precoMedio'] - preco) * abs(current_quantity)
                        summary['lucroRealizado'] += short_closing_profit
                        remaining_qty = new_quantity
                        summary['quantidade'] = remaining_qty
                        summary['valorTotalInvestido'] = remaining_qty * preco
                        summary['precoMedio'] = preco
                else:
                    # Normal purchase (from zero or positive)
                    new_value = current_value + valor_operacao
                    summary['quantidade'] = new_quantity
                    summary['valorTotalInvestido'] = new_value
                    summary['precoMedio'] = new_value / new_quantity if new_quantity > 0 else 0.0
                    if new_quantity == 0:
                        summary['valorTotalInvestido'] = 0.0
                        summary['precoMedio'] = 0.0
                
            elif tipo_operacao == 'V':  # Sale
                # Calculate realized profit using current average cost
                current_average_cost = summary['precoMedio']
                current_quantity = summary['quantidade']
                
                # Calculate realized profit for the full sale quantity
                # Allow selling more than available (short position) for both stocks and FIIs
                if current_quantity > 0:
                    realized_profit = PortfolioService.calculate_average_cost_profit(
                        quantidade, preco, current_average_cost
                    )
                    
                    # Recalculate value invested (proportional reduction)
                    reduction_ratio = quantidade / current_quantity
                    summary['valorTotalInvestido'] *= (1 - reduction_ratio)
                    if summary['valorTotalInvestido'] < 0:
                        summary['valorTotalInvestido'] = 0.0
                else:
                    # Selling more than available (short position or negative quantity)
                    if current_quantity < 0:
                        # Already in short position
                        realized_profit = PortfolioService.calculate_average_cost_profit(
                            quantidade, preco, current_average_cost
                        )
                    else:
                        # Going from positive/zero to negative
                        realized_profit = 0.0
                    summary['valorTotalInvestido'] = 0.0
                
                # Update realized profit (cumulative)
                summary['lucroRealizado'] += realized_profit
                
                # Update quantity - allow negative values
                summary['quantidade'] = current_quantity - quantidade
                
                # If quantity reached zero, zero out invested value
                if summary['quantidade'] == 0:
                    summary['valorTotalInvestido'] = 0.0
                    summary['precoMedio'] = 0.0
                elif summary['quantidade'] > 0:
                    # Positive quantity - update average cost from remaining invested value
                    if summary['valorTotalInvestido'] > 0:
                        summary['precoMedio'] = summary['valorTotalInvestido'] / summary['quantidade']
                    else:
                        summary['precoMedio'] = 0.0
                else:
                    # Negative quantity (short position) - use sale price as average for tracking
                    # This represents the average price at which we're short
                    # Calculate weighted average: (old_qty * old_price + new_qty * new_price) / total_qty
                    old_abs_qty = abs(current_quantity) if current_quantity < 0 else 0
                    old_price = summary['precoMedio'] if current_quantity < 0 and summary['precoMedio'] > 0 else 0.0
                    
                    new_abs_qty = abs(summary['quantidade'])
                    if old_abs_qty > 0:
                        # Weighted average of short positions
                        total_short_value = old_abs_qty * old_price + quantidade * preco
                        summary['precoMedio'] = total_short_value / new_abs_qty
                    else:
                        # First time going short
                        summary['precoMedio'] = preco
                    summary['valorTotalInvestido'] = 0.0
        
        # Apply any remaining corporate events that haven't been applied yet
        # This handles cases where all operations occurred before the ex-date
        for ticker_key, events in events_by_ticker.items():
            ticker_upper = ticker_key.upper()
            for event in events:
                # Skip if event already applied
                if ticker_upper in applied_events and event.id in applied_events[ticker_upper]:
                    continue
                
                # Check if ticker has a position (check both original and uppercase key)
                ticker_in_summary = ticker_upper if ticker_upper in ticker_summaries else None
                if not ticker_in_summary:
                    # Try to find matching ticker (case-insensitive)
                    for existing_ticker in ticker_summaries.keys():
                        if existing_ticker.upper() == ticker_upper:
                            ticker_in_summary = existing_ticker
                            break
                
                # If ticker has a position, apply the event
                if ticker_in_summary and ticker_summaries[ticker_in_summary]['quantidade'] > 0:
                    PortfolioService._apply_corporate_event_to_summary(
                        ticker_summaries[ticker_in_summary], event
                    )
                    # Mark as applied
                    if ticker_upper not in applied_events:
                        applied_events[ticker_upper] = []
                    applied_events[ticker_upper].append(event.id)
        
        return ticker_summaries
    
    @staticmethod
    def _apply_corporate_event_to_summary(summary: Dict, event: CorporateEvent) -> None:
        """
        Apply a corporate event adjustment to a ticker summary dictionary.
        
        For grouping (reverse split): If resulting quantity < 1, the position is zeroed (sold at market).
        """
        try:
            numerator, denominator = event.parse_ratio()
        except ValueError:
            return  # Skip invalid events
        
        old_quantity = summary['quantidade']
        old_price = summary['precoMedio']
        old_total = summary['valorTotalInvestido']
        
        if old_quantity <= 0:
            return  # Nothing to adjust
        
        # Convert to Decimal for calculations
        old_price_decimal = Decimal(str(old_price))
        old_total_decimal = Decimal(str(old_total))
        
        if event.event_type == 'GROUPING':
            # Reverse split (grupamento): 20:1 means 20 old shares become 1 new share
            # Quantity decreases by dividing by numerator (20), price increases by multiplying by numerator
            new_quantity_float = old_quantity / numerator
            new_quantity = int(new_quantity_float)
            
            # If resulting quantity is less than 1 (fraction), position is sold at market (zeroed)
            if new_quantity < 1:
                # Position liquidated (sold at market value)
                summary['quantidade'] = 0
                summary['precoMedio'] = 0.0
                summary['valorTotalInvestido'] = 0.0
            else:
                new_price = old_price_decimal * Decimal(str(numerator))
                new_total = Decimal(str(new_quantity)) * new_price
                summary['quantidade'] = new_quantity
                summary['precoMedio'] = float(new_price)
                summary['valorTotalInvestido'] = float(new_total)
                
        elif event.event_type == 'SPLIT':
            # Split (desdobramento): 1:5 means 1 old share becomes 5 new shares
            # Quantity increases, price decreases
            new_quantity = int(old_quantity * numerator)
            new_price = old_price_decimal / Decimal(str(numerator))
            new_total = Decimal(str(new_quantity)) * new_price
            summary['quantidade'] = new_quantity
            summary['precoMedio'] = float(new_price)
            summary['valorTotalInvestido'] = float(new_total)
            
        elif event.event_type == 'BONUS':
            # Bonus: increases quantity
            # If bonus share value is specified in description (e.g., "R$ 5"), add it to total invested
            # Otherwise, maintain total invested constant (bonus shares have zero cost basis)
            bonus_share_value = None
            if event.description:
                # Try to extract bonus share value from description (e.g., "R$ 5", "R$5.00", "valor R$ 5")
                match = re.search(r'R\$\s*(\d+(?:[.,]\d+)?)', event.description, re.IGNORECASE)
                if match:
                    try:
                        bonus_share_value = Decimal(match.group(1).replace(',', '.'))
                    except (ValueError, AttributeError):
                        pass
            
            bonus_shares = int((old_quantity / denominator) * numerator)
            new_quantity = old_quantity + bonus_shares
            
            if bonus_share_value is not None:
                # Add bonus share value to total invested
                bonus_total_value = Decimal(str(bonus_shares)) * bonus_share_value
                new_total = old_total_decimal + bonus_total_value
            else:
                # Keep total invested constant (bonus shares have zero cost basis)
                new_total = old_total_decimal
            
            new_price = new_total / Decimal(str(new_quantity)) if new_quantity > 0 else Decimal('0.00')
            summary['quantidade'] = new_quantity
            summary['precoMedio'] = float(new_price)
            summary['valorTotalInvestido'] = float(new_total)
    
    @staticmethod
    @transaction.atomic
    def apply_ticker_change(event: CorporateEvent) -> Dict:
        """
        Apply a ticker change event to consolidate positions and operations under the new ticker.
        
        This method:
        1. Finds all positions with the old ticker
        2. Updates them to use the new ticker (or merges if new ticker position already exists)
        3. Updates all operations in brokerage notes to use the new ticker
        
        Args:
            event: CorporateEvent with event_type='TICKER_CHANGE'
        
        Returns:
            Dict with result information
        """
        if event.event_type != 'TICKER_CHANGE':
            raise ValueError(f"Event must be of type TICKER_CHANGE, got {event.event_type}")
        
        if not event.previous_ticker:
            raise ValueError("previous_ticker is required for TICKER_CHANGE events")
        
        old_ticker = event.previous_ticker.upper()
        new_ticker = event.ticker.upper()
        
        # Find all positions with the old ticker
        old_positions = PortfolioPosition.objects.filter(ticker=old_ticker)
        positions_updated = 0
        
        for old_pos in old_positions:
            # Check if a position with the new ticker already exists for this user
            try:
                new_pos = PortfolioPosition.objects.get(user_id=old_pos.user_id, ticker=new_ticker)
                # Merge positions: add quantities and recalculate weighted average
                total_quantity = new_pos.quantidade + old_pos.quantidade
                total_invested = float(new_pos.valor_total_investido) + float(old_pos.valor_total_investido)
                
                if total_quantity > 0:
                    new_pos.preco_medio = Decimal(str(total_invested / total_quantity))
                else:
                    new_pos.preco_medio = Decimal('0.00')
                
                new_pos.quantidade = total_quantity
                new_pos.valor_total_investido = Decimal(str(total_invested))
                new_pos.lucro_realizado += old_pos.lucro_realizado
                new_pos.save()
                
                # Delete the old position
                old_pos.delete()
                positions_updated += 1
            except PortfolioPosition.DoesNotExist:
                # No existing position with new ticker, just rename
                old_pos.ticker = new_ticker
                old_pos.save()
                positions_updated += 1
        
        # Update operations in brokerage notes
        from brokerage_notes.models import BrokerageNote
        notes = BrokerageNote.objects.all()
        operations_updated = 0
        
        for note in notes:
            operations = note.operations or []
            modified = False
            
            for operation in operations:
                if operation.get('titulo', '').upper() == old_ticker:
                    operation['titulo'] = new_ticker
                    modified = True
                    operations_updated += 1
            
            if modified:
                note.operations = operations
                note.save()
        
        return {
            'success': True,
            'message': f'Ticker change applied: {old_ticker} -> {new_ticker}',
            'positions_updated': positions_updated,
            'operations_updated': operations_updated,
            'old_ticker': old_ticker,
            'new_ticker': new_ticker,
        }
    
    @staticmethod
    @transaction.atomic
    def apply_fund_conversion(event: CorporateEvent, user_id: Optional[str] = None) -> Dict:
        """
        Apply a fund conversion event (extinction/liquidation with conversion to another fund).
        
        This method:
        1. Finds all positions with the old ticker (extinct fund)
        2. Calculates new quantities using conversion ratio (e.g., 3:2 = 3 new for each 2 old)
        3. Creates/updates positions with the new ticker
        4. Removes old positions (extinct fund)
        5. Updates operations in brokerage notes
        
        Args:
            event: CorporateEvent with event_type='FUND_CONVERSION'
            user_id: Optional user_id to apply only for specific user
        
        Returns:
            Dict with result information
        """
        if event.event_type != 'FUND_CONVERSION':
            raise ValueError(f"Event must be of type FUND_CONVERSION, got {event.event_type}")
        
        if not event.previous_ticker:
            raise ValueError("previous_ticker is required for FUND_CONVERSION events (extinct fund)")
        
        if not event.ratio:
            raise ValueError("ratio is required for FUND_CONVERSION events (e.g., '3:2' = 3 new for 2 old)")
        
        old_ticker = event.previous_ticker.upper()
        new_ticker = event.ticker.upper()
        
        # Parse ratio (e.g., "3:2" means 3 new shares for every 2 old shares)
        ratio_parts = event.ratio.split(':')
        if len(ratio_parts) != 2:
            raise ValueError(f"Invalid ratio format: {event.ratio}. Expected format: 'X:Y' (e.g., '3:2')")
        
        new_shares_numerator = Decimal(ratio_parts[0])
        old_shares_denominator = Decimal(ratio_parts[1])
        conversion_factor = new_shares_numerator / old_shares_denominator
        
        # Find all positions with the old ticker (extinct fund)
        old_positions = PortfolioPosition.objects.filter(ticker=old_ticker)
        if user_id:
            old_positions = old_positions.filter(user_id=user_id)
        
        positions_updated = 0
        positions_created = 0
        
        for old_pos in old_positions:
            if old_pos.quantidade <= 0:
                continue  # Skip zero-quantity positions
            
            # Calculate new quantity: old_quantity * (new_shares / old_shares)
            # Example: 198 old * (3/2) = 297, then we need to check if we should round
            # For FIIs, typically quantities are whole numbers, so we should round
            new_quantity_float = float(old_pos.quantidade) * float(conversion_factor)
            new_quantity = int(round(new_quantity_float))
            
            # Calculate new price: maintain the same total invested value
            # New price = (old_price * old_quantity) / new_quantity
            old_total_invested = float(old_pos.valor_total_investido)
            if new_quantity > 0:
                new_price = Decimal(str(old_total_invested / new_quantity))
            else:
                new_price = Decimal('0.00')
            
            # Check if a position with the new ticker already exists for this user
            try:
                new_pos = PortfolioPosition.objects.get(user_id=old_pos.user_id, ticker=new_ticker)
                # Consolidate positions: add quantities and recalculate weighted average
                total_old_quantity = new_pos.quantidade
                total_old_invested = float(new_pos.valor_total_investido)
                
                # Add converted position
                total_new_quantity = total_old_quantity + new_quantity
                total_new_invested = total_old_invested + old_total_invested
                
                if total_new_quantity > 0:
                    new_pos.preco_medio = Decimal(str(total_new_invested / total_new_quantity))
                else:
                    new_pos.preco_medio = Decimal('0.00')
                
                new_pos.quantidade = total_new_quantity
                new_pos.valor_total_investido = Decimal(str(total_new_invested))
                new_pos.lucro_realizado += old_pos.lucro_realizado  # Sum realized profit
                new_pos.save()
                positions_updated += 1
            except PortfolioPosition.DoesNotExist:
                # Create new position with converted values
                new_pos = PortfolioPosition.objects.create(
                    user_id=old_pos.user_id,
                    ticker=new_ticker,
                    quantidade=new_quantity,
                    preco_medio=new_price,
                    valor_total_investido=Decimal(str(old_total_invested)),
                    lucro_realizado=old_pos.lucro_realizado,
                )
                positions_created += 1
            
            # Delete the old position (extinct fund)
            old_pos.delete()
        
        # Update operations in brokerage notes (convert old ticker to new ticker)
        from brokerage_notes.models import BrokerageNote
        notes = BrokerageNote.objects.all()
        operations_updated = 0
        
        for note in notes:
            if user_id and note.user_id != user_id:
                continue  # Skip notes from other users if filtering
            
            operations = note.operations or []
            modified = False
            
            for operation in operations:
                if operation.get('titulo', '').upper() == old_ticker:
                    operation['titulo'] = new_ticker
                    modified = True
                    operations_updated += 1
            
            if modified:
                note.operations = operations
                note.save()
        
        return {
            'success': True,
            'message': f'Fund conversion applied: {old_ticker} (extinct) -> {new_ticker} (ratio {event.ratio})',
            'positions_created': positions_created,
            'positions_updated': positions_updated,
            'operations_updated': operations_updated,
            'old_ticker': old_ticker,
            'new_ticker': new_ticker,
            'conversion_ratio': event.ratio,
        }
    
    @staticmethod
    def refresh_portfolio_from_brokerage_notes() -> None:
        """
        Rebuild entire portfolio from all brokerage notes.
        This function processes all operations from brokerage notes chronologically
        and rebuilds the complete portfolio summary, applying corporate events when appropriate.
        """
        from datetime import datetime
        
        # Load all brokerage notes
        notes = BrokerageNoteHistoryService.load_history()
        
        if not notes:
            # No notes, create empty portfolio
            PortfolioService.save_portfolio({})
            return
        
        # Load all corporate events
        corporate_events = CorporateEvent.objects.filter(applied=True).order_by('ex_date')
        events_by_ticker = {}
        for event in corporate_events:
            ticker_key = event.ticker.upper()  # Use uppercase for consistency
            if ticker_key not in events_by_ticker:
                events_by_ticker[ticker_key] = []
            events_by_ticker[ticker_key].append(event)
        
        # Extract all operations from all notes
        all_operations = []
        for note in notes:
            user_id = note.get('user_id')
            note_date = note.get('note_date', '')
            operations = note.get('operations', [])
            
            for operation in operations:
                # Always use the note's user_id as the source of truth
                # This ensures operations are grouped correctly even if they have incorrect clientId
                if user_id:
                    operation['clientId'] = user_id
                # Ensure operation has note_date for sorting
                if 'data' not in operation and note_date:
                    operation['data'] = note_date
                
                all_operations.append(operation)
        
        # Sort operations chronologically: by date, then by ordem
        all_operations.sort(key=lambda op: (
            PortfolioService.parse_date(op.get('data', '')),
            op.get('ordem', 0)
        ))
        
        # Group operations by user_id (now always from note's user_id)
        operations_by_user = {}
        for operation in all_operations:
            user_id = operation.get('clientId') or operation.get('user_id')
            if not user_id:
                continue
            
            if user_id not in operations_by_user:
                operations_by_user[user_id] = []
            operations_by_user[user_id].append(operation)
        
        # Process each user's operations
        portfolio = {}
        for user_id, user_operations in operations_by_user.items():
            # Process operations with corporate events
            ticker_summaries = PortfolioService.process_operations_with_corporate_events(
                user_operations, events_by_ticker
            )
            
            # Convert to list format sorted by ticker
            ticker_list = [
                {
                    'titulo': ticker,
                    'quantidade': summary['quantidade'],
                    'precoMedio': round(summary['precoMedio'], 2),
                    'valorTotalInvestido': round(summary['valorTotalInvestido'], 2),
                    'lucroRealizado': round(summary['lucroRealizado'], 2)
                }
                for ticker, summary in sorted(ticker_summaries.items())
            ]
            
            portfolio[user_id] = ticker_list
        
        # Save portfolio to database
        PortfolioService.save_portfolio(portfolio)
        print(f"Portfolio refreshed: {len(portfolio)} users, {sum(len(tickers) for tickers in portfolio.values())} total ticker positions")
    
    @staticmethod
    @transaction.atomic
    def apply_corporate_event(event: CorporateEvent, user_id: Optional[str] = None) -> Dict:
        """
        Apply a corporate event adjustment to portfolio positions.
        
        For grouping (reverse split) events:
        - Quantity: divide by ratio denominator (e.g., 20:1 -> divide by 20)
        - Average price: multiply by ratio denominator (to maintain total invested value)
        - Total invested: remains constant
        
        For split events:
        - Quantity: multiply by ratio numerator (e.g., 1:5 -> multiply by 5)
        - Average price: divide by ratio numerator
        - Total invested: remains constant
        
        Args:
            event: CorporateEvent instance
            user_id: Optional user ID to apply only to that user. If None, applies to all users with the ticker.
        
        Returns:
            Dict with statistics about the adjustment
        """
        try:
            numerator, denominator = event.parse_ratio()
        except ValueError as e:
            raise ValueError(f"Invalid ratio format for event {event.id}: {e}")
        
        # Query positions to adjust
        query = PortfolioPosition.objects.filter(ticker=event.ticker.upper())
        if user_id:
            query = query.filter(user_id=user_id)
        
        positions_to_adjust = list(query)
        
        if not positions_to_adjust:
            return {
                'success': True,
                'message': f'No positions found for ticker {event.ticker}',
                'positions_adjusted': 0
            }
        
        adjusted_count = 0
        
        # Apply adjustment based on event type
        for position in positions_to_adjust:
            if position.quantidade <= 0:
                # Skip positions with zero or negative quantity
                continue
            
            old_quantity = position.quantidade
            old_price = Decimal(str(position.preco_medio))
            old_total = Decimal(str(position.valor_total_investido))
            
            if event.event_type == 'GROUPING':
                # Reverse split (grupamento): 20:1 means 20 old shares become 1 new share
                # Quantity decreases, price increases
                new_quantity = int(old_quantity / denominator)
                if new_quantity < 1:
                    new_quantity = 0
                    new_price = Decimal('0.00')
                    new_total = Decimal('0.00')
                else:
                    new_price = old_price * Decimal(str(denominator))
                    new_total = Decimal(str(new_quantity)) * new_price
                
            elif event.event_type == 'SPLIT':
                # Split (desdobramento): 1:5 means 1 old share becomes 5 new shares
                # Quantity increases, price decreases
                new_quantity = int(old_quantity * numerator)
                new_price = old_price / Decimal(str(numerator))
                new_total = Decimal(str(new_quantity)) * new_price
                
            elif event.event_type == 'BONUS':
                # Bonus: increases quantity
                # If bonus share value is specified in description (e.g., "R$ 5"), add it to total invested
                # Otherwise, maintain total invested constant (bonus shares have zero cost basis)
                bonus_share_value = None
                if event.description:
                    # Try to extract bonus share value from description (e.g., "R$ 5", "R$5.00", "valor R$ 5")
                    match = re.search(r'R\$\s*(\d+(?:[.,]\d+)?)', event.description, re.IGNORECASE)
                    if match:
                        try:
                            bonus_share_value = Decimal(match.group(1).replace(',', '.'))
                        except (ValueError, AttributeError):
                            pass
                
                bonus_shares = int((old_quantity / denominator) * numerator)
                new_quantity = old_quantity + bonus_shares
                
                if bonus_share_value is not None:
                    # Add bonus share value to total invested
                    bonus_total_value = Decimal(str(bonus_shares)) * bonus_share_value
                    new_total = old_total + bonus_total_value
                else:
                    # Keep total invested constant (bonus shares have zero cost basis)
                    new_total = old_total
                
                new_price = new_total / Decimal(str(new_quantity)) if new_quantity > 0 else Decimal('0.00')
                
            else:
                # Unknown event type, skip
                continue
            
            # Update position
            position.quantidade = new_quantity
            position.preco_medio = float(new_price) if isinstance(new_price, Decimal) else new_price
            position.valor_total_investido = float(new_total) if isinstance(new_total, Decimal) else new_total
            position.save(update_fields=['quantidade', 'preco_medio', 'valor_total_investido'])
            
            adjusted_count += 1
        
        return {
            'success': True,
            'message': f'Applied {event.get_event_type_display()} adjustment to {adjusted_count} position(s)',
            'positions_adjusted': adjusted_count,
            'ticker': event.ticker,
            'event_type': event.event_type,
            'ratio': event.ratio
        }