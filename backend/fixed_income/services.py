"""
Services for fixed income portfolio import and management.
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple
import openpyxl
from django.utils import timezone
from .models import FixedIncomePosition, TesouroDiretoPosition
from configuration.models import InvestmentType, InvestmentSubType


class PortfolioExcelImportService:
    """Service for importing portfolio positions from Excel files."""
    
    @staticmethod
    def parse_currency(value: str) -> Decimal:
        """Parse Brazilian currency format (R$ X.XXX,XX) to Decimal."""
        if not value or value == '-':
            return Decimal('0.00')
        
        # Remove R$ and spaces
        value = str(value).replace('R$', '').strip()
        
        # Handle comma as decimal separator
        if ',' in value:
            # Replace dots (thousands) and comma (decimal)
            value = value.replace('.', '').replace(',', '.')
        else:
            # No comma, assume it's already in standard format
            pass
        
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return Decimal('0.00')
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """Parse date string in DD/MM/YYYY format."""
        if not date_str or date_str == '-':
            return None
        
        try:
            # Handle Excel date format or string format
            if isinstance(date_str, datetime):
                return date_str
            elif isinstance(date_str, str):
                # Try DD/MM/YYYY format
                parts = date_str.split('/')
                if len(parts) == 3:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    return datetime(year, month, day)
        except (ValueError, AttributeError):
            pass
        
        return None
    
    @staticmethod
    def parse_percentage(value: str) -> Optional[str]:
        """Parse percentage value (e.g., '+9,00%')."""
        if not value or value == '-':
            return None
        return str(value).strip()
    
    @staticmethod
    def parse_quantity(value: str) -> Decimal:
        """Parse quantity value."""
        if not value or value == '-':
            return Decimal('0.00')
        
        # Handle comma as decimal separator
        value = str(value).replace(',', '.')
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return Decimal('0.00')
    
    @staticmethod
    def detect_section(row: List) -> Optional[str]:
        """Detect which section a row belongs to (Ações, Renda Fixa, Tesouro Direto)."""
        if not row or len(row) == 0:
            return None
        
        first_cell = str(row[0]).upper() if row[0] else ''
        
        if 'AÇÕES' in first_cell or '%|AÇÕES' in first_cell:
            return 'acoes'
        elif 'RENDA FIXA' in first_cell or '%|RENDA FIXA' in first_cell:
            return 'renda_fixa'
        elif 'TESOURO' in first_cell or 'TESOURO DIRETO' in first_cell or '%|TESOURO' in first_cell:
            return 'tesouro_direto'
        
        return None
    
    @staticmethod
    def is_header_row(row: List) -> bool:
        """Check if a row is a header row."""
        if not row:
            return False
        
        header_keywords = ['ATIVO', 'QTD', 'PREÇO', 'POSIÇÃO', 'APLICAÇÃO', 'VENCIMENTO']
        first_cell = str(row[0]).upper() if row[0] else ''
        
        return any(keyword in first_cell for keyword in header_keywords)
    
    @staticmethod
    def extract_cdb_from_row(row: List, user_id: str, current_section: str) -> Optional[Dict]:
        """Extract CDB data from a row."""
        if not row or len(row) < 3:
            return None
        
        asset_name = str(row[0]).strip() if row[0] else ''
        
        # Check if it's a CDB
        if 'CDB' not in asset_name.upper():
            return None
        
        # CDB rows in Excel format:
        # [Asset Name, Application Date, Grace Period End, Maturity Date, Rate, Quantity, Guarantee, Applied Value, Position Value, Net Value, ...]
        
        try:
            application_date = PortfolioExcelImportService.parse_date(row[1])
            grace_period_end = PortfolioExcelImportService.parse_date(row[2]) if len(row) > 2 else None
            maturity_date = PortfolioExcelImportService.parse_date(row[3]) if len(row) > 3 else None
            
            # If maturity_date is None, try to extract from asset_name (e.g., "CDB BANCO MASTER S/A - DEZ/2026")
            if not maturity_date:
                maturity_date = PortfolioExcelImportService._extract_date_from_name(asset_name)
            
            rate = PortfolioExcelImportService.parse_percentage(row[4]) if len(row) > 4 else None
            quantity = PortfolioExcelImportService.parse_quantity(row[5]) if len(row) > 5 else Decimal('0.00')
            guarantee_quantity = PortfolioExcelImportService.parse_quantity(row[6]) if len(row) > 6 else Decimal('0.00')
            applied_value = PortfolioExcelImportService.parse_currency(row[7]) if len(row) > 7 else Decimal('0.00')
            position_value = PortfolioExcelImportService.parse_currency(row[8]) if len(row) > 8 else Decimal('0.00')
            net_value = PortfolioExcelImportService.parse_currency(row[9]) if len(row) > 9 else Decimal('0.00')
            
            # Extract asset code from asset_name or generate one
            asset_code = PortfolioExcelImportService._extract_asset_code(asset_name)
            
            # Calculate yields
            gross_yield = position_value - applied_value if position_value and applied_value else Decimal('0.00')
            net_yield = net_value - applied_value if net_value and applied_value else Decimal('0.00')
            income_tax = gross_yield - net_yield if gross_yield and net_yield else Decimal('0.00')
            
            if not application_date:
                return None
            
            return {
                'user_id': user_id,
                'asset_name': asset_name,
                'asset_code': asset_code,
                'application_date': application_date.date() if isinstance(application_date, datetime) else application_date,
                'grace_period_end': grace_period_end.date() if grace_period_end and isinstance(grace_period_end, datetime) else grace_period_end,
                'maturity_date': maturity_date.date() if maturity_date and isinstance(maturity_date, datetime) else maturity_date,
                'rate': rate,
                'quantity': quantity,
                'available_quantity': quantity,  # Assume same as quantity initially
                'guarantee_quantity': guarantee_quantity,
                'applied_value': applied_value,
                'position_value': position_value,
                'net_value': net_value,
                'gross_yield': gross_yield,
                'net_yield': net_yield,
                'income_tax': income_tax,
                'iof': Decimal('0.00'),  # Default, can be updated later
                'source': 'Excel Import',
                'import_date': timezone.now(),
            }
        except Exception as e:
            print(f"Error extracting CDB from row: {e}")
            return None
    
    @staticmethod
    def _extract_date_from_name(asset_name: str) -> Optional[datetime]:
        """Extract date from asset name (e.g., 'CDB BANCO MASTER S/A - DEZ/2026')."""
        # Look for month/year pattern (e.g., DEZ/2026, SET/2031)
        month_map = {
            'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
        }
        
        pattern = r'([A-Z]{3})/(\d{4})'
        match = re.search(pattern, asset_name.upper())
        
        if match:
            month_str, year_str = match.groups()
            if month_str in month_map:
                try:
                    return datetime(int(year_str), month_map[month_str], 1)
                except ValueError:
                    pass
        
        return None
    
    @staticmethod
    def _extract_asset_code(asset_name: str) -> str:
        """Extract or generate asset code from asset name."""
        # Try to find a code pattern in the name
        # For now, use a simplified version of the name as code
        # In real scenarios, this might come from a separate column
        code = asset_name.replace(' ', '_').upper()[:50]
        return code
    
    @staticmethod
    def extract_tesouro_from_row(row: List, user_id: str) -> Optional[Dict]:
        """Extract Tesouro Direto data from a row."""
        if not row or len(row) < 3:
            return None
        
        titulo_name = str(row[0]).strip() if row[0] else ''
        
        # Check if it's Tesouro Direto
        if 'TESOURO' not in titulo_name.upper():
            return None
        
        try:
            # Tesouro format might vary, but typically has título name and vencimento
            application_date = PortfolioExcelImportService.parse_date(row[1]) if len(row) > 1 else None
            vencimento = PortfolioExcelImportService.parse_date(row[2]) if len(row) > 2 else None
            
            if not vencimento:
                # Try to extract from título name
                vencimento = PortfolioExcelImportService._extract_date_from_name(titulo_name)
            
            if not vencimento:
                return None
            
            # Extract other fields similar to CDB
            quantity = PortfolioExcelImportService.parse_quantity(row[5]) if len(row) > 5 else Decimal('0.00')
            applied_value = PortfolioExcelImportService.parse_currency(row[7]) if len(row) > 7 else Decimal('0.00')
            position_value = PortfolioExcelImportService.parse_currency(row[8]) if len(row) > 8 else Decimal('0.00')
            net_value = PortfolioExcelImportService.parse_currency(row[9]) if len(row) > 9 else Decimal('0.00')
            
            asset_code = f"TESOURO_{titulo_name.replace(' ', '_').upper()[:30]}"
            
            return {
                'user_id': user_id,
                'asset_name': titulo_name,
                'asset_code': asset_code,
                'application_date': application_date.date() if application_date and isinstance(application_date, datetime) else (timezone.now().date() if not application_date else None),
                'maturity_date': vencimento.date() if isinstance(vencimento, datetime) else vencimento,
                'quantity': quantity,
                'available_quantity': quantity,
                'applied_value': applied_value,
                'position_value': position_value,
                'net_value': net_value,
                'gross_yield': position_value - applied_value if position_value and applied_value else Decimal('0.00'),
                'net_yield': net_value - applied_value if net_value and applied_value else Decimal('0.00'),
                'source': 'Excel Import',
                'import_date': timezone.now(),
                'titulo_name': titulo_name,
                'vencimento': vencimento.date() if isinstance(vencimento, datetime) else vencimento,
            }
        except Exception as e:
            print(f"Error extracting Tesouro from row: {e}")
            return None
    
    @staticmethod
    def import_from_excel(file_path: str, user_id: str) -> Dict:
        """Import portfolio positions from Excel file."""
        results = {
            'created': 0,
            'updated': 0,
            'errors': [],
            'cdb_count': 0,
            'tesouro_count': 0,
            'debug_info': [],
        }
        
        try:
            workbook = openpyxl.load_workbook(file_path)
            worksheet = workbook.active
            
            results['debug_info'].append(f"Worksheet: {worksheet.title}, Rows: {worksheet.max_row}, Cols: {worksheet.max_column}")
            
            current_section = None
            
            # Get or create Renda Fixa investment type
            renda_fixa_type, _ = InvestmentType.objects.get_or_create(
                code='RENDA_FIXA',
                defaults={'name': 'Renda Fixa', 'display_order': 2}
            )
            
            # Get or create Tesouro Direto investment type
            tesouro_type, _ = InvestmentType.objects.get_or_create(
                code='TESOURO_DIRETO',
                defaults={'name': 'Tesouro Direto', 'display_order': 3}
            )
            
            rows_processed = 0
            sections_found = []
            
            for row_idx, row in enumerate(worksheet.iter_rows(values_only=True), 1):
                # Skip empty rows
                if not row or all(cell is None for cell in row):
                    continue
                
                rows_processed += 1
                
                # Detect section
                section = PortfolioExcelImportService.detect_section(row)
                if section:
                    current_section = section
                    sections_found.append(section)
                    results['debug_info'].append(f"Row {row_idx}: Found section '{section}' - {str(row[0])[:100]}")
                    continue
                
                # Skip header rows
                if PortfolioExcelImportService.is_header_row(row):
                    results['debug_info'].append(f"Row {row_idx}: Skipped header row")
                    continue
                
                # Process CDB entries
                if current_section == 'renda_fixa':
                    cdb_data = PortfolioExcelImportService.extract_cdb_from_row(row, user_id, current_section)
                    if cdb_data:
                        try:
                            position, created = FixedIncomePosition.objects.update_or_create(
                                user_id=cdb_data['user_id'],
                                asset_code=cdb_data['asset_code'],
                                application_date=cdb_data['application_date'],
                                defaults={
                                    **cdb_data,
                                    'investment_type': renda_fixa_type,
                                }
                            )
                            
                            if created:
                                results['created'] += 1
                            else:
                                results['updated'] += 1
                            results['cdb_count'] += 1
                        except Exception as e:
                            results['errors'].append(f"Row {row_idx}: {str(e)}")
                    else:
                        # Log why CDB extraction failed
                        if row[0]:
                            asset_name = str(row[0]).strip()
                            if asset_name and 'CDB' not in asset_name.upper():
                                results['debug_info'].append(f"Row {row_idx}: Skipped (not a CDB): {asset_name[:50]}")
                
                # Process Tesouro Direto entries
                elif current_section == 'tesouro_direto':
                    tesouro_data = PortfolioExcelImportService.extract_tesouro_from_row(row, user_id)
                    if tesouro_data:
                        try:
                            titulo_name = tesouro_data.pop('titulo_name')
                            vencimento = tesouro_data.pop('vencimento')
                            
                            position, created = FixedIncomePosition.objects.update_or_create(
                                user_id=tesouro_data['user_id'],
                                asset_code=tesouro_data['asset_code'],
                                application_date=tesouro_data['application_date'],
                                defaults={
                                    **tesouro_data,
                                    'investment_type': tesouro_type,
                                }
                            )
                            
                            # Create or update TesouroDiretoPosition
                            tesouro_pos, _ = TesouroDiretoPosition.objects.update_or_create(
                                fixed_income_position=position,
                                defaults={
                                    'titulo_name': titulo_name,
                                    'vencimento': vencimento,
                                }
                            )
                            
                            if created:
                                results['created'] += 1
                            else:
                                results['updated'] += 1
                            results['tesouro_count'] += 1
                        except Exception as e:
                            results['errors'].append(f"Row {row_idx}: {str(e)}")
                    else:
                        # Log why Tesouro extraction failed
                        if row[0]:
                            titulo_name = str(row[0]).strip()
                            if titulo_name and 'TESOURO' not in titulo_name.upper():
                                results['debug_info'].append(f"Row {row_idx}: Skipped (not Tesouro): {titulo_name[:50]}")
                else:
                    # Log rows that don't match any section
                    if row[0] and current_section is None:
                        first_cell = str(row[0]).strip()[:50]
                        if first_cell:
                            results['debug_info'].append(f"Row {row_idx}: No section detected, first cell: {first_cell}")
            
            results['debug_info'].append(f"Total rows processed: {rows_processed}")
            results['debug_info'].append(f"Sections found: {', '.join(sections_found) if sections_found else 'None'}")
            
            if not sections_found:
                results['errors'].append("Nenhuma seção 'RENDA FIXA' ou 'TESOURO DIRETO' foi encontrada no arquivo. Verifique o formato do arquivo Excel.")
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            results['errors'].append(f"Import error: {str(e)}")
            results['error_details'] = error_details
        
        return results


