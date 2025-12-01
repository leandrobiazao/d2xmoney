"""
Service for managing Clube do Valor stock recommendations from Google Sheets.
"""
import csv
import io
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from .models import StockSnapshot, Stock


class ClubeDoValorService:
    """Service for managing stock recommendations from Google Sheets."""
    
    # AMBB1 URLs (default)
    GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRcssbJB5jamNErlaJ2KNYnnI-O8JSlti4lTyEhhjqM2X6x0Ql4pmrw07XbW6T4osXAjs9qecu8rds8/pubhtml?gid=0&single=true&widget=true&headers=false"
    GOOGLE_SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRcssbJB5jamNErlaJ2KNYnnI-O8JSlti4lTyEhhjqM2X6x0Ql4pmrw07XbW6T4osXAjs9qecu8rds8/pub?output=csv"
    
    # AMBB2 URLs
    AMBB2_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS_BDO0YIK41Cp97PBzWyM_-UlRAIm8j3gSuN3tOtTKwMEXwGdhAatILM2HGUk7VhoAeXBGnhGiG65o/pubhtml/sheet?headers=false&gid=0"
    AMBB2_SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS_BDO0YIK41Cp97PBzWyM_-UlRAIm8j3gSuN3tOtTKwMEXwGdhAatILM2HGUk7VhoAeXBGnhGiG65o/pub?output=csv"
    
    # MDIV URLs
    MDIV_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6MykGC4sSVN3m-MsCIRIpr8AS_BrUfp29EEixC_9kl6Jbh7Gc4KVRC81dqMelm0QWfDai-WGvatyF/pubhtml/sheet?headers=false&gid=0"
    MDIV_SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6MykGC4sSVN3m-MsCIRIpr8AS_BrUfp29EEixC_9kl6Jbh7Gc4KVRC81dqMelm0QWfDai-WGvatyF/pub?output=csv"
    
    # MOMM (Momentum Melhores) URLs - same sheet as MOMP
    MOMM_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMf0eVU2__2N5bvhCvVOKJIeteE8HMpdhMlqj70pWxN7ZR655WkQJ854TznhPo-d8V4gdZK0dDiUiH/pubhtml/sheet?headers=false&gid=0"
    MOMM_SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMf0eVU2__2N5bvhCvVOKJIeteE8HMpdhMlqj70pWxN7ZR655WkQJ854TznhPo-d8V4gdZK0dDiUiH/pub?output=csv"
    
    # MOMP (Momentum Piores) URLs - same sheet as MOMM
    MOMP_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMf0eVU2__2N5bvhCvVOKJIeteE8HMpdhMlqj70pWxN7ZR655WkQJ854TznhPo-d8V4gdZK0dDiUiH/pubhtml/sheet?headers=false&gid=0"
    MOMP_SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMf0eVU2__2N5bvhCvVOKJIeteE8HMpdhMlqj70pWxN7ZR655WkQJ854TznhPo-d8V4gdZK0dDiUiH/pub?output=csv"
    
    @staticmethod
    def get_default_urls_for_strategy(strategy_type: str) -> tuple:
        """Get default URLs for a specific strategy."""
        if strategy_type == 'AMBB2':
            return (ClubeDoValorService.AMBB2_SHEETS_URL, ClubeDoValorService.AMBB2_SHEETS_CSV_URL)
        elif strategy_type == 'MDIV':
            return (ClubeDoValorService.MDIV_SHEETS_URL, ClubeDoValorService.MDIV_SHEETS_CSV_URL)
        elif strategy_type == 'MOMM':
            return (ClubeDoValorService.MOMM_SHEETS_URL, ClubeDoValorService.MOMM_SHEETS_CSV_URL)
        elif strategy_type == 'MOMP':
            return (ClubeDoValorService.MOMP_SHEETS_URL, ClubeDoValorService.MOMP_SHEETS_CSV_URL)
        # Default to AMBB1
        return (ClubeDoValorService.GOOGLE_SHEETS_URL, ClubeDoValorService.GOOGLE_SHEETS_CSV_URL)
    
    @staticmethod
    def parse_brazilian_date(date_str: str) -> str:
        """Parse Brazilian date format (DD/MM/YYYY) to ISO 8601 format. Returns current time on failure."""
        try:
            parts = date_str.strip().split('/')
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                dt = datetime(year, month, day)
                return dt.isoformat() + 'Z'
        except (ValueError, IndexError) as e:
            print(f"Error parsing date '{date_str}': {e}")
        return datetime.now().isoformat() + 'Z'

    @staticmethod
    def _find_date_in_rows(rows: List[List[str]]) -> str:
        """
        Helper to find the snapshot date in CSV rows.
        Strategies:
        1. Look for 'Data Screening' cell, take value from cell below it.
        2. Look for 'Atualização' cell, extract date from it.
        3. Fallback: Check specific cells (row 1 col 0, row 2 col 0) for date-like strings.
        """
        print(f"DEBUG: _find_date_in_rows checking {min(5, len(rows))} rows")
        if len(rows) > 0:
            print(f"DEBUG: Row 0: {rows[0][:5]}")
        if len(rows) > 1:
            print(f"DEBUG: Row 1: {rows[1][:5]}")
            
        # Strategy 1 & 2: Search for keywords
        for i in range(min(5, len(rows))):
            for j in range(min(5, len(rows[i]))):
                cell = rows[i][j].strip()
                cell_lower = cell.lower()
                
                # Strategy 1: 'Data Screening' header -> Value is below
                if 'data screening' in cell_lower:
                    print(f"DEBUG: Found 'data screening' at [{i}][{j}]")
                    if i + 1 < len(rows) and len(rows[i+1]) > j:
                        candidate = rows[i+1][j].strip()
                        print(f"DEBUG: Candidate below: '{candidate}'")
                        if '/' in candidate:
                            parsed = ClubeDoValorService.parse_brazilian_date(candidate)
                            # Only accept if it didn't fail (parse_brazilian_date returns now on fail, check input format)
                            # Check if parsed date is reasonably close to candidate (not just 'now')
                            # But parse_brazilian_date returns ISO string, hard to compare easily without parsing back
                            # For now, just return it
                            print(f"DEBUG: Parsed date: {parsed}")
                            return parsed
                            
                # Strategy 2: 'Última atualização: DD/MM/YYYY' format
                if 'atualização' in cell_lower or 'atualizacao' in cell_lower:
                    print(f"DEBUG: Found 'atualização' at [{i}][{j}]: '{cell}'")
                    # Try to extract date part
                    if ':' in cell:
                        date_part = cell.split(':')[-1].strip()
                        if '/' in date_part:
                            parsed = ClubeDoValorService.parse_brazilian_date(date_part)
                            print(f"DEBUG: Parsed date from string: {parsed}")
                            return parsed
                    # Maybe it's just the date in the string?
                    if '/' in cell:
                        # Simple regex-like check or just try parsing
                        try:
                            # Try finding substring matching DD/MM/YYYY
                            import re
                            match = re.search(r'\d{2}/\d{2}/\d{4}', cell)
                            if match:
                                parsed = ClubeDoValorService.parse_brazilian_date(match.group(0))
                                print(f"DEBUG: Parsed date from regex: {parsed}")
                                return parsed
                        except:
                            pass

        # Strategy 3: Fallback to hardcoded positions if they look like dates
        print("DEBUG: Fallback strategies...")
        # Check row 1, col 0 (often the date in some layouts)
        if len(rows) > 1 and len(rows[1]) > 0:
            candidate = rows[1][0].strip()
            if '/' in candidate:
                 parsed = ClubeDoValorService.parse_brazilian_date(candidate)
                 print(f"DEBUG: Parsed date from fallback row 1 col 0: {parsed}")
                 return parsed
        
        # Check row 2, col 0 (if row 1 was header)
        if len(rows) > 2 and len(rows[2]) > 0:
            candidate = rows[2][0].strip()
            if '/' in candidate:
                 parsed = ClubeDoValorService.parse_brazilian_date(candidate)
                 print(f"DEBUG: Parsed date from fallback row 2 col 0: {parsed}")
                 return parsed

        # Default to now
        now_ts = datetime.now().isoformat() + 'Z'
        print(f"DEBUG: Date not found, defaulting to NOW: {now_ts}")
        return now_ts

    
    @staticmethod
    def parse_brazilian_currency(value_str: str) -> float:
        """Parse Brazilian currency format (R$ 1.234.567,89) to float."""
        if not value_str or value_str.strip() == '' or value_str == '-x-':
            return 0.0
        # Remove R$ and spaces
        cleaned = value_str.replace('R$', '').replace(' ', '').strip()
        # Remove thousands separators (dots) and replace comma with dot
        cleaned = cleaned.replace('.', '').replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    @staticmethod
    def parse_percentage(value_str: str) -> float:
        """Parse percentage format (20,60%) to float."""
        if not value_str or value_str.strip() == '':
            return 0.0
        # Remove % and spaces
        cleaned = value_str.replace('%', '').replace(' ', '').strip()
        # Replace comma with dot
        cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    @staticmethod
    def fetch_from_google_sheets_url(url: str) -> str:
        """Fetch content from a specific Google Sheets URL."""
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Charset': 'UTF-8',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        
        try:
            # Try with SSL verification first
            response = requests.get(
                url, 
                timeout=30,
                verify=True,
                headers=headers,
                allow_redirects=True  # Follow redirects automatically
            )
            response.raise_for_status()
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as ssl_err:
            print(f"SSL/Connection Error, trying without verification: {ssl_err}")
            # Fallback: try without SSL verification (for development only)
            response = requests.get(
                url,
                timeout=30,
                verify=False,
                headers=headers,
                allow_redirects=True  # Follow redirects automatically
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching Google Sheets: {e}")
            raise
        
        # Always decode from raw bytes as UTF-8 to preserve Portuguese accents
        # Don't trust response.encoding as it may be incorrectly detected
        try:
            # Try UTF-8 first
            content = response.content.decode('utf-8')
            return content
        except UnicodeDecodeError:
            try:
                # Try UTF-8 with BOM
                content = response.content.decode('utf-8-sig')
                return content
            except UnicodeDecodeError:
                # Fallback: use response.text but force UTF-8 if possible
                print(f"Warning: UTF-8 decode failed, trying detected encoding: {response.encoding}")
                # Re-encode and decode to fix encoding issues
                if response.encoding and response.encoding.lower() == 'iso-8859-1':
                    # If detected as ISO-8859-1 but content is actually UTF-8, fix it
                    try:
                        content = response.text.encode('iso-8859-1').decode('utf-8')
                        return content
                    except:
                        pass
                return response.text
    
    @staticmethod
    def parse_html_table(html_content: str) -> tuple:
        """
        Parse HTML table and extract stock data.
        Returns tuple of (timestamp, stocks_list).
        """
        # Ensure the content is properly decoded as UTF-8
        if isinstance(html_content, bytes):
            html_content = html_content.decode('utf-8')
        # Use 'html.parser' with explicit encoding handling
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table')
        
        if not table:
            raise ValueError("No table found in HTML")
        
        rows = table.find_all('tr')
        if len(rows) < 5:
            raise ValueError("Not enough rows in table")
        
        # Extract "Data Screening" date using html parser features
        timestamp = datetime.now().isoformat() + 'Z'
        
        # Look for 'Data Screening' or date-like strings in the first few rows
        date_found = False
        for i in range(min(5, len(rows))):
            cells = rows[i].find_all(['td', 'th'])
            for j, cell in enumerate(cells):
                text = cell.get_text(strip=True).lower()
                if 'data screening' in text:
                    # Check if date is in this cell or next row
                    # Usually in HTML tables, headers and values might be in different rows
                    if i + 1 < len(rows):
                        next_row_cells = rows[i+1].find_all(['td', 'th'])
                        if j < len(next_row_cells):
                            date_candidate = next_row_cells[j].get_text(strip=True)
                            if '/' in date_candidate:
                                timestamp = ClubeDoValorService.parse_brazilian_date(date_candidate)
                                date_found = True
                                break
                if date_found: break
            if date_found: break
            
        # Fallback to fixed position if simple search fails
        if not date_found and len(rows) > 1:
            row2 = rows[1]
            cells = row2.find_all(['td', 'th'])
            if len(cells) > 0:
                # Use get_text with proper encoding handling
                date_cell = cells[0].get_text(strip=True)
                if date_cell and '/' in date_cell:
                    timestamp = ClubeDoValorService.parse_brazilian_date(date_cell)
        
        # Parse stock data starting from row 5 (index 4)
        stocks = []
        for i in range(4, len(rows)):
            row = rows[i]
            cells = row.find_all(['td', 'th'])
            
            if len(cells) < 10:
                continue
            
            # Extract data from cells with proper encoding handling
            try:
                ranking_str = cells[0].get_text(strip=True)
                codigo = cells[1].get_text(strip=True)
                earning_yield_str = cells[2].get_text(strip=True)
                # Ensure proper UTF-8 encoding for text fields with Portuguese accents
                nome = cells[3].get_text(strip=True)
                setor = cells[4].get_text(strip=True)
                ev_str = cells[5].get_text(strip=True)
                ebit_str = cells[6].get_text(strip=True)
                liquidez_str = cells[7].get_text(strip=True)
                cotacao_str = cells[8].get_text(strip=True)
                observacao = cells[9].get_text(strip=True) if len(cells) > 9 else ''
                
                # Skip if no codigo (empty row)
                if not codigo:
                    continue
                
                # Parse values
                ranking = int(ranking_str) if ranking_str.isdigit() else 0
                earning_yield = ClubeDoValorService.parse_percentage(earning_yield_str)
                ev = ClubeDoValorService.parse_brazilian_currency(ev_str)
                ebit = ClubeDoValorService.parse_brazilian_currency(ebit_str)
                liquidez = ClubeDoValorService.parse_brazilian_currency(liquidez_str)
                cotacao = ClubeDoValorService.parse_brazilian_currency(cotacao_str)
                
                stock = {
                    'ranking': ranking,
                    'codigo': codigo,
                    'earningYield': earning_yield,
                    'nome': nome,
                    'setor': setor,
                    'ev': ev,
                    'ebit': ebit,
                    'liquidez': liquidez,
                    'cotacaoAtual': cotacao,
                    'observacao': observacao
                }
                
                stocks.append(stock)
            except (ValueError, IndexError) as e:
                print(f"Error parsing row {i}: {e}")
                continue
        
        return timestamp, stocks
    
    @staticmethod
    def parse_csv_table_ambb2(csv_content: str) -> tuple:
        """Parse CSV content for AMBB2 format."""
        if isinstance(csv_content, bytes):
            try:
                csv_content = csv_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    csv_content = csv_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    csv_content = csv_content.decode('latin-1', errors='replace')
        
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        if len(rows) < 5:
            raise ValueError("Not enough rows in CSV")
        
        timestamp = ClubeDoValorService._find_date_in_rows(rows)
        
        stocks = []
        for i in range(4, len(rows)):
            row = rows[i]
            if len(row) < 13:
                continue
            
            try:
                ranking_str = row[0].strip() if len(row) > 0 else ''
                codigo = row[1].strip() if len(row) > 1 else ''
                value_idx_str = row[2].strip() if len(row) > 2 else ''
                nome = row[3].strip() if len(row) > 3 else ''
                setor = row[4].strip() if len(row) > 4 else ''
                ey_str = row[5].strip() if len(row) > 5 else ''
                cfy_str = row[6].strip() if len(row) > 6 else ''
                btm_str = row[7].strip() if len(row) > 7 else ''
                mktcap_str = row[8].strip() if len(row) > 8 else ''
                ev_str = row[9].strip() if len(row) > 9 else ''
                liquidez_str = row[10].strip() if len(row) > 10 else ''
                cotacao_str = row[11].strip() if len(row) > 11 else ''
                observacao = row[12].strip() if len(row) > 12 else ''
                
                if not codigo or codigo.lower() in ['código', 'codigo', 'ranking']:
                    continue
                
                ranking = int(ranking_str) if ranking_str.isdigit() else 0
                value_idx = ClubeDoValorService.parse_decimal_value(value_idx_str)
                earning_yield = ClubeDoValorService.parse_percentage(ey_str)
                cfy = ClubeDoValorService.parse_decimal_value(cfy_str)
                btm = ClubeDoValorService.parse_brazilian_currency(btm_str)
                mktcap = ClubeDoValorService.parse_brazilian_currency(mktcap_str)
                ev = ClubeDoValorService.parse_brazilian_currency(ev_str)
                liquidez = ClubeDoValorService.parse_brazilian_currency(liquidez_str)
                cotacao = ClubeDoValorService.parse_brazilian_currency(cotacao_str)
                
                stock = {
                    'ranking': ranking,
                    'codigo': codigo,
                    'valueIdx': value_idx,
                    'nome': nome,
                    'setor': setor,
                    'earningYield': earning_yield,
                    'cfy': cfy,
                    'btm': btm,
                    'mktcap': mktcap,
                    'ev': ev,
                    'liquidez': liquidez,
                    'cotacaoAtual': cotacao,
                    'observacao': observacao
                }
                stocks.append(stock)
            except (ValueError, IndexError) as e:
                print(f"Error parsing AMBB2 CSV row {i}: {e}")
                continue
        
        return timestamp, stocks
    
    @staticmethod
    def parse_csv_table_mdiv(csv_content: str) -> tuple:
        """Parse CSV content for MDIV format."""
        if isinstance(csv_content, bytes):
            try:
                csv_content = csv_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    csv_content = csv_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    csv_content = csv_content.decode('latin-1', errors='replace')
        
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        if len(rows) < 3:
            raise ValueError("Not enough rows in CSV")
        
        timestamp = datetime.now().isoformat() + 'Z'
        if len(rows) > 0 and len(rows[0]) > 0:
            # MDIV format has date in first row
            date_cell = rows[0][0].strip() if 'atualização' in rows[0][0].lower() else ''
            if date_cell and len(rows) > 0:
                # Extract date from "Última atualização:03/11/2025"
                date_part = date_cell.split(':')[-1].strip()
                if date_part:
                    timestamp = ClubeDoValorService.parse_brazilian_date(date_part)
        
        stocks = []
        # MDIV starts from row 2 (index 2) - row 1 is header
        for i in range(2, len(rows)):
            row = rows[i]
            if len(row) < 6:
                continue
            
            try:
                ranking_str = row[0].strip() if len(row) > 0 else ''
                codigo = row[1].strip() if len(row) > 1 else ''
                dividend_yield_str = row[2].strip() if len(row) > 2 else ''
                nome = row[3].strip() if len(row) > 3 else ''
                setor = row[4].strip() if len(row) > 4 else ''
                liquidez_str = row[5].strip() if len(row) > 5 else ''
                
                if not codigo or codigo.lower() in ['código', 'codigo', 'ranking', 'rank']:
                    continue
                
                ranking = int(ranking_str) if ranking_str.isdigit() else 0
                dividend_yield = ClubeDoValorService.parse_percentage(dividend_yield_str)
                liquidez = ClubeDoValorService.parse_brazilian_currency(liquidez_str)
                
                # Debug: print first stock to verify parsing
                if len(stocks) == 0:
                    print(f"MDIV First stock parsed - codigo: {codigo}, dividend_yield: {dividend_yield}, liquidez: {liquidez}")
                
                stock = {
                    'ranking': ranking,
                    'codigo': codigo,
                    'dividendYield36m': dividend_yield,
                    'nome': nome,
                    'setor': setor,
                    'liquidezMedia3m': liquidez,
                    'observacao': ''
                }
                stocks.append(stock)
            except (ValueError, IndexError) as e:
                print(f"Error parsing MDIV CSV row {i}: {e}")
                continue
        
        return timestamp, stocks
    
    @staticmethod
    def parse_csv_table_mom(csv_content: str, strategy_type: str = 'MOMM') -> tuple:
        """Parse CSV content for MOM (Momentum) format.
        
        The CSV contains two sections:
        - "Melhores 40 papeis" - MOMM (Momentum Melhores) - positive momentum
        - "Piores" section - MOMP (Momentum Piores) - negative momentum
        
        Args:
            csv_content: CSV content from Google Sheets
            strategy_type: 'MOMM' for Melhores or 'MOMP' for Piores
        """
        if isinstance(csv_content, bytes):
            try:
                csv_content = csv_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    csv_content = csv_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    csv_content = csv_content.decode('latin-1', errors='replace')
        
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        if len(rows) < 5:
            raise ValueError("Not enough rows in CSV")
        
        timestamp = ClubeDoValorService._find_date_in_rows(rows)
        
        stocks = []
        # MOM structure:
        # Row 0: "Data Screening" | "Filtro de liquidez:"
        # Row 1: "03/11/2025" | "R$ 3.000.000,00"
        # Row 2: "Melhores 40 papeis" (MOMM section)
        # Row 3 (index 3): Header row: "#" | "Ticker" | "6 months Mom(%)" | "ID ratio" | "Nome" | "Setor" | "Subsetor" | "Segmento" | "Volume(MM)" | "Capitalização (MM)"
        # Row 4+ (index 4+): Data rows for MOMM
        # Later: "Piores" section (MOMP) - need to find where this starts
        
        # Find sections: "Melhores 40 papeis" and "Piores"
        melhores_start_row = None
        piores_start_row = None
        
        for i, row in enumerate(rows):
            # Check all columns in the row, not just first 3
            row_text = ' '.join([str(cell).lower() for cell in row if cell])
            if 'melhores' in row_text and ('40' in row_text or 'papereis' in row_text or 'papeis' in row_text):
                melhores_start_row = i
                print(f"Found 'Melhores' section at row {i}: {row[:5]}")
            elif 'piores' in row_text:
                piores_start_row = i
                print(f"Found 'Piores' section at row {i}: {row[:5]}")
        
        # Determine which section to parse based on strategy_type
        if strategy_type == 'MOMM':
            if melhores_start_row is None:
                raise ValueError("'Melhores' section not found in MOM CSV")
            # Header is at melhores_start_row + 1, data starts at melhores_start_row + 2
            header_row_index = melhores_start_row + 1
            start_row = melhores_start_row + 2  # Skip section title and header
            end_row = piores_start_row if piores_start_row is not None else len(rows)
            print(f"Parsing MOMM section: header at row {header_row_index}, data from row {start_row} to {end_row}")
        elif strategy_type == 'MOMP':
            if piores_start_row is None:
                raise ValueError("'Piores' section not found in MOM CSV")
            # Header is at piores_start_row + 1, data starts at piores_start_row + 2
            header_row_index = piores_start_row + 1
            start_row = piores_start_row + 2  # Skip section title and header
            end_row = len(rows)
            print(f"Parsing MOMP section: header at row {header_row_index}, data from row {start_row} to {end_row}")
        else:
            # Default to MOMM if strategy_type not specified
            if melhores_start_row is None:
                raise ValueError("'Melhores' section not found in MOM CSV")
            header_row_index = melhores_start_row + 1
            start_row = melhores_start_row + 2
            end_row = piores_start_row if piores_start_row is not None else len(rows)
            print(f"Parsing default (MOMM) section: header at row {header_row_index}, data from row {start_row} to {end_row}")
        
        # Verify header row exists
        if len(rows) <= header_row_index:
            raise ValueError(f"Header row not found at index {header_row_index} in MOM CSV")
        
        # Verify and log header row
        try:
            header_row = rows[header_row_index] if len(rows) > header_row_index else []
            header_text = ' '.join([str(cell).lower() for cell in header_row[:10]])
            print(f"MOM Header row {header_row_index} for {strategy_type}: {header_row[:5]}")
            print(f"  Header text: {header_text[:100]}")
            
            # Store header values to check against later
            header_codigo = header_row[1].strip().lower() if len(header_row) > 1 else ''
            header_ranking = header_row[0].strip().lower() if len(header_row) > 0 else ''
            print(f"  Header codigo: '{header_codigo}', header ranking: '{header_ranking}'")
        except Exception as e:
            print(f"Warning: Could not read header row: {e}")
        
        # Parse rows from start_row to end_row
        for i in range(start_row, end_row):
            row = rows[i]
            if len(row) < 10:
                continue
            
            try:
                ranking_str = row[0].strip() if len(row) > 0 else ''
                codigo = row[1].strip() if len(row) > 1 else ''
                momentum_str = row[2].strip() if len(row) > 2 else ''
                id_ratio_str = row[3].strip() if len(row) > 3 else ''
                nome = row[4].strip() if len(row) > 4 else ''
                setor = row[5].strip() if len(row) > 5 else ''
                subsetor = row[6].strip() if len(row) > 6 else ''
                segmento = row[7].strip() if len(row) > 7 else ''
                volume_str = row[8].strip() if len(row) > 8 else ''
                capitalizacao_str = row[9].strip() if len(row) > 9 else ''
                
                # Skip empty rows
                if not codigo and not ranking_str:
                    continue
                
                # Skip header row - check if this row matches the header exactly (safety check)
                if i == header_row_index:
                    print(f"Skipping header row at index {i} (should not happen)")
                    continue
                
                codigo_lower = codigo.lower() if codigo else ''
                ranking_lower = ranking_str.lower() if ranking_str else ''
                nome_lower = nome.lower() if nome else ''
                
                # Skip if ranking is not a valid number FIRST (header rows often have "#" or text)
                if not ranking_str or not ranking_str.strip().isdigit():
                    if ranking_str and ranking_str.strip() and ranking_str.strip() != '#':  # Only log if not empty and not just "#"
                        print(f"Skipping row {i} - invalid ranking: '{ranking_str}'")
                    continue
                
                # Skip if codigo is empty
                if not codigo or not codigo.strip():
                    continue
                
                # Get header values for comparison
                try:
                    header_codigo_check = rows[header_row_index][1].strip().lower() if len(rows[header_row_index]) > 1 else ''
                    header_ranking_check = rows[header_row_index][0].strip().lower() if len(rows[header_row_index]) > 0 else ''
                except:
                    header_codigo_check = ''
                    header_ranking_check = ''
                
                # Skip if codigo matches header value exactly (case-insensitive)
                if codigo_lower == header_codigo_check:
                    print(f"Skipping header row at row {i}: codigo='{codigo}' matches header")
                    continue
                
                # Skip if ranking matches header value exactly
                if ranking_lower == header_ranking_check:
                    print(f"Skipping header row at row {i}: ranking='{ranking_str}' matches header")
                    continue
                
                # Skip if ranking is "#" (definitely a header row)
                if ranking_str.strip() == '#':
                    print(f"Skipping header row at row {i}: ranking='{ranking_str}'")
                    continue
                
                # Skip if codigo is a known header value (Ticker, Código, etc.)
                if codigo_lower in ['ticker', 'código', 'codigo', 'ranking', 'rank']:
                    print(f"Skipping header-like row {i}: codigo='{codigo}'")
                    continue
                
                # Skip if ranking is a header value (Ranking, Rank, etc.) - but not numbers
                if ranking_lower in ['ranking', 'rank', '#']:
                    print(f"Skipping header-like row {i}: ranking='{ranking_str}'")
                    continue
                
                # Additional check: if nome looks like a header value, skip
                if nome_lower in ['nome', '6 months mom(%)', '6 months mom', 'id ratio', 'volume(mm)', 'capitalização (mm)', 'volume', 'capitalização']:
                    print(f"Skipping header-like row {i}: nome='{nome}'")
                    continue
                
                # Additional check: if setor looks like a header value, skip
                setor_lower = setor.lower() if setor else ''
                if setor_lower in ['setor', 'subsetor', 'segmento', 'id ratio']:
                    print(f"Skipping header-like row {i}: setor='{setor}'")
                    continue
                
                # Validate codigo format - should be alphanumeric ticker (e.g., "CSMG3", "DIRR3")
                # Skip if it's just "#" (header marker)
                if codigo.strip() == '#':
                    print(f"Skipping row {i} - codigo is '#': '{codigo}'")
                    continue
                
                # Validate codigo is a valid stock ticker (has at least 2 chars and contains letters)
                # Brazilian stock tickers are like "CSMG3", "DIRR3", "PETR4" - should have letters
                # Some tickers might be pure numbers like "11" (BPAC11), but we need at least 2 chars
                if len(codigo.strip()) < 2:
                    print(f"Skipping row {i} - codigo too short: '{codigo}'")
                    continue
                
                # Ticker must contain at least one letter (to distinguish from ranking numbers)
                # But allow pure numbers if they're longer (like "11" for BPAC11 - but this won't match)
                # Actually, pure numeric tickers should be skipped - all valid tickers have letters
                if not any(c.isalpha() for c in codigo):
                    print(f"Skipping row {i} - codigo has no letters (not a valid ticker): '{codigo}'")
                    continue
                
                # Parse ranking - should be a positive integer
                ranking = int(ranking_str.strip())
                if ranking <= 0 or ranking > 10000:  # Reasonable upper bound
                    print(f"Skipping row {i} - invalid ranking value: {ranking}")
                    continue
                momentum = ClubeDoValorService.parse_percentage(momentum_str)
                id_ratio = ClubeDoValorService.parse_decimal_value(id_ratio_str)
                volume = ClubeDoValorService.parse_brazilian_currency(volume_str)
                capitalizacao = ClubeDoValorService.parse_brazilian_currency(capitalizacao_str)
                
                # Debug: print first stocks to verify parsing
                if len(stocks) == 0:
                    print(f"{strategy_type} First stock parsed - row {i}: ranking={ranking}, codigo={codigo}, momentum={momentum}, id_ratio={id_ratio}, nome={nome}, setor={setor}")
                    print(f"  Row data: {row[:10]}")
                elif len(stocks) < 5:
                    print(f"{strategy_type} Stock {len(stocks)+1} parsed: codigo={codigo}, momentum={momentum}")
                
                # Check for duplicates before adding
                if any(s.get('codigo') == codigo for s in stocks):
                    print(f"Warning: Duplicate codigo '{codigo}' found at row {i}, skipping")
                    continue
                
                stock = {
                    'ranking': ranking,
                    'codigo': codigo,
                    'momentum6m': momentum,
                    'idRatio': id_ratio,
                    'nome': nome,
                    'setor': setor,
                    'subsetor': subsetor,
                    'segmento': segmento,
                    'volumeMm': volume,
                    'capitalizacaoMm': capitalizacao,
                    'observacao': ''
                }
                stocks.append(stock)
            except (ValueError, IndexError, AttributeError) as e:
                import traceback
                print(f"Error parsing MOM CSV row {i}: {e}")
                print(f"Row data: {row[:10]}")
                print(f"Traceback: {traceback.format_exc()}")
                continue
            except Exception as e:
                import traceback
                print(f"Unexpected error parsing MOM CSV row {i}: {e}")
                print(f"Row data: {row[:10]}")
                print(f"Traceback: {traceback.format_exc()}")
                continue
        
        return timestamp, stocks
    
    @staticmethod
    def parse_csv_table(csv_content: str) -> tuple:
        """
        Parse CSV content and extract stock data.
        Auto-detects strategy format (AMBB1, AMBB2, MDIV, or MOM).
        Returns tuple of (timestamp, stocks_list).
        """
        # Try to detect format by checking header row
        if isinstance(csv_content, bytes):
            try:
                csv_content = csv_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    csv_content = csv_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    csv_content = csv_content.decode('latin-1', errors='replace')
        
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        if len(rows) < 2:
            raise ValueError("Not enough rows in CSV")
        
        # Check for MOM format first - has "Data Screening" in first row and "mom" in header
        # Note: parse_csv_table_mom now requires strategy_type, but we can't detect it here
        # The strategy_type should be passed from refresh_from_google_sheets
        # For now, default to MOMM if detected
        if len(rows) > 0:
            first_row_text = ' '.join(rows[0]).lower() if rows[0] else ''
            if 'data screening' in first_row_text and len(rows) >= 4:
                # Check header row (row 3, index 3) for MOM indicators
                header_row = rows[3] if len(rows) > 3 else []
                header_text = ' '.join(header_row).lower()
                if ('mom' in header_text or 'momentum' in header_text) and 'id ratio' in header_text:
                    print("Detected Momentum format by header - defaulting to MOMM")
                    # Default to MOMM, but this should be set by the caller based on strategy_type
                    # This is a fallback - parse_csv_table_mom should be called directly with strategy_type
                    return ClubeDoValorService.parse_csv_table_mom(csv_content, 'MOMM')
        
        # Check header row to detect strategy
        header_row = rows[1] if len(rows) > 1 else []
        header_text = ' '.join(header_row).lower()
        
        # Detect MDIV by checking for "dividend yield" in header
        # MDIV format has: RANKING, CÓDIGO, DIVIDEND YIELD (36 MESES...), NOME, SETOR, LIQUIDEZ MÉDIA 3M
        if 'dividend' in header_text and '36' in header_text:
            if len(rows) >= 3:
                print("Detected MDIV format by header")
                return ClubeDoValorService.parse_csv_table_mdiv(csv_content)
        elif 'dividend' in header_text and 'earning' not in header_text:
            if len(rows) >= 3:
                print("Detected MDIV format by dividend (no earning)")
                return ClubeDoValorService.parse_csv_table_mdiv(csv_content)
        
        # Detect AMBB2 by checking for "value idx" or number of columns (13+)
        if 'value idx' in header_text or 'valueidx' in header_text:
            if len(rows) >= 5:
                return ClubeDoValorService.parse_csv_table_ambb2(csv_content)
        
        # Check column count - AMBB2 has 13 columns, AMBB1 has 10
        if len(rows) > 4 and len(rows[4]) >= 13:
            return ClubeDoValorService.parse_csv_table_ambb2(csv_content)
        
        # Default to AMBB1 format
        # Ensure the content is properly decoded as UTF-8
        if isinstance(csv_content, bytes):
            try:
                csv_content = csv_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    csv_content = csv_content.decode('utf-8-sig')
                except UnicodeDecodeError:
                    csv_content = csv_content.decode('latin-1', errors='replace')
        
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        if len(rows) < 5:
            raise ValueError("Not enough rows in CSV")
        
        timestamp = ClubeDoValorService._find_date_in_rows(rows)
        
        stocks = []
        for i in range(4, len(rows)):
            row = rows[i]
            if len(row) < 10:
                continue
            
            try:
                ranking_str = row[0].strip() if len(row) > 0 else ''
                codigo = row[1].strip() if len(row) > 1 else ''
                earning_yield_str = row[2].strip() if len(row) > 2 else ''
                nome = row[3].strip() if len(row) > 3 else ''
                setor = row[4].strip() if len(row) > 4 else ''
                ev_str = row[5].strip() if len(row) > 5 else ''
                ebit_str = row[6].strip() if len(row) > 6 else ''
                liquidez_str = row[7].strip() if len(row) > 7 else ''
                cotacao_str = row[8].strip() if len(row) > 8 else ''
                observacao = row[9].strip() if len(row) > 9 else ''
                
                if not codigo or codigo.lower() in ['código', 'codigo', 'ranking']:
                    continue
                
                ranking = int(ranking_str) if ranking_str.isdigit() else 0
                earning_yield = ClubeDoValorService.parse_percentage(earning_yield_str)
                ev = ClubeDoValorService.parse_brazilian_currency(ev_str)
                ebit = ClubeDoValorService.parse_brazilian_currency(ebit_str)
                liquidez = ClubeDoValorService.parse_brazilian_currency(liquidez_str)
                cotacao = ClubeDoValorService.parse_brazilian_currency(cotacao_str)
                
                stock = {
                    'ranking': ranking,
                    'codigo': codigo,
                    'earningYield': earning_yield,
                    'nome': nome,
                    'setor': setor,
                    'ev': ev,
                    'ebit': ebit,
                    'liquidez': liquidez,
                    'cotacaoAtual': cotacao,
                    'observacao': observacao
                }
                stocks.append(stock)
            except (ValueError, IndexError) as e:
                print(f"Error parsing CSV row {i}: {e}")
                continue
        
        return timestamp, stocks
    
    @staticmethod
    def load_ambb_data(strategy_type: str = 'AMBB1') -> Dict:
        """Load data from database for a specific strategy."""
        # Get all historical snapshots (not current)
        snapshots = StockSnapshot.objects.filter(strategy_type=strategy_type, is_current=False).order_by('-timestamp')
        snapshots_data = []
        for snapshot in snapshots:
            stocks = Stock.objects.filter(snapshot=snapshot).order_by('ranking')
            snapshots_data.append({
                'timestamp': snapshot.timestamp,
                'data': [ClubeDoValorService._stock_to_dict(stock) for stock in stocks]
            })
        
        # Get current snapshot
        current_snapshot = StockSnapshot.objects.filter(strategy_type=strategy_type, is_current=True).first()
        current_data = {
            'timestamp': current_snapshot.timestamp if current_snapshot else '',
            'data': []
        }
        if current_snapshot:
            stocks = Stock.objects.filter(snapshot=current_snapshot).order_by('ranking')
            current_data['data'] = [ClubeDoValorService._stock_to_dict(stock) for stock in stocks]
        
        return {
            'snapshots': snapshots_data,
            'current': current_data
        }
    
    @staticmethod
    def add_monthly_snapshot(timestamp: str, stocks: List[Dict], strategy_type: str = 'AMBB1') -> None:
        """Add a new monthly snapshot to database."""
        # Detect strategy if not provided
        if not strategy_type or strategy_type == 'AMBB1':
            strategy_type = ClubeDoValorService.detect_strategy_from_data(stocks)
        
        # Mark all existing snapshots of this strategy as not current
        StockSnapshot.objects.filter(strategy_type=strategy_type, is_current=True).update(is_current=False)
        
        # Create new snapshot
        snapshot = StockSnapshot.objects.create(
            timestamp=timestamp,
            strategy_type=strategy_type,
            is_current=True
        )
        
        # Helper function to safely get and parse a field
        def safe_get_decimal(stock_dict, key):
            value = stock_dict.get(key)
            if value is not None and value != '':
                parsed = ClubeDoValorService._parse_decimal(value)
                # Even if parsed is 0, return it (0 is a valid value)
                return parsed
            return None
        
        # Debug: print first stock data to verify
        if stocks and len(stocks) > 0:
            first_stock = stocks[0]
            print(f"Saving first stock for {strategy_type}: {first_stock.get('codigo')}")
            print(f"  dividendYield36m: {first_stock.get('dividendYield36m')}")
            print(f"  liquidezMedia3m: {first_stock.get('liquidezMedia3m')}")
        
        # Check for duplicates in the stocks list before saving
        seen_codigos = set()
        unique_stocks = []
        for stock_data in stocks:
            codigo = stock_data.get('codigo', '').strip()
            if not codigo:
                continue
            if codigo in seen_codigos:
                print(f"Warning: Duplicate codigo '{codigo}' found in stocks list, skipping duplicate")
                continue
            seen_codigos.add(codigo)
            unique_stocks.append(stock_data)
        
        print(f"Creating {len(unique_stocks)} unique stocks (removed {len(stocks) - len(unique_stocks)} duplicates)")
        
        # Create stocks for this snapshot
        for stock_data in unique_stocks:
            codigo = stock_data.get('codigo', '').strip()
            if not codigo:
                continue
            
            # Check if stock already exists in this snapshot (shouldn't happen, but safety check)
            existing = Stock.objects.filter(snapshot=snapshot, codigo=codigo).first()
            if existing:
                print(f"Warning: Stock {codigo} already exists in snapshot {snapshot.id}, updating instead of creating")
                # Update existing stock instead of creating new one
                existing.ranking = stock_data.get('ranking', 0)
                existing.nome = stock_data.get('nome', '')
                existing.setor = stock_data.get('setor', '')
                existing.observacao = stock_data.get('observacao', '')
                existing.earning_yield = safe_get_decimal(stock_data, 'earningYield')
                existing.ev = safe_get_decimal(stock_data, 'ev')
                existing.liquidez = safe_get_decimal(stock_data, 'liquidez')
                existing.cotacao_atual = safe_get_decimal(stock_data, 'cotacaoAtual')
                existing.ebit = safe_get_decimal(stock_data, 'ebit')
                existing.value_idx = safe_get_decimal(stock_data, 'valueIdx')
                existing.cfy = safe_get_decimal(stock_data, 'cfy')
                existing.btm = safe_get_decimal(stock_data, 'btm')
                existing.mktcap = safe_get_decimal(stock_data, 'mktcap')
                existing.dividend_yield_36m = safe_get_decimal(stock_data, 'dividendYield36m')
                existing.liquidez_media_3m = safe_get_decimal(stock_data, 'liquidezMedia3m')
                existing.momentum_6m = safe_get_decimal(stock_data, 'momentum6m')
                existing.id_ratio = safe_get_decimal(stock_data, 'idRatio')
                existing.volume_mm = safe_get_decimal(stock_data, 'volumeMm')
                existing.capitalizacao_mm = safe_get_decimal(stock_data, 'capitalizacaoMm')
                existing.subsetor = stock_data.get('subsetor', '')
                existing.segmento = stock_data.get('segmento', '')
                existing.save()
                continue
            
            Stock.objects.create(
                snapshot=snapshot,
                ranking=stock_data.get('ranking', 0),
                codigo=codigo,
                nome=stock_data.get('nome', ''),
                setor=stock_data.get('setor', ''),
                observacao=stock_data.get('observacao', ''),
                # AMBB1 & AMBB2 fields
                earning_yield=safe_get_decimal(stock_data, 'earningYield'),
                ev=safe_get_decimal(stock_data, 'ev'),
                liquidez=safe_get_decimal(stock_data, 'liquidez'),
                cotacao_atual=safe_get_decimal(stock_data, 'cotacaoAtual'),
                # AMBB1 specific
                ebit=safe_get_decimal(stock_data, 'ebit'),
                # AMBB2 specific
                value_idx=safe_get_decimal(stock_data, 'valueIdx'),
                cfy=safe_get_decimal(stock_data, 'cfy'),
                btm=safe_get_decimal(stock_data, 'btm'),
                mktcap=safe_get_decimal(stock_data, 'mktcap'),
                # MDIV specific
                dividend_yield_36m=safe_get_decimal(stock_data, 'dividendYield36m'),
                liquidez_media_3m=safe_get_decimal(stock_data, 'liquidezMedia3m'),
                # MOM specific
                momentum_6m=safe_get_decimal(stock_data, 'momentum6m'),
                id_ratio=safe_get_decimal(stock_data, 'idRatio'),
                volume_mm=safe_get_decimal(stock_data, 'volumeMm'),
                capitalizacao_mm=safe_get_decimal(stock_data, 'capitalizacaoMm'),
                subsetor=stock_data.get('subsetor', ''),
                segmento=stock_data.get('segmento', ''),
            )
    
    @staticmethod
    def refresh_from_google_sheets(sheets_url: Optional[str] = None, strategy_type: Optional[str] = None) -> Dict:
        """Fetch from Google Sheets and create new snapshot. Tries CSV first, then HTML."""
        # Use provided URL or default based on strategy
        if sheets_url:
            # Clean the URL first - remove query params and fragments
            clean_url = sheets_url.strip().rstrip('/')
            if '?' in clean_url:
                clean_url = clean_url.split('?')[0]
            if '#' in clean_url:
                clean_url = clean_url.split('#')[0]
            
            print(f"Processing Google Sheets URL: {clean_url}")
            
            # Extract URLs from provided URL
            # Check for /pubhtml FIRST (if URL already has it, we know how to construct CSV)
            if '/pubhtml' in sheets_url:
                # User provided HTML URL
                html_url = sheets_url
                # Extract base URL and construct CSV URL
                # For /d/e/ format with /pubhtml, CSV should be /pub?output=csv
                base = sheets_url.split('/pubhtml')[0]
                # Remove query parameters from base for CSV URL
                if '?' in base:
                    base = base.split('?')[0]
                csv_url = f"{base}/pub?output=csv"
                print(f"Detected HTML URL. CSV URL: {csv_url}, HTML URL: {html_url}")
            elif '/export?format=csv' in sheets_url:
                # User provided CSV URL
                csv_url = sheets_url
                # Extract base URL and construct HTML URL
                base = sheets_url.split('/export?format=csv')[0]
                gid_param = ''
                if '&gid=' in sheets_url:
                    gid_param = '&gid=' + sheets_url.split('&gid=')[1].split('&')[0]
                elif '?gid=' in sheets_url:
                    gid_param = '?gid=' + sheets_url.split('?gid=')[1].split('&')[0]
                html_url = f"{base}/pubhtml/sheet?headers=false{gid_param}"
                print(f"Detected CSV export URL. CSV URL: {csv_url}, HTML URL: {html_url}")
            elif '/d/e/' in clean_url or '/spreadsheets/d/e/' in clean_url:
                # Handle published/embedded URL format (/d/e/PUBLISH_ID)
                # For /d/e/ format, use pub?output=csv for CSV and /pubhtml for HTML
                csv_url = f"{clean_url}/pub?output=csv"
                html_url = f"{clean_url}/pubhtml"
                print(f"Detected /d/e/ format. CSV URL: {csv_url}, HTML URL: {html_url}")
            elif '/d/' in clean_url and '/e/' not in clean_url:
                # Handle direct document ID format (/d/DOC_ID)
                # For /d/DOC_ID format, use export?format=csv and pubhtml/sheet
                csv_url = f"{clean_url}/export?format=csv&gid=0"
                html_url = f"{clean_url}/pubhtml/sheet?headers=false&gid=0"
                print(f"Detected /d/ format. CSV URL: {csv_url}, HTML URL: {html_url}")
            else:
                # Fallback: assume it's a base URL, construct both
                csv_url = f"{clean_url}/export?format=csv&gid=0"
                html_url = f"{clean_url}/pubhtml/sheet?headers=false&gid=0"
                print(f"Using fallback format. CSV URL: {csv_url}, HTML URL: {html_url}")
        else:
            # Use default URLs for the specified strategy
            if strategy_type:
                html_url, csv_url = ClubeDoValorService.get_default_urls_for_strategy(strategy_type)
            else:
                csv_url = ClubeDoValorService.GOOGLE_SHEETS_CSV_URL
                html_url = ClubeDoValorService.GOOGLE_SHEETS_URL
        
        csv_error = None
        html_error = None
        
        # Try CSV first (more reliable, no SSL issues usually)
        try:
            print(f"Attempting to fetch from Google Sheets as CSV: {csv_url}")
            print(f"Strategy type: {strategy_type}")
            csv_content = ClubeDoValorService.fetch_from_google_sheets_url(csv_url)
            print(f"CSV content length: {len(csv_content)}")
            
            # For MOMM and MOMP, call parse_csv_table_mom directly with strategy_type
            if strategy_type in ['MOMM', 'MOMP']:
                print(f"Using parse_csv_table_mom for {strategy_type}")
                timestamp, stocks = ClubeDoValorService.parse_csv_table_mom(csv_content, strategy_type)
            else:
                timestamp, stocks = ClubeDoValorService.parse_csv_table(csv_content)
            
            print(f"Successfully parsed {len(stocks)} stocks from CSV")
            if stocks:
                print(f"First stock keys: {list(stocks[0].keys())}")
        except Exception as csv_err:
            import traceback
            csv_error = str(csv_err)
            traceback_str = traceback.format_exc()
            print(f"CSV fetch failed: {csv_error}")
            print(f"CSV URL that failed: {csv_url}")
            print(f"Traceback: {traceback_str}")
            print(f"Trying HTML fallback...")
            # Fallback to HTML
            try:
                print(f"Attempting to fetch from Google Sheets as HTML: {html_url}")
                html_content = ClubeDoValorService.fetch_from_google_sheets_url(html_url)
                timestamp, stocks = ClubeDoValorService.parse_html_table(html_content)
                print(f"Successfully parsed {len(stocks)} stocks from HTML")
            except Exception as html_err:
                html_error = str(html_err)
                print(f"HTML fetch also failed: {html_error}")
                print(f"HTML URL that failed: {html_url}")
                error_msg = f"Both CSV and HTML fetch failed. CSV error: {csv_error}. HTML error: {html_error}"
                print(error_msg)
                raise Exception(error_msg)
        
        # Detect strategy from parsed data if not provided
        if not strategy_type:
            strategy_type = ClubeDoValorService.detect_strategy_from_data(stocks)
        
        # Save to database
        try:
            print(f"Saving {len(stocks)} stocks to database for strategy {strategy_type}")
            ClubeDoValorService.add_monthly_snapshot(timestamp, stocks, strategy_type)
            print(f"Successfully saved data to database")
        except Exception as db_err:
            import traceback
            error_msg = f"Failed to save data to database: {str(db_err)}"
            traceback_str = traceback.format_exc()
            print(f"Database save error: {error_msg}")
            print(f"Traceback: {traceback_str}")
            print(error_msg)
            raise Exception(error_msg)
        
        return {
            'timestamp': timestamp,
            'stocks': stocks,
            'count': len(stocks),
            'strategy_type': strategy_type
        }
    
    @staticmethod
    def get_current_stocks(strategy_type: str = 'AMBB1') -> List[Dict]:
        """Get current month's stocks for a specific strategy."""
        current_snapshot = StockSnapshot.objects.filter(strategy_type=strategy_type, is_current=True).first()
        if not current_snapshot:
            return []
        
        stocks = Stock.objects.filter(snapshot=current_snapshot).order_by('ranking')
        return [ClubeDoValorService._stock_to_dict(stock) for stock in stocks]
    
    @staticmethod
    def get_historical_snapshots(strategy_type: str = 'AMBB1') -> List[Dict]:
        """Get all snapshots (including current) for a specific strategy."""
        # Order by timestamp (newest first), then by id (newest first) to handle same timestamps
        snapshots = StockSnapshot.objects.filter(strategy_type=strategy_type).order_by('-timestamp', '-id')
        result = []
        for snapshot in snapshots:
            stocks = Stock.objects.filter(snapshot=snapshot).order_by('ranking')
            # Validate snapshot data consistency
            if stocks.exists():
                first_stock = stocks.first()
                # For MDIV, check if it has MDIV-specific fields
                if strategy_type == 'MDIV':
                    # Skip snapshots that have ebit (AMBB1 field) but no dividend_yield_36m
                    if first_stock.ebit is not None and first_stock.dividend_yield_36m is None:
                        print(f"Warning: Skipping inconsistent MDIV snapshot {snapshot.id} - has AMBB1 data")
                        continue
                # For AMBB1, check if it has AMBB1-specific fields
                elif strategy_type == 'AMBB1':
                    # Skip snapshots that have dividend_yield_36m (MDIV field) but no ebit
                    if first_stock.dividend_yield_36m is not None and first_stock.ebit is None:
                        print(f"Warning: Skipping inconsistent AMBB1 snapshot {snapshot.id} - has MDIV data")
                        continue
                # For MOMM and MOMP, check if it has momentum-specific fields
                elif strategy_type in ['MOMM', 'MOMP']:
                    # Skip snapshots that have ebit (AMBB1 field) or dividend_yield_36m (MDIV field) but no momentum_6m
                    if (first_stock.ebit is not None or first_stock.dividend_yield_36m is not None) and first_stock.momentum_6m is None:
                        print(f"Warning: Skipping inconsistent {strategy_type} snapshot {snapshot.id} - has other strategy data")
                        continue
                
            result.append({
                'timestamp': snapshot.timestamp,
                'data': [ClubeDoValorService._stock_to_dict(stock) for stock in stocks]
            })
        return result
    
    @staticmethod
    def delete_stock(codigo: str, strategy_type: str = 'AMBB1') -> bool:
        """Delete a stock from current data and reorder rankings."""
        current_snapshot = StockSnapshot.objects.filter(strategy_type=strategy_type, is_current=True).first()
        if not current_snapshot:
            return False
        
        # Delete the stock
        deleted_count = Stock.objects.filter(snapshot=current_snapshot, codigo=codigo).delete()[0]
        if deleted_count == 0:
            return False
        
        # Reorder rankings
        ClubeDoValorService.reorder_rankings(strategy_type)
        return True
    
    @staticmethod
    def reorder_rankings(strategy_type: str = 'AMBB1') -> None:
        """Reorder rankings in current data (called after deletion)."""
        current_snapshot = StockSnapshot.objects.filter(strategy_type=strategy_type, is_current=True).first()
        if not current_snapshot:
            return
        
        stocks = Stock.objects.filter(snapshot=current_snapshot).order_by('ranking')
        for i, stock in enumerate(stocks, start=1):
            stock.ranking = i
            stock.save()
    
    @staticmethod
    def _stock_to_dict(stock: Stock) -> Dict:
        """Convert Stock model instance to dictionary with all fields."""
        try:
            result = {
                'ranking': stock.ranking,
                'codigo': stock.codigo,
                'nome': stock.nome,
                'setor': stock.setor,
                'observacao': stock.observacao or '',
            }
            
            # AMBB1 & AMBB2 fields
            if stock.earning_yield is not None:
                result['earningYield'] = float(stock.earning_yield)
            if stock.ev is not None:
                result['ev'] = float(stock.ev)
            if stock.liquidez is not None:
                result['liquidez'] = float(stock.liquidez)
            if stock.cotacao_atual is not None:
                result['cotacaoAtual'] = float(stock.cotacao_atual)
            
            # AMBB1 specific
            if stock.ebit is not None:
                result['ebit'] = float(stock.ebit)
            
            # AMBB2 specific
            if stock.value_idx is not None:
                result['valueIdx'] = float(stock.value_idx)
            if stock.cfy is not None:
                result['cfy'] = float(stock.cfy)
            if stock.btm is not None:
                result['btm'] = float(stock.btm)
            if stock.mktcap is not None:
                result['mktcap'] = float(stock.mktcap)
            
            # MDIV specific
            if stock.dividend_yield_36m is not None:
                result['dividendYield36m'] = float(stock.dividend_yield_36m)
            if stock.liquidez_media_3m is not None:
                result['liquidezMedia3m'] = float(stock.liquidez_media_3m)
            
            # MOM specific
            if stock.momentum_6m is not None:
                result['momentum6m'] = float(stock.momentum_6m)
            if stock.id_ratio is not None:
                result['idRatio'] = float(stock.id_ratio)
            if stock.volume_mm is not None:
                result['volumeMm'] = float(stock.volume_mm)
            if stock.capitalizacao_mm is not None:
                result['capitalizacaoMm'] = float(stock.capitalizacao_mm)
            if stock.subsetor:
                result['subsetor'] = stock.subsetor
            if stock.segmento:
                result['segmento'] = stock.segmento
            
            return result
        except Exception as e:
            print(f"Error converting stock {stock.codigo} to dict: {e}")
            # Return minimal data if conversion fails
            return {
                'ranking': stock.ranking,
                'codigo': stock.codigo,
                'nome': stock.nome or '',
                'setor': stock.setor or '',
                'observacao': stock.observacao or '',
            }
    
    @staticmethod
    def _parse_decimal(value):
        """Parse value to Decimal-compatible format."""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def detect_strategy_from_data(stocks: List[Dict]) -> str:
        """Detect strategy type from stock data structure."""
        if not stocks:
            return 'AMBB1'  # Default
        
        # Check first stock for strategy indicators
        first_stock = stocks[0]
        
        # MOMM/MOMP: Has momentum6m, idRatio, volumeMm, capitalizacaoMm
        # Note: Can't distinguish between MOMM and MOMP from data alone
        # Both use the same fields, difference is which section of the CSV
        if ('momentum6m' in first_stock or 'momentum_6m' in first_stock or
            'idRatio' in first_stock or 'id_ratio' in first_stock or
            'volumeMm' in first_stock or 'volume_mm' in first_stock):
            # Default to MOMM if not specified
            return 'MOMM'
        
        # MDIV: Has dividend_yield_36m, no earning_yield
        if 'dividendYield36m' in first_stock or 'dividend_yield_36m' in first_stock:
            return 'MDIV'
        
        # AMBB2: Has value_idx, cfy, btm, mktcap
        if ('valueIdx' in first_stock or 'value_idx' in first_stock or 
            'cfy' in first_stock or 'btm' in first_stock or 'mktcap' in first_stock):
            return 'AMBB2'
        
        # AMBB1: Has ebit, no value_idx
        if 'ebit' in first_stock:
            return 'AMBB1'
        
        # Default to AMBB1
        return 'AMBB1'
    
    @staticmethod
    def parse_decimal_value(value_str: str) -> float:
        """Parse a decimal value that could be a number or currency."""
        if not value_str or value_str.strip() == '' or value_str == '-x-':
            return 0.0
        # Try parsing as currency first
        if 'R$' in value_str:
            return ClubeDoValorService.parse_brazilian_currency(value_str)
        # Try parsing as percentage
        if '%' in value_str:
            return ClubeDoValorService.parse_percentage(value_str)
        # Try parsing as regular decimal
        cleaned = value_str.replace('.', '').replace(',', '.').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

