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
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar usuários. Verifique se o servidor está rodando.';
        this.isLoading = false;
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
