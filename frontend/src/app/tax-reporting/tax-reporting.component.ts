import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TaxReportingService } from './tax-reporting.service';
import {
  AssetClass,
  CapitalGainsReport,
  CarryforwardMonth,
  TaxReportSection,
  YearEndPosition,
} from './tax-reporting.models';
import { exportCapitalGainsReportToExcel } from './tax-reporting-excel';
import { formatCurrency } from '../shared/utils/common-utils';

@Component({
  selector: 'app-tax-reporting',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './tax-reporting.component.html',
  styleUrl: './tax-reporting.component.css'
})
export class TaxReportingComponent implements OnInit, OnChanges {
  @Input() userId!: string;
  @Input() userName = '';
  @Input() section: TaxReportSection = 'acoes';

  selectedYear = 2025;
  availableYears: number[] = [];
  report: CapitalGainsReport | null = null;
  isLoading = false;
  errorMessage: string | null = null;

  formatCurrency = formatCurrency;

  constructor(private taxReportingService: TaxReportingService) {
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= currentYear - 5; y--) {
      this.availableYears.push(y);
    }
  }

  ngOnInit(): void {
    if (this.userId) {
      this.loadReport();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ((changes['userId'] || changes['section']) && this.userId) {
      this.report = null;
      this.errorMessage = null;
      this.loadReport();
    }
  }

  get isCarryforwardSection(): boolean {
    return this.section === 'acoes' || this.section === 'fii';
  }

  get pageTitle(): string {
    switch (this.section) {
      case 'acoes':
        return 'IRPF — Ganho de Capital (Ações)';
      case 'fii':
        return 'IRPF — Ganho de Capital (FIIs)';
      default:
        return 'IRPF — Ganho de Capital (ETF e BDR)';
    }
  }

  get yearSelectorId(): string {
    return `irpf-${this.section}-year`;
  }

  get carryforwardMonths(): CarryforwardMonth[] {
    if (!this.report || !this.isCarryforwardSection) {
      return [];
    }
    return this.section === 'acoes' ? this.report.acoes.months : this.report.fii.months;
  }

  get remainingLossCarryforward(): number {
    if (!this.report || !this.isCarryforwardSection) {
      return 0;
    }
    return this.section === 'acoes'
      ? this.report.acoes.year_summary.remaining_loss_carryforward
      : this.report.fii.year_summary.remaining_loss_carryforward;
  }

  get filteredPositions(): YearEndPosition[] {
    if (!this.report) {
      return [];
    }
    const classesBySection: Record<TaxReportSection, AssetClass[]> = {
      acoes: ['acoes'],
      fii: ['fii'],
      etf_bdr: ['etf', 'bdr'],
    };
    const classes = classesBySection[this.section];
    return this.report.position_at_year_end.filter((p) => classes.includes(p.asset_class));
  }

  onYearChange(year: number | string): void {
    this.selectedYear = typeof year === 'string' ? parseInt(year, 10) : year;
    this.loadReport();
  }

  loadReport(): void {
    if (!this.userId) {
      return;
    }
    this.isLoading = true;
    this.errorMessage = null;
    this.taxReportingService.getCapitalGainsReport(this.userId, this.selectedYear).subscribe({
      next: (report) => {
        this.report = report;
        this.isLoading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.error || 'Erro ao carregar relatório IRPF.';
        this.isLoading = false;
      }
    });
  }

  exportExcel(): void {
    if (!this.report) {
      return;
    }
    try {
      exportCapitalGainsReportToExcel(this.report, this.userName || 'Cliente', this.section);
    } catch {
      this.errorMessage = 'Erro ao exportar arquivo Excel.';
    }
  }

  get canExport(): boolean {
    return !!this.report && !this.isLoading;
  }
}
