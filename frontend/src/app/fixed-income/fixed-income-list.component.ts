import { Component, Input, OnInit, OnChanges, SimpleChanges, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { FixedIncomeService } from './fixed-income.service';
import { FixedIncomePosition, ImportResult } from './fixed-income.models';
import { FixedIncomeDetailComponent } from './fixed-income-detail.component';
import { PortfolioService } from '../portfolio/portfolio.service';

interface GroupedPositions {
  type: string;
  typeName: string;
  percentage: number;
  totalValue: number;
  positions: FixedIncomePosition[];
  isTesouroDireto?: boolean;
  subTypeGroups?: SubTypeGroup[];
}

interface SubTypeGroup {
  subTypeName: string;
  percentage: number;
  totalValue: number;
  positions: FixedIncomePosition[];
}

@Component({
  selector: 'app-fixed-income-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    FixedIncomeDetailComponent
  ],
  templateUrl: './fixed-income-list.component.html',
  styleUrl: './fixed-income-list.component.css'
})
export class FixedIncomeListComponent implements OnInit, OnChanges {
  @Input() userId?: string;
  @ViewChild('fileInput') fileInput?: ElementRef<HTMLInputElement>;
  
  positions: FixedIncomePosition[] = [];
  /** ETF Renda Fixa positions (e.g. AUPO11) from portfolio, shown as Renda Fixa options. */
  etfRendaFixaPositions: FixedIncomePosition[] = [];
  /** Current prices for ETF tickers (asset_code -> price) used to compute Valor Líquido / Posição. */
  etfCurrentPrices = new Map<string, number>();
  groupedPositions: GroupedPositions[] = [];
  filteredPositions: FixedIncomePosition[] = [];
  selectedPosition: FixedIncomePosition | null = null;
  isLoading = false;
  errorMessage: string | null = null;
  
  // Import related properties
  isImporting = false;
  importResult: ImportResult | null = null;
  importErrorMessage: string | null = null;

  constructor(
    private fixedIncomeService: FixedIncomeService,
    private portfolioService: PortfolioService
  ) {}

