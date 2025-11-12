import { Component } from '@angular/core';
import { HeaderComponent } from "./header/header";
import { UserListComponent } from "./users/user-list/user-list";
import { CreateUserComponent } from "./users/create-user/create-user";
import { PortfolioComponent } from './portfolio/portfolio';
import { HistoryListComponent } from './brokerage-history/history-list/history-list';
import { UserService } from './users/user.service';
import { User } from './users/user.model';
import { DebugService } from './shared/services/debug.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [HeaderComponent, UserListComponent, CreateUserComponent, PortfolioComponent, HistoryListComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  selectedUser: User | null = null;
  showCreateUser: boolean = false;
  showBrokerageHistory: boolean = false;

  constructor(
    private userService: UserService,
    private debug: DebugService
  ) {}

  onUserSelected(userId: string): void {
    this.debug.log('User selected:', userId);
    this.userService.getUserById(userId).subscribe({
      next: (user) => {
        this.debug.log('User loaded:', user);
        this.selectedUser = user;
      },
      error: (error) => {
        this.debug.error('Error loading user:', error);
        // Try to find user from the list instead
        this.userService.getUsers().subscribe({
          next: (users) => {
            const foundUser = users.find(u => u.id === userId);
            if (foundUser) {
              this.debug.log('User found in list:', foundUser);
              this.selectedUser = foundUser;
            } else {
              this.selectedUser = null;
            }
          },
          error: (listError) => {
            this.debug.error('Error loading users list:', listError);
            this.selectedUser = null;
          }
        });
      }
    });
  }

  onCreateUser(): void {
    this.showCreateUser = true;
  }

  onCloseCreateUser(): void {
    this.showCreateUser = false;
  }

  onUserCreated(): void {
    this.showCreateUser = false;
    // Trigger user list refresh by emitting a custom event
    window.dispatchEvent(new CustomEvent('user-created'));
  }

  onShowHistory(): void {
    this.showBrokerageHistory = true;
  }

  onBackToMain(): void {
    this.showBrokerageHistory = false;
  }
}
