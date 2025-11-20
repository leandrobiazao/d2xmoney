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

  getCurrentStocks(strategy: string = 'AMBB1'): Observable<ClubeDoValorResponse> {
    const url = this.apiUrl.endsWith('/') ? this.apiUrl : `${this.apiUrl}/`;
    console.log(`[SERVICE] getCurrentStocks called with strategy: ${strategy}`);
    return this.http.get<ClubeDoValorResponse>(url, {
      params: { strategy }
    });
  }

  getHistory(strategy: string = 'AMBB1'): Observable<ClubeDoValorHistoryResponse> {
    console.log(`[SERVICE] getHistory called with strategy: ${strategy}`);
    return this.http.get<ClubeDoValorHistoryResponse>(`${this.apiUrl}/history/`, {
      params: { strategy }
    });
  }

  refreshFromSheets(strategy: string = 'AMBB1'): Observable<any> {
    return this.http.post(`${this.apiUrl}/refresh/`, {
      strategy: strategy
    }, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  deleteStock(codigo: string, strategy: string = 'AMBB1'): Observable<any> {
    return this.http.delete(`${this.apiUrl}/stocks/${codigo}/`, {
      params: { strategy }
    });
  }
}

