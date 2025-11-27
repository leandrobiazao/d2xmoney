import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CryptoService } from '../../crypto/crypto.service';
import { ConfigurationService, InvestmentType, InvestmentSubType } from '../configuration.service';
import { CryptoCurrency } from '../../crypto/crypto.models';

@Component({
  selector: 'app-cryptocurrencies',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cryptocurrencies.component.html',
  styleUrl: './cryptocurrencies.component.css'
})
export class CryptocurrenciesComponent implements OnInit {
  currencies: CryptoCurrency[] = [];
  investmentTypes: InvestmentType[] = [];
  investmentSubTypes: InvestmentSubType[] = [];
  
  isLoading = false;
  errorMessage: string | null = null;
  
  showCreateCurrencyModal = false;
  editingCurrency: CryptoCurrency | null = null;
  
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
  }

  loadInvestmentTypes(): void {
    this.configService.getInvestmentTypes(true).subscribe({
      next: (types) => {
        this.investmentTypes = types
          .filter(type => type.is_active)
          .sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
        this.loadInvestmentSubTypes();
      },
      error: (error) => {
        console.error('Error loading investment types:', error);
        this.errorMessage = `Erro ao carregar tipos de investimento: ${error.message || 'Erro desconhecido'}`;
      }
    });
  }

  loadInvestmentSubTypes(): void {
    this.configService.getInvestmentSubTypes(undefined, true).subscribe({
      next: (subTypes) => {
        this.investmentSubTypes = subTypes
          .filter(subType => subType.is_active)
          .sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
      },
      error: (error) => {
        console.error('Error loading investment subtypes:', error);
      }
    });
  }

  getSubTypesForType(investmentTypeId: number | null | undefined): InvestmentSubType[] {
    if (!investmentTypeId) {
      return [];
    }
    return this.investmentSubTypes.filter(
      subType => subType.investment_type === investmentTypeId
    );
  }

  loadCurrencies(): void {
    this.isLoading = true;
    this.errorMessage = null;
    
    this.cryptoService.getCurrencies(undefined, false).subscribe({
      next: (currencies) => {
        this.currencies = currencies.sort((a, b) => a.symbol.localeCompare(b.symbol));
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading currencies:', error);
        this.errorMessage = `Erro ao carregar criptomoedas: ${error.message || 'Erro desconhecido'}`;
        this.isLoading = false;
      }
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
      investment_type_id: currency.investment_type_id ?? currency.investment_type?.id,
      investment_subtype_id: currency.investment_subtype_id ?? currency.investment_subtype?.id,
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
}

