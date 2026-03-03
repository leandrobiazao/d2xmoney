import { Component, Input, OnInit, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FixedIncomeService } from './fixed-income.service';
import { FixedIncomePosition } from './fixed-income.models';
import { ConfigurationService, InvestmentType, InvestmentSubType } from '../configuration/configuration.service';
import { PortfolioService } from '../portfolio/portfolio.service';

@Component({
  selector: 'app-fixed-income-detail',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './fixed-income-detail.component.html',
  styleUrl: './fixed-income-detail.component.css'
})
export class FixedIncomeDetailComponent implements OnInit, OnChanges {
  @Input() positionId!: number;
  @Input() position?: FixedIncomePosition;
  
  activeTab: 'evolucao' | 'rendimento' = 'evolucao';
  isLoading = false;
  errorMessage: string | null = null;
  isEditingAppliedValue = false;
  editedAppliedValue: number = 0;
  isSaving = false;
  
  /** Current market price fetched from API (e.g. Google Finance) when position has a ticker. */
  currentPrice: number | null = null;
  currentPriceLoading = false;
  
  // Investment type and subtype configuration
  investmentTypes: InvestmentType[] = [];
  investmentSubTypes: InvestmentSubType[] = [];
  selectedInvestmentTypeId: number | null = null;
  selectedInvestmentSubTypeId: number | null = null;
  isSavingInvestmentConfig = false;

  constructor(
    private fixedIncomeService: FixedIncomeService,
    private configurationService: ConfigurationService,
    private portfolioService: PortfolioService
  ) {}

  ngOnInit(): void {
    if (this.positionId && !this.position) {
      this.loadPosition();
    } else if (this.position) {
      this.initializeInvestmentConfig();
      this.fetchCurrentPriceIfTicker();
    }
    this.loadInvestmentTypes();
    this.loadInvestmentSubTypes();
  }
  
  ngOnChanges(): void {
    if (this.position) {
      this.initializeInvestmentConfig();
      this.fetchCurrentPriceIfTicker();
    }
  }
  
  /** Returns true if this position has a ticker we can fetch price for (e.g. ETF like AUPO11). */
  private isTickerPosition(): boolean {
    if (!this.position?.asset_code) return false;
    const code = this.position.asset_code.trim().toUpperCase();
    if (code.length < 4 || code.length > 10) return false;
    // B3 tickers are typically 4–6 alphanumeric (e.g. PETR4, AUPO11)
    return /^[A-Z0-9]+$/.test(code);
  }
  
  /** Fetch current market price when position has a ticker (ETF Renda Fixa, etc.). */
  private fetchCurrentPriceIfTicker(): void {
    this.currentPrice = null;
    if (!this.isTickerPosition()) return;
    const ticker = this.position!.asset_code.trim().toUpperCase();
    this.currentPriceLoading = true;
    this.portfolioService.fetchCurrentPrices([ticker], 'B3').subscribe({
      next: (priceMap) => {
        const price = priceMap.get(ticker);
        this.currentPrice = price != null && price > 0 ? price : null;
        this.currentPriceLoading = false;
      },
      error: () => {
        this.currentPriceLoading = false;
      }
    });
  }
  
  /** Display price: current API price if available, else position.price. */
  getDisplayPrice(): number | undefined | null {
    if (this.currentPrice != null && this.currentPrice > 0) return this.currentPrice;
    return this.position?.price;
  }

  /** Posição to show: when we have current price (e.g. ETF), quantity × price; else position.position_value. */
  getDisplayPositionValue(): number {
    if (!this.position) return 0;
    if (this.currentPrice != null && this.currentPrice > 0) {
      const qty = typeof this.position.quantity === 'number' ? this.position.quantity : parseInt(String(this.position.quantity), 10) || 0;
      return qty * this.currentPrice;
    }
    const v = this.position.position_value;
    return typeof v === 'string' ? parseFloat(v) || 0 : (v ?? 0);
  }

