import * as XLSX from 'xlsx';
import { CapitalGainsReport } from './tax-reporting.models';

function sanitizeFilenamePart(value: string): string {
  return value.replace(/[\\/:*?"<>|]/g, '').trim() || 'cliente';
}

function downloadWorkbook(workbook: XLSX.WorkBook, filename: string): void {
  const wbout = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
  const blob = new Blob(
    [wbout],
    { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }
  );
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

export function exportCapitalGainsReportToExcel(
  report: CapitalGainsReport,
  userName: string
): void {
  const workbook = XLSX.utils.book_new();

  const monthsRows = report.months.map((m) => ({
    'Mês': m.label,
    'Vendas ações (R$)': m.acoes_sales,
    'Vendas BDR (R$)': m.bdr_sales,
    'Vendas total (R$)': m.total_sales,
    'Isento?': m.is_exempt ? 'Sim' : 'Não',
    'Ações isentas?': m.acoes_exempt ? 'Sim' : 'Não',
    'Lucro (R$)': m.gross_gain,
    'Prejuízo (R$)': m.gross_loss,
    'Resultado (R$)': m.net_result,
    'Base tributável (R$)': m.taxable_gain,
    'IR 15% (R$)': m.tax_due,
    'IRRF (R$)': m.irrf_withheld,
    'DARF (R$)': m.darf_amount,
    'Vencimento DARF': m.darf_due_date,
    'Qtd vendas': m.sales_count,
  }));

  if (monthsRows.length > 0) {
    monthsRows.push({
      'Mês': 'Totais',
      'Vendas ações (R$)': report.months.reduce((s, m) => s + m.acoes_sales, 0),
      'Vendas BDR (R$)': report.months.reduce((s, m) => s + m.bdr_sales, 0),
      'Vendas total (R$)': report.months.reduce((s, m) => s + m.total_sales, 0),
      'Isento?': '',
      'Ações isentas?': '',
      'Lucro (R$)': report.months.reduce((s, m) => s + m.gross_gain, 0),
      'Prejuízo (R$)': report.months.reduce((s, m) => s + m.gross_loss, 0),
      'Resultado (R$)': report.months.reduce((s, m) => s + m.net_result, 0),
      'Base tributável (R$)': report.year_summary.total_taxable_gain,
      'IR 15% (R$)': report.year_summary.total_tax_due,
      'IRRF (R$)': report.year_summary.total_irrf,
      'DARF (R$)': report.months.reduce((s, m) => s + m.darf_amount, 0),
      'Vencimento DARF': '',
      'Qtd vendas': report.months.reduce((s, m) => s + m.sales_count, 0),
    });
  }

  const monthsSheet = XLSX.utils.json_to_sheet(monthsRows);
  XLSX.utils.book_append_sheet(workbook, monthsSheet, 'Meses com Vendas');

  const positionsRows = report.position_at_year_end.map((p) => ({
    'Ticker': p.ticker,
    'Tipo': p.asset_class_label,
    'Quantidade': p.quantidade,
    'Preço médio (R$)': p.preco_medio,
    'Custo total (R$)': p.valor_total_investido,
  }));
  const positionsSheet = XLSX.utils.json_to_sheet(positionsRows);
  XLSX.utils.book_append_sheet(
    workbook,
    positionsSheet,
    `Posição 31-12-${report.year}`
  );

  const safeName = sanitizeFilenamePart(userName);
  const filename = `${safeName} - IRPF Ações BDR ${report.year}.xlsx`;
  downloadWorkbook(workbook, filename);
}
