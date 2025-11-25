import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CryptoService } from '../crypto.service';
import { CryptoCurrency, CryptoOperation } from '../crypto.models';

@Component({
  selector: 'app-crypto-operation-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './crypto-operation-dialog.component.html',
  styleUrl: './crypto-operation-dialog.component.css'
})
export class CryptoOperationDialogComponent implements OnInit {
  @Input() userId!: string;
  @Input() operation: CryptoOperation | null = null;
  @Input() currencies: CryptoCurrency[] = [];
  @Output() saved = new EventEmitter<void>();
  @Output() canceled = new EventEmitter<void>();

  formData: Partial<CryptoOperation> = {
    crypto_currency_id: undefined,
    operation_type: 'BUY',
    quantity: 0,
    price: 0,
    operation_date: new Date().toISOString().split('T')[0],
    broker: '',
    notes: ''
  };

  constructor(private cryptoService: CryptoService) {}

  ngOnInit(): void {
    if (this.operation) {
      this.formData = {
        crypto_currency_id: this.operation.crypto_currency_id,
        operation_type: this.operation.operation_type,
        quantity: this.operation.quantity,
        price: this.operation.price,
        operation_date: this.operation.operation_date.split('T')[0],
        broker: this.operation.broker || '',
        notes: this.operation.notes || ''
      };
    }
  }

  onSave(): void {
    if (!this.formData.crypto_currency_id || !this.formData.quantity || !this.formData.price || !this.formData.operation_date) {
      alert('Preencha todos os campos obrigatórios');
      return;
    }

    const operationData = {
      ...this.formData,
      user_id: this.userId
    };

    if (this.operation) {
      this.cryptoService.updateOperation(this.operation.id, operationData).subscribe({
        next: () => {
          this.saved.emit();
        },
        error: (error) => {
          alert('Erro ao atualizar operação: ' + (error.error?.error || error.message));
        }
      });
    } else {
      this.cryptoService.createOperation(operationData).subscribe({
        next: () => {
          this.saved.emit();
        },
        error: (error) => {
          alert('Erro ao criar operação: ' + (error.error?.error || error.message));
        }
      });
    }
  }

  onCancel(): void {
    this.canceled.emit();
  }

  onOverlayClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.onCancel();
    }
  }

  get totalValue(): number {
    if (this.formData.quantity && this.formData.price) {
      return Number(this.formData.quantity) * Number(this.formData.price);
    }
    return 0;
  }

  formatCurrency(value: number): string {
    if (value === undefined || value === null || isNaN(value)) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  }
}

