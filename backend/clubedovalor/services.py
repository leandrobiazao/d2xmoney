"""
Service for managing Clube do Valor stock recommendations from Google Sheets.
"""
import json
import re
import csv
import io
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from django.conf import settings
import requests
from bs4 import BeautifulSoup


class ClubeDoValorService:
    """Service for managing stock recommendations from Google Sheets."""
    
    GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/u/0/d/1-C7tynYu9CHbQzg-bCAH4StLGfYqDcKWWqSvHbWxrCw/pubhtml/sheet?headers=false&gid=0"
    GOOGLE_SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/u/0/d/1-C7tynYu9CHbQzg-bCAH4StLGfYqDcKWWqSvHbWxrCw/export?format=csv&gid=0"
    
    @staticmethod
    def get_ambb_file_path() -> Path:
        """Get the path to the ambb JSON file."""
        data_dir = Path(settings.DATA_DIR)
        return data_dir / 'ambb.json'
    
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
        try:
            # Try with SSL verification first
            response = requests.get(
                url, 
                timeout=30,
                verify=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.SSLError as ssl_err:
            print(f"SSL Error, trying without verification: {ssl_err}")
            # Fallback: try without SSL verification (for development only)
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                response = requests.get(
                    url,
                    timeout=30,
                    verify=False,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                response.raise_for_status()
                return response.text
            except Exception as e2:
                print(f"Error fetching Google Sheets (fallback): {e2}")
                raise
        except Exception as e:
            print(f"Error fetching Google Sheets: {e}")
            raise
    
    @staticmethod
    def parse_html_table(html_content: str) -> tuple:
        """
        Parse HTML table and extract stock data.
        Returns tuple of (timestamp, stocks_list).
        """
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
            
            # Extract data from cells
            try:
                ranking_str = cells[0].get_text(strip=True)
                codigo = cells[1].get_text(strip=True)
                earning_yield_str = cells[2].get_text(strip=True)
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
        
        # Parse stock data starting from row 5 (index 4)
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
                print(f"Error parsing CSV row {i}: {e}")
                continue
        
        return timestamp, stocks
    
    @staticmethod
    def load_ambb_data() -> Dict:
        """Load ambb.json data."""
        file_path = ClubeDoValorService.get_ambb_file_path()
        
        if not file_path.exists():
            return {
                'snapshots': [],
                'current': {
                    'timestamp': '',
                    'data': []
                }
            }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {
                    'snapshots': [],
                    'current': {
                        'timestamp': '',
                        'data': []
                    }
                }
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading ambb data: {e}")
            return {
                'snapshots': [],
                'current': {
                    'timestamp': '',
                    'data': []
                }
            }
    
    @staticmethod
    def save_ambb_data(data: Dict) -> None:
        """Save ambb.json data."""
        file_path = ClubeDoValorService.get_ambb_file_path()
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving ambb data: {e}")
            raise
    
    @staticmethod
    def add_monthly_snapshot(timestamp: str, stocks: List[Dict]) -> None:
        """Add a new monthly snapshot to ambb.json."""
        data = ClubeDoValorService.load_ambb_data()
        
        # Add to snapshots
        snapshot = {
            'timestamp': timestamp,
            'data': stocks
        }
        data['snapshots'].append(snapshot)
        
        # Update current
        data['current'] = {
            'timestamp': timestamp,
            'data': stocks
        }
        
        ClubeDoValorService.save_ambb_data(data)
    
    @staticmethod
    def refresh_from_google_sheets(sheets_url: Optional[str] = None) -> Dict:
        """Fetch from Google Sheets and create new snapshot. Tries CSV first, then HTML."""
        # Use provided URL or default
        if sheets_url:
            # Extract URLs from provided URL
            if '/export?format=csv' in sheets_url or '/pubhtml' in sheets_url:
                # User provided full URL, extract base
                if '/export?format=csv' in sheets_url:
                    csv_url = sheets_url
                    html_url = sheets_url.replace('/export?format=csv', '/pubhtml/sheet?headers=false')
                else:
                    html_url = sheets_url
                    csv_url = sheets_url.replace('/pubhtml/sheet?headers=false', '/export?format=csv')
            else:
                # Assume it's a base URL, construct both
                base_url = sheets_url.rstrip('/')
                csv_url = f"{base_url}/export?format=csv&gid=0"
                html_url = f"{base_url}/pubhtml/sheet?headers=false&gid=0"
        else:
            csv_url = ClubeDoValorService.GOOGLE_SHEETS_CSV_URL
            html_url = ClubeDoValorService.GOOGLE_SHEETS_URL
        
        try:
            # Try CSV first (more reliable, no SSL issues usually)
            print(f"Attempting to fetch from Google Sheets as CSV: {csv_url}")
            csv_content = ClubeDoValorService.fetch_from_google_sheets_url(csv_url)
            timestamp, stocks = ClubeDoValorService.parse_csv_table(csv_content)
            print(f"Successfully parsed {len(stocks)} stocks from CSV")
        except Exception as csv_err:
            print(f"CSV fetch failed: {csv_err}, trying HTML...")
            # Fallback to HTML
            html_content = ClubeDoValorService.fetch_from_google_sheets_url(html_url)
            timestamp, stocks = ClubeDoValorService.parse_html_table(html_content)
            print(f"Successfully parsed {len(stocks)} stocks from HTML")
        
        ClubeDoValorService.add_monthly_snapshot(timestamp, stocks)
        return {
            'timestamp': timestamp,
            'stocks': stocks,
            'count': len(stocks)
        }
    
    @staticmethod
    def get_current_stocks() -> List[Dict]:
        """Get current month's stocks."""
        data = ClubeDoValorService.load_ambb_data()
        return data.get('current', {}).get('data', [])
    
    @staticmethod
    def get_historical_snapshots() -> List[Dict]:
        """Get all historical snapshots."""
        data = ClubeDoValorService.load_ambb_data()
        return data.get('snapshots', [])
    
    @staticmethod
    def delete_stock(codigo: str) -> bool:
        """Delete a stock from current data and reorder rankings."""
        data = ClubeDoValorService.load_ambb_data()
        current_data = data.get('current', {}).get('data', [])
        
        # Find and remove stock
        original_count = len(current_data)
        current_data = [s for s in current_data if s.get('codigo') != codigo]
        
        if len(current_data) == original_count:
            return False  # Stock not found
        
        # Reorder rankings
        for i, stock in enumerate(current_data, start=1):
            stock['ranking'] = i
        
        # Update current data
        data['current']['data'] = current_data
        
        # Also update the latest snapshot if it exists
        if data.get('snapshots'):
            latest_snapshot = data['snapshots'][-1]
            if latest_snapshot.get('timestamp') == data['current'].get('timestamp'):
                latest_snapshot['data'] = current_data
        
        ClubeDoValorService.save_ambb_data(data)
        return True
    
    @staticmethod
    def reorder_rankings() -> None:
        """Reorder rankings in current data (called after deletion)."""
        data = ClubeDoValorService.load_ambb_data()
        current_data = data.get('current', {}).get('data', [])
        
        # Sort by current ranking to maintain order, then renumber
        current_data.sort(key=lambda x: x.get('ranking', 0))
        
        for i, stock in enumerate(current_data, start=1):
            stock['ranking'] = i
        
        data['current']['data'] = current_data
        
        # Also update the latest snapshot if it exists
        if data.get('snapshots'):
            latest_snapshot = data['snapshots'][-1]
            if latest_snapshot.get('timestamp') == data['current'].get('timestamp'):
                latest_snapshot['data'] = current_data
        
        ClubeDoValorService.save_ambb_data(data)

