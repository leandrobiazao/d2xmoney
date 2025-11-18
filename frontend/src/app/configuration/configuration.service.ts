import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface InvestmentType {
  id: number;
  name: string;
  code: string;
  display_order: number;
  is_active: boolean;
  sub_types?: InvestmentSubType[];
}

export interface InvestmentSubType {
  id: number;
  name: string;
  code: string;
  display_order: number;
  is_predefined: boolean;
  is_active: boolean;
  investment_type?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ConfigurationService {
  private apiUrl = '/api/configuration';

  constructor(private http: HttpClient) {}

  getInvestmentTypes(activeOnly: boolean = true): Observable<InvestmentType[]> {
    // Ensure trailing slash for Django compatibility
    const url = `${this.apiUrl}/investment-types/`;
    return this.http.get<InvestmentType[]>(url, { 
      params: { active_only: activeOnly.toString() } 
    });
  }

  getInvestmentType(id: number): Observable<InvestmentType> {
    return this.http.get<InvestmentType>(`${this.apiUrl}/investment-types/${id}/`);
  }

  createInvestmentType(type: Partial<InvestmentType>): Observable<InvestmentType> {
    return this.http.post<InvestmentType>(`${this.apiUrl}/investment-types/`, type);
  }

  updateInvestmentType(id: number, type: Partial<InvestmentType>): Observable<InvestmentType> {
    return this.http.put<InvestmentType>(`${this.apiUrl}/investment-types/${id}/`, type);
  }

  deleteInvestmentType(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/investment-types/${id}/`);
  }

  getInvestmentSubTypes(investmentTypeId?: number, activeOnly: boolean = true): Observable<InvestmentSubType[]> {
    // Ensure trailing slash for Django compatibility
    const url = `${this.apiUrl}/investment-subtypes/`;
    const params: any = { active_only: activeOnly.toString() };
    if (investmentTypeId) {
      params.investment_type_id = investmentTypeId.toString();
    }
    return this.http.get<InvestmentSubType[]>(url, { params });
  }

  getInvestmentSubType(id: number): Observable<InvestmentSubType> {
    return this.http.get<InvestmentSubType>(`${this.apiUrl}/investment-subtypes/${id}/`);
  }

  createInvestmentSubType(subType: Partial<InvestmentSubType>): Observable<InvestmentSubType> {
    return this.http.post<InvestmentSubType>(`${this.apiUrl}/investment-subtypes/`, subType);
  }

  updateInvestmentSubType(id: number, subType: Partial<InvestmentSubType>): Observable<InvestmentSubType> {
    return this.http.put<InvestmentSubType>(`${this.apiUrl}/investment-subtypes/${id}/`, subType);
  }

  deleteInvestmentSubType(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/investment-subtypes/${id}/`);
  }

  importSubTypesFromExcel(file: File, investmentTypeCode: string, sheetName?: string): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('investment_type_code', investmentTypeCode);
    if (sheetName) {
      formData.append('sheet_name', sheetName);
    }
    return this.http.post(`${this.apiUrl}/investment-subtypes/import_excel/`, formData);
  }
}

