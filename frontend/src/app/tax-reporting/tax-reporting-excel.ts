import * as XLSX from 'xlsx';
import { AssetClass, CapitalGainsReport, TaxReportSection } from './tax-reporting.models';

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

function filterPositions(report: CapitalGainsReport, classes: AssetClass[]) {
  return report.position_at_year_end.filter((p) => classes.includes(p.asset_class));
}

function appendPositionsSheet(
  workbook: XLSX.WorkBook,
  report: CapitalGainsReport,
  classes: AssetClass[]
): void {
  const positions = filterPositions(report, classes);
  const positionsSheet = XLSX.utils.json_to_sheet(
    positions.map((p) => ({
      'Ticker': p.ticker,
      'Tipo': p.asset_class_label,
      'Quantidade': p.quantidade,
      'Preço médio (R$)': p.preco_medio,
      'Custo total (R$)': p.valor_total_investido,
    }))
  );
  XLSX.utils.book_append_sheet(workbook, positionsSheet, `Posição 31-12-${report.year}`);
}

export function exportCapitalGainsReportToExcel(
  report: CapitalGainsReport,
  userName: string,
  section: TaxReportSection = 'acoes'
): void {
  const workbook = XLSX.utils.book_new();
  const safeName = sanitizeFilenamePart(userName);

  if (section === 'acoes') {
    const months = report.acoes.months;
    const monthsRows = months.map((m) => ({
      'Mês': m.label,
      'Vendas (R$)': m.total_sales,
      'Isento?': m.is_exempt ? 'Sim' : 'Não',
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
        'Vendas (R$)': months.reduce((s, m) => s + m.total_sales, 0),
        'Isento?': '',
        'Lucro (R$)': months.reduce((s, m) => s + m.gross_gain, 0),
        'Prejuízo (R$)': months.reduce((s, m) => s + m.gross_loss, 0),
        'Resultado (R$)': months.reduce((s, m) => s + m.net_result, 0),
        'Base tributável (R$)': report.acoes.year_summary.total_taxable_gain,
        'IR 15% (R$)': report.acoes.year_summary.total_tax_due,
        'IRRF (R$)': report.acoes.year_summary.total_irrf,
        'DARF (R$)': months.reduce((s, m) => s + m.darf_amount, 0),
        'Vencimento DARF': '',
        'Qtd vendas': months.reduce((s, m) => s + m.sales_count, 0),
      });
    }

    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(monthsRows), 'Ações');
    appendPositionsSheet(workbook, report, ['acoes']);
    downloadWorkbook(workbook, `${safeName} - IRPF Ações ${report.year}.xlsx`);
    return;
  }

  if (section === 'fii') {
    const months = report.fii.months;
    const monthsRows = months.map((m) => ({
      'Mês': m.label,
      'Vendas (R$)': m.total_sales,
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
        'Vendas (R$)': months.reduce((s, m) => s + m.total_sales, 0),
        'Lucro (R$)': months.reduce((s, m) => s + m.gross_gain, 0),
        'Prejuízo (R$)': months.reduce((s, m) => s + m.gross_loss, 0),
        'Resultado (R$)': months.reduce((s, m) => s + m.net_result, 0),
        'Base tributável (R$)': report.fii.year_summary.total_taxable_gain,
        'IR 15% (R$)': report.fii.year_summary.total_tax_due,
        'IRRF (R$)': report.fii.year_summary.total_irrf,
        'DARF (R$)': months.reduce((s, m) => s + m.darf_amount, 0),
        'Vencimento DARF': '',
        'Qtd vendas': months.reduce((s, m) => s + m.sales_count, 0),
      });
    }

    XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(monthsRows), 'FIIs');
    appendPositionsSheet(workbook, report, ['fii']);
    downloadWorkbook(workbook, `${safeName} - IRPF FIIs ${report.year}.xlsx`);
    return;
  }

  const months = report.etf_bdr.months;
  const monthsRows = months.map((m) => ({
    'Mês': m.label,
    'Vendas ETF (R$)': m.etf_sales,
    'Vendas BDR (R$)': m.bdr_sales,
    'Vendas total (R$)': m.total_sales,
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
      'Vendas ETF (R$)': months.reduce((s, m) => s + m.etf_sales, 0),
      'Vendas BDR (R$)': months.reduce((s, m) => s + m.bdr_sales, 0),
      'Vendas total (R$)': months.reduce((s, m) => s + m.total_sales, 0),
      'Lucro (R$)': months.reduce((s, m) => s + m.gross_gain, 0),
      'Prejuízo (R$)': months.reduce((s, m) => s + m.gross_loss, 0),
      'Resultado (R$)': months.reduce((s, m) => s + m.net_result, 0),
      'Base tributável (R$)': report.etf_bdr.year_summary.total_taxable_gain,
      'IR 15% (R$)': report.etf_bdr.year_summary.total_tax_due,
      'IRRF (R$)': report.etf_bdr.year_summary.total_irrf,
      'DARF (R$)': months.reduce((s, m) => s + m.darf_amount, 0),
      'Vencimento DARF': '',
      'Qtd vendas': months.reduce((s, m) => s + m.sales_count, 0),
    });
  }

  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(monthsRows), 'ETF e BDR');
  appendPositionsSheet(workbook, report, ['etf', 'bdr']);
  downloadWorkbook(workbook, `${safeName} - IRPF ETF BDR ${report.year}.xlsx`);
}
