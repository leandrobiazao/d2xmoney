import { Component, OnInit, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BrokerageHistoryService } from '../history.service';
import { BrokerageNote, HistoryFilters } from '../note.model';
import { UserService } from '../../users/user.service';
import { User } from '../../users/user.model';
import { DebugService } from '../../shared/services/debug.service';
import { OperationsModalComponent } from '../operations-modal/operations-modal';

@Component({
  selector: 'app-history-list',
  standalone: true,
  imports: [CommonModule, OperationsModalComponent],
  templateUrl: './history-list.html',
  styleUrl: './history-list.css'
})
export class HistoryListComponent implements OnInit, OnChanges {
  @Input() userId?: string;
  
  notes: BrokerageNote[] = [];
  filteredNotes: BrokerageNote[] = [];
  users: User[] = [];
  selectedUserId: string | null = null;
  isLoadingNotes: boolean = false;
  isLoadingUsers: boolean = false;
  error: string | null = null;
  filters: HistoryFilters = {};
  
  // Modal state
  showOperationsModal: boolean = false;
  selectedNoteId: string | null = null;

  constructor(
    private historyService: BrokerageHistoryService,
    private userService: UserService,
    private debug: DebugService
  ) {}

  ngOnInit() {
    // Only load users if userId is not provided (standalone mode)
    if (!this.userId) {
      this.loadUsers();
    } else {
      // When userId is provided, set it as selected
      this.selectedUserId = this.userId;
    }
    this.loadHistory();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['userId'] && !changes['userId'].firstChange) {
      this.selectedUserId = this.userId || null;
      this.applyUserFilter();
    }
  }

  loadUsers() {
    this.isLoadingUsers = true;
    this.userService.getUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.isLoadingUsers = false;
      },
      error: (error) => {
        this.debug.error('Error loading users:', error);
        this.isLoadingUsers = false;
      }
    });
  }

  loadHistory() {
    this.isLoadingNotes = true;
    this.error = null;

    this.historyService.getHistory(this.filters).subscribe({
      next: (notes) => {
        this.debug.log('✅ History loaded:', notes.length, 'notes');
        // Ensure all notes have status field (for backward compatibility)
        this.notes = notes.map((note: BrokerageNote) => {
          const statusValue = note.status || 'success';
          return {
            ...note,
            status: (statusValue === 'success' || statusValue === 'partial' || statusValue === 'failed') 
              ? statusValue 
              : 'success' as 'success' | 'partial' | 'failed',
            error_message: note.error_message || undefined
          } as BrokerageNote;
        });
        this.applyUserFilter();
        this.isLoadingNotes = false;
      },
      error: (error) => {
        this.debug.error('❌ Error loading history:', error);
        this.debug.error('❌ Error details:', error.status, error.message, error.error);
        const errorMsg = error.error?.error || error.error?.message || error.message || 'Erro desconhecido';
        this.error = `Erro ao carregar histórico: ${errorMsg}`;
        this.isLoadingNotes = false;
      }
    });
  }

  selectUser(userId: string | null) {
    this.selectedUserId = userId;
    this.applyUserFilter();
  }

  applyUserFilter() {
    if (this.selectedUserId) {
      this.filteredNotes = this.notes.filter(note => note.user_id === this.selectedUserId);
    } else {
      this.filteredNotes = this.notes;
    }
  }

  getUserById(userId: string): User | undefined {
    return this.users.find(u => u.id === userId);
  }

  onDeleteNote(noteId: string) {
    if (confirm('Tem certeza que deseja excluir esta nota?')) {
      this.debug.log('🗑️ Attempting to delete note:', noteId);
      this.historyService.deleteNote(noteId).subscribe({
        next: (response) => {
          this.debug.log('✅ Note deleted successfully:', response);
          this.loadHistory();
          
          // Dispatch event to notify portfolio component to refresh
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('brokerage-note-deleted', {
              detail: { noteId }
            }));
          }
        },
        error: (error) => {
          this.debug.error('❌ Error deleting note:', error);
          this.debug.error('❌ Error details:', error.status, error.message, error.error);
          const errorMsg = error.error?.error || error.error?.message || error.message || 'Erro desconhecido';
          alert(`Erro ao excluir nota: ${errorMsg}\n\nVerifique o console para mais detalhes.`);
        }
      });
    }
  }

  viewNote(noteId: string) {
    this.debug.log('View note:', noteId);
    this.selectedNoteId = noteId;
    this.showOperationsModal = true;
  }

  onModalClose(): void {
    this.showOperationsModal = false;
    this.selectedNoteId = null;
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
