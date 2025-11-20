import { AfterViewInit, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ClubeDoValorService } from '../clubedovalor.service';
import { Stock } from '../stock.model';

@Component({
  selector: 'app-clubedovalor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './clubedovalor.html',
  styleUrl: './clubedovalor.css'
})
export class ClubeDoValorComponent implements OnInit, AfterViewInit {
  stocks: Stock[] = [];
  filteredStocks: Stock[] = [];
  loading = false;
  error: string | null = null;
  timestamp: string = '';

  // Sorting
  sortField: string = '';
  sortDirection: 'asc' | 'desc' = 'asc';

  // Strategy Selection
  selectedStrategy: string = 'AMBB1';
  strategies = [
    { code: 'AMBB1', label: 'AMBB 1.0', fullName: 'Ações mais baratas da bolsa' },
    { code: 'AMBB2', label: 'AMBB 2.0', fullName: 'Ações mais baratas da bolsa' },
    { code: 'MDIV', label: 'MDIV', fullName: 'Máquina de Dividendos' },
    { code: 'MOMM', label: 'MOMM', fullName: 'Momentum Melhores' },
    { code: 'MOMP', label: 'MOMP', fullName: 'Momentum Piores' }
  ];

  // Month Selection
  selectedMonth: string = '';
  availableMonths: Array<{key: string, label: string}> = [];

  constructor(private clubeDoValorService: ClubeDoValorService) {}

  getMonths(): Array<{key: string, label: string}> {
    return this.availableMonths;
  }

  getCurrentMonthLabel(): string {
    const currentMonth = this.availableMonths.find(m => m.key === this.selectedMonth);
    return currentMonth ? currentMonth.label : '';
  }

  getCurrentStrategyLabel(): string {
    const strategy = this.strategies.find(s => s.code === this.selectedStrategy);
    if (!strategy) return '';
    
    // Add version number for AMBB strategies
    if (this.selectedStrategy === 'AMBB1') {
      return `${strategy.fullName} 1.0`;
    } else if (this.selectedStrategy === 'AMBB2') {
      return `${strategy.fullName} 2.0`;
    }
    
    return strategy.fullName;
  }

  selectStrategy(strategyCode: string): void {
    if (this.selectedStrategy === strategyCode) return;
    console.log(`[STRATEGY] Switching from ${this.selectedStrategy} to ${strategyCode}`);
    this.selectedStrategy = strategyCode;
    this.selectedMonth = '';
    this.availableMonths = [];
    this.stocks = [];
    this.filteredStocks = [];
    this.timestamp = '';
    this.loadAvailableMonths();
  }

  selectMonth(monthKey: string): void {
    this.selectedMonth = monthKey;
    this.loadStocks(monthKey);
  }

  ngOnInit(): void {
    this.loadAvailableMonths();
  }

  loadAvailableMonths(): void {
    console.log(`[STRATEGY] loadAvailableMonths called with strategy: ${this.selectedStrategy}`);
    this.clubeDoValorService.getHistory(this.selectedStrategy).subscribe({
      next: (response) => {
        const monthSet = new Set<string>();
        const monthMap = new Map<string, string>();

        // Extract unique months from snapshots
        response.snapshots.forEach(snapshot => {
          const date = new Date(snapshot.timestamp);
          const year = date.getFullYear();
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const monthKey = `${year}-${month}`;
          
          if (!monthSet.has(monthKey)) {
            monthSet.add(monthKey);
            // Format as "Novembro/2025" instead of "novembro de 2025"
            const monthName = date.toLocaleDateString('pt-BR', { month: 'long' });
            const year = date.getFullYear();
            const monthLabel = `${monthName.charAt(0).toUpperCase() + monthName.slice(1)}/${year}`;
            monthMap.set(monthKey, monthLabel);
          }
        });

        // Convert to array and sort by key (newest first)
        this.availableMonths = Array.from(monthMap.entries())
          .map(([key, label]) => ({ key, label }))
          .sort((a, b) => b.key.localeCompare(a.key));

        // Initialize with most recent month or current month
        if (this.availableMonths.length > 0) {
          this.selectedMonth = this.availableMonths[0].key;
          this.loadStocks(this.selectedMonth);
        } else {
          // Fallback to current month if no history
          const now = new Date();
          const year = now.getFullYear();
          const month = String(now.getMonth() + 1).padStart(2, '0');
          this.selectedMonth = `${year}-${month}`;
          this.loadStocks();
        }
      },
      error: (error) => {
        console.error('Error loading available months:', error);
        // Fallback to current month
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        this.selectedMonth = `${year}-${month}`;
        this.loadStocks();
      }
    });
  }