  /** Valor líquido to show: when we have current price (e.g. ETF), quantity × price; else position.net_value. */
  getDisplayNetValue(): number {
    if (!this.position) return 0;
    if (this.currentPrice != null && this.currentPrice > 0) {
      const qty = typeof this.position.quantity === 'number' ? this.position.quantity : parseInt(String(this.position.quantity), 10) || 0;
      return qty * this.currentPrice;
    }
    const v = this.position.net_value;
    return typeof v === 'string' ? parseFloat(v) || 0 : (v ?? 0);
  }

  initializeInvestmentConfig(): void {
    if (this.position) {
      this.selectedInvestmentTypeId = this.position.investment_type || null;
      this.selectedInvestmentSubTypeId = this.position.investment_sub_type || null;
    }
  }
  
  loadInvestmentTypes(): void {
    this.configurationService.getInvestmentTypes(true).subscribe({
      next: (types) => {
        this.investmentTypes = types.filter(t => t.is_active).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
      },
      error: (error) => {
        console.error('Error loading investment types:', error);
      }
    });
  }
  
  loadInvestmentSubTypes(): void {
    this.configurationService.getInvestmentSubTypes(undefined, true).subscribe({
      next: (subTypes) => {
        this.investmentSubTypes = subTypes.filter(s => s.is_active).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
      },
      error: (error) => {
        console.error('Error loading investment subtypes:', error);
      }
    });
  }
  
  getSubTypesForInvestmentType(investmentTypeId: number | null): InvestmentSubType[] {
    if (!investmentTypeId) return [];
    return this.investmentSubTypes.filter(s => s.investment_type === investmentTypeId);
  }
  
  onInvestmentTypeChange(typeId: number | null): void {
    this.selectedInvestmentTypeId = typeId;
    // Clear subtype if it doesn't belong to the new type
    if (typeId && this.selectedInvestmentSubTypeId) {
      const availableSubTypes = this.getSubTypesForInvestmentType(typeId);
      if (!availableSubTypes.find(s => s.id === this.selectedInvestmentSubTypeId)) {
        this.selectedInvestmentSubTypeId = null;
      }
    } else if (!typeId) {
      this.selectedInvestmentSubTypeId = null;
    }
    this.saveInvestmentConfig();
  }
  
  onInvestmentSubTypeChange(subTypeId: number | null): void {
    this.selectedInvestmentSubTypeId = subTypeId;
    this.saveInvestmentConfig();
  }
  
  saveInvestmentConfig(): void {
    if (!this.position || this.isSavingInvestmentConfig) return;
    
    this.isSavingInvestmentConfig = true;
    
    const updateData: any = {};
    if (this.selectedInvestmentTypeId !== null) {
      updateData.investment_type_id = this.selectedInvestmentTypeId;
    }
    if (this.selectedInvestmentSubTypeId !== null) {
      updateData.investment_sub_type_id = this.selectedInvestmentSubTypeId;
    }
    
    this.fixedIncomeService.updatePosition(this.position.id, updateData).subscribe({
      next: (updatedPosition) => {
        this.position = updatedPosition;
        this.isSavingInvestmentConfig = false;
      },
      error: (error) => {
        console.error('Error updating investment config:', error);
        alert('Erro ao atualizar tipo/subtipo de investimento: ' + (error.error?.detail || error.message || 'Erro desconhecido'));
        this.isSavingInvestmentConfig = false;
        // Revert to original values on error
        this.initializeInvestmentConfig();
      }
    });
  }

  loadPosition(): void {
    if (!this.positionId) return;
    
    this.isLoading = true;
    this.fixedIncomeService.getPositionById(this.positionId).subscribe({
      next: (position) => {
        this.position = position;
        this.initializeInvestmentConfig();
        this.fetchCurrentPriceIfTicker();
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar detalhes de Renda Fixa';
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
    const appliedValue = typeof this.position.applied_value === 'string' ? parseFloat(this.position.applied_value) || 0 : (this.position.applied_value ?? 0);
    return this.getDisplayPositionValue() - appliedValue;
  }

  calculateNetYield(): number {
    if (!this.position) return 0;
    const appliedValue = typeof this.position.applied_value === 'string' ? parseFloat(this.position.applied_value) || 0 : (this.position.applied_value ?? 0);
    return this.getDisplayNetValue() - appliedValue;
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

