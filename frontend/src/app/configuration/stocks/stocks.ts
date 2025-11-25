import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { StocksService } from './stocks.service';
import { ConfigurationService, InvestmentType, InvestmentSubType } from '../configuration.service';
import { Stock } from './stocks.models';

@Component({
  selector: 'app-stocks',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './stocks.html',
  styleUrl: './stocks.css'
})
export class StocksComponent implements OnInit {
  stocks: Stock[] = [];
  investmentTypes: InvestmentType[] = [];
  investmentSubTypes: InvestmentSubType[] = [];
  isLoading = false;
  isSyncing = false;
  errorMessage: string | null = null;
  searchTerm: string = '';
  syncMessage: string | null = null;

  constructor(
    private stocksService: StocksService,
    private configService: ConfigurationService
  ) {}

  ngOnInit(): void {
    // Load investment types first
    this.configService.getInvestmentTypes(true).subscribe({
      next: (types) => {
        // Filter active types and sort by display_order
        this.investmentTypes = types
          .filter(type => type.is_active)
          .sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
        
        // Load investment subtypes
        this.loadInvestmentSubTypes();
        
        // Load stocks from database first
        this.loadStocks();
        
        // Then sync portfolio to update prices and add new stocks
        this.syncPortfolioStocks();
      },
      error: (error) => {
        console.error('Error loading investment types:', error);
        console.error('Error details:', error.error);
        console.error('Error status:', error.status);
        console.error('Error message:', error.message);
        this.errorMessage = `Erro ao carregar tipos de investimento: ${error.message || error.status || 'Erro desconhecido'}`;
        // Still try to load stocks even if types fail
        this.loadStocks();
        this.syncPortfolioStocks();
      }
    });
  }

  loadInvestmentSubTypes(): void {
    this.configService.getInvestmentSubTypes(undefined, true).subscribe({
      next: (subTypes) => {
        // Filter active subtypes and sort by display_order
        this.investmentSubTypes = subTypes
          .filter(subType => subType.is_active)
          .sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
        console.log('Loaded investment subtypes:', this.investmentSubTypes);
      },
      error: (error) => {
        console.error('Error loading investment subtypes:', error);
      }
    });
  }

  getSubTypesForInvestmentType(investmentTypeId: number | null | undefined): InvestmentSubType[] {
    if (!investmentTypeId) {
      return [];
    }
    const filtered = this.investmentSubTypes.filter(
      subType => subType.investment_type === investmentTypeId
    );
    console.log(`Filtering subtypes for investment type ${investmentTypeId}:`, filtered);
    return filtered;
  }

  syncPortfolioStocks(): void {
    this.isSyncing = true;
    this.syncMessage = null;
    
    // Sync stocks from portfolio to catalog (updates prices and adds new stocks)
    this.stocksService.syncFromPortfolio().subscribe({
      next: (results) => {
        console.log('Portfolio stocks synced:', results);
        this.isSyncing = false;
        
        if (results.created > 0 || results.updated > 0) {
          this.syncMessage = `${results.created} ações criadas, ${results.updated} preços atualizados`;
          setTimeout(() => {
            this.syncMessage = null;
          }, 5000);
        }
        
        // After sync, reload stocks to show updated prices and new stocks
        this.loadStocks();
      },
      error: (error) => {
        console.error('Error syncing portfolio stocks:', error);
        this.isSyncing = false;
        this.syncMessage = 'Erro ao sincronizar ações do portfólio';
        setTimeout(() => {
          this.syncMessage = null;
        }, 5000);
        // Stocks are already loaded, so we don't need to reload on error
      }
    });
  }

  loadStocks(): void {
    this.isLoading = true;
    this.errorMessage = null;
    
    this.stocksService.getStocks(this.searchTerm).subscribe({
      next: (stocks) => {
        this.stocks = stocks;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar ações';
        this.isLoading = false;
        console.error('Error loading stocks:', error);
      }
    });
  }


