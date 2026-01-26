export interface InvestmentFund {
  id: number;
  user_id: string;
  fund_name: string;
  fund_cnpj?: string;
  fund_type: 'RF_POS' | 'RF_PRE' | 'RF_IPCA' | 'MULTI' | 'ACOES' | 'CAMBIO' | 'OTHER';
  fund_type_display: string;
  quota_date?: string; // ISO date string
  quota_value?: number | string; // Can be string from Django DecimalField
  quota_quantity: number | string;
  in_quotation: number | string;
  position_value: number | string;
  net_value: number | string;
  applied_value: number | string;
  gross_return_percent?: number | string;
  net_return_percent?: number | string;
  source: string;
  import_date?: string;
  created_at: string;
  updated_at: string;
  allocation_percent?: number;
}

export interface InvestmentFundSummary {
  summary: {
    [fundType: string]: {
      count: number;
      total_position: number;
      total_net_value: number;
      total_applied: number;
      allocation_percent: number;
    };
  };
  total_position: number;
  total_funds: number;
}








