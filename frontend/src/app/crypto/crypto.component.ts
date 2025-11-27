import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CryptoService } from './crypto.service';
import { CryptoCurrency, CryptoOperation, CryptoPosition } from './crypto.models';
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
  
  isLoading = false;
  errorMessage: string | null = null;
  
  showOperationDialog = false;
  editingOperation: CryptoOperation | null = null;

  constructor(
    private cryptoService: CryptoService
  ) {}

  ngOnInit(): void {
    this.loadCurrencies();
    if (this.userId) {
      this.loadOperations();
      this.loadPositions();
    }
  }

  loadCurrencies(): void {
    this.cryptoService.getCurrencies(undefined, true).subscribe({
      next: (currencies) => {
        this.currencies = currencies;
      },
      error: (error) => {
        console.error('Error loading currencies:', error);
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

