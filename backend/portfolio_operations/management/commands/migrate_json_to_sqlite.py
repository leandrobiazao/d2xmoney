"""
Django management command to migrate data from JSON files to SQLite database.
This command loads data from all JSON files and inserts them into the database.
"""
import json
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from users.models import User
from brokerage_notes.models import BrokerageNote, Operation
from portfolio_operations.models import PortfolioPosition
from ticker_mappings.models import TickerMapping
from clubedovalor.models import StockSnapshot, Stock


class Command(BaseCommand):
    help = 'Migrate data from JSON files to SQLite database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create backup of JSON files before migration',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting JSON to SQLite migration...')
        
        data_dir = Path(settings.DATA_DIR)
        
        # Create backup if requested
        if options['backup']:
            self.create_backup(data_dir)
        
        # Migrate each service
        self.migrate_users(data_dir)
        self.migrate_ticker_mappings(data_dir)
        self.migrate_brokerage_notes(data_dir)
        self.migrate_portfolio(data_dir)
        self.migrate_clubedovalor(data_dir)
        
        self.stdout.write(
            self.style.SUCCESS('\nMigration completed successfully!')
        )

    def create_backup(self, data_dir):
        """Create backup of JSON files."""
        self.stdout.write('Creating backup of JSON files...')
        backup_dir = data_dir / 'backup'
        backup_dir.mkdir(exist_ok=True)
        
        json_files = ['users.json', 'brokerage_notes.json', 'portfolio.json', 
                     'ticker.json', 'ambb.json']
        
        for json_file in json_files:
            source = data_dir / json_file
            if source.exists():
                import shutil
                backup_path = backup_dir / f"{json_file}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(source, backup_path)
                self.stdout.write(f'  Backed up {json_file}')
        
        self.stdout.write(self.style.SUCCESS('Backup created'))

    def migrate_users(self, data_dir):
        """Migrate users from users.json."""
        self.stdout.write('\nMigrating users...')
        users_file = data_dir / 'users.json'
        
        if not users_file.exists():
            self.stdout.write(self.style.WARNING('  users.json not found, skipping'))
            return
        
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            count = 0
            for user_data in users_data:
                user, created = User.objects.update_or_create(
                    id=user_data['id'],
                    defaults={
                        'name': user_data.get('name', ''),
                        'cpf': user_data.get('cpf', ''),
                        'account_provider': user_data.get('account_provider', ''),
                        'account_number': user_data.get('account_number', ''),
                        'picture': user_data.get('picture'),
                        'created_at': self.parse_datetime(user_data.get('created_at')),
                        'updated_at': self.parse_datetime(user_data.get('updated_at')),
                    }
                )
                if created:
                    count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'  Migrated {len(users_data)} users ({count} new)')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  Error migrating users: {e}')
            )
            raise

    def migrate_ticker_mappings(self, data_dir):
        """Migrate ticker mappings from ticker.json."""
        self.stdout.write('\nMigrating ticker mappings...')
        ticker_file = data_dir / 'ticker.json'
        
        if not ticker_file.exists():
            self.stdout.write(self.style.WARNING('  ticker.json not found, skipping'))
            return
        
        try:
            with open(ticker_file, 'r', encoding='utf-8') as f:
                mappings_data = json.load(f)
            
            count = 0
            for company_name, ticker in mappings_data.items():
                mapping, created = TickerMapping.objects.update_or_create(
                    company_name=company_name,
                    defaults={'ticker': ticker}
                )
                if created:
                    count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'  Migrated {len(mappings_data)} mappings ({count} new)')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  Error migrating ticker mappings: {e}')
            )
            raise

    def migrate_brokerage_notes(self, data_dir):
        """Migrate brokerage notes from brokerage_notes.json."""
        self.stdout.write('\nMigrating brokerage notes...')
        notes_file = data_dir / 'brokerage_notes.json'
        
        if not notes_file.exists():
            self.stdout.write(self.style.WARNING('  brokerage_notes.json not found, skipping'))
            return
        
        try:
            with open(notes_file, 'r', encoding='utf-8') as f:
                notes_data = json.load(f)
            
            notes_count = 0
            operations_count = 0
            
            for note_data in notes_data:
                # Parse processed_at if it exists
                processed_at = None
                if note_data.get('processed_at'):
                    processed_at = self.parse_datetime(note_data['processed_at'])
                
                # Create or update brokerage note
                note, created = BrokerageNote.objects.update_or_create(
                    id=note_data['id'],
                    defaults={
                        'user_id': note_data.get('user_id', ''),
                        'file_name': note_data.get('file_name', ''),
                        'original_file_path': note_data.get('original_file_path'),
                        'note_date': note_data.get('note_date', ''),
                        'note_number': note_data.get('note_number', ''),
                        'processed_at': processed_at,
                        'operations_count': note_data.get('operations_count', 0),
                        'operations': note_data.get('operations', []),
                    }
                )
                if created:
                    notes_count += 1
                
                # Migrate operations
                operations = note_data.get('operations', [])
                for op_data in operations:
                    op, created = Operation.objects.update_or_create(
                        id=op_data.get('id', f"op-{note.id}-{operations_count}"),
                        defaults={
                            'note': note,
                            'tipo_operacao': op_data.get('tipoOperacao', ''),
                            'tipo_mercado': op_data.get('tipoMercado'),
                            'ordem': op_data.get('ordem', 0),
                            'titulo': op_data.get('titulo', ''),
                            'qtd_total': op_data.get('qtdTotal'),
                            'preco_medio': self.parse_decimal(op_data.get('precoMedio')),
                            'quantidade': op_data.get('quantidade', 0),
                            'preco': self.parse_decimal(op_data.get('preco', 0)),
                            'valor_operacao': self.parse_decimal(op_data.get('valorOperacao', 0)),
                            'dc': op_data.get('dc'),
                            'nota_tipo': op_data.get('notaTipo'),
                            'corretora': op_data.get('corretora'),
                            'nota_number': op_data.get('nota'),
                            'data': op_data.get('data', ''),
                            'client_id': op_data.get('clientId'),
                            'extra_data': {k: v for k, v in op_data.items() 
                                         if k not in ['id', 'tipoOperacao', 'tipoMercado', 'ordem',
                                                     'titulo', 'qtdTotal', 'precoMedio', 'quantidade',
                                                     'preco', 'valorOperacao', 'dc', 'notaTipo',
                                                     'corretora', 'nota', 'data', 'clientId']},
                        }
                    )
                    if created:
                        operations_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Migrated {len(notes_data)} notes ({notes_count} new), '
                    f'{operations_count} operations'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  Error migrating brokerage notes: {e}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
            raise

    def migrate_portfolio(self, data_dir):
        """Migrate portfolio from portfolio.json."""
        self.stdout.write('\nMigrating portfolio...')
        portfolio_file = data_dir / 'portfolio.json'
        
        if not portfolio_file.exists():
            self.stdout.write(self.style.WARNING('  portfolio.json not found, skipping'))
            return
        
        try:
            with open(portfolio_file, 'r', encoding='utf-8') as f:
                portfolio_data = json.load(f)
            
            positions_count = 0
            
            for user_id, ticker_summaries in portfolio_data.items():
                for summary in ticker_summaries:
                    position, created = PortfolioPosition.objects.update_or_create(
                        user_id=user_id,
                        ticker=summary.get('titulo', ''),
                        defaults={
                            'quantidade': summary.get('quantidade', 0),
                            'preco_medio': self.parse_decimal(summary.get('precoMedio', 0)),
                            'valor_total_investido': self.parse_decimal(summary.get('valorTotalInvestido', 0)),
                            'lucro_realizado': self.parse_decimal(summary.get('lucroRealizado', 0)),
                        }
                    )
                    if created:
                        positions_count += 1
            
            total_positions = sum(len(tickers) for tickers in portfolio_data.values())
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Migrated {total_positions} positions ({positions_count} new) '
                    f'for {len(portfolio_data)} users'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  Error migrating portfolio: {e}')
            )
            raise

    def migrate_clubedovalor(self, data_dir):
        """Migrate Clube do Valor data from ambb.json."""
        self.stdout.write('\nMigrating Clube do Valor data...')
        ambb_file = data_dir / 'ambb.json'
        
        if not ambb_file.exists():
            self.stdout.write(self.style.WARNING('  ambb.json not found, skipping'))
            return
        
        try:
            with open(ambb_file, 'r', encoding='utf-8') as f:
                ambb_data = json.load(f)
            
            # Migrate historical snapshots first
            snapshots_count = 0
            stocks_count = 0
            
            snapshots = ambb_data.get('snapshots', [])
            for snapshot_data in snapshots:
                # Use timestamp + is_current=False to uniquely identify historical snapshots
                snapshot, created = StockSnapshot.objects.update_or_create(
                    timestamp=snapshot_data.get('timestamp', ''),
                    is_current=False,
                    defaults={}
                )
                if created:
                    snapshots_count += 1
                
                # Migrate stocks for this snapshot
                stocks_data = snapshot_data.get('data', [])
                for stock_data in stocks_data:
                    stock, created = Stock.objects.update_or_create(
                        snapshot=snapshot,
                        codigo=stock_data.get('codigo', ''),
                        defaults={
                            'ranking': stock_data.get('ranking', 0),
                            'earning_yield': self.parse_decimal(stock_data.get('earningYield', 0)),
                            'nome': stock_data.get('nome', ''),
                            'setor': stock_data.get('setor', ''),
                            'ev': self.parse_decimal(stock_data.get('ev', 0)),
                            'ebit': self.parse_decimal(stock_data.get('ebit', 0)),
                            'liquidez': self.parse_decimal(stock_data.get('liquidez', 0)),
                            'cotacao_atual': self.parse_decimal(stock_data.get('cotacaoAtual', 0)),
                            'observacao': stock_data.get('observacao', ''),
                        }
                    )
                    if created:
                        stocks_count += 1
            
            # Migrate current snapshot (after historical to avoid conflicts)
            current_data = ambb_data.get('current', {})
            if current_data.get('timestamp'):
                # Mark all existing snapshots as not current
                StockSnapshot.objects.filter(is_current=True).update(is_current=False)
                
                # Use timestamp + is_current=True to uniquely identify current snapshot
                # This ensures we don't update a historical snapshot with the same timestamp
                snapshot, created = StockSnapshot.objects.update_or_create(
                    timestamp=current_data.get('timestamp', ''),
                    is_current=True,
                    defaults={}
                )
                if created:
                    snapshots_count += 1
                
                # Migrate current stocks
                stocks_data = current_data.get('data', [])
                for stock_data in stocks_data:
                    stock, created = Stock.objects.update_or_create(
                        snapshot=snapshot,
                        codigo=stock_data.get('codigo', ''),
                        defaults={
                            'ranking': stock_data.get('ranking', 0),
                            'earning_yield': self.parse_decimal(stock_data.get('earningYield', 0)),
                            'nome': stock_data.get('nome', ''),
                            'setor': stock_data.get('setor', ''),
                            'ev': self.parse_decimal(stock_data.get('ev', 0)),
                            'ebit': self.parse_decimal(stock_data.get('ebit', 0)),
                            'liquidez': self.parse_decimal(stock_data.get('liquidez', 0)),
                            'cotacao_atual': self.parse_decimal(stock_data.get('cotacaoAtual', 0)),
                            'observacao': stock_data.get('observacao', ''),
                        }
                    )
                    if created:
                        stocks_count += 1
            
            total_snapshots = len(snapshots) + (1 if current_data.get('timestamp') else 0)
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Migrated {total_snapshots} snapshots ({snapshots_count} new), '
                    f'{stocks_count} stocks'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  Error migrating Clube do Valor data: {e}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
            raise

    def parse_datetime(self, dt_str):
        """Parse datetime string to datetime object."""
        if not dt_str:
            return None
        try:
            if isinstance(dt_str, str):
                # Try ISO format first
                if 'T' in dt_str:
                    # Remove 'Z' and microseconds if present
                    dt_str_clean = dt_str.replace('Z', '').split('.')[0]
                    # Try parsing with different formats
                    for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                        try:
                            return datetime.strptime(dt_str_clean, fmt)
                        except ValueError:
                            continue
            return None
        except Exception:
            return None

    def parse_decimal(self, value):
        """Parse value to Decimal-compatible format."""
        if value is None:
            return 0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0

