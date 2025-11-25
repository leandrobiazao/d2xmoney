export interface CryptoCurrency {
  id: number;
  symbol: string;
  name: string;
  investment_type?: {
    id: number;
    name: string;
    code: string;
  };
  investment_type_id?: number;
  investment_subtype?: {
    id: number;
    name: string;
    code: string;
  };
  investment_subtype_id?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CryptoOperation {
  id: number;
  user_id: string;
  crypto_currency: CryptoCurrency;
  crypto_currency_id: number;
  operation_type: 'BUY' | 'SELL';
  quantity: number;
  price: number;
  operation_date: string;
  broker?: string;
  notes?: string;
  total_value?: number;
  created_at: string;
  updated_at: string;
}

export interface CryptoPosition {
  id: number;
  user_id: string;
  crypto_currency: CryptoCurrency;
  crypto_currency_id: number;
  quantity: number;
  average_price: number;
  broker?: string;
  total_invested?: number;
  current_price?: number; // Preço atual da moeda (calculado via yfinance)
  current_value?: number; // Valor atual da posição (quantity × current_price)
  created_at: string;
  updated_at: string;
}

