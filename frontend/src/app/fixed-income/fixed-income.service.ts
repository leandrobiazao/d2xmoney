import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { FixedIncomePosition, TesouroDiretoPosition, ImportResult } from './fixed-income.models';

@Injectable({
  providedIn: 'root'
})
export class FixedIncomeService {
  private apiUrl = '/api/fixed-income';

  constructor(private http: HttpClient) {}

  getPositions(userId?: string, investmentType?: string): Observable<FixedIncomePosition[]> {
    let params = new HttpParams();
    if (userId) {
      params = params.set('user_id', userId);
    }
    if (investmentType) {
      params = params.set('investment_type', investmentType);
    }
    return this.http.get<FixedIncomePosition[]>(`${this.apiUrl}/positions/`, { params });
  }

  getPositionById(id: number): Observable<FixedIncomePosition> {
    return this.http.get<FixedIncomePosition>(`${this.apiUrl}/positions/${id}/`);
  }

  createPosition(position: Partial<FixedIncomePosition>): Observable<FixedIncomePosition> {
    return this.http.post<FixedIncomePosition>(`${this.apiUrl}/positions/`, position);
  }

  updatePosition(id: number, position: Partial<FixedIncomePosition>): Observable<FixedIncomePosition> {
    return this.http.put<FixedIncomePosition>(`${this.apiUrl}/positions/${id}/`, position);
  }

  deletePosition(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/positions/${id}/`);
  }

  importExcel(file: File, userId: string): Observable<ImportResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);
    return this.http.post<ImportResult>(`${this.apiUrl}/positions/import-excel/`, formData);
  }

  getTesouroDiretoPositions(userId?: string): Observable<TesouroDiretoPosition[]> {
    let params = new HttpParams();
    if (userId) {
      params = params.set('user_id', userId);
    }
    return this.http.get<TesouroDiretoPosition[]>(`${this.apiUrl}/tesouro-direto/`, { params });
  }
}


