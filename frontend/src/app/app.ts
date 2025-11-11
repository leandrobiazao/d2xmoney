import { Component, ViewChild, AfterViewInit } from '@angular/core';

import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from "./header/header";
import { UserListComponent } from "./users/user-list/user-list";
import { CreateUserComponent } from "./users/create-user/create-user";
import { PortfolioComponent } from './portfolio/portfolio';
import { UserService } from './users/user.service';
import { User } from './users/user.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, HeaderComponent, UserListComponent, CreateUserComponent, PortfolioComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements AfterViewInit {
  @ViewChild(UserListComponent) userListComponent!: UserListComponent;
  
  selectedUser: User | null = null;
  showCreateUser: boolean = false;

  constructor(private userService: UserService) {}

  ngAfterViewInit() {
    // ViewChild is now available
  }

  onUserSelected(userId: string) {
    console.log('User selected:', userId);
    this.userService.getUserById(userId).subscribe({
      next: (user) => {
        console.log('User loaded:', user);
        this.selectedUser = user;
      },
      error: (error) => {
        console.error('Error loading user:', error);
        console.error('Error details:', error.error);
        console.error('Error status:', error.status);
        // Try to find user from the list instead
        this.userService.getUsers().subscribe({
          next: (users) => {
            const foundUser = users.find(u => u.id === userId);
            if (foundUser) {
              console.log('User found in list:', foundUser);
              this.selectedUser = foundUser;
            } else {
              this.selectedUser = null;
            }
          },
          error: (listError) => {
            console.error('Error loading users list:', listError);
            this.selectedUser = null;
          }
        });
      }
    });
  }

  onCreateUser() {
    this.showCreateUser = true;
  }

  onCloseCreateUser() {
    this.showCreateUser = false;
  }

  onUserCreated() {
    this.showCreateUser = false;
    // Refresh the user list - use setTimeout to ensure ViewChild is available
    setTimeout(() => {
      if (this.userListComponent) {
        this.userListComponent.loadUsers();
      }
    }, 0);
  }
}
