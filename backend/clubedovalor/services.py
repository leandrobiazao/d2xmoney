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
    
    GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/u/0/d/1-C7tynYu9CHbQzg-bCAH4StLGfYqDcKWWqSvHbWxrCw/pubhtml/sheet?headers=false&gid=0"
    GOOGLE_SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/u/0/d/1-C7tynYu9CHbQzg-bCAH4StLGfYqDcKWWqSvHbWxrCw/export?format=csv&gid=0"
    
    @staticmethod
    def parse_brazilian_date(date_str: str) -> str:
        """Parse Brazilian date format (DD/MM/YYYY) to ISO 8601 format."""
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
        
        # Extract "Data Screening" date from row 2, column 1 (index 1, cell 0)
        timestamp = datetime.now().isoformat() + 'Z'
        if len(rows) > 1:
            row2 = rows[1]
            cells = row2.find_all(['td', 'th'])
            if len(cells) > 0:
                # Use get_text with proper encoding handling
                date_cell = cells[0].get_text(strip=True)
                if date_cell:
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
    def parse_csv_table(csv_content: str) -> tuple:
        """
        Parse CSV content and extract stock data.
        Returns tuple of (timestamp, stocks_list).
        """
        # Ensure the content is properly decoded as UTF-8
        if isinstance(csv_content, bytes):
            # Try UTF-8 first, then try other encodings
            try:
                csv_content = csv_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    csv_content = csv_content.decode('utf-8-sig')  # Handle BOM
                except UnicodeDecodeError:
                    try:
                        csv_content = csv_content.decode('latin-1')  # Fallback
                    except UnicodeDecodeError:
                        csv_content = csv_content.decode('utf-8', errors='replace')
        
        # Use csv.reader with proper encoding handling
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        
        if len(rows) < 5:
            raise ValueError("Not enough rows in CSV")
        
        # Extract "Data Screening" date from row 2, column 1 (index 1, column 0)
        timestamp = datetime.now().isoformat() + 'Z'
        if len(rows) > 1 and len(rows[1]) > 0:
            date_cell = rows[1][0].strip()
            if date_cell:
                timestamp = ClubeDoValorService.parse_brazilian_date(date_cell)
        
        # Parse stock data starting from row 5 (index 4) - row 4 is first data row
        stocks = []
        for i in range(4, len(rows)):
            row = rows[i]
            
            if len(row) < 10:
                continue
            
            # Extract data from columns
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
                
                # Skip if no codigo or if codigo looks like a header (not a valid ticker)
                if not codigo or codigo.lower() in ['código', 'codigo', 'ranking']:
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
                print(f"Error parsing CSV row {i}: {e}")
                continue
        
        return timestamp, stocks
    
    @staticmethod
    def load_ambb_data() -> Dict:
        """Load ambb data from database."""
        # Get all snapshots
        snapshots = StockSnapshot.objects.filter(is_current=False).order_by('-timestamp')
        snapshots_data = []
        for snapshot in snapshots:
            stocks = Stock.objects.filter(snapshot=snapshot).order_by('ranking')
            snapshots_data.append({
                'timestamp': snapshot.timestamp,
                'data': [ClubeDoValorService._stock_to_dict(stock) for stock in stocks]
            })
        
        # Get current snapshot
        current_snapshot = StockSnapshot.objects.filter(is_current=True).first()
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
    def add_monthly_snapshot(timestamp: str, stocks: List[Dict]) -> None:
        """Add a new monthly snapshot to database."""
        # Mark all existing snapshots as not current
        StockSnapshot.objects.filter(is_current=True).update(is_current=False)
        
        # Create new snapshot
        snapshot = StockSnapshot.objects.create(
            timestamp=timestamp,
            is_current=True
        )
        
        # Create stocks for this snapshot
        for stock_data in stocks:
            Stock.objects.create(
                snapshot=snapshot,
                ranking=stock_data.get('ranking', 0),
                codigo=stock_data.get('codigo', ''),
                earning_yield=ClubeDoValorService._parse_decimal(stock_data.get('earningYield', 0)),
                nome=stock_data.get('nome', ''),
                setor=stock_data.get('setor', ''),
                ev=ClubeDoValorService._parse_decimal(stock_data.get('ev', 0)),
                ebit=ClubeDoValorService._parse_decimal(stock_data.get('ebit', 0)),
                liquidez=ClubeDoValorService._parse_decimal(stock_data.get('liquidez', 0)),
                cotacao_atual=ClubeDoValorService._parse_decimal(stock_data.get('cotacaoAtual', 0)),
                observacao=stock_data.get('observacao', ''),
            )
    
    @staticmethod
    def refresh_from_google_sheets(sheets_url: Optional[str] = None) -> Dict:
        """Fetch from Google Sheets and create new snapshot. Tries CSV first, then HTML."""
        # Use provided URL or default
        if sheets_url:
            # Extract URLs from provided URL
            if '/export?format=csv' in sheets_url:
                # User provided CSV URL
                csv_url = sheets_url
                # Extract base URL and construct HTML URL
                if '/export?format=csv' in sheets_url:
                    base = sheets_url.split('/export?format=csv')[0]
                    gid_param = ''
                    if '&gid=' in sheets_url:
                        gid_param = '&gid=' + sheets_url.split('&gid=')[1].split('&')[0]
                    elif '?gid=' in sheets_url:
                        gid_param = '?gid=' + sheets_url.split('?gid=')[1].split('&')[0]
                    html_url = f"{base}/pubhtml/sheet?headers=false{gid_param}"
                else:
                    html_url = sheets_url.replace('/export?format=csv', '/pubhtml/sheet?headers=false')
            elif '/pubhtml' in sheets_url:
                # User provided HTML URL
                html_url = sheets_url
                # Extract base URL and construct CSV URL
                base = sheets_url.split('/pubhtml')[0]
                gid_param = ''
                if '&gid=' in sheets_url:
                    gid_param = '&gid=' + sheets_url.split('&gid=')[1].split('&')[0]
                elif '?gid=' in sheets_url:
                    gid_param = '&gid=' + sheets_url.split('?gid=')[1].split('&')[0]
                csv_url = f"{base}/export?format=csv{gid_param}"
            else:
                # Assume it's a base URL, construct both
                base_url = sheets_url.rstrip('/')
                csv_url = f"{base_url}/export?format=csv&gid=0"
                html_url = f"{base_url}/pubhtml/sheet?headers=false&gid=0"
        else:
            csv_url = ClubeDoValorService.GOOGLE_SHEETS_CSV_URL
            html_url = ClubeDoValorService.GOOGLE_SHEETS_URL
        
        csv_error = None
        html_error = None
        
        # Try CSV first (more reliable, no SSL issues usually)
        try:
            print(f"Attempting to fetch from Google Sheets as CSV: {csv_url}")
            csv_content = ClubeDoValorService.fetch_from_google_sheets_url(csv_url)
            timestamp, stocks = ClubeDoValorService.parse_csv_table(csv_content)
            print(f"Successfully parsed {len(stocks)} stocks from CSV")
        except Exception as csv_err:
            csv_error = str(csv_err)
            print(f"CSV fetch failed: {csv_error}, trying HTML...")
            # Fallback to HTML
            try:
                html_content = ClubeDoValorService.fetch_from_google_sheets_url(html_url)
                timestamp, stocks = ClubeDoValorService.parse_html_table(html_content)
                print(f"Successfully parsed {len(stocks)} stocks from HTML")
            except Exception as html_err:
                html_error = str(html_err)
                error_msg = f"Both CSV and HTML fetch failed. CSV error: {csv_error}. HTML error: {html_error}"
                print(error_msg)
                raise Exception(error_msg)
        
        # Save to database
        try:
            ClubeDoValorService.add_monthly_snapshot(timestamp, stocks)
        except Exception as db_err:
            error_msg = f"Failed to save data to database: {str(db_err)}"
            print(error_msg)
            raise Exception(error_msg)
        
        return {
            'timestamp': timestamp,
            'stocks': stocks,
            'count': len(stocks)
        }
    
    @staticmethod
    def get_current_stocks() -> List[Dict]:
        """Get current month's stocks."""
        current_snapshot = StockSnapshot.objects.filter(is_current=True).first()
        if not current_snapshot:
            return []
        
        stocks = Stock.objects.filter(snapshot=current_snapshot).order_by('ranking')
        return [ClubeDoValorService._stock_to_dict(stock) for stock in stocks]
    
    @staticmethod
    def get_historical_snapshots() -> List[Dict]:
        """Get all snapshots (including current)."""
        # Include all snapshots, not just historical ones, so the current month is also shown
        snapshots = StockSnapshot.objects.all().order_by('-timestamp')
        result = []
        for snapshot in snapshots:
            stocks = Stock.objects.filter(snapshot=snapshot).order_by('ranking')
            result.append({
                'timestamp': snapshot.timestamp,
                'data': [ClubeDoValorService._stock_to_dict(stock) for stock in stocks]
            })
        return result
    
    @staticmethod
    def delete_stock(codigo: str) -> bool:
        """Delete a stock from current data and reorder rankings."""
        current_snapshot = StockSnapshot.objects.filter(is_current=True).first()
        if not current_snapshot:
            return False
        
        # Delete the stock
        deleted_count = Stock.objects.filter(snapshot=current_snapshot, codigo=codigo).delete()[0]
        if deleted_count == 0:
            return False
        
        # Reorder rankings
        ClubeDoValorService.reorder_rankings()
        return True
    
    @staticmethod
    def reorder_rankings() -> None:
        """Reorder rankings in current data (called after deletion)."""
        current_snapshot = StockSnapshot.objects.filter(is_current=True).first()
        if not current_snapshot:
            return
        
        stocks = Stock.objects.filter(snapshot=current_snapshot).order_by('ranking')
        for i, stock in enumerate(stocks, start=1):
            stock.ranking = i
            stock.save()
    
    @staticmethod
    def _stock_to_dict(stock: Stock) -> Dict:
        """Convert Stock model instance to dictionary."""
        return {
            'ranking': stock.ranking,
            'codigo': stock.codigo,
            'earningYield': float(stock.earning_yield),
            'nome': stock.nome,
            'setor': stock.setor,
            'ev': float(stock.ev),
            'ebit': float(stock.ebit),
            'liquidez': float(stock.liquidez),
            'cotacaoAtual': float(stock.cotacao_atual),
            'observacao': stock.observacao,
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