  ngAfterViewInit(): void {
    this.logLayoutDebug('afterViewInit');
  }

  loadStocks(monthKey?: string): void {
    console.log(`[STRATEGY] loadStocks called with strategy: ${this.selectedStrategy}, monthKey: ${monthKey}`);
    this.loading = true;
    this.error = null;

    if (monthKey) {
      // Load from history for specific month
      this.clubeDoValorService.getHistory(this.selectedStrategy).subscribe({
        next: (response) => {
          console.log(`[STRATEGY] getHistory response for ${this.selectedStrategy}:`, response);
          console.log(`[STRATEGY] Total snapshots: ${response.snapshots?.length || 0}`);
          // Find snapshot for the selected month
          const targetSnapshot = response.snapshots.find(snapshot => {
            const date = new Date(snapshot.timestamp);
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const snapshotMonthKey = `${year}-${month}`;
            return snapshotMonthKey === monthKey;
          });

          if (targetSnapshot) {
            console.log(`[STRATEGY] Found snapshot for ${this.selectedStrategy}:`, targetSnapshot);
            console.log(`[STRATEGY] Snapshot stocks count: ${targetSnapshot.data?.length || 0}`);
            this.stocks = targetSnapshot.data;
            this.timestamp = targetSnapshot.timestamp;
            // Debug: log first stock to verify data structure
            if (this.stocks.length > 0) {
              const firstStock: any = this.stocks[0];
              console.log(`[STRATEGY] First stock for ${this.selectedStrategy} (from history):`, firstStock);
              console.log(`[STRATEGY] First stock keys:`, Object.keys(firstStock));
              if (this.selectedStrategy === 'MDIV') {
                console.log('MDIV - dividendYield36m:', firstStock['dividendYield36m']);
                console.log('MDIV - liquidezMedia3m:', firstStock['liquidezMedia3m']);
              }
            }
            this.applyFilters();
          } else {
            // If no snapshot found for the month, try to load current stocks as fallback
            console.warn(`No snapshot found for month ${monthKey}, falling back to current stocks`);
            this.clubeDoValorService.getCurrentStocks(this.selectedStrategy).subscribe({
              next: (currentResponse) => {
                this.stocks = currentResponse.stocks;
                this.timestamp = currentResponse.timestamp;
                // Debug: log first stock to verify data structure
                if (this.stocks.length > 0 && this.selectedStrategy === 'MDIV') {
                  console.log('MDIV First stock (fallback):', this.stocks[0]);
                }
                this.applyFilters();
                this.loading = false;
              },
              error: (error) => {
                console.error('Error loading current stocks:', error);
                this.stocks = [];
                this.timestamp = '';
                this.filteredStocks = [];
                this.loading = false;
              }
            });
            return; // Exit early, loading will be set to false in the subscribe
          }
          this.loading = false;
          this.logLayoutDebug('loadStocks from history success');
        },
        error: (error) => {
          this.error = 'Erro ao carregar dados. Verifique se o servidor está rodando.';
          console.error('Error loading stocks from history:', error);
          this.loading = false;
        }
      });
    } else {
      // Load current stocks (fallback)
      console.log(`[STRATEGY] Loading current stocks with strategy: ${this.selectedStrategy}`);
      this.clubeDoValorService.getCurrentStocks(this.selectedStrategy).subscribe({
        next: (response) => {
          console.log(`[STRATEGY] Received response for strategy: ${this.selectedStrategy}, stocks count: ${response.stocks?.length || 0}`);
          this.stocks = response.stocks;
          this.timestamp = response.timestamp;
          // Debug: log first stock to verify data structure
          if (this.stocks.length > 0) {
            const firstStock: any = this.stocks[0];
            console.log(`[STRATEGY] First stock for ${this.selectedStrategy}:`, firstStock);
            console.log(`[STRATEGY] First stock keys:`, Object.keys(firstStock));
            if (this.selectedStrategy === 'MDIV') {
              console.log('MDIV - Has dividendYield36m?', 'dividendYield36m' in firstStock, 'Value:', firstStock['dividendYield36m']);
              console.log('MDIV - Has liquidezMedia3m?', 'liquidezMedia3m' in firstStock, 'Value:', firstStock['liquidezMedia3m']);
            } else if (this.selectedStrategy === 'MOMM' || this.selectedStrategy === 'MOMP') {
              console.log(`${this.selectedStrategy} - Has momentum6m?`, 'momentum6m' in firstStock, 'Value:', firstStock['momentum6m']);
              console.log(`${this.selectedStrategy} - Has idRatio?`, 'idRatio' in firstStock, 'Value:', firstStock['idRatio']);
            }
          }
          this.applyFilters();
          this.loading = false;
          this.logLayoutDebug('loadStocks success');
        },
        error: (error) => {
          this.error = 'Erro ao carregar dados. Verifique se o servidor está rodando.';
          console.error('Error loading stocks:', error);
          this.loading = false;
        }
      });
    }
  }

