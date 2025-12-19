import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CorporateEvent, CorporateEventCreateRequest, CorporateEventApplyResponse } from './corporate-events.models';

@Injectable({
  providedIn: 'root'
})
export class CorporateEventsService {
  private readonly apiUrl = '/api/corporate-events';

  constructor(private http: HttpClient) {}

  getAllEvents(): Observable<CorporateEvent[]> {
    return this.http.get<CorporateEvent[]>(`${this.apiUrl}/`);
  }

  getEvent(id: number): Observable<CorporateEvent> {
    return this.http.get<CorporateEvent>(`${this.apiUrl}/${id}/`);
  }

  createEvent(event: CorporateEventCreateRequest): Observable<CorporateEvent> {
    return this.http.post<CorporateEvent>(`${this.apiUrl}/`, event);
  }

  updateEvent(id: number, event: Partial<CorporateEventCreateRequest>): Observable<CorporateEvent> {
    return this.http.put<CorporateEvent>(`${this.apiUrl}/${id}/`, event);
  }

  deleteEvent(id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${id}/`);
  }

  applyEvent(id: number, userId?: string): Observable<CorporateEventApplyResponse> {
    const body = userId ? { user_id: userId } : {};
    return this.http.post<CorporateEventApplyResponse>(`${this.apiUrl}/${id}/apply/`, body);
  }
}






