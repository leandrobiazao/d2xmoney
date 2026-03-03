import { Component, EventEmitter, Input, Output, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PdfParserService, NoteParseResult } from '../pdf-parser.service';
import { Operation } from '../operation.model';
import { TickerDialogComponent } from '../ticker-dialog/ticker-dialog';
import { TickerMappingService } from '../../portfolio/ticker-mapping/ticker-mapping.service';
import { DebugService } from '../../shared/services/debug.service';

export interface OperationsAddedEvent {
  /** One note per item; single-note PDFs produce an array of length 1. */
  notes: NoteParseResult[];
  fileName?: string;
  accountNumber?: string;
}

@Component({
  selector: 'app-upload-pdf',
  standalone: true,
  imports: [CommonModule, TickerDialogComponent],
  templateUrl: './upload-pdf.html',
  styleUrl: './upload-pdf.css'
})
export class UploadPdfComponent implements OnInit, OnDestroy {
  @Input() clientId!: string;
  @Output() operationsAdded = new EventEmitter<OperationsAddedEvent>();

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
        this.debug.log(`🔔 onTickerRequired called for: "${nome}"`);
        this.debug.log(`🔔 Setting up dialog state...`);
        
        return new Promise((resolve) => {
          this.currentNome = nome;
          this.currentOperationData = operationData;
          this.pendingTickerResolve = resolve;
          this.showTickerDialog = true;
          
          this.debug.log(`🔔 Dialog state set: showTickerDialog=${this.showTickerDialog}, currentNome="${this.currentNome}"`);
          this.debug.log(`🔔 Waiting for user input...`);
          
          // Add a small delay to ensure Angular detects the change
          setTimeout(() => {
            this.debug.log(`🔔 Dialog should be visible now. showTickerDialog=${this.showTickerDialog}`);
          }, 100);
        });
      };
      
      let parseResult: { notes: NoteParseResult[]; accountNumber?: string };
      try {
        parseResult = await this.pdfParserService.parsePdf(this.selectedFile, onTickerRequired);
      } catch (parseError) {
        const errorMsg = parseError instanceof Error ? parseError.message : 'Erro desconhecido ao processar PDF';
        this.errorMessage = errorMsg;
        this.isProcessing = false;
        this.debug.error('PDF parsing error:', parseError);
        return;
      }

      const hasAnyOperations = parseResult.notes.some(n => n.operations.length > 0);
      if (!hasAnyOperations || parseResult.notes.length === 0) {
        this.errorMessage = 'Nenhuma operação foi encontrada no PDF. Verifique se o arquivo é uma nota de corretagem válida da B3.';
        this.isProcessing = false;
        return;
      }

      const notesWithClientId: NoteParseResult[] = parseResult.notes.map(n => ({
        ...n,
        operations: n.operations.map(op => ({ ...op, clientId: this.clientId }))
      }));

      this.operationsAdded.emit({
        notes: notesWithClientId,
        fileName: this.selectedFile.name,
        accountNumber: parseResult.accountNumber
      });

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
