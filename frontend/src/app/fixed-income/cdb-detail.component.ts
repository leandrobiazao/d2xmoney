import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FixedIncomeService } from './fixed-income.service';
import { FixedIncomePosition } from './fixed-income.models';

@Component({
  selector: 'app-cdb-detail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cdb-detail.component.html',
  styleUrl: './cdb-detail.component.css'
})
export class CdbDetailComponent implements OnInit {
  @Input() positionId!: number;
  @Input() position?: FixedIncomePosition;
  
  activeTab: 'evolucao' | 'rendimento' = 'evolucao';
  isLoading = false;
  errorMessage: string | null = null;
  isEditingAppliedValue = false;
  editedAppliedValue: number = 0;
  isSaving = false;

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

  startEditingAppliedValue(): void {
    if (!this.position) return;
    this.isEditingAppliedValue = true;
    this.editedAppliedValue = this.position.applied_value || 0;
    // Focus the input after a short delay to ensure it's rendered
    setTimeout(() => {
      const input = document.querySelector('.value-input') as HTMLInputElement;
      if (input) {
        input.focus();
        input.select();
      }
    }, 0);
  }

  cancelEditingAppliedValue(): void {
    this.isEditingAppliedValue = false;
    this.editedAppliedValue = 0;
  }

  saveAppliedValue(): void {
    if (!this.position || this.isSaving) return;
    
    // Validate the value
    if (this.editedAppliedValue < 0 || isNaN(this.editedAppliedValue)) {
      alert('Valor inválido');
      return;
    }

    this.isSaving = true;
    
    // Only send applied_value - backend will calculate yields automatically
    const updateData = {
      applied_value: this.editedAppliedValue
    };

    this.fixedIncomeService.updatePosition(this.position.id, updateData).subscribe({
      next: (updatedPosition) => {
        this.position = updatedPosition;
        this.isEditingAppliedValue = false;
        this.isSaving = false;
      },
      error: (error) => {
        console.error('Error updating applied value:', error);
        console.error('Error details:', error.error);
        alert('Erro ao atualizar valor aplicado: ' + (error.error?.detail || error.message || 'Erro desconhecido'));
        this.isSaving = false;
      }
    });
  }

  calculateGrossYield(): number {
    if (!this.position) return 0;
    const appliedValue = this.position.applied_value || 0;
    const positionValue = this.position.position_value || 0;
    return positionValue - appliedValue;
  }

  calculateNetYield(): number {
    if (!this.position) return 0;
    const appliedValue = this.position.applied_value || 0;
    const netValue = this.position.net_value || 0;
    return netValue - appliedValue;
  }

  parseCurrencyInput(value: string): number {
    // Remove currency formatting and parse to number
    const cleaned = value.replace(/[R$\s.]/g, '').replace(',', '.');
    return parseFloat(cleaned) || 0;
  }

  formatCurrencyInput(value: number): string {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  }
}

