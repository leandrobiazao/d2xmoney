"""
Portfolio service for managing aggregated portfolio summaries.
This service manages portfolio summaries per user per ticker, including realized profit calculations using FIFO method.
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from .models import PortfolioPosition, CorporateEvent
from brokerage_notes.services import BrokerageNoteHistoryService


class PortfolioService:
    """Service for managing portfolio summaries using Django ORM."""
    
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
                new_value = current_value + valor_operacao
                
                # Update quantity and total invested value
                summary['quantidade'] = new_quantity
                summary['valorTotalInvestido'] = new_value
                
                # Recalculate weighted average price
                summary['precoMedio'] = new_value / new_quantity if new_quantity > 0 else 0.0
                
            elif tipo_operacao == 'V':  # Sale
                # Calculate realized profit using current average cost
                current_average_cost = summary['precoMedio']
                realized_profit = PortfolioService.calculate_average_cost_profit(
                    quantidade, preco, current_average_cost
                )
                
                # Update realized profit (cumulative)
                summary['lucroRealizado'] += realized_profit
                
                # Update quantity and total invested value
                current_quantity = summary['quantidade']
                new_quantity = current_quantity - quantidade
                if new_quantity < 0:
                    new_quantity = 0
                
                # Recalculate value invested (proportional reduction)
                if current_quantity > 0:
                    reduction_ratio = quantidade / current_quantity
                    summary['valorTotalInvestido'] *= (1 - reduction_ratio)
                    if summary['valorTotalInvestido'] < 0:
                        summary['valorTotalInvestido'] = 0.0
                else:
                    summary['valorTotalInvestido'] = 0.0
                
                summary['quantidade'] = new_quantity
                
                # Update average cost (should remain the same if using average cost method correctly)
                # But recalculate to ensure accuracy after rounding
                if new_quantity > 0 and summary['valorTotalInvestido'] > 0:
                    summary['precoMedio'] = summary['valorTotalInvestido'] / new_quantity
                else:
                    summary['precoMedio'] = 0.0
                
                print(f"  [VENDA] {ticker} {operation_date_str}: -{quantidade} -> Total: {new_quantity}")
        
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
                realized_profit, updated_queue = PortfolioService.calculate_fifo_profit(
                    quantidade, preco, summary['purchase_queue']
                )
                
                # Update realized profit
                summary['lucroRealizado'] += realized_profit
                
                # Update purchase queue
                summary['purchase_queue'] = updated_queue
                
                # Update quantity
                summary['quantidade'] -= quantidade
                if summary['quantidade'] < 0:
                    summary['quantidade'] = 0
                
                # Recalculate weighted average price from remaining purchases
                if len(summary['purchase_queue']) > 0:
                    total_value = sum(p['quantidade'] * p['preco'] for p in summary['purchase_queue'])
                    total_quantity = sum(p['quantidade'] for p in summary['purchase_queue'])
                    summary['precoMedio'] = total_value / total_quantity if total_quantity > 0 else 0.0
                    summary['valorTotalInvestido'] = total_value
                else:
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
                new_value = current_value + valor_operacao
                
                # Update quantity and total invested value
                summary['quantidade'] = new_quantity
                summary['valorTotalInvestido'] = new_value
                
                # Recalculate weighted average price
                summary['precoMedio'] = new_value / new_quantity if new_quantity > 0 else 0.0
                
            elif tipo_operacao == 'V':  # Sale
                # Calculate realized profit using current average cost
                current_average_cost = summary['precoMedio']
                realized_profit = PortfolioService.calculate_average_cost_profit(
                    quantidade, preco, current_average_cost
                )
                
                # Update realized profit (cumulative)
                summary['lucroRealizado'] += realized_profit
                
                # Update quantity and total invested value
                current_quantity = summary['quantidade']
                new_quantity = current_quantity - quantidade
                if new_quantity < 0:
                    new_quantity = 0
                
                # Recalculate value invested (proportional reduction)
                if current_quantity > 0:
                    reduction_ratio = quantidade / current_quantity
                    summary['valorTotalInvestido'] *= (1 - reduction_ratio)
                    if summary['valorTotalInvestido'] < 0:
                        summary['valorTotalInvestido'] = 0.0
                else:
                    summary['valorTotalInvestido'] = 0.0
                
                summary['quantidade'] = new_quantity
                
                # Update average cost (should remain the same if using average cost method correctly)
                if new_quantity > 0:
                    summary['precoMedio'] = summary['valorTotalInvestido'] / new_quantity
                else:
                    summary['precoMedio'] = 0.0
        
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
            # Bonus: typically increases quantity, maintains total value
            bonus_shares = int((old_quantity / denominator) * numerator)
            new_quantity = old_quantity + bonus_shares
            new_total = old_total_decimal  # Keep total invested constant
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
                # Bonus: typically increases quantity, maintains total value
                # Ratio format: "X:Y" where X new shares are given for Y existing
                # Example: "1:10" means 1 bonus share for every 10 existing
                bonus_shares = int((old_quantity / denominator) * numerator)
                new_quantity = old_quantity + bonus_shares
                # Price adjusts to maintain total invested value
                new_total = old_total  # Keep total invested constant
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
