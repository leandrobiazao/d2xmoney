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
        elif 'TESOURO' in first_cell or 'TESOURO DIRETO' in first_cell or '%|TESOURO' in first_cell or 'TESOURO DIRETO' in first_cell:
            return 'tesouro_direto'
        
        return None
    
    @staticmethod
    def detect_tesouro_subsection(row: List) -> Optional[Tuple[str, Decimal]]:
        """Detect Tesouro Direto sub-section header (e.g., '15,2% | Pós-Fixado').
        Returns tuple of (sub_type_name, allocation_percentage) or None."""
        if not row or len(row) == 0:
            return None
        
        first_cell = str(row[0]).strip() if row[0] else ''
        
        # Pattern: "{percentage}% | {sub-type}"
        # Examples: "15,2% | Pós-Fixado", "14,3% | Inflação", "4,6% | Prefixado"
        # Also handles: "15,20%|Pós-Fixada", "4,50%|Prefixada"
        pattern = r'([\d,]+)\s*%\s*\|\s*(.+)'
        match = re.search(pattern, first_cell, re.IGNORECASE)
        
        if match:
            percentage_str = match.group(1).replace(',', '.')
            sub_type_name = match.group(2).strip()
            
            # Normalize sub-type names (handle variations)
            sub_type_name_upper = sub_type_name.upper()
            if 'PÓS-FIXAD' in sub_type_name_upper or 'POS-FIXAD' in sub_type_name_upper:
                sub_type_name = 'Pós-Fixado'
            elif 'PREFIXAD' in sub_type_name_upper:
                sub_type_name = 'Prefixado'
            elif 'INFLA' in sub_type_name_upper:
                sub_type_name = 'Inflação'
            
            try:
                percentage = Decimal(percentage_str)
                return (sub_type_name, percentage)
            except (InvalidOperation, ValueError):
                pass
        
        return None
    
    @staticmethod
    def is_header_row(row: List) -> bool:
        """Check if a row is a header row."""
        if not row:
            return False
        
        header_keywords = ['ATIVO', 'QTD', 'PREÇO', 'POSIÇÃO', 'APLICAÇÃO', 'VENCIMENTO', 'ALOCAÇÃO', 'DISPONÍVEL', 'TOTAL APLICADO']
        first_cell = str(row[0]).upper() if row[0] else ''
        
        return any(keyword in first_cell for keyword in header_keywords)
    
    @staticmethod
    def get_tesouro_subtype_from_bond(titulo_name: str) -> Optional[str]:
        """Determine Tesouro Direto sub-type from bond title.
        Returns sub-type name: 'Pós-Fixado', 'Inflação', or 'Prefixado'."""
        titulo_upper = titulo_name.upper().strip()
        
        # LFT (Letra Financeira do Tesouro) → Pós-Fixado
        if 'LFT' in titulo_upper:
            return 'Pós-Fixado'
        # NTNB (Nota do Tesouro Nacional - B) → Inflação
        # Also handles "NTNB PRINC" format
        elif 'NTNB' in titulo_upper:
            return 'Inflação'
        # LTN (Letra do Tesouro Nacional) → Prefixado
        elif 'LTN' in titulo_upper:
            return 'Prefixado'
        # NTN-B (alternative notation) → Inflação
        elif 'NTN-B' in titulo_upper or 'NTN B' in titulo_upper:
            return 'Inflação'
        
        return None
    
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
    def extract_tesouro_from_row(row: List, user_id: str, sub_type_name: Optional[str] = None) -> Optional[Dict]:
        """Extract Tesouro Direto data from a row.
        Actual Excel format: [Título, Vencimento, Preço, Total, Disponível, Garantia, Posição]
        Column mapping:
        - Row[0]: Título name (e.g., "LTN", "LFT", "NTNB PRINC")
        - Row[1]: Vencimento (maturity_date) - "01/01/2027"
        - Row[2]: Preço (price) - "867,57"
        - Row[3]: Total (total quantity) - "R$ 10,00" (this is the quantity in currency format)
        - Row[4]: Disponível (available_quantity) - "R$ 1,63" (this is also in currency format)
        - Row[5]: Garantia (guarantee_quantity) - "R$ 0,00"
        - Row[6]: Posição (position_value) - "R$ 8.675,70"
        """
        if not row or len(row) < 2:
            return None
        
        titulo_name = str(row[0]).strip() if row[0] else ''
        
        # Check if it's a Tesouro Direto bond (LFT, NTNB, LTN, etc.)
        if not any(bond_type in titulo_name.upper() for bond_type in ['LFT', 'NTNB', 'LTN', 'NTN-B', 'NTN B', 'TESOURO']):
            return None
        
        try:
            # Parse columns according to actual Excel format
            vencimento = PortfolioExcelImportService.parse_date(row[1]) if len(row) > 1 else None
            price = PortfolioExcelImportService.parse_currency(row[2]) if len(row) > 2 else Decimal('0.00')
            
            # Row[3] is Total - quantity (may be stored as number or currency-formatted string)
            if len(row) > 3 and row[3] is not None:
                if isinstance(row[3], (int, float)):
                    quantity = Decimal(str(row[3]))
                else:
                    total_str = str(row[3]).strip().replace('R$', '').strip()
                    quantity = PortfolioExcelImportService.parse_quantity(total_str)
            else:
                quantity = Decimal('0.00')
            
            # Row[4] is Disponível - available quantity
            if len(row) > 4 and row[4] is not None:
                if isinstance(row[4], (int, float)):
                    available_quantity = Decimal(str(row[4]))
                else:
                    disponivel_str = str(row[4]).strip().replace('R$', '').strip()
                    available_quantity = PortfolioExcelImportService.parse_quantity(disponivel_str)
            else:
                available_quantity = quantity
            
            # Row[5] is Garantia - guarantee quantity
            if len(row) > 5 and row[5] is not None:
                if isinstance(row[5], (int, float)):
                    guarantee_quantity = Decimal(str(row[5]))
                else:
                    garantia_str = str(row[5]).strip().replace('R$', '').strip()
                    guarantee_quantity = PortfolioExcelImportService.parse_quantity(garantia_str)
            else:
                guarantee_quantity = Decimal('0.00')
            
            # Row[6] is Posição (position value)
            position_value = PortfolioExcelImportService.parse_currency(row[6]) if len(row) > 6 else Decimal('0.00')
            
            if not vencimento:
                return None
            
            # Determine sub-type if not provided
            if not sub_type_name:
                sub_type_name = PortfolioExcelImportService.get_tesouro_subtype_from_bond(titulo_name)
            
            # Build full asset name with maturity date
            # Format: "LTN jan/2027" or "LFT mar/2029"
            from datetime import date as date_class
            vencimento_date = vencimento.date() if isinstance(vencimento, datetime) else vencimento
            month_map_reverse = {
                1: 'jan', 2: 'fev', 3: 'mar', 4: 'abr', 5: 'mai', 6: 'jun',
                7: 'jul', 8: 'ago', 9: 'set', 10: 'out', 11: 'nov', 12: 'dez'
            }
            if isinstance(vencimento_date, (datetime, date_class)):
                if isinstance(vencimento_date, datetime):
                    month = vencimento_date.month
                    year = vencimento_date.year
                else:
                    month = vencimento_date.month
                    year = vencimento_date.year
                month_str = month_map_reverse.get(month, '')
                full_titulo_name = f"{titulo_name} {month_str}/{year}"
            else:
                full_titulo_name = titulo_name
            
            # Generate asset code from título name and maturity
            from datetime import date as date_class
            if isinstance(vencimento_date, (datetime, date_class)):
                if isinstance(vencimento_date, datetime):
                    date_str = vencimento_date.strftime('%Y%m%d')
                else:
                    date_str = vencimento_date.strftime('%Y%m%d')
                asset_code = f"TESOURO_{titulo_name.replace(' ', '_').upper()}_{date_str}"
            else:
                asset_code = f"TESOURO_{titulo_name.replace(' ', '_').upper()}_{str(vencimento_date).replace('-', '')}"
            
            # Calculate applied_value from price * quantity
            # For Tesouro Direto, applied_value is typically price * quantity
            applied_value = price * quantity if price and quantity else position_value  # Fallback to position_value if calculation fails
            
            # Calculate yields
            gross_yield = position_value - applied_value if position_value and applied_value else Decimal('0.00')
            net_yield = gross_yield  # For Tesouro Direto, net is typically same as gross (taxes applied at sale)
            net_value = position_value  # Net value is same as position value for Tesouro Direto
            
            return {
                'user_id': user_id,
                'asset_name': full_titulo_name,
                'asset_code': asset_code,
                'application_date': timezone.now().date(),  # Default to today if not available
                'maturity_date': vencimento_date,
                'price': price,
                'quantity': quantity,
                'available_quantity': available_quantity,
                'guarantee_quantity': guarantee_quantity,
                'applied_value': applied_value,
                'position_value': position_value,
                'net_value': net_value,
                'gross_yield': gross_yield,
                'net_yield': net_yield,
                'income_tax': Decimal('0.00'),  # Taxes applied at sale
                'iof': Decimal('0.00'),
                'source': 'Excel Import',
                'import_date': timezone.now(),
                'titulo_name': full_titulo_name,
                'vencimento': vencimento_date,
                'sub_type_name': sub_type_name,  # Store for later use in import
            }
        except Exception as e:
            print(f"Error extracting Tesouro from row: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def extract_cash_balance(worksheet) -> Optional[Decimal]:
        """Extract Saldo Disponível (cash balance) from Excel.
        Looks for the value in row 4, column 3 (index 2) or row 61, column 1 (index 0)."""
        try:
            # Method 1: Check row 4, column 3 (after "Saldo Disponível" header in row 3)
            if worksheet.max_row >= 4:
                row_3 = list(worksheet.iter_rows())[2]  # Row 3 (0-indexed)
                row_4 = list(worksheet.iter_rows())[3]  # Row 4 (0-indexed)
                
                # Check if row 3 has "Saldo Disponível" header
                if row_3[2] and 'SALDO DISPON' in str(row_3[2].value).upper():
                    cash_value = row_4[2].value if len(row_4) > 2 else None
                    if cash_value is not None:
                        if isinstance(cash_value, (int, float)):
                            return Decimal(str(cash_value))
                        else:
                            return PortfolioExcelImportService.parse_currency(str(cash_value))
            
            # Method 2: Check row 61, column 1 (after "Saldo Disponível" header in row 60)
            if worksheet.max_row >= 61:
                row_60 = list(worksheet.iter_rows())[59]  # Row 60 (0-indexed)
                row_61 = list(worksheet.iter_rows())[60]  # Row 61 (0-indexed)
                
                # Check if row 60 has "Saldo Disponível" header
                if row_60[0] and 'SALDO DISPON' in str(row_60[0].value).upper():
                    cash_value = row_61[0].value if len(row_61) > 0 else None
                    if cash_value is not None:
                        if isinstance(cash_value, (int, float)):
                            return Decimal(str(cash_value))
                        else:
                            return PortfolioExcelImportService.parse_currency(str(cash_value))
        except Exception as e:
            print(f"Error extracting cash balance: {e}")
        
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
            'caixa_count': 0,
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
            
            # Get or create TESOURO_DIRETO as a sub-type of RENDA_FIXA (not as an investment type)
            tesouro_subtype, _ = InvestmentSubType.objects.get_or_create(
                investment_type=renda_fixa_type,
                code='TESOURO_DIRETO',
                defaults={'name': 'Tesouro Direto', 'display_order': 2, 'is_active': True}
            )
            
            # Get or create CDB_PREFIXADO sub-type for CDB positions
            cdb_prefixado_subtype, _ = InvestmentSubType.objects.get_or_create(
                investment_type=renda_fixa_type,
                code='CDB_PREFIXADO',
                defaults={'name': 'CDB Pré-fixado', 'display_order': 3, 'is_active': True}
            )
            
            # Extract and create CAIXA position from Saldo Disponível
            cash_balance = PortfolioExcelImportService.extract_cash_balance(worksheet)
            if cash_balance and cash_balance > 0:
                try:
                    # Create CAIXA position
                    caixa_asset_code = f"CAIXA_{user_id}"
                    caixa_asset_name = "XP Investimentos - Conta Investimento"
                    
                    # Use a fixed date (first day of current year) for CAIXA so it always updates the same position
                    today = timezone.now().date()
                    fixed_date = datetime(today.year, 1, 1).date()
                    # Set maturity far in the future for cash (or use a default)
                    future_date = datetime(today.year + 10, 12, 31).date()
                    
                    # Get or create Caixa subtype
                    caixa_subtype, _ = InvestmentSubType.objects.get_or_create(
                        investment_type=renda_fixa_type,
                        code='CAIXA',
                        defaults={
                            'name': 'Caixa',
                            'display_order': 1,
                            'is_predefined': False,
                            'is_active': True
                        }
                    )
                    
                    caixa_position, created = FixedIncomePosition.objects.update_or_create(
                        user_id=user_id,
                        asset_code=caixa_asset_code,
                        application_date=fixed_date,
                        defaults={
                            'asset_name': caixa_asset_name,
                            'maturity_date': future_date,
                            'quantity': Decimal('1.00'),
                            'available_quantity': Decimal('1.00'),
                            'guarantee_quantity': Decimal('0.00'),
                            'applied_value': cash_balance,
                            'position_value': cash_balance,
                            'net_value': cash_balance,
                            'gross_yield': Decimal('0.00'),
                            'net_yield': Decimal('0.00'),
                            'income_tax': Decimal('0.00'),
                            'iof': Decimal('0.00'),
                            'liquidity': 'Imediata',
                            'investment_type': renda_fixa_type,
                            'investment_sub_type': caixa_subtype,
                            'source': 'Excel Import',
                            'import_date': timezone.now(),
                        }
                    )
                    
                    if created:
                        results['created'] += 1
                    else:
                        results['updated'] += 1
                    results['caixa_count'] += 1
                    results['debug_info'].append(f"CAIXA position {'created' if created else 'updated'}: R$ {cash_balance}")
                except Exception as e:
                    results['errors'].append(f"Error creating CAIXA position: {str(e)}")
                    results['debug_info'].append(f"Failed to create CAIXA: {str(e)}")
            
            rows_processed = 0
            sections_found = []
            current_tesouro_subsection = None
            current_tesouro_subtype = None
            
            # Create or get Tesouro Direto sub-types under RENDA_FIXA
            # These are sub-types of TESOURO_DIRETO, but stored as separate sub-types under RENDA_FIXA
            # For now, we'll use the main TESOURO_DIRETO sub-type for all Tesouro positions
            # The specific sub-types (Pós-Fixado, Inflação, Prefixado) can be added later if needed
            
            # Map sub-type names to InvestmentSubType objects
            # Default to TESOURO_DIRETO sub-type for all Tesouro positions
            subtype_map = {
                'Pós-Fixado': tesouro_subtype,
                'Inflação': tesouro_subtype,
                'Prefixado': tesouro_subtype,
                'Tesouro Direto': tesouro_subtype,
                'TESOURO_DIRETO': tesouro_subtype,
            }
            
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
                    current_tesouro_subsection = None
                    current_tesouro_subtype = None
                    results['debug_info'].append(f"Row {row_idx}: Found section '{section}' - {str(row[0])[:100]}")
                    continue
                
                # Detect Tesouro Direto sub-section (e.g., "15,2% | Pós-Fixado")
                # Note: In Excel, the sub-section header row also contains column headers
                if current_section == 'tesouro_direto':
                    subsection_info = PortfolioExcelImportService.detect_tesouro_subsection(row)
                    if subsection_info:
                        sub_type_name, allocation_pct = subsection_info
                        current_tesouro_subsection = sub_type_name
                        # Map to InvestmentSubType
                        current_tesouro_subtype = subtype_map.get(sub_type_name)
                        if not current_tesouro_subtype:
                            # Try to find by name match
                            for key, subtype_obj in subtype_map.items():
                                if key.lower() in sub_type_name.lower() or sub_type_name.lower() in key.lower():
                                    current_tesouro_subtype = subtype_obj
                                    break
                        results['debug_info'].append(f"Row {row_idx}: Found Tesouro sub-section '{sub_type_name}' ({allocation_pct}%) - skipping header row")
                        continue  # Skip this row as it's both sub-section header and column headers
                
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
                                    'investment_sub_type': cdb_prefixado_subtype,  # Assign CDB_PREFIXADO sub-type
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
                    tesouro_data = PortfolioExcelImportService.extract_tesouro_from_row(
                        row, user_id, current_tesouro_subsection
                    )
                    if tesouro_data:
                        try:
                            titulo_name = tesouro_data.pop('titulo_name')
                            vencimento = tesouro_data.pop('vencimento')
                            sub_type_name = tesouro_data.pop('sub_type_name', None)
                            
                            # Use current sub-type if available, otherwise determine from bond
                            investment_sub_type = current_tesouro_subtype
                            if not investment_sub_type and sub_type_name:
                                investment_sub_type = subtype_map.get(sub_type_name)
                            
                            position, created = FixedIncomePosition.objects.update_or_create(
                                user_id=tesouro_data['user_id'],
                                asset_code=tesouro_data['asset_code'],
                                application_date=tesouro_data['application_date'],
                                defaults={
                                    **tesouro_data,
                                    'investment_type': renda_fixa_type,  # RENDA_FIXA, not Tesouro Direto
                                    'investment_sub_type': investment_sub_type or tesouro_subtype,  # TESOURO_DIRETO sub-type
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
                            import traceback
                            results['debug_info'].append(f"Row {row_idx}: Error details: {traceback.format_exc()}")
                    else:
                        # Log why Tesouro extraction failed
                        if row[0]:
                            titulo_name = str(row[0]).strip()
                            if titulo_name and not any(bond_type in titulo_name.upper() for bond_type in ['LFT', 'NTNB', 'LTN', 'NTN-B', 'NTN B', 'TESOURO']):
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


