import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { User } from '../user.model';

@Component({
  selector: 'app-user-item',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './user-item.html',
  styleUrl: './user-item.css'
})
export class UserItemComponent {
  @Input({ required: true }) user!: User;
  @Input() selected: boolean = false;
  @Output() select = new EventEmitter<string>();

  get imagePath() {
    if (this.user.picture) {
      // If it's already a full URL, use it; otherwise prepend /media
      return this.user.picture.startsWith('http') || this.user.picture.startsWith('/media')
        ? this.user.picture
        : `/media/${this.user.picture}`;
    }
    return 'assets/users/user-1.jpg'; // Default avatar
  }

  onSelectUser() {
    this.select.emit(this.user.id);
  }
}

