import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CapitalGainsReport } from './tax-reporting.models';

@Injectable({
  providedIn: 'root'
})
export class TaxReportingService {
  private readonly API_URL = '/api/tax-reporting/capital-gains/';

  constructor(private http: HttpClient) {}

  getCapitalGainsReport(userId: string, year: number): Observable<CapitalGainsReport> {
    const params = new HttpParams()
      .set('user_id', userId)
      .set('year', year.toString());
    return this.http.get<CapitalGainsReport>(this.API_URL, { params });
  }
}
