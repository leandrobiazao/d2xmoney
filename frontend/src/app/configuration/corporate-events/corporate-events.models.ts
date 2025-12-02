export interface CorporateEvent {
  id: number;
  ticker: string;
  previous_ticker?: string; // For TICKER_CHANGE events
  event_type: 'GROUPING' | 'SPLIT' | 'BONUS' | 'SUBSCRIPTION' | 'TICKER_CHANGE';
  event_type_display: string;
  asset_type: 'STOCK' | 'FII';
  asset_type_display: string;
  ex_date: string; // ISO date string (YYYY-MM-DD)
  ratio: string; // e.g., "20:1", "1:5" (not used for TICKER_CHANGE)
  description: string;
  applied: boolean;
  created_at: string;
  updated_at: string;
}

export interface CorporateEventCreateRequest {
  ticker: string;
  previous_ticker?: string; // Required for TICKER_CHANGE
  event_type: 'GROUPING' | 'SPLIT' | 'BONUS' | 'SUBSCRIPTION' | 'TICKER_CHANGE';
  asset_type: 'STOCK' | 'FII';
  ex_date: string; // ISO date string (YYYY-MM-DD)
  ratio?: string; // Optional for TICKER_CHANGE
  description?: string;
}

export interface CorporateEventApplyResponse {
  success: boolean;
  message: string;
  positions_adjusted?: number;
  positions_updated?: number; // For TICKER_CHANGE
  operations_updated?: number; // For TICKER_CHANGE
  ticker?: string;
  event_type?: string;
  ratio?: string;
}

