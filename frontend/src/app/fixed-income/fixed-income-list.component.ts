import { Component, Input, OnInit, OnChanges, SimpleChanges, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FixedIncomeService } from './fixed-income.service';
import { FixedIncomePosition, ImportResult } from './fixed-income.models';
import { FixedIncomeDetailComponent } from './fixed-income-detail.component';

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
  groupedPositions: GroupedPositions[] = [];
  filteredPositions: FixedIncomePosition[] = [];
  selectedPosition: FixedIncomePosition | null = null;
  isLoading = false;
  errorMessage: string | null = null;
  
  // Import related properties
  isImporting = false;
  importResult: ImportResult | null = null;
  importErrorMessage: string | null = null;

  constructor(private fixedIncomeService: FixedIncomeService) {}

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
      this.groupedPositions = [];
      this.filteredPositions = [];
      this.selectedPosition = null;
      this.errorMessage = null;
      
      // Load new user's data
      this.loadPositions();
    } else if (changes['userId'] && !this.userId) {
      // Clear data if userId is removed
      this.positions = [];
      this.groupedPositions = [];
      this.filteredPositions = [];
      this.selectedPosition = null;
    }
  }

  loadPositions(): void {
    this.isLoading = true;
    this.fixedIncomeService.getPositions(this.userId).subscribe({
      next: (positions) => {
        this.positions = positions;
        this.groupPositions();
        this.isLoading = false;
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

    // Calculate total portfolio value using position_value
    this.positions.forEach(pos => {
      const positionValue = getPositionValue(pos.position_value);
      totalPortfolioValue += positionValue;
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

    // Sort: Tesouro Direto first, then others by value
    this.groupedPositions = Array.from(groups.values()).sort((a, b) => {
      if (a.isTesouroDireto && !b.isTesouroDireto) return -1;
      if (!a.isTesouroDireto && b.isTesouroDireto) return 1;
      return b.totalValue - a.totalValue;
    });
  }

  getTotalInvestido(): number {
    // Sum all applied_value (Total Aplicado) from all positions
    return this.positions.reduce((sum, pos) => {
      const appliedValue = this.getPositionValue(pos.applied_value);
      return sum + appliedValue;
    }, 0);
  }

  getValorAtual(): number {
    // Sum all position_value (Posição atual) from all positions
    return this.groupedPositions.reduce((sum, group) => sum + group.totalValue, 0);
  }

  getActivePositionsCount(): number {
    // Count positions with position_value > 0 (active positions)
    return this.positions.filter(pos => {
      const positionValue = this.getPositionValue(pos.position_value);
      return positionValue > 0;
    }).length;
  }

  getSubtypePercentage(position: FixedIncomePosition): number {
    // Calculate percentage of this position's value relative to total Valor Atual
    const totalValorAtual = this.getValorAtual();
    if (totalValorAtual === 0) return 0;
    const positionValue = this.getPositionValue(position.position_value);
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

