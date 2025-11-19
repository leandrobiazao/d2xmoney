"""
Portfolio service for managing aggregated portfolio summaries.
This service manages portfolio summaries per user per ticker, including realized profit calculations using FIFO method.
"""
from typing import List, Dict, Optional, Tuple
from .models import PortfolioPosition
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
    def refresh_portfolio_from_brokerage_notes() -> None:
        """
        Rebuild entire portfolio from all brokerage notes.
        This function processes all operations from brokerage notes chronologically
        and rebuilds the complete portfolio summary.
        """
        # Load all brokerage notes
        notes = BrokerageNoteHistoryService.load_history()
        
        if not notes:
            # No notes, create empty portfolio
            PortfolioService.save_portfolio({})
            return
        
        # Extract all operations from all notes
        all_operations = []
        for note in notes:
            user_id = note.get('user_id')
            note_date = note.get('note_date', '')
            operations = note.get('operations', [])
            
            for operation in operations:
                # Ensure operation has user_id (from note if not in operation)
                if 'clientId' not in operation and user_id:
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
        
        # Group operations by user_id
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
            # Process operations using Average Cost method
            ticker_summaries = PortfolioService.process_operations_average_cost(user_operations)
            
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
