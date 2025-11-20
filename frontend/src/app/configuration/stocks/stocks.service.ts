import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Stock } from './stocks.models';

@Injectable({
  providedIn: 'root'
})
export class StocksService {
  private apiUrl = '/api/stocks';

  constructor(private http: HttpClient) {}

  getStocks(search?: string, activeOnly: boolean = true): Observable<Stock[]> {
    let params = new HttpParams();
    if (activeOnly) {
      params = params.set('active_only', 'true');
    }
    if (search) {
      params = params.set('search', search);
    }
    return this.http.get<Stock[]>(`${this.apiUrl}/stocks/`, { params });
  }

  getStock(id: number): Observable<Stock> {
    return this.http.get<Stock>(`${this.apiUrl}/stocks/${id}/`);
  }

  updateStock(id: number, stock: Partial<Stock>): Observable<Stock> {
    return this.http.patch<Stock>(`${this.apiUrl}/stocks/${id}/`, stock);
  }

  syncFromPortfolio(userId?: string): Observable<any> {
    const body = userId ? { user_id: userId } : {};
    return this.http.post<any>(`${this.apiUrl}/stocks/sync_from_portfolio/`, body);
  }
}

