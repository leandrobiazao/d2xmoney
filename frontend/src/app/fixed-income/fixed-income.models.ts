export interface FixedIncomePosition {
  id: number;
  user_id: string;
  asset_name: string;
  asset_code: string;
  application_date: string;
  grace_period_end?: string;
  maturity_date: string;
  price_date?: string;
  rate?: string;
  price?: number;
  quantity: number;
  available_quantity: number;
  guarantee_quantity: number;
  applied_value: number;
  position_value: number;
  net_value: number;
  gross_yield: number;
  net_yield: number;
  income_tax: number;
  iof: number;
  rating?: string;
  liquidity?: string;
  interest?: string;
  investment_type?: number;
  investment_type_name?: string;
  investment_sub_type?: number;
  investment_sub_type_name?: string;
  source: string;
  import_date?: string;
  created_at: string;
  updated_at: string;
}

export interface TesouroDiretoPosition {
  id: number;
  fixed_income_position: FixedIncomePosition;
  titulo_name: string;
  vencimento: string;
  created_at: string;
  updated_at: string;
}

export interface ImportResult {
  created: number;
  updated: number;
  errors: string[];
  cdb_count: number;
  tesouro_count: number;
  debug_info?: string[];
  error_details?: string;
}


