import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BrokerageHistoryService } from '../history.service';
import { BrokerageNote, HistoryFilters } from '../note.model';
import { HistoryFiltersComponent } from '../history-filters/history-filters';
import { DebugService } from '../../shared/services/debug.service';

@Component({
  selector: 'app-history-list',
  standalone: true,
  imports: [CommonModule, HistoryFiltersComponent],
  templateUrl: './history-list.html',
  styleUrl: './history-list.css'
})
export class HistoryListComponent implements OnInit {
  notes: BrokerageNote[] = [];
  filteredNotes: BrokerageNote[] = [];
  isLoading: boolean = false;
  error: string | null = null;
  filters: HistoryFilters = {};

  constructor(
    private historyService: BrokerageHistoryService,
    private debug: DebugService
  ) {}

  ngOnInit() {
    this.loadHistory();
  }

  loadHistory() {
    this.isLoading = true;
    this.error = null;

    this.historyService.getHistory(this.filters).subscribe({
      next: (notes) => {
        this.notes = notes;
        this.filteredNotes = notes;
        this.isLoading = false;
      },
      error: (error) => {
        this.error = 'Erro ao carregar histórico. Tente novamente.';
        this.isLoading = false;
        this.debug.error('Error loading history:', error);
      }
    });
  }

  onFiltersChange(filters: HistoryFilters) {
    this.filters = filters;
    this.loadHistory();
  }

  onDeleteNote(noteId: string) {
    if (confirm('Tem certeza que deseja excluir esta nota?')) {
      this.historyService.deleteNote(noteId).subscribe({
        next: () => {
          this.loadHistory();
        },
        error: (error) => {
          this.debug.error('Error deleting note:', error);
          alert('Erro ao excluir nota. Tente novamente.');
        }
      });
    }
  }

  viewNote(noteId: string) {
    this.debug.log('View note:', noteId);
    // Note: Detail view would be shown here if routing was enabled
  }

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'success':
        return 'badge-success';
      case 'partial':
        return 'badge-warning';
      case 'failed':
        return 'badge-error';
      default:
        return 'badge-default';
    }
  }
}
