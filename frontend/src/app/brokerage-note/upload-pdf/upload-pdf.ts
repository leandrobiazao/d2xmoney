import { Component, EventEmitter, Input, Output, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PdfParserService } from '../pdf-parser.service';
import { Operation } from '../operation.model';
import { TickerDialogComponent } from '../ticker-dialog/ticker-dialog';
import { TickerMappingService } from '../../portfolio/ticker-mapping/ticker-mapping.service';
import { DebugService } from '../../shared/services/debug.service';

@Component({
  selector: 'app-upload-pdf',
  standalone: true,
  imports: [CommonModule, TickerDialogComponent],
  templateUrl: './upload-pdf.html',
  styleUrl: './upload-pdf.css'
})
export class UploadPdfComponent implements OnInit, OnDestroy {
  @Input() clientId!: string;
  @Output() operationsAdded = new EventEmitter<Operation[]>();

  isProcessing = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;
  selectedFile: File | null = null;
  
  // Dialog state
  showTickerDialog = false;
  pendingTickerResolve: ((value: string | null) => void) | null = null;
  currentNome: string = '';
  currentOperationData: any = null;

  constructor(
    private pdfParserService: PdfParserService,
    private tickerMappingService: TickerMappingService,
    private debug: DebugService
  ) {}

  ngOnInit(): void {
    // Component initialization
  }

  ngOnDestroy(): void {
    // Cleanup if needed
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      if (file.type !== 'application/pdf') {
        this.errorMessage = 'Por favor, selecione um arquivo PDF.';
        this.successMessage = null;
        return;
      }
      this.selectedFile = file;
      this.errorMessage = null;
      this.successMessage = null;
      
      // Show confirmation popup
      const confirmed = confirm(`Deseja fazer upload e processar o arquivo "${file.name}"?`);
      if (confirmed) {
        this.onUpload();
      } else {
        // Reset file selection if user cancels
        this.selectedFile = null;
        if (input) {
          input.value = '';
        }
      }
    }
  }

  async onUpload(): Promise<void> {
    if (!this.selectedFile || !this.clientId) {
      this.errorMessage = 'Por favor, selecione um arquivo PDF.';
      return;
    }

    if (this.isProcessing || this.showTickerDialog) {
      return;
    }

    this.isProcessing = true;
    this.errorMessage = null;
    this.successMessage = null;

    try {
      const onTickerRequired = async (nome: string, operationData: any): Promise<string | null> => {
        return new Promise((resolve) => {
          this.currentNome = nome;
          this.currentOperationData = operationData;
          this.pendingTickerResolve = resolve;
          this.showTickerDialog = true;
        });
      };
      
      const operations = await this.pdfParserService.parsePdf(this.selectedFile, onTickerRequired);

      if (operations.length === 0) {
        this.errorMessage = 'Nenhuma operação foi encontrada no PDF. Verifique se o arquivo é uma nota de corretagem válida da B3.';
        this.isProcessing = false;
        return;
      }

      const operationsWithClientId = operations.map(op => ({
        ...op,
        clientId: this.clientId
      }));

      // Emit operations - success/error will be handled by parent component
      this.operationsAdded.emit(operationsWithClientId);

      this.selectedFile = null;
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      if (fileInput) {
        fileInput.value = '';
      }
    } catch (error) {
      this.debug.error('Error uploading PDF:', error);
      this.errorMessage = error instanceof Error ? error.message : 'Erro ao processar o PDF. Tente novamente.';
    } finally {
      this.isProcessing = false;
      if (!this.showTickerDialog && this.pendingTickerResolve) {
        this.pendingTickerResolve = null;
      }
    }
  }

  clearMessages(): void {
    this.errorMessage = null;
    this.successMessage = null;
  }

  onTickerConfirm(ticker: string): void {
    if (this.pendingTickerResolve) {
      this.pendingTickerResolve(ticker);
      this.pendingTickerResolve = null;
    }
    
    this.showTickerDialog = false;
    this.currentNome = '';
    this.currentOperationData = null;
  }

  onTickerCancel(): void {
    if (this.pendingTickerResolve) {
      this.pendingTickerResolve(null);
      this.pendingTickerResolve = null;
    }
    this.showTickerDialog = false;
    this.currentNome = '';
    this.currentOperationData = null;
  }
}
