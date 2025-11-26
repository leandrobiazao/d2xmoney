from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import datetime
import re

from configuration.models import InvestmentType, InvestmentSubType
from stocks.models import Stock
from fiis.models import FIIProfile
from ticker_mappings.models import TickerMapping

class Command(BaseCommand):
    help = 'Import FIIs from fiis.com.br using Playwright - extracts all 17 columns'

    def handle(self, *args, **options):
        self.stdout.write('Starting FII import with Playwright...')
        
        # 1. Fetch Data using Playwright (separate from Django ORM)
        url = "https://fiis.com.br/lupa-de-fiis/"
        fiis_data = []
        
        try:
            # Use Playwright to scrape data
            fiis_data = self._scrape_fiis(url)
            self.stdout.write(f'Extracted {len(fiis_data)} FIIs from page')
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error scraping FIIs: {e}'))
            import traceback
            self.stderr.write(traceback.format_exc())
            return
        
        # 2. Now save to database (outside Playwright context)
        try:
            fiis_type = self._ensure_types()
            subtypes = self._ensure_subtypes(fiis_type)
            count = self._save_fiis(fiis_data, fiis_type, subtypes)
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} FIIs with all fields'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error saving FIIs: {e}'))
            import traceback
            self.stderr.write(traceback.format_exc())

    def _scrape_fiis(self, url):
        """Scrape FII data using Playwright - returns list of dicts with all 17 columns"""
        fiis_data = []
        
        with sync_playwright() as p:
            self.stdout.write('Launching browser...')
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            self.stdout.write(f'Navigating to {url}...')
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for content to load
            try:
                page.wait_for_selector('tr', timeout=10000)
            except PlaywrightTimeoutError:
                self.stdout.write(self.style.WARNING('Timeout waiting for page elements'))
            
            # Try to find table rows
            self.stdout.write('Looking for table rows...')
            rows = page.query_selector_all('tr')
            self.stdout.write(f'Found {len(rows)} rows')
            
            # Column mapping (ALL 17 columns):
            # 0: Ticker
            # 1: Público Alvo
            # 2: Tipo de Fii
            # 3: Administrador
            # 4: Último Rend. (R$)
            # 5: Último Rend. (%)
            # 6: Data Pagamento
            # 7: Data Base
            # 8: Rend. Méd. 12m (R$)
            # 9: Rend. Méd. 12m (%)
            # 10: Patrimônio/Cota
            # 11: Cotação/VP
            # 12: N° negócios/mês
            # 13: Partic. IFIX
            # 14: Número Cotistas
            # 15: Patrimônio
            # 16: Cota base
            
            for idx, row in enumerate(rows):
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) < 4:  # Need at least ticker and some basic data
                        continue
                    
                    # Try to get ticker from first cell
                    ticker_elem = cells[0].query_selector('a')
                    if not ticker_elem:
                        ticker_text = cells[0].inner_text().strip()
                        if not re.match(r'^[A-Z]{4}\d{2}$', ticker_text):
                            continue
                        ticker = ticker_text
                    else:
                        ticker = ticker_elem.inner_text().strip()
                    
                    # Validate ticker format
                    if not re.match(r'^[A-Z]{4}\d{2}$', ticker):
                        continue
                    
                    # Extract ALL 17 fields
                    fiis_data.append({
                        'ticker': ticker,
                        'publico_alvo': cells[1].inner_text().strip() if len(cells) > 1 else 'N/A',
                        'tipo_fii': cells[2].inner_text().strip() if len(cells) > 2 else 'Outros',
                        'administrador': cells[3].inner_text().strip() if len(cells) > 3 else 'N/A',
                        'ultimo_rend_rs': cells[4].inner_text().strip() if len(cells) > 4 else None,
                        'ultimo_rend_pct': cells[5].inner_text().strip() if len(cells) > 5 else None,
                        'data_pagamento': cells[6].inner_text().strip() if len(cells) > 6 else None,
                        'data_base': cells[7].inner_text().strip() if len(cells) > 7 else None,
                        'rend_med_12m_rs': cells[8].inner_text().strip() if len(cells) > 8 else None,
                        'rend_med_12m_pct': cells[9].inner_text().strip() if len(cells) > 9 else None,
                        'patrimonio_cota': cells[10].inner_text().strip() if len(cells) > 10 else None,
                        'cotacao_vp': cells[11].inner_text().strip() if len(cells) > 11 else None,
                        'negocios_mes': cells[12].inner_text().strip() if len(cells) > 12 else None,
                        'partic_ifix': cells[13].inner_text().strip() if len(cells) > 13 else None,
                        'num_cotistas': cells[14].inner_text().strip() if len(cells) > 14 else None,
                        'patrimonio': cells[15].inner_text().strip() if len(cells) > 15 else None,
                        'cota_base': cells[16].inner_text().strip() if len(cells) > 16 else None
                    })
                    
                    if len(fiis_data) % 50 == 0:
                        self.stdout.write(f'Processed {len(fiis_data)} FIIs...')
                    
                except Exception as e:
                    continue
            
            browser.close()
        
        return fiis_data

    def _parse_decimal(self, value_str):
        """Parse Brazilian decimal format to Decimal"""
        if not value_str or value_str == 'N/A' or value_str == '-' or value_str.strip() == '':
            return None
        try:
            # Remove currency symbol, dots (thousand separator) and replace comma with dot
            clean_str = value_str.replace('R$', '').replace('.', '').replace(',', '.').replace('%', '').strip()
            if clean_str == '':
                return None
            return Decimal(clean_str)
        except:
            return None

    def _parse_int(self, value_str):
        """Parse integer with thousand separators"""
        if not value_str or value_str == 'N/A' or value_str == '-' or value_str.strip() == '':
            return None
        try:
            clean_str = value_str.replace('.', '').replace(',', '').strip()
            if clean_str == '':
                return None
            return int(clean_str)
        except:
            return None

    def _parse_date(self, date_str):
        """Parse Brazilian date format to date object"""
        if not date_str or date_str == 'N/A' or date_str == '-' or date_str.strip() == '':
            return None
        try:
            return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
        except:
            return None

    def _ensure_types(self):
        fiis_type, _ = InvestmentType.objects.get_or_create(
            code='FIIS',
            defaults={
                'name': 'Fundos Imobiliários',
                'display_order': 15,
                'is_active': True
            }
        )
        return fiis_type

    def _ensure_subtypes(self, fiis_type):
        subtypes = {}
        
        predefined = {
            'TIJOLO': 'Tijolo',
            'PAPEL': 'Papel',
            'HIBRIDO': 'Híbrido',
            'OUTROS': 'Outros'
        }
        
        for code, name in predefined.items():
            subtype, _ = InvestmentSubType.objects.get_or_create(
                investment_type=fiis_type,
                code=code,
                defaults={
                    'name': name,
                    'display_order': 10,
                    'is_predefined': True,
                    'is_active': True
                }
            )
            subtypes[code] = subtype
            
        return subtypes

    def _map_segment_to_subtype(self, segment, subtypes):
        segment_upper = segment.upper()
        if 'TIJOLO' in segment_upper or 'IMÓVEIS' in segment_upper or 'SHOPPING' in segment_upper or 'LOGÍSTICA' in segment_upper or 'LOGISTICA' in segment_upper:
            return subtypes['TIJOLO']
        elif 'PAPEL' in segment_upper or 'RECEBÍVEIS' in segment_upper or 'RECEBIVEIS' in segment_upper or 'CRI' in segment_upper:
            return subtypes['PAPEL']
        elif 'HÍBRIDO' in segment_upper or 'HIBRIDO' in segment_upper:
            return subtypes['HIBRIDO']
        else:
            return subtypes['OUTROS']

    def _save_fiis(self, fiis_data, fiis_type, subtypes):
        count = 0
        
        for fii in fiis_data:
            try:
                ticker = fii['ticker']
                tipo_fii = fii.get('tipo_fii', 'Outros')
                
                # Map tipo to subtype
                subtype = self._map_segment_to_subtype(tipo_fii, subtypes)
                
                # Parse ALL financial data fields
                last_yield = self._parse_decimal(fii.get('ultimo_rend_rs'))
                dividend_yield = self._parse_decimal(fii.get('ultimo_rend_pct'))
                payment_date = self._parse_date(fii.get('data_pagamento'))
                base_date = self._parse_date(fii.get('data_base'))
                avg_yield_12m_value = self._parse_decimal(fii.get('rend_med_12m_rs'))
                avg_yield_12m_pct = self._parse_decimal(fii.get('rend_med_12m_pct'))
                equity_per_share = self._parse_decimal(fii.get('patrimonio_cota'))
                price_to_vp = self._parse_decimal(fii.get('cotacao_vp'))
                trades_per_month = self._parse_int(fii.get('negocios_mes'))
                ifix_participation = self._parse_decimal(fii.get('partic_ifix'))
                shareholders_count = self._parse_int(fii.get('num_cotistas'))
                equity = self._parse_decimal(fii.get('patrimonio'))
                base_share_price = self._parse_decimal(fii.get('cota_base'))
                
                with transaction.atomic():
                    # Create/Update Stock
                    stock, created = Stock.objects.update_or_create(
                        ticker=ticker,
                        defaults={
                            'name': ticker,
                            'stock_class': 'FII',
                            'financial_market': 'B3',
                            'investment_type': fiis_type,
                            'investment_subtype': subtype
                        }
                    )
                    
                    # Create/Update Profile with ALL fields
                    FIIProfile.objects.update_or_create(
                        stock=stock,
                        defaults={
                            'segment': tipo_fii,
                            'target_audience': fii.get('publico_alvo', 'N/A'),
                            'administrator': fii.get('administrador', 'N/A'),
                            'last_yield': last_yield,
                            'dividend_yield': dividend_yield,
                            'payment_date': payment_date,
                            'base_date': base_date,
                            'average_yield_12m_value': avg_yield_12m_value,
                            'average_yield_12m_percentage': avg_yield_12m_pct,
                            'equity_per_share': equity_per_share,
                            'price_to_vp': price_to_vp,
                            'trades_per_month': trades_per_month,
                            'ifix_participation': ifix_participation,
                            'shareholders_count': shareholders_count,
                            'equity': equity,
                            'base_share_price': base_share_price
                        }
                    )
                    
                    # Create Ticker Mappings
                    TickerMapping.objects.get_or_create(
                        company_name=ticker,
                        defaults={'ticker': ticker}
                    )
                    
                    TickerMapping.objects.get_or_create(
                        company_name=f"FUNDO {ticker}",
                        defaults={'ticker': ticker}
                    )
                    
                    count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error saving {ticker}: {e}'))
                continue
        
        return count
