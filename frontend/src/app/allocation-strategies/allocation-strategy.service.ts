import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UserAllocationStrategy {
  id: number;
  user: string;
  user_name: string;
  total_portfolio_value?: number;
  created_at: string;
  updated_at: string;
  type_allocations?: InvestmentTypeAllocation[];
}

export interface InvestmentTypeAllocation {
  id: number;
  investment_type: {
    id: number;
    name: string;
    code: string;
  };
  target_percentage: number;
  display_order: number;
  sub_type_allocations?: SubTypeAllocation[];
  fii_allocations?: FIIAllocation[];
}

export interface SubTypeAllocation {
  id: number;
  sub_type?: {
    id: number;
    name: string;
    code: string;
  };
  custom_name?: string;
  target_percentage: number;
  display_order: number;
  stock_allocations?: StockAllocation[];
}

export interface StockAllocation {
  id: number;
  stock: {
    id: number;
    ticker: string;
    name: string;
  };
  target_percentage: number;
  display_order: number;
}

export interface FIIAllocation {
  id: number;
  stock: {
    id: number;
    ticker: string;
    name: string;
  };
  target_percentage: number;
  display_order: number;
}

export interface PieChartData {
  target: {
    labels: string[];
    data: number[];
    colors: string[];
  };
  current: {
    labels: string[];
    data: number[];
    colors: string[];
  };
}

@Injectable({
  providedIn: 'root'
})
export class AllocationStrategyService {
  private apiUrl = '/api/allocation-strategies';

  constructor(private http: HttpClient) {}

  getAllocationStrategies(userId?: string): Observable<UserAllocationStrategy[]> {
    let params = new HttpParams();
    if (userId) {
      params = params.set('user_id', userId);
    }
    return this.http.get<UserAllocationStrategy[]>(`${this.apiUrl}/allocation-strategies/`, { params });
  }

  getAllocationStrategy(id: number): Observable<UserAllocationStrategy> {
    return this.http.get<UserAllocationStrategy>(`${this.apiUrl}/allocation-strategies/${id}/`);
  }

  createOrUpdateStrategy(userId: string, typeAllocations: any[], totalPortfolioValue?: number): Observable<UserAllocationStrategy> {
    return this.http.post<UserAllocationStrategy>(`${this.apiUrl}/allocation-strategies/create_strategy/`, {
      user_id: userId,
      type_allocations: typeAllocations,
      total_portfolio_value: totalPortfolioValue
    });
  }

  getCurrentVsTarget(userId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/allocation-strategies/current_vs_target/`, {
      params: { user_id: userId }
    });
  }

  getPieChartData(userId: string): Observable<PieChartData> {
    return this.http.get<PieChartData>(`${this.apiUrl}/allocation-strategies/pie_chart_data/`, {
      params: { user_id: userId }
    });
  }
}


