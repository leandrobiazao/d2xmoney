import { InvestmentType, InvestmentSubType } from '../configuration.service';

export interface Stock {
  id: number;
  ticker: string;
  name: string;
  cnpj?: string;
  investment_type?: InvestmentType;
  investment_type_id?: number;
  investment_subtype?: InvestmentSubType;
  investment_subtype_id?: number;
  financial_market: string;
  stock_class: string;
  current_price: number;
  last_updated: string;
  is_active: boolean;
}

