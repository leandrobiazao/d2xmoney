import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CryptoService } from './crypto.service';
import { CryptoCurrency, CryptoOperation, CryptoPosition } from './crypto.models';
import { ConfigurationService, InvestmentType, InvestmentSubType } from '../configuration/configuration.service';
import { CryptoOperationDialogComponent } from './crypto-operation-dialog/crypto-operation-dialog.component';

@Component({
  selector: 'app-crypto',
  standalone: true,
  imports: [CommonModule, FormsModule, CryptoOperationDialogComponent],
  templateUrl: './crypto.component.html',
  styleUrl: './crypto.component.css'
})
export class CryptoComponent implements OnInit {
  @Input() userId!: string;

  currencies: CryptoCurrency[] = [];
  operations: CryptoOperation[] = [];
  positions: CryptoPosition[] = [];
  investmentTypes: InvestmentType[] = [];
  investmentSubTypes: InvestmentSubType[] = [];
  
  isLoading = false;
  errorMessage: string | null = null;
  
  showCreateCurrencyModal = false;
  showOperationDialog = false;
  editingCurrency: CryptoCurrency | null = null;
  editingOperation: CryptoOperation | null = null;
  
  currencyForm: Partial<CryptoCurrency> = {
    symbol: '',
    name: '',
    investment_type_id: undefined,
    investment_subtype_id: undefined,
    is_active: true
  };

  constructor(
    private cryptoService: CryptoService,
    private configService: ConfigurationService
  ) {}

  ngOnInit(): void {
    this.loadInvestmentTypes();
    this.loadCurrencies();
    if (this.userId) {
      this.loadOperations();
      this.loadPositions();
    }
  }

  loadInvestmentTypes(): void {
    this.configService.getInvestmentTypes(true).subscribe({
      next: (types) => {
        this.investmentTypes = types.filter(t => t.is_active).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
      },
      error: (error) => {
        console.error('Error loading investment types:', error);
      }
    });
    
    this.configService.getInvestmentSubTypes(undefined, true).subscribe({
      next: (subTypes) => {
        this.investmentSubTypes = subTypes.filter(s => s.is_active).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
      },
      error: (error) => {
        console.error('Error loading investment subtypes:', error);
      }
    });
  }

  getSubTypesForType(typeId: number | undefined): InvestmentSubType[] {
    if (!typeId) return [];
    return this.investmentSubTypes.filter(s => s.investment_type === typeId);
  }

  loadCurrencies(): void {
    this.isLoading = true;
    this.errorMessage = null;
    this.cryptoService.getCurrencies(undefined, true).subscribe({
      next: (currencies) => {
        this.currencies = currencies;
        this.isLoading = false;
        this.errorMessage = null;
      },
      error: (error) => {
        this.errorMessage = `Erro ao carregar criptomoedas: ${error.message || error.status || 'Erro desconhecido'}`;
        this.isLoading = false;
        console.error('Error loading currencies:', error);
        console.error('Error details:', error.error);
        console.error('Error status:', error.status);
      }
    });
  }

  loadOperations(): void {
    if (!this.userId) return;
    
    this.cryptoService.getOperations(this.userId).subscribe({
      next: (operations) => {
        this.operations = operations;
      },
      error: (error) => {
        console.error('Error loading operations:', error);
      }
    });
  }

  loadPositions(): void {
    if (!this.userId) return;
    
    this.cryptoService.getPositions(this.userId).subscribe({
      next: (positions) => {
        this.positions = positions;
        // Load current prices for each position
        this.loadCurrentPrices();
      },
      error: (error) => {
        console.error('Error loading positions:', error);
      }
    });
  }

  loadCurrentPrices(): void {
    // Load current prices for each position's crypto currency
    this.positions.forEach((position) => {
      const symbol = position.crypto_currency.symbol;
      this.cryptoService.getCryptoPrice(symbol, 'BRL').subscribe({
        next: (priceData) => {
          position.current_price = priceData.price;
          position.current_value = position.quantity * priceData.price;
        },
        error: (error) => {
          console.error(`Error loading price for ${symbol}:`, error);
          // If price fetch fails, set to undefined so it won't display
          position.current_price = undefined;
          position.current_value = undefined;
        }
      });
    });
  }

