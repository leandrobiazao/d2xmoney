import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConfigurationService, InvestmentType } from './configuration.service';
import { InvestmentTypesComponent } from './investment-types/investment-types';
import { InvestmentSubtypesComponent } from './investment-subtypes/investment-subtypes';
import { StocksComponent } from './stocks/stocks';

@Component({
  selector: 'app-configuration',
  standalone: true,
  imports: [CommonModule, InvestmentTypesComponent, InvestmentSubtypesComponent, StocksComponent],
  templateUrl: './configuration.html',
  styleUrl: './configuration.css'
})
export class ConfigurationComponent implements OnInit {
  investmentTypes: InvestmentType[] = [];
  isLoading = false;
  errorMessage: string | null = null;
  activeTab: 'types' | 'subtypes' = 'types';

  constructor(private configService: ConfigurationService) {}

  ngOnInit(): void {
    this.loadInvestmentTypes();
  }

  loadInvestmentTypes(): void {
    this.isLoading = true;
    this.errorMessage = null;
    
    this.configService.getInvestmentTypes(false).subscribe({
      next: (types) => {
        this.investmentTypes = types;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar tipos de investimento';
        this.isLoading = false;
        console.error('Error loading investment types:', error);
      }
    });
  }

  onTypeCreated(): void {
    this.loadInvestmentTypes();
  }

  onTypeUpdated(): void {
    this.loadInvestmentTypes();
  }

  onTypeDeleted(): void {
    this.loadInvestmentTypes();
  }
}

