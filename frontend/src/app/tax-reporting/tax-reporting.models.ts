export interface CapitalGainsMonth {
  month: number;
  label: string;
  total_sales: number;
  acoes_sales: number;
  bdr_sales: number;
  is_exempt: boolean;
  acoes_exempt: boolean;
  gross_gain: number;
  gross_loss: number;
  net_result: number;
  loss_carryforward_in: number;
  loss_carryforward_out: number;
  taxable_gain: number;
  tax_rate: number;
  tax_due: number;
  irrf_withheld: number;
  darf_amount: number;
  darf_due_date: string;
  sales_count: number;
}

export interface YearEndPosition {
  ticker: string;
  asset_class: 'acoes' | 'bdr';
  asset_class_label: string;
  quantidade: number;
  preco_medio: number;
  valor_total_investido: number;
}

export interface CapitalGainsReport {
  year: number;
  months_with_sales_count: number;
  months: CapitalGainsMonth[];
  year_summary: {
    total_taxable_gain: number;
    total_tax_due: number;
    total_irrf: number;
    remaining_loss_carryforward: number;
  };
  position_at_year_end: YearEndPosition[];
}
