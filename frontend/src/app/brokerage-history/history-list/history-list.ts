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
      // When userId is provided, set it as selected and in filters
      this.selectedUserId = this.userId;
      this.filters.user_id = this.userId;
    }
    this.loadHistory();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['userId'] && !changes['userId'].firstChange) {
      this.selectedUserId = this.userId || null;
      // Update filters to match selected user
      if (this.userId) {
        this.filters.user_id = this.userId;
      } else {
        delete this.filters.user_id;
      }
      // Reload history with new filters instead of just filtering client-side
      this.loadHistory();
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

    // Ensure filters include user_id if a user is selected
    const filtersToUse: HistoryFilters = { ...this.filters };
    if (this.selectedUserId) {
      filtersToUse.user_id = this.selectedUserId;
    } else {
      delete filtersToUse.user_id;
    }

    this.debug.log('📋 Loading history with filters:', filtersToUse);

    this.historyService.getHistory(filtersToUse).subscribe({
      next: (notes) => {
        this.debug.log('✅ History loaded:', notes.length, 'notes for user:', this.selectedUserId || 'all users');
        // Ensure all notes have status field (for backward compatibility)
        this.notes = notes.map((note: BrokerageNote) => {
          const statusValue = note.status || 'success';
          // Verify user_id matches (additional safety check)
          if (this.selectedUserId && note.user_id !== this.selectedUserId) {
            this.debug.warn(`⚠️ Warning: Note ${note.id} has user_id ${note.user_id} but filter expects ${this.selectedUserId}`);
          }
          return {
            ...note,
            status: (statusValue === 'success' || statusValue === 'partial' || statusValue === 'failed') 
              ? statusValue 
              : 'success' as 'success' | 'partial' | 'failed',
            error_message: note.error_message || undefined
          } as BrokerageNote;
        });
        // No need to filter again - backend already filtered
        this.filteredNotes = this.notes;
        // Still apply date sorting
        this.sortFilteredNotes();
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
    // Update filters and reload from backend
    if (userId) {
      this.filters.user_id = userId;
    } else {
      delete this.filters.user_id;
    }
    this.loadHistory();
  }

  private sortFilteredNotes() {
    // Sort by date: most recent at the top (descending order)
    this.filteredNotes.sort((a, b) => {
      // Convert DD/MM/YYYY to Date for comparison
      const parseDate = (dateStr: string): Date => {
        const [day, month, year] = dateStr.split('/').map(Number);
        return new Date(year, month - 1, day);
      };
      
      const dateA = parseDate(a.note_date);
      const dateB = parseDate(b.note_date);
      
      // Descending order: most recent first
      return dateB.getTime() - dateA.getTime();
    });
  }

  applyUserFilter() {
    // This method is now deprecated - filtering is done by backend
    // Keeping for backward compatibility but it should not be needed
    if (this.selectedUserId) {
      this.filteredNotes = this.notes.filter(note => {
        const matches = note.user_id === this.selectedUserId;
        if (!matches) {
          this.debug.warn(`⚠️ Note ${note.id} filtered out: user_id ${note.user_id} !== ${this.selectedUserId}`);
        }
        return matches;
      });
    } else {
      this.filteredNotes = this.notes;
    }
    
    // Sort by date: most recent at the top (descending order)
    this.filteredNotes.sort((a, b) => {
      // Convert DD/MM/YYYY to Date for comparison
      const parseDate = (dateStr: string): Date => {
        const [day, month, year] = dateStr.split('/').map(Number);
        return new Date(year, month - 1, day);
      };
      
      const dateA = parseDate(a.note_date);
      const dateB = parseDate(b.note_date);
      
      // Descending order: most recent first
      return dateB.getTime() - dateA.getTime();
    });
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