  ngOnInit(): void {
    if (this.userId) {
      this.loadPositions();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Reload positions when userId changes
    if (changes['userId'] && this.userId) {
      // Clear previous data immediately
      this.positions = [];
      this.etfRendaFixaPositions = [];
      this.etfCurrentPrices.clear();
      this.groupedPositions = [];
      this.filteredPositions = [];
      this.selectedPosition = null;
      this.errorMessage = null;
      
      // Load new user's data
      this.loadPositions();
    } else if (changes['userId'] && !this.userId) {
      // Clear data if userId is removed
      this.positions = [];
      this.etfRendaFixaPositions = [];
      this.etfCurrentPrices.clear();
      this.groupedPositions = [];
      this.filteredPositions = [];
      this.selectedPosition = null;
    }
  }

  loadPositions(): void {
    if (!this.userId) {
      this.isLoading = false;
      return;
    }
    this.isLoading = true;
    forkJoin({
      positions: this.fixedIncomeService.getPositions(this.userId),
      etfRendaFixa: this.fixedIncomeService.getEtfRendaFixaPositions(this.userId)
    }).subscribe({
      next: ({ positions, etfRendaFixa }) => {
        this.positions = positions;
        this.etfRendaFixaPositions = etfRendaFixa || [];
        this.groupPositions();
        this.isLoading = false;
        this.fetchEtfCurrentPrices();
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar posições de Renda Fixa';
        this.isLoading = false;
      }
    });
  }

  groupPositions(): void {
    const groups: Map<string, GroupedPositions> = new Map();
    let totalPortfolioValue = 0;

    // Helper function to safely convert position_value to number
    const getPositionValue = (value: any): number => {
      if (value == null) return 0;
      // Handle both string and number types (Django DecimalField serializes as string)
      const numValue = typeof value === 'string' ? parseFloat(value) : value;
      return (typeof numValue === 'number' && !isNaN(numValue)) ? numValue : 0;
    };

    // Helper function to safely convert net_value to number
    const getNetValue = (value: any): number => {
      if (value == null) return 0;
      // Handle both string and number types (Django DecimalField serializes as string)
      const numValue = typeof value === 'string' ? parseFloat(value) : value;
      return (typeof numValue === 'number' && !isNaN(numValue)) ? numValue : 0;
    };

    // Separate Tesouro Direto from other fixed income
    const tesouroPositions: FixedIncomePosition[] = [];
    const otherPositions: FixedIncomePosition[] = [];

    this.positions.forEach(pos => {
      if (pos.investment_type_name === 'Tesouro Direto') {
        tesouroPositions.push(pos);
      } else {
        otherPositions.push(pos);
      }
    });

    // Calculate total portfolio value using position_value (fixed income + ETF Renda Fixa)
    this.positions.forEach(pos => {
      const positionValue = getPositionValue(pos.position_value);
      totalPortfolioValue += positionValue;
    });
    this.etfRendaFixaPositions.forEach(pos => {
      totalPortfolioValue += getPositionValue(pos.position_value);
    });

    // Group non-Tesouro positions by investment type
    otherPositions.forEach(pos => {
      const typeName = pos.investment_type_name || 'Outros';
      const typeCode = pos.investment_type_name || 'outros';
      
      if (!groups.has(typeCode)) {
        groups.set(typeCode, {
          type: typeCode,
          typeName: typeName,
          percentage: 0,
          totalValue: 0,
          positions: [],
          isTesouroDireto: false
        });
      }

      const group = groups.get(typeCode)!;
      group.positions.push(pos);
      const positionValue = getPositionValue(pos.position_value);
      group.totalValue += positionValue;
    });

    // Group Tesouro Direto by sub-type
    if (tesouroPositions.length > 0) {
      const tesouroSubTypes: Map<string, SubTypeGroup> = new Map();
      let tesouroTotalValue = 0;

      tesouroPositions.forEach(pos => {
        const subTypeName = pos.investment_sub_type_name || 'Outros';
        const positionValue = getPositionValue(pos.position_value);
        tesouroTotalValue += positionValue;

        if (!tesouroSubTypes.has(subTypeName)) {
          tesouroSubTypes.set(subTypeName, {
            subTypeName: subTypeName,
            percentage: 0,
            totalValue: 0,
            positions: []
          });
        }

        const subTypeGroup = tesouroSubTypes.get(subTypeName)!;
        subTypeGroup.positions.push(pos);
        subTypeGroup.totalValue += positionValue;
      });

      // Calculate percentages for sub-types and sort positions by net_value
      tesouroSubTypes.forEach(subTypeGroup => {
        subTypeGroup.percentage = tesouroTotalValue > 0
          ? (subTypeGroup.totalValue / tesouroTotalValue) * 100
          : 0;
        // Sort positions by net_value descending (higher to lower)
        subTypeGroup.positions.sort((a, b) => {
          const netValueA = getNetValue(a.net_value);
          const netValueB = getNetValue(b.net_value);
          return netValueB - netValueA;
        });
      });

      // Create Tesouro Direto group with sub-type groups
      const tesouroGroup: GroupedPositions = {
        type: 'tesouro_direto',
        typeName: 'Tesouro Direto',
        percentage: totalPortfolioValue > 0
          ? (tesouroTotalValue / totalPortfolioValue) * 100
          : 0,
        totalValue: tesouroTotalValue,
        positions: tesouroPositions,
        isTesouroDireto: true,
        subTypeGroups: Array.from(tesouroSubTypes.values()).sort((a, b) => 
          b.totalValue - a.totalValue
        )
      };

      groups.set('tesouro_direto', tesouroGroup);
    }

    // ETF Renda Fixa group (e.g. AUPO11) - always show so it appears as a Renda Fixa option
    const etfRendaFixaTotalValue = this.etfRendaFixaPositions.reduce(
      (sum, pos) => sum + getPositionValue(pos.position_value),
      0
    );
    const etfRendaFixaGroup: GroupedPositions = {
      type: 'etf_renda_fixa',
      typeName: 'ETF Renda Fixa',
      percentage: totalPortfolioValue > 0 ? (etfRendaFixaTotalValue / totalPortfolioValue) * 100 : 0,
      totalValue: etfRendaFixaTotalValue,
      positions: [...this.etfRendaFixaPositions].sort((a, b) =>
        getNetValue(b.net_value) - getNetValue(a.net_value)
      ),
      isTesouroDireto: false
    };
    groups.set('etf_renda_fixa', etfRendaFixaGroup);

    // Calculate percentages based on position_value totals and sort positions by net_value
    groups.forEach(group => {
      if (!group.isTesouroDireto) {
        group.percentage = totalPortfolioValue > 0 
          ? (group.totalValue / totalPortfolioValue) * 100 
          : 0;
        // Sort positions by net_value descending (higher to lower)
        group.positions.sort((a, b) => {
          const netValueA = getNetValue(a.net_value);
          const netValueB = getNetValue(b.net_value);
          return netValueB - netValueA;
        });
      }
    });

    // Sort: Tesouro Direto first, then ETF Renda Fixa (so AUPO11 etc. always visible), then others by value
    this.groupedPositions = Array.from(groups.values()).sort((a, b) => {
      if (a.isTesouroDireto && !b.isTesouroDireto) return -1;
      if (!a.isTesouroDireto && b.isTesouroDireto) return 1;
      if (a.type === 'etf_renda_fixa' && b.type !== 'etf_renda_fixa') return -1;
      if (a.type !== 'etf_renda_fixa' && b.type === 'etf_renda_fixa') return 1;
      return b.totalValue - a.totalValue;
    });
  }

  getTotalInvestido(): number {
    // Sum all applied_value (fixed income + ETF Renda Fixa)
    const fromPositions = this.positions.reduce((sum, pos) => {
      const appliedValue = this.getPositionValue(pos.applied_value);
      return sum + appliedValue;
    }, 0);
    const fromEtf = this.etfRendaFixaPositions.reduce((sum, pos) => {
      return sum + this.getPositionValue(pos.applied_value);
    }, 0);
    return fromPositions + fromEtf;
  }

  /** Fetch current prices for ETF Renda Fixa tickers so Posição / Valor Líquido can differ from Valor Aplicado. */
  private fetchEtfCurrentPrices(): void {
    if (this.etfRendaFixaPositions.length === 0) return;
    const tickers = [...new Set(this.etfRendaFixaPositions.map(p => (p.asset_code || '').trim().toUpperCase()).filter(Boolean))];
    if (tickers.length === 0) return;
    this.portfolioService.fetchCurrentPrices(tickers, 'B3').subscribe({
      next: (priceMap) => {
        this.etfCurrentPrices.clear();
        priceMap.forEach((price, ticker) => {
          if (price > 0) this.etfCurrentPrices.set(ticker, price);
        });
      }
    });
  }

  /** True if position is ETF Renda Fixa (from portfolio) and we can use current price for display. */
  private isEtfRendaFixaPosition(position: FixedIncomePosition): boolean {
    return position.source === 'portfolio' || position.investment_sub_type_name === 'ETF Renda Fixa';
  }

  /** Posição to show: for ETF with current price = quantity × price; else position.position_value. */
  getDisplayPositionValue(position: FixedIncomePosition): number {
    if (!this.isEtfRendaFixaPosition(position) || !position.asset_code) return this.getPositionValue(position.position_value);
    const price = this.etfCurrentPrices.get((position.asset_code || '').trim().toUpperCase());
    if (price == null || price <= 0) return this.getPositionValue(position.position_value);
    const qty = typeof position.quantity === 'number' ? position.quantity : parseInt(String(position.quantity), 10) || 0;
    return qty * price;
  }

  /** Valor Líquido to show: for ETF with current price = quantity × price; else position.net_value. */
  getDisplayNetValue(position: FixedIncomePosition): number {
    if (!this.isEtfRendaFixaPosition(position) || !position.asset_code) return this.getPositionValue(position.net_value);
    const price = this.etfCurrentPrices.get((position.asset_code || '').trim().toUpperCase());
    if (price == null || price <= 0) return this.getPositionValue(position.net_value);
    const qty = typeof position.quantity === 'number' ? position.quantity : parseInt(String(position.quantity), 10) || 0;
    return qty * price;
  }

  getValorAtual(): number {
    return this.groupedPositions.reduce((sum, group) => {
      if (group.type === 'etf_renda_fixa' && this.etfCurrentPrices.size > 0) {
        return sum + group.positions.reduce((s, p) => s + this.getDisplayPositionValue(p), 0);
      }
      return sum + group.totalValue;
    }, 0);
  }

  getActivePositionsCount(): number {
    const fromPositions = this.positions.filter(pos => {
      const positionValue = this.getPositionValue(pos.position_value);
      return positionValue > 0;
    }).length;
    const fromEtf = this.etfRendaFixaPositions.filter(pos => {
      return this.getPositionValue(pos.position_value) > 0;
    }).length;
    return fromPositions + fromEtf;
  }

  getSubtypePercentage(position: FixedIncomePosition): number {
    const totalValorAtual = this.getValorAtual();
    if (totalValorAtual === 0) return 0;
    const positionValue = this.getDisplayPositionValue(position);
    return (positionValue / totalValorAtual) * 100;
  }

  getSubtypeName(position: FixedIncomePosition): string {
    // Get investment subtype name, fallback to type name if subtype not available
    return position.investment_sub_type_name || position.investment_type_name || 'Outros';
  }

  selectPosition(position: FixedIncomePosition): void {
    // Make a copy to ensure change detection works
    this.selectedPosition = { ...position };
    console.log('Selected position:', {
      asset_name: position.asset_name,
      investment_type_name: position.investment_type_name,
      investment_sub_type_name: position.investment_sub_type_name
    });
  }

  closeDetail(): void {
    this.selectedPosition = null;
  }

  formatCurrency(value: number | undefined | null): string {
    if (value === undefined || value === null || isNaN(value)) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  }

  formatDate(date: string | undefined): string {
    if (!date) return '-';
    try {
      const d = new Date(date);
      return d.toLocaleDateString('pt-BR');
    } catch {
      return date;
    }
  }

  formatPercentage(value: number): string {
    return `${value.toFixed(2)}%`;
  }

  getPositionValue(value: any): number {
    if (value == null) return 0;
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    return (typeof numValue === 'number' && !isNaN(numValue)) ? numValue : 0;
  }

  isCaixaPosition(position: FixedIncomePosition): boolean {
    // Check if position is CAIXA by asset_code or asset_name
    return position.asset_code?.startsWith('CAIXA_') || 
           position.asset_name?.toLowerCase().includes('caixa') ||
           position.asset_name?.toLowerCase().includes('xp investimentos');
  }

  onImportClick(): void {
    if (this.fileInput) {
      this.fileInput.nativeElement.click();
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0 && this.userId) {
      const file = input.files[0];
      this.importExcel(file);
      // Reset input so same file can be selected again
      input.value = '';
    }
  }

  importExcel(file: File): void {
    if (!this.userId) {
      this.importErrorMessage = 'Usuário não selecionado.';
      return;
    }

    this.isImporting = true;
    this.importErrorMessage = null;
    this.importResult = null;

    this.fixedIncomeService.importExcel(file, this.userId).subscribe({
      next: (result) => {
        this.importResult = result;
        this.isImporting = false;
        
        // Check if there are errors in the result
        if (result.errors && result.errors.length > 0) {
          const errorText = result.errors.join('\n');
          let debugInfo = '';
          if (result.debug_info && result.debug_info.length > 0) {
            debugInfo = '\n\nInformações de debug:\n' + result.debug_info.join('\n');
          }
          this.importErrorMessage = `Erros durante a importação:\n${errorText}${debugInfo}`;
        } else if (result.created === 0 && result.updated === 0) {
          let debugInfo = '';
          if (result.debug_info && result.debug_info.length > 0) {
            debugInfo = '\n\nInformações de debug:\n' + result.debug_info.join('\n');
          }
          this.importErrorMessage = 'Nenhum registro foi importado. Verifique se o arquivo contém dados válidos nas seções "RENDA FIXA" ou "TESOURO DIRETO".' + debugInfo;
        } else {
          // Success - refresh positions
          this.loadPositions();
          // Clear success message after 5 seconds
          setTimeout(() => {
            this.importResult = null;
          }, 5000);
        }
      },
      error: (error) => {
        console.error('Import error:', error);
        const errorMsg = error.error?.error || error.error?.details || error.message || 'Erro ao importar arquivo Excel.';
        this.importErrorMessage = `Erro ao importar arquivo: ${errorMsg}`;
        this.isImporting = false;
        // Clear error message after 5 seconds
        setTimeout(() => {
          this.importErrorMessage = null;
        }, 5000);
      }
    });
  }

  dismissImportMessage(): void {
    this.importResult = null;
    this.importErrorMessage = null;
  }
}

