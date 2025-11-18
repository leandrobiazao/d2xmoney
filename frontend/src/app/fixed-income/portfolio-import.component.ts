import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FixedIncomeService } from './fixed-income.service';
import { ImportResult } from './fixed-income.models';

@Component({
  selector: 'app-portfolio-import',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './portfolio-import.component.html',
  styleUrl: './portfolio-import.component.css'
})
export class PortfolioImportComponent {
  @Input() userId!: string;
  
  selectedFile: File | null = null;
  isImporting = false;
  importResult: ImportResult | null = null;
  errorMessage: string | null = null;

  constructor(private fixedIncomeService: FixedIncomeService) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      this.errorMessage = null;
      this.importResult = null;
    }
  }

  onImport(): void {
    if (!this.selectedFile || !this.userId) {
      this.errorMessage = 'Por favor, selecione um arquivo.';
      return;
    }

    this.isImporting = true;
    this.errorMessage = null;
    this.importResult = null;

    this.fixedIncomeService.importExcel(this.selectedFile, this.userId).subscribe({
      next: (result) => {
        this.importResult = result;
        this.isImporting = false;
        
        // Check if there are errors in the result
        if (result.errors && result.errors.length > 0) {
          const errorText = result.errors.join('\n');
          let debugInfo = '';
          if (result.debug_info && result.debug_info.length > 0) {
            debugInfo = '\n\nInformações de debug:\n' + result.debug_info.join('\n');
          }
          this.errorMessage = `Erros durante a importação:\n${errorText}${debugInfo}`;
        } else if (result.created === 0 && result.updated === 0) {
          let debugInfo = '';
          if (result.debug_info && result.debug_info.length > 0) {
            debugInfo = '\n\nInformações de debug:\n' + result.debug_info.join('\n');
          }
          this.errorMessage = 'Nenhum registro foi importado. Verifique se o arquivo contém dados válidos nas seções "RENDA FIXA" ou "TESOURO DIRETO".' + debugInfo;
        }
      },
      error: (error) => {
        console.error('Import error:', error);
        const errorMsg = error.error?.error || error.error?.details || error.message || 'Erro ao importar arquivo Excel.';
        this.errorMessage = `Erro ao importar arquivo: ${errorMsg}`;
        this.isImporting = false;
      }
    });
  }
}

