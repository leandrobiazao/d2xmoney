import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RebalancingAction {
  id: number;
  action_type: 'buy' | 'sell' | 'rebalance';
  stock?: {
    id: number;
    ticker: string;
    name: string;
    stock_class?: string;
    investment_type?: {
      id: number;
      name: string;
      code: string;
    };
    investment_subtype?: {
      id: number;
      name: string;
      code: string;
    };
  };
  investment_subtype?: {
    id: number;
    name: string;
    code: string;
  };
  subtype_name?: string;
  subtype_display_name?: string;
  crypto_currency_symbol?: string;
  crypto_currency_name?: string;
  current_value: number;
  target_value: number;
  difference: number;
  quantity_to_buy?: number;
  quantity_to_sell?: number;
  display_order: number;
  reason?: string;
}

export interface RebalancingRecommendation {
  id: number;
  user: string;
  user_name: string;
  strategy: number;
  recommendation_date: string;
  status: 'pending' | 'applied' | 'dismissed';
  total_sales_value: number;
  sales_limit_remaining: number;
  sales_limit_reached: boolean;
  previous_sales_this_month: number;
  total_complete_sales_value: number;
  total_partial_sales_value: number;
  partial_sales_count: number;
  created_at: string;
  updated_at: string;
  actions: RebalancingAction[];
}

@Injectable({
  providedIn: 'root'
})
export class RebalancingService {
  private apiUrl = '/api/rebalancing';

  constructor(private http: HttpClient) {}

  getRecommendations(userId?: string, status?: string): Observable<RebalancingRecommendation[]> {
    let params = new HttpParams();
    if (userId) {
      params = params.set('user_id', userId);
    }
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<RebalancingRecommendation[]>(`${this.apiUrl}/recommendations/`, { params });
  }

  getRecommendation(id: number): Observable<RebalancingRecommendation> {
    return this.http.get<RebalancingRecommendation>(`${this.apiUrl}/recommendations/${id}/`);
  }

  generateRecommendations(userId: string): Observable<RebalancingRecommendation> {
    return this.http.post<RebalancingRecommendation>(`${this.apiUrl}/recommendations/generate/`, {
      user_id: userId
    });
  }

  applyRecommendation(id: number): Observable<RebalancingRecommendation> {
    return this.http.post<RebalancingRecommendation>(`${this.apiUrl}/recommendations/${id}/apply/`, {});
  }

  dismissRecommendation(id: number): Observable<RebalancingRecommendation> {
    return this.http.post<RebalancingRecommendation>(`${this.apiUrl}/recommendations/${id}/dismiss/`, {});
  }
}

