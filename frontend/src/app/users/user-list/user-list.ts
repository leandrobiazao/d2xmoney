import { Component, OnInit, EventEmitter, Output } from '@angular/core';
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
export class UserListComponent implements OnInit {
  @Output() userSelected = new EventEmitter<string>();
  @Output() createUser = new EventEmitter<void>();

  users: User[] = [];
  selectedUserId: string | null = null;
  isLoading: boolean = false;
  error: string | null = null;

  constructor(private userService: UserService) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.isLoading = true;
    this.error = null;

    this.userService.getUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.isLoading = false;
      },
      error: (error) => {
        this.error = 'Erro ao carregar usuários. Tente novamente.';
        this.isLoading = false;
        console.error('Error loading users:', error);
        console.error('Error status:', error.status);
        console.error('Error message:', error.message);
        console.error('Error details:', error.error);
        
        // Provide more helpful error message
        if (error.status === 0) {
          this.error = 'Erro de conexão. Verifique se o servidor Django está rodando na porta 8000.';
        } else if (error.status === 404) {
          this.error = 'Endpoint não encontrado. Verifique a configuração do backend.';
        } else if (error.status >= 500) {
          this.error = 'Erro no servidor. Verifique os logs do Django.';
        }
      }
    });
  }

  onUserSelect(userId: string) {
    this.selectedUserId = userId;
    this.userSelected.emit(userId);
  }

  onCreateUser() {
    this.createUser.emit();
  }

  onUserCreated() {
    this.loadUsers();
  }
}

// Export a method that can be called from parent
export function getUserListComponentRefresh(component: UserListComponent) {
  return () => component.loadUsers();
}

