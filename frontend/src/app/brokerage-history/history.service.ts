import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { BrokerageNote, HistoryFilters } from './note.model';

@Injectable({
  providedIn: 'root'
})
export class BrokerageHistoryService {
  private apiUrl = '/api/brokerage-notes';

  constructor(private http: HttpClient) {}

  getHistory(filters?: HistoryFilters): Observable<BrokerageNote[]> {
    let params = new HttpParams();
    
    if (filters?.user_id) {
      params = params.set('user_id', filters.user_id);
    }
    if (filters?.date_from) {
      params = params.set('date_from', filters.date_from);
    }
    if (filters?.date_to) {
      params = params.set('date_to', filters.date_to);
    }
    if (filters?.note_number) {
      params = params.set('note_number', filters.note_number);
    }
    
    return this.http.get<BrokerageNote[]>(this.apiUrl, { params });
  }

  getNoteById(id: string): Observable<BrokerageNote> {
    return this.http.get<BrokerageNote>(`${this.apiUrl}/${id}/`);
  }

  addNote(note: BrokerageNote): Observable<BrokerageNote> {
    // Ensure trailing slash for Django compatibility
    const url = this.apiUrl.endsWith('/') ? this.apiUrl : `${this.apiUrl}/`;
    return this.http.post<BrokerageNote>(url, note);
  }

  deleteNote(id: string): Observable<any> {
    const url = `${this.apiUrl}/${id}/`;
    console.log('🗑️ DELETE request to:', url);
    return this.http.delete<any>(url);
  }
}

