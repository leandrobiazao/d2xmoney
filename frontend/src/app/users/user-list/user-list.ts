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
        
        // Provide more detailed error messages
        if (error.status === 0) {
          // Network error - server not reachable
          this.errorMessage = 'Erro de conexão. Verifique se o servidor Django está rodando em http://localhost:8000';
        } else if (error.status === 404) {
          this.errorMessage = 'Endpoint não encontrado. Verifique a configuração da API.';
        } else if (error.status >= 500) {
          // Server error - show backend error details if available
          const errorDetails = error.error?.details || error.error?.error || 'Erro desconhecido no servidor';
          this.errorMessage = `Erro no servidor (${error.status}): ${errorDetails}`;
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
