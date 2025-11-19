import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Stock, ClubeDoValorResponse, ClubeDoValorHistoryResponse } from './stock.model';

@Injectable({
  providedIn: 'root'
})
export class ClubeDoValorService {
  private apiUrl = '/api/clubedovalor';

  constructor(private http: HttpClient) {}

  getCurrentStocks(): Observable<ClubeDoValorResponse> {
    const url = this.apiUrl.endsWith('/') ? this.apiUrl : `${this.apiUrl}/`;
    return this.http.get<ClubeDoValorResponse>(url);
  }

  getHistory(): Observable<ClubeDoValorHistoryResponse> {
    return this.http.get<ClubeDoValorHistoryResponse>(`${this.apiUrl}/history/`);
  }

  refreshFromSheets(): Observable<any> {
    return this.http.post(`${this.apiUrl}/refresh/`, {}, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  deleteStock(codigo: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/stocks/${codigo}/`);
  }
}

