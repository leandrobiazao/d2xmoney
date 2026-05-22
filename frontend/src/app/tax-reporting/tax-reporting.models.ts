export type TaxReportSection = 'acoes' | 'fii' | 'etf_bdr';

export type AssetClass = 'acoes' | 'fii' | 'etf' | 'bdr';

export interface CarryforwardMonth {
  month: number;
  label: string;
  total_sales: number;
  is_exempt: boolean;
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

export interface EtfBdrMonth {
  month: number;
  label: string;
  total_sales: number;
  etf_sales: number;
  bdr_sales: number;
  gross_gain: number;
  gross_loss: number;
  net_result: number;
  taxable_gain: number;
  tax_rate: number;
  tax_due: number;
  irrf_withheld: number;
  darf_amount: number;
  darf_due_date: string;
  sales_count: number;
}

export interface CarryforwardYearSummary {
  total_taxable_gain: number;
  total_tax_due: number;
  total_irrf: number;
  remaining_loss_carryforward: number;
}

export interface EtfBdrYearSummary {
  total_taxable_gain: number;
  total_tax_due: number;
  total_irrf: number;
}

export interface YearEndPosition {
  ticker: string;
  asset_class: AssetClass;
  asset_class_label: string;
  quantidade: number;
  preco_medio: number;
  valor_total_investido: number;
}

export interface CapitalGainsReport {
  year: number;
  acoes: {
    months_with_sales_count: number;
    months: CarryforwardMonth[];
    year_summary: CarryforwardYearSummary;
  };
  fii: {
    months_with_sales_count: number;
    months: CarryforwardMonth[];
    year_summary: CarryforwardYearSummary;
  };
  etf_bdr: {
    months_with_sales_count: number;
    months: EtfBdrMonth[];
    year_summary: EtfBdrYearSummary;
  };
  position_at_year_end: YearEndPosition[];
}
