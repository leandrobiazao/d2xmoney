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
  sortField: keyof Stock | '' = '';
  sortDirection: 'asc' | 'desc' = 'asc';

  // URL Dialog
  showUrlDialog: boolean = false;
  sheetsUrl: string = '';

  // Month Selection
  selectedMonth: string = '';
  availableMonths: Array<{key: string, label: string}> = [];

  constructor(private clubeDoValorService: ClubeDoValorService) {}

  getMonths(): Array<{key: string, label: string}> {
    return this.availableMonths;
  }

  selectMonth(monthKey: string): void {
    this.selectedMonth = monthKey;
    this.loadStocks(monthKey);
  }

  ngOnInit(): void {
    this.loadAvailableMonths();
  }

  loadAvailableMonths(): void {
    this.clubeDoValorService.getHistory().subscribe({
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
            const monthLabel = date.toLocaleDateString('pt-BR', { year: 'numeric', month: 'long' });
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
    this.loading = true;
    this.error = null;

    if (monthKey) {
      // Load from history for specific month
      this.clubeDoValorService.getHistory().subscribe({
        next: (response) => {
          // Find snapshot for the selected month
          const targetSnapshot = response.snapshots.find(snapshot => {
            const date = new Date(snapshot.timestamp);
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const snapshotMonthKey = `${year}-${month}`;
            return snapshotMonthKey === monthKey;
          });

          if (targetSnapshot) {
            this.stocks = targetSnapshot.data;
            this.timestamp = targetSnapshot.timestamp;
            this.applyFilters();
          } else {
            // If no snapshot found for the month, try to load current stocks as fallback
            console.warn(`No snapshot found for month ${monthKey}, falling back to current stocks`);
            this.clubeDoValorService.getCurrentStocks().subscribe({
              next: (currentResponse) => {
                this.stocks = currentResponse.stocks;
                this.timestamp = currentResponse.timestamp;
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
      this.clubeDoValorService.getCurrentStocks().subscribe({
        next: (response) => {
          this.stocks = response.stocks;
          this.timestamp = response.timestamp;
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
    // Show dialog to get URL
    this.showUrlDialog = true;
    this.sheetsUrl = '';
  }

  onUrlDialogCancel(): void {
    this.showUrlDialog = false;
    this.sheetsUrl = '';
  }

  onUrlDialogConfirm(): void {
    if (!this.sheetsUrl || !this.sheetsUrl.trim()) {
      this.error = 'Por favor, informe a URL do Google Sheets.';
      return;
    }

    this.showUrlDialog = false;
    this.loading = true;
    this.error = null;

    this.clubeDoValorService.refreshFromSheets(this.sheetsUrl.trim()).subscribe({
      next: (response) => {
        // Reload available months and then load stocks
        this.loadAvailableMonths();
        this.sheetsUrl = ''; // Clear URL after successful refresh
      },
      error: (error) => {
        this.error = error.error?.details || error.error?.error || 'Erro ao atualizar dados do Google Sheets.';
        console.error('Error refreshing from sheets:', error);
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

    this.clubeDoValorService.deleteStock(stock.codigo).subscribe({
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

    // Apply sorting
    if (this.sortField) {
      filtered.sort((a, b) => {
        const aValue = a[this.sortField as keyof Stock];
        const bValue = b[this.sortField as keyof Stock];

        let comparison = 0;
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          comparison = aValue.localeCompare(bValue);
        } else if (typeof aValue === 'number' && typeof bValue === 'number') {
          comparison = aValue - bValue;
        }

        return this.sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    this.filteredStocks = filtered;
    this.logLayoutDebug('applyFilters');
  }

  selectSortField(field: keyof Stock): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.applyFilters();
  }

  getSortIcon(field: keyof Stock): string {
    if (this.sortField !== field) {
      return '⇅';
    }
    return this.sortDirection === 'asc' ? '↑' : '↓';
  }

  formatCurrency(value: number): string {
    if (value === 0) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  }

  formatPercentage(value: number): string {
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

