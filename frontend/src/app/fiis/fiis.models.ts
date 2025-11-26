export interface FIIProfile {
  id: number;
  stock_id: number;
  ticker: string;
  segment: string;
  target_audience: string;
  administrator: string;
  last_yield?: number;
  dividend_yield?: number;
  base_date?: string;
  payment_date?: string;
  average_yield_12m_value?: number;
  average_yield_12m_percentage?: number;
  equity_per_share?: number;
  price_to_vp?: number;
  trades_per_month?: number;
  ifix_participation?: number;
  shareholders_count?: number;
  equity?: number;
  base_share_price?: number;
}

export interface FIIPosition {
  ticker: string;
  quantity: number;
  averagePrice: number;
  totalInvested: number;
  currentPrice?: number;
  currentValue?: number;
  profit?: number;
  profile?: FIIProfile;
}
