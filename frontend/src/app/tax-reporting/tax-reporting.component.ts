import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TaxReportingService } from './tax-reporting.service';
import { CapitalGainsReport } from './tax-reporting.models';
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
    if (changes['userId'] && this.userId) {
      this.report = null;
      this.errorMessage = null;
      this.loadReport();
    }
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
      exportCapitalGainsReportToExcel(this.report, this.userName || 'Cliente');
    } catch {
      this.errorMessage = 'Erro ao exportar arquivo Excel.';
    }
  }

  get canExport(): boolean {
    return !!this.report && !this.isLoading;
  }
}