  refreshFromSheets(): void {
    // Refresh directly using the URL for the selected strategy
    this.loading = true;
    this.error = null;

    this.clubeDoValorService.refreshFromSheets(this.selectedStrategy).subscribe({
      next: (response) => {
        // Reload available months and then load stocks
        this.loadAvailableMonths();
      },
      error: (error) => {
        const errorMsg = error.error?.details || error.error?.error || error.message || 'Erro ao atualizar dados do Google Sheets.';
        this.error = errorMsg;
        console.error('Error refreshing from sheets:', error);
        console.error('Error details:', error.error);
        this.loading = false;
      }
    });
  }

  deleteStock(stock: Stock): void {
    if (!confirm(`Tem certeza que deseja remover ${stock.codigo} - ${stock.nome}?`)) {
      return;
    }

    this.loading = true;
    this.error = null;

    this.clubeDoValorService.deleteStock(stock.codigo, this.selectedStrategy).subscribe({
      next: () => {
        this.loadStocks();
      },
      error: (error) => {
        this.error = error.error?.error || 'Erro ao remover ação.';
        console.error('Error deleting stock:', error);
        this.loading = false;
      }
    });
  }

  applyFilters(): void {
    let filtered = [...this.stocks];
    
    // Debug: log first stock structure for MDIV
    if (filtered.length > 0 && this.selectedStrategy === 'MDIV') {
      console.log('[DEBUG] applyFilters - First stock:', filtered[0]);
      console.log('[DEBUG] Has dividendYield36m?', 'dividendYield36m' in filtered[0]);
      console.log('[DEBUG] dividendYield36m value:', (filtered[0] as any).dividendYield36m);
    }

    // Apply sorting
    if (this.sortField) {
      filtered.sort((a, b) => {
        const aValue = (a as any)[this.sortField];
        const bValue = (b as any)[this.sortField];

        let comparison = 0;
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          comparison = aValue.localeCompare(bValue);
        } else if (typeof aValue === 'number' && typeof bValue === 'number') {
          comparison = aValue - bValue;
        } else if (aValue === undefined || aValue === null) {
          comparison = 1;
        } else if (bValue === undefined || bValue === null) {
          comparison = -1;
        }

        return this.sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    this.filteredStocks = filtered;
    this.logLayoutDebug('applyFilters');
  }

  selectSortField(field: string): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.applyFilters();
  }

  getSortIcon(field: string): string {
    if (this.sortField !== field) {
      return '⇅';
    }
    return this.sortDirection === 'asc' ? '↑' : '↓';
  }

  isAMBB1Stock(stock: Stock): stock is import('../stock.model').AMBB1Stock {
    return 'ebit' in stock && !('valueIdx' in stock) && !('dividendYield36m' in stock);
  }

  isAMBB2Stock(stock: Stock): stock is import('../stock.model').AMBB2Stock {
    return 'valueIdx' in stock || 'cfy' in stock || 'btm' in stock || 'mktcap' in stock;
  }

  isMDIVStock(stock: Stock): stock is import('../stock.model').MDIVStock {
    return 'dividendYield36m' in stock || 'liquidezMedia3m' in stock;
  }

  getStockField(stock: Stock, field: string): number {
    const stockAny: any = stock;
    const value = stockAny[field];
    
    // Debug log for MDIV fields (only first stock to avoid spam)
    if ((field === 'dividendYield36m' || field === 'liquidezMedia3m') && this.filteredStocks[0] === stock) {
      console.log(`[DEBUG] getStockField - Field: ${field}, Stock:`, stockAny);
      console.log(`[DEBUG] Value:`, value, 'Type:', typeof value);
      console.log(`[DEBUG] All keys:`, Object.keys(stockAny));
    }
    
    if (value !== undefined && value !== null && value !== '') {
      const numValue = typeof value === 'number' ? value : parseFloat(String(value));
      if (!isNaN(numValue)) {
        return numValue;
      }
    }
    return 0;
  }
  
  getDividendYield(stock: Stock): number {
    const stockAny: any = stock;
    const value = stockAny['dividendYield36m'] ?? stockAny.dividendYield36m ?? null;
    if (value !== null && value !== undefined && value !== '') {
      const numValue = typeof value === 'number' ? value : parseFloat(String(value));
      if (!isNaN(numValue)) {
        return numValue;
      }
    }
    return 0;
  }
  
  getLiquidezMedia(stock: Stock): number {
    const stockAny: any = stock;
    const value = stockAny['liquidezMedia3m'] ?? stockAny.liquidezMedia3m ?? null;
    if (value !== null && value !== undefined && value !== '') {
      const numValue = typeof value === 'number' ? value : parseFloat(String(value));
      if (!isNaN(numValue)) {
        return numValue;
      }
    }
    return 0;
  }
  
  getStockStringField(stock: Stock, field: string): string {
    const stockAny: any = stock;
    const value = stockAny[field];
    if (value !== undefined && value !== null && value !== '') {
      return String(value);
    }
    return '';
  }

  formatValueIdx(stock: Stock): string {
    const stockAny = stock as any;
    const valueIdx = stockAny['valueIdx'];
    if (valueIdx !== undefined && valueIdx !== null) {
      return valueIdx.toFixed(2);
    }
    return '-';
  }

  formatCurrency(value: number | undefined | null): string {
    if (value === undefined || value === null || value === 0) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  }
  
  formatDecimal(value: number | undefined | null, decimals: number = 2): string {
    if (value === undefined || value === null || isNaN(value)) return '0.00';
    return value.toFixed(decimals);
  }

  formatPercentage(value: number | undefined | null): string {
    if (value === undefined || value === null) return '0,00%';
    return `${value.toFixed(2)}%`;
  }

  formatDate(timestamp: string): string {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      return date.toLocaleDateString('pt-BR');
    } catch {
      return timestamp;
    }
  }

  private logLayoutDebug(source: string): void {
    setTimeout(() => {
      const container = document.querySelector('.table-container') as HTMLElement | null;
      const contentArea = document.querySelector('.content-area') as HTMLElement | null;
      console.log(`[DEBUG] (${source}) table-container bounds`, container?.getBoundingClientRect());
      console.log(`[DEBUG] (${source}) content-area bounds`, contentArea?.getBoundingClientRect());
    }, 0);
  }
}