  onCreateCurrency(): void {
    this.editingCurrency = null;
    this.currencyForm = {
      symbol: '',
      name: '',
      investment_type_id: undefined,
      investment_subtype_id: undefined,
      is_active: true
    };
    this.showCreateCurrencyModal = true;
  }

  onEditCurrency(currency: CryptoCurrency): void {
    this.editingCurrency = currency;
    this.currencyForm = {
      symbol: currency.symbol,
      name: currency.name,
      investment_type_id: currency.investment_type_id,
      investment_subtype_id: currency.investment_subtype_id,
      is_active: currency.is_active
    };
    this.showCreateCurrencyModal = true;
  }

  onSaveCurrency(): void {
    if (!this.currencyForm.symbol || !this.currencyForm.name) {
      alert('Símbolo e nome são obrigatórios');
      return;
    }

    if (this.editingCurrency) {
      this.cryptoService.updateCurrency(this.editingCurrency.id, this.currencyForm).subscribe({
        next: () => {
          this.loadCurrencies();
          this.showCreateCurrencyModal = false;
        },
        error: (error) => {
          alert('Erro ao atualizar criptomoeda: ' + (error.error?.error || error.message));
        }
      });
    } else {
      this.cryptoService.createCurrency(this.currencyForm).subscribe({
        next: () => {
          this.loadCurrencies();
          this.showCreateCurrencyModal = false;
        },
        error: (error) => {
          alert('Erro ao criar criptomoeda: ' + (error.error?.error || error.message));
        }
      });
    }
  }

  onDeleteCurrency(currency: CryptoCurrency): void {
    if (confirm(`Tem certeza que deseja deletar ${currency.name} (${currency.symbol})?`)) {
      this.cryptoService.deleteCurrency(currency.id).subscribe({
        next: () => {
          this.loadCurrencies();
        },
        error: (error) => {
          alert('Erro ao deletar criptomoeda: ' + (error.error?.error || error.message));
        }
      });
    }
  }

  onCloseCurrencyModal(): void {
    this.showCreateCurrencyModal = false;
    this.editingCurrency = null;
  }

  onCreateOperation(): void {
    this.editingOperation = null;
    this.showOperationDialog = true;
  }

  onEditOperation(operation: CryptoOperation): void {
    this.editingOperation = operation;
    this.showOperationDialog = true;
  }

  onOperationSaved(): void {
    this.showOperationDialog = false;
    this.editingOperation = null;
    this.loadOperations();
    this.loadPositions(); // This will also trigger loadCurrentPrices()
  }

  onOperationCanceled(): void {
    this.showOperationDialog = false;
    this.editingOperation = null;
  }

  onDeleteOperation(operation: CryptoOperation): void {
    if (confirm(`Tem certeza que deseja deletar esta operação?`)) {
      this.cryptoService.deleteOperation(operation.id).subscribe({
        next: () => {
          this.loadOperations();
          this.loadPositions();
        },
        error: (error) => {
          alert('Erro ao deletar operação: ' + (error.error?.error || error.message));
        }
      });
    }
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

  getTotalInvested(): number {
    return this.positions.reduce((sum, pos) => {
      return sum + ((pos.quantity * pos.average_price) || 0);
    }, 0);
  }

  getTotalCurrentValue(): number {
    return this.positions.reduce((sum, pos) => {
      return sum + (pos.current_value || 0);
    }, 0);
  }

  getTotalGainLoss(): number {
    return this.getTotalCurrentValue() - this.getTotalInvested();
  }

  getTotalGainLossPercent(): number {
    const invested = this.getTotalInvested();
    if (invested === 0) return 0;
    return ((this.getTotalCurrentValue() - invested) / invested) * 100;
  }
}

