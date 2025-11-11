import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { User } from './user.model';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private apiUrl = '/api/users';

  constructor(private http: HttpClient) {}

  getUsers(): Observable<User[]> {
    // Ensure trailing slash for Django compatibility
    const url = this.apiUrl.endsWith('/') ? this.apiUrl : `${this.apiUrl}/`;
    return this.http.get<User[]>(url);
  }

  getUserById(id: string): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/${id}/`);
  }

  createUser(userData: FormData): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/`, userData);
  }

  updateUser(id: string, userData: FormData): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/${id}/`, userData);
  }

  deleteUser(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}/`);
  }
}

