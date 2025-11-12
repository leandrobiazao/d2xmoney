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
  
  // Server status
  serverStatus: 'checking' | 'online' | 'offline' = 'checking';
  
  private tickerUpdateListener?: (event: CustomEvent) => void;

  constructor(
    private pdfParserService: PdfParserService,
    private tickerMappingService: TickerMappingService,
    private debug: DebugService
  ) {}

  ngOnInit(): void {
    this.checkServerStatus();
    
    this.tickerUpdateListener = (event: CustomEvent) => {
      const detail = event.detail;
      if (detail.success) {
        this.serverStatus = 'online';
      } else {
        this.serverStatus = 'offline';
      }
    };
    
    window.addEventListener('ticker-mappings-updated', this.tickerUpdateListener as EventListener);
  }

  private async checkServerStatus(): Promise<void> {
    this.serverStatus = 'checking';
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);
      
      const response = await fetch('/api/ticker-mappings/', {
        method: 'HEAD',
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (response.status === 200 || response.status === 405 || response.status === 404) {
        this.serverStatus = 'online';
      } else {
        this.serverStatus = 'offline';
      }
    } catch (error) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const testResponse = await fetch('/api/users/', {
          method: 'HEAD',
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        this.serverStatus = 'online';
      } catch (backendError) {
        this.serverStatus = 'offline';
        this.debug.warn('Backend não está acessível. Certifique-se de que o Django está rodando na porta 8000.');
      }
    }
  }

  ngOnDestroy(): void {
    if (this.tickerUpdateListener) {
      window.removeEventListener('ticker-mappings-updated', this.tickerUpdateListener as EventListener);
    }
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

      this.successMessage = `${operations.length} operação(ões) importada(s) com sucesso!`;
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
