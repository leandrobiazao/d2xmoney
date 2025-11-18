import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FixedIncomeService } from './fixed-income.service';
import { FixedIncomePosition } from './fixed-income.models';

@Component({
  selector: 'app-cdb-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './cdb-detail.component.html',
  styleUrl: './cdb-detail.component.css'
})
export class CdbDetailComponent implements OnInit {
  @Input() positionId!: number;
  @Input() position?: FixedIncomePosition;
  
  activeTab: 'evolucao' | 'rendimento' = 'evolucao';
  isLoading = false;
  errorMessage: string | null = null;

  constructor(private fixedIncomeService: FixedIncomeService) {}

  ngOnInit(): void {
    if (this.positionId && !this.position) {
      this.loadPosition();
    }
  }

  loadPosition(): void {
    if (!this.positionId) return;
    
    this.isLoading = true;
    this.fixedIncomeService.getPositionById(this.positionId).subscribe({
      next: (position) => {
        this.position = position;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar detalhes do CDB';
        this.isLoading = false;
      }
    });
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

  setTab(tab: 'evolucao' | 'rendimento'): void {
    this.activeTab = tab;
  }
}

