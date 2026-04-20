import { Component, OnInit, EventEmitter, Output, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UserService } from '../user.service';
import { User } from '../user.model';
import { UserItemComponent } from '../user-item/user-item';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, UserItemComponent],
  templateUrl: './user-list.html',
  styleUrl: './user-list.css'
})
export class UserListComponent implements OnInit, OnDestroy {
  @Output() userSelected = new EventEmitter<string>();
  @Output() createUser = new EventEmitter<void>();
  
  users: User[] = [];
  selectedUserId: string | null = null;
  isLoading = false;
  errorMessage: string | null = null;
  
  private userCreatedListener?: EventListener;

  constructor(private userService: UserService) {}

  ngOnInit(): void {
    this.loadUsers();
    
    // Listen for user-created event
    this.userCreatedListener = () => {
      this.loadUsers();
    };
    window.addEventListener('user-created', this.userCreatedListener);
  }

  ngOnDestroy(): void {
    if (this.userCreatedListener) {
      window.removeEventListener('user-created', this.userCreatedListener);
    }
  }

  loadUsers(): void {
    this.isLoading = true;
    this.errorMessage = null;

    this.userService.getUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.isLoading = false;
        this.errorMessage = null;
      },
      error: (error) => {
        console.error('Error loading users:', error);
        this.isLoading = false;

        if (error.status === 0) {
          this.errorMessage =
            'Erro de conexão. Verifique se o servidor Django está rodando em http://localhost:8000';
        } else if (error.status === 404) {
          this.errorMessage = 'Endpoint não encontrado. Verifique a configuração da API.';
        } else if (error.status >= 500) {
          const body = error.error;
          let detail = 'Erro desconhecido no servidor';
          if (body && typeof body === 'object') {
            detail = (body as { details?: string; error?: string }).details
              || (body as { details?: string; error?: string }).error
              || detail;
          } else if (typeof body === 'string' && body.trim().length) {
            detail = body.length > 300 ? `${body.slice(0, 300)}…` : body;
          }
          this.errorMessage = `Erro no servidor (${error.status}): ${detail}`;
        } else {
          this.errorMessage = `Erro ao carregar usuários: ${error.message || 'Erro desconhecido'}`;
        }
      }
    });
  }

  onSelectUser(userId: string): void {
    this.selectedUserId = userId;
    this.userSelected.emit(userId);
  }

  onCreateUser(): void {
    this.createUser.emit();
  }
}
