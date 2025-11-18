import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FixedIncomeService } from './fixed-income.service';
import { FixedIncomePosition } from './fixed-income.models';
import { CdbDetailComponent } from './cdb-detail.component';

interface GroupedPositions {
  type: string;
  typeName: string;
  percentage: number;
  totalValue: number;
  positions: FixedIncomePosition[];
}

@Component({
  selector: 'app-fixed-income-list',
  standalone: true,
  imports: [CommonModule, FormsModule, CdbDetailComponent],
  templateUrl: './fixed-income-list.component.html',
  styleUrl: './fixed-income-list.component.css'
})
export class FixedIncomeListComponent implements OnInit {
  @Input() userId?: string;
  
  positions: FixedIncomePosition[] = [];
  groupedPositions: GroupedPositions[] = [];
  filteredPositions: FixedIncomePosition[] = [];
  selectedPosition: FixedIncomePosition | null = null;
  isLoading = false;
  errorMessage: string | null = null;
  
  filterType: string = 'all';
  searchTerm: string = '';

  constructor(private fixedIncomeService: FixedIncomeService) {}

  ngOnInit(): void {
    if (this.userId) {
      this.loadPositions();
    }
  }

  loadPositions(): void {
    this.isLoading = true;
    this.fixedIncomeService.getPositions(this.userId).subscribe({
      next: (positions) => {
        this.positions = positions;
        this.groupPositions();
        this.applyFilters();
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

    // Calculate total portfolio value using position_value
    this.positions.forEach(pos => {
      const positionValue = getPositionValue(pos.position_value);
      totalPortfolioValue += positionValue;
    });

    // Group by investment type
    this.positions.forEach(pos => {
      const typeName = pos.investment_type_name || 'Outros';
      const typeCode = pos.investment_type_name || 'outros';
      
      if (!groups.has(typeCode)) {
        groups.set(typeCode, {
          type: typeCode,
          typeName: typeName,
          percentage: 0,
          totalValue: 0,
          positions: []
        });
      }

      const group = groups.get(typeCode)!;
      group.positions.push(pos);
      // Sum position_value instead of net_value
      const positionValue = getPositionValue(pos.position_value);
      group.totalValue += positionValue;
    });

    // Calculate percentages based on position_value totals
    groups.forEach(group => {
      group.percentage = totalPortfolioValue > 0 
        ? (group.totalValue / totalPortfolioValue) * 100 
        : 0;
    });

    this.groupedPositions = Array.from(groups.values()).sort((a, b) => 
      b.totalValue - a.totalValue
    );
  }

  applyFilters(): void {
    let filtered = [...this.positions];

    // Filter by type
    if (this.filterType !== 'all') {
      filtered = filtered.filter(pos => 
        pos.investment_type_name?.toLowerCase() === this.filterType.toLowerCase()
      );
    }

    // Filter by search term
    if (this.searchTerm) {
      const term = this.searchTerm.toLowerCase();
      filtered = filtered.filter(pos =>
        pos.asset_name.toLowerCase().includes(term) ||
        pos.asset_code.toLowerCase().includes(term)
      );
    }

    this.filteredPositions = filtered;
  }

  onFilterChange(): void {
    this.applyFilters();
  }

  onSearchChange(): void {
    this.applyFilters();
  }

  selectPosition(position: FixedIncomePosition): void {
    this.selectedPosition = position;
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
}

