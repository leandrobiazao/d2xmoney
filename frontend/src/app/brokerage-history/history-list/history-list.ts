import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BrokerageHistoryService } from '../history.service';
import { BrokerageNote, HistoryFilters } from '../note.model';
import { UserService } from '../../users/user.service';
import { User } from '../../users/user.model';
import { DebugService } from '../../shared/services/debug.service';

@Component({
  selector: 'app-history-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './history-list.html',
  styleUrl: './history-list.css'
})
export class HistoryListComponent implements OnInit {
  notes: BrokerageNote[] = [];
  filteredNotes: BrokerageNote[] = [];
  users: User[] = [];
  selectedUserId: string | null = null;
  isLoadingNotes: boolean = false;
  isLoadingUsers: boolean = false;
  error: string | null = null;
  filters: HistoryFilters = {};

  constructor(
    private historyService: BrokerageHistoryService,
    private userService: UserService,
    private debug: DebugService
  ) {}

  ngOnInit() {
    this.loadUsers();
    this.loadHistory();
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
        this.notes = notes;
        this.applyUserFilter();
        this.isLoadingNotes = false;
      },
      error: (error) => {
        this.error = 'Erro ao carregar histórico. Tente novamente.';
        this.isLoadingNotes = false;
        this.debug.error('Error loading history:', error);
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