  onSearchChange(): void {
    this.loadStocks();
  }

  onInvestmentTypeChange(stock: Stock, value: string | number | null): void {
    // Convert value to number or null
    const investmentTypeId = value === '' || value === null || value === undefined 
      ? null 
      : (typeof value === 'number' ? value : parseInt(String(value), 10));
    
    // Optimistically update the UI
    const index = this.stocks.findIndex(s => s.id === stock.id);
    if (index !== -1) {
      // Create a copy to ensure change detection
      const updatedStock = { ...this.stocks[index] };
      if (investmentTypeId) {
        // Find the investment type from the list
        const investmentType = this.investmentTypes.find(t => t.id === investmentTypeId);
        updatedStock.investment_type = investmentType;
        updatedStock.investment_type_id = investmentTypeId;
        // Clear subtype when investment type changes (subtype should belong to the new type)
        updatedStock.investment_subtype = undefined;
        updatedStock.investment_subtype_id = undefined;
      } else {
        updatedStock.investment_type = undefined;
        updatedStock.investment_type_id = undefined;
        updatedStock.investment_subtype = undefined;
        updatedStock.investment_subtype_id = undefined;
      }
      this.stocks[index] = updatedStock;
    }
    
    // Prepare update data - also clear subtype when type changes
    const updateData: any = {
      investment_type_id: investmentTypeId,
      investment_subtype_id: null // Clear subtype when type changes
    };

    this.stocksService.updateStock(stock.id, updateData).subscribe({
      next: (updatedStock) => {
        // Update the stock in the list with the server response
        const index = this.stocks.findIndex(s => s.id === stock.id);
        if (index !== -1) {
          // Replace with the complete updated stock from server
          this.stocks[index] = updatedStock;
        }
      },
      error: (error) => {
        console.error('Error updating stock investment type:', error);
        console.error('Error details:', error.error);
        alert('Erro ao atualizar tipo de investimento: ' + (error.error?.error || error.message || 'Erro desconhecido'));
        // Reload to revert changes and get correct state from server
        this.loadStocks();
      }
    });
  }

  onInvestmentSubtypeChange(stock: Stock, value: string | number | null): void {
    // Convert value to number or null
    const investmentSubtypeId = value === '' || value === null || value === undefined 
      ? null 
      : (typeof value === 'number' ? value : parseInt(String(value), 10));
    
    // Optimistically update the UI
    const index = this.stocks.findIndex(s => s.id === stock.id);
    if (index !== -1) {
      // Create a copy to ensure change detection
      const updatedStock = { ...this.stocks[index] };
      if (investmentSubtypeId) {
        // Find the investment subtype from the list
        const investmentSubtype = this.investmentSubTypes.find(s => s.id === investmentSubtypeId);
        updatedStock.investment_subtype = investmentSubtype;
        updatedStock.investment_subtype_id = investmentSubtypeId;
      } else {
        updatedStock.investment_subtype = undefined;
        updatedStock.investment_subtype_id = undefined;
      }
      this.stocks[index] = updatedStock;
    }
    
    // Prepare update data
    const updateData: any = {
      investment_subtype_id: investmentSubtypeId
    };

    this.stocksService.updateStock(stock.id, updateData).subscribe({
      next: (updatedStock) => {
        // Update the stock in the list with the server response
        const index = this.stocks.findIndex(s => s.id === stock.id);
        if (index !== -1) {
          // Replace with the complete updated stock from server
          this.stocks[index] = updatedStock;
        }
      },
      error: (error) => {
        console.error('Error updating stock investment subtype:', error);
        console.error('Error details:', error.error);
        alert('Erro ao atualizar sub-tipo de investimento: ' + (error.error?.error || error.message || 'Erro desconhecido'));
        // Reload to revert changes and get correct state from server
        this.loadStocks();
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
      return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return date;
    }
  }
}

