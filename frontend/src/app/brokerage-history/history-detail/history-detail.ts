import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { BrokerageHistoryService } from '../history.service';
import { BrokerageNote } from '../note.model';
import { DebugService } from '../../shared/services/debug.service';
import { formatCurrency } from '../../shared/utils/common-utils';

@Component({
  selector: 'app-history-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './history-detail.html',
  styleUrl: './history-detail.css'
})
export class HistoryDetailComponent implements OnInit {
  note: BrokerageNote | null = null;
  isLoading: boolean = false;
  error: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private historyService: BrokerageHistoryService,
    private debug: DebugService
  ) {}

  ngOnInit() {
    const noteId = this.route.snapshot.paramMap.get('id');
    if (noteId) {
      this.loadNote(noteId);
    }
  }

  loadNote(noteId: string) {
    this.isLoading = true;
    this.error = null;

    this.historyService.getNoteById(noteId).subscribe({
      next: (note) => {
        this.note = note;
        this.isLoading = false;
      },
      error: (error) => {
        this.error = 'Erro ao carregar nota. Tente novamente.';
        this.isLoading = false;
        this.debug.error('Error loading note:', error);
      }
    });
  }

  onBack() {
    if (typeof window !== 'undefined') {
      window.history.back();
    }
  }

  onDelete() {
    if (this.note && confirm('Tem certeza que deseja excluir esta nota?')) {
      this.historyService.deleteNote(this.note.id).subscribe({
        next: () => {
          this.onBack();
        },
        error: (error) => {
          this.debug.error('Error deleting note:', error);
          alert('Erro ao excluir nota. Tente novamente.');
        }
      });
    }
  }

  formatCurrency(value: number): string {
    return formatCurrency(value);
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
