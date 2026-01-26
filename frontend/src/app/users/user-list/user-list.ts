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
    
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/acab8374-5e33-40bd-8c47-7aa99bf1c597',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'user-list.ts:43',message:'loadUsers() entry',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
    // #endregion
    
    this.userService.getUsers().subscribe({
      next: (users) => {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/acab8374-5e33-40bd-8c47-7aa99bf1c597',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'user-list.ts:48',message:'getUsers() success',data:{users_count:users?.length||0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B,C,D'})}).catch(()=>{});
        // #endregion
        this.users = users;
        this.isLoading = false;
        this.errorMessage = null;
      },
      error: (error) => {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/acab8374-5e33-40bd-8c47-7aa99bf1c597',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'user-list.ts:54',message:'getUsers() error',data:{status:error?.status,statusText:error?.statusText,error_obj:error?.error,error_keys:error?.error?Object.keys(error.error):[],message:error?.message,name:error?.name},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
        // #endregion
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
