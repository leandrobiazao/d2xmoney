import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CryptoCurrency, CryptoOperation, CryptoPosition } from './crypto.models';

@Injectable({
  providedIn: 'root'
})
export class CryptoService {
  private apiUrl = '/api/crypto';

  constructor(private http: HttpClient) {}

  // Crypto Currency methods
  getCurrencies(search?: string, activeOnly: boolean = true): Observable<CryptoCurrency[]> {
    let params = new HttpParams();
    if (search) {
      params = params.set('search', search);
    }
    params = params.set('active_only', activeOnly.toString());
    return this.http.get<CryptoCurrency[]>(`${this.apiUrl}/currencies/`, { params });
  }

  getCurrency(id: number): Observable<CryptoCurrency> {
    return this.http.get<CryptoCurrency>(`${this.apiUrl}/currencies/${id}/`);
  }

  createCurrency(currency: Partial<CryptoCurrency>): Observable<CryptoCurrency> {
    return this.http.post<CryptoCurrency>(`${this.apiUrl}/currencies/`, currency);
  }

  updateCurrency(id: number, currency: Partial<CryptoCurrency>): Observable<CryptoCurrency> {
    return this.http.patch<CryptoCurrency>(`${this.apiUrl}/currencies/${id}/`, currency);
  }

  deleteCurrency(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/currencies/${id}/`);
  }

  // Crypto Operation methods
  getOperations(userId?: string, cryptoCurrencyId?: number, operationType?: string): Observable<CryptoOperation[]> {
    let params = new HttpParams();
    if (userId) {
      params = params.set('user_id', userId);
    }
    if (cryptoCurrencyId) {
      params = params.set('crypto_currency_id', cryptoCurrencyId.toString());
    }
    if (operationType) {
      params = params.set('operation_type', operationType);
    }
    return this.http.get<CryptoOperation[]>(`${this.apiUrl}/operations/`, { params });
  }

  getOperation(id: number): Observable<CryptoOperation> {
    return this.http.get<CryptoOperation>(`${this.apiUrl}/operations/${id}/`);
  }

  createOperation(operation: Partial<CryptoOperation>): Observable<CryptoOperation> {
    return this.http.post<CryptoOperation>(`${this.apiUrl}/operations/`, operation);
  }

  updateOperation(id: number, operation: Partial<CryptoOperation>): Observable<CryptoOperation> {
    return this.http.patch<CryptoOperation>(`${this.apiUrl}/operations/${id}/`, operation);
  }

  deleteOperation(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/operations/${id}/delete_and_recalculate/`);
  }

  // Crypto Position methods
  getPositions(userId?: string): Observable<CryptoPosition[]> {
    let params = new HttpParams();
    if (userId) {
      params = params.set('user_id', userId);
    }
    return this.http.get<CryptoPosition[]>(`${this.apiUrl}/positions/`, { params });
  }

  getPosition(id: number): Observable<CryptoPosition> {
    return this.http.get<CryptoPosition>(`${this.apiUrl}/positions/${id}/`);
  }

  recalculatePositions(userId: string): Observable<CryptoPosition[]> {
    return this.http.post<CryptoPosition[]>(`${this.apiUrl}/positions/recalculate/`, { user_id: userId });
  }

  // Crypto Price methods
  getBtcBrlPrice(): Observable<{ symbol: string; currency: string; price: number; timestamp: string }> {
    return this.http.get<{ symbol: string; currency: string; price: number; timestamp: string }>(`${this.apiUrl}/prices/btc_brl/`);
  }

  getCryptoPrice(symbol: string, currency: string = 'BRL'): Observable<{ symbol: string; currency: string; price: number; timestamp: string }> {
    let params = new HttpParams();
    params = params.set('symbol', symbol);
    params = params.set('currency', currency);
    return this.http.get<{ symbol: string; currency: string; price: number; timestamp: string }>(`${this.apiUrl}/prices/price/`, { params });
  }
}

