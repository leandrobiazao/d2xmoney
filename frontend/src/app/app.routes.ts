import { Routes } from '@angular/router';
import { HistoryListComponent } from './brokerage-history/history-list/history-list';
import { HistoryDetailComponent } from './brokerage-history/history-detail/history-detail';

export const routes: Routes = [
  { path: 'brokerage-history', component: HistoryListComponent },
  { path: 'brokerage-history/:id', component: HistoryDetailComponent },
];
