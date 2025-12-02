import { Routes } from '@angular/router';
import { HistoryListComponent } from './brokerage-history/history-list/history-list';
import { ClubeDoValorComponent } from './clubedovalor/clubedovalor/clubedovalor';
import { ConfigurationComponent } from './configuration/configuration.component';
import { AllocationStrategyComponent } from './allocation-strategies/allocation-strategy.component';
import { StocksComponent } from './configuration/stocks/stocks';
import { FIICatalogComponent } from './configuration/fii-catalog.component';
import { InvestmentTypesComponent } from './configuration/investment-types/investment-types';
import { InvestmentSubtypesComponent } from './configuration/investment-subtypes/investment-subtypes';
import { CryptocurrenciesComponent } from './configuration/cryptocurrencies/cryptocurrencies.component';
import { CorporateEventsComponent } from './configuration/corporate-events/corporate-events.component';

export const routes: Routes = [
  { path: '', redirectTo: '/home', pathMatch: 'full' },
  { path: 'home', children: [] }, // Home is handled by App component itself
  { path: 'history', component: HistoryListComponent },
  { path: 'clube-do-valor', component: ClubeDoValorComponent },
  { 
    path: 'configuration', 
    component: ConfigurationComponent,
    children: [
      { path: '', redirectTo: 'types', pathMatch: 'full' },
      { path: 'types', component: InvestmentTypesComponent },
      { path: 'subtypes', component: InvestmentSubtypesComponent },
      { path: 'stocks', component: StocksComponent },
      { path: 'fii-catalog', component: FIICatalogComponent },
      { path: 'cryptocurrencies', component: CryptocurrenciesComponent },
      { path: 'corporate-events', component: CorporateEventsComponent }
    ]
  },
  { path: 'allocation-strategies', component: AllocationStrategyComponent }
];

