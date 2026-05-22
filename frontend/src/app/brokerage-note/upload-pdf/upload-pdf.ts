import { Component, EventEmitter, Input, Output, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PdfParserService, NoteParseResult } from '../pdf-parser.service';
import { mapAccountProviderToPdfBroker } from '../map-account-provider-to-pdf-broker';
import { TickerDialogComponent } from '../ticker-dialog/ticker-dialog';
import { DebugService } from '../../shared/services/debug.service';
import {
  isPdfFile,
  MAX_BATCH_PDF_FILES,
  sortPdfFilesByNoteDate,
} from './upload-pdf-file-order';

export interface BatchUploadContext {
  batchId: string;
  fileIndex: number;
  fileTotal: number;
  isLast: boolean;
}

export interface FileSaveResult {
  ok: boolean;
  savedNoteNumbers: string[];
  skipped?: boolean;
  error?: string;
}

export interface OperationsAddedEvent {
  /** One note per item; single-note PDFs produce an array of length 1. */
  notes: NoteParseResult[];
  fileName?: string;
  accountNumber?: string;
  batch?: BatchUploadContext;
  /** Called when the parent finishes saving (multi-file upload waits before next PDF). */
  resolveSave?: (result: FileSaveResult) => void;
}

export type BatchFileStatus = 'success' | 'error' | 'skipped';

export interface BatchFileResult {
  fileName: string;
  status: BatchFileStatus;
  message?: string;
  savedNotes?: string[];
}

@Component({
  selector: 'app-upload-pdf',
  standalone: true,
  imports: [CommonModule, TickerDialogComponent],
  templateUrl: './upload-pdf.html',
  styleUrl: './upload-pdf.css'
})
export class UploadPdfComponent {
  @Input() clientId!: string;
  /** From User.account_provider — selects XP vs BTG PDF layout. */
  @Input() accountProvider: string | undefined;
  @Output() operationsAdded = new EventEmitter<OperationsAddedEvent>();

  @ViewChild('fileInput') fileInputRef!: ElementRef<HTMLInputElement>;

  isProcessing = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;
  batchProgress: { current: number; total: number; fileName: string } | null = null;
  batchResults: BatchFileResult[] | null = null;

  showTickerDialog = false;
  pendingTickerResolve: ((value: string | null) => void) | null = null;
  currentNome = '';
  currentOperationData: unknown = null;

  constructor(
    private pdfParserService: PdfParserService,
    private debug: DebugService
  ) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) {
      return;
    }

    const allFiles = Array.from(input.files);
    const pdfFiles = allFiles.filter(isPdfFile);
    const rejected = allFiles.length - pdfFiles.length;

    if (pdfFiles.length === 0) {
      this.errorMessage = 'Por favor, selecione um ou mais arquivos PDF.';
      this.successMessage = null;
      this.batchResults = null;
      this.resetFileInput();
      return;
    }

    if (pdfFiles.length > MAX_BATCH_PDF_FILES) {
      this.errorMessage = `Máximo de ${MAX_BATCH_PDF_FILES} arquivos por vez. Selecionados: ${pdfFiles.length}.`;
      this.resetFileInput();
      return;
    }

    const sorted = sortPdfFilesByNoteDate(pdfFiles);
    let confirmMsg: string;
    if (sorted.length === 1) {
      confirmMsg = `Deseja fazer upload e processar o arquivo "${sorted[0].name}"?`;
    } else {
      const preview = sorted.slice(0, 5).map(f => `• ${f.name}`).join('\n');
      const more = sorted.length > 5 ? `\n… e mais ${sorted.length - 5} arquivo(s)` : '';
      const rejectedMsg = rejected > 0 ? `\n\n(${rejected} arquivo(s) ignorado(s) — não são PDF.)` : '';
      confirmMsg =
        `Deseja processar ${sorted.length} arquivos PDF?\n\n` +
        `Ordem: por data no nome do arquivo (mais antigo primeiro).\n\n${preview}${more}${rejectedMsg}`;
    }

    if (!confirm(confirmMsg)) {
      this.resetFileInput();
      return;
    }

    this.errorMessage = null;
    this.successMessage = null;
    this.batchResults = null;
    void this.processFileQueue(sorted);
  }

  /** Allow drag-and-drop on the upload zone. */
  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    if (this.isProcessing) {
      return;
    }
    const files = event.dataTransfer?.files;
    if (!files?.length) {
      return;
    }
    const input = this.fileInputRef?.nativeElement;
    if (!input) {
      return;
    }
    const dt = new DataTransfer();
    Array.from(files).forEach(f => dt.items.add(f));
    input.files = dt.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
  }

  private async processFileQueue(files: File[]): Promise<void> {
    if (!this.clientId || this.isProcessing) {
      return;
    }

    this.isProcessing = true;
    const batchId = crypto.randomUUID();
    const results: BatchFileResult[] = [];
    const total = files.length;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileIndex = i + 1;
      this.batchProgress = { current: fileIndex, total, fileName: file.name };

      try {
        const saveResult = await this.parseAndSaveFile(file, {
          batchId,
          fileIndex,
          fileTotal: total,
          isLast: fileIndex === total,
        });
        if (saveResult.skipped) {
          results.push({
            fileName: file.name,
            status: 'skipped',
            message: saveResult.error ?? 'Arquivo ignorado.',
          });
        } else if (saveResult.ok) {
          results.push({
            fileName: file.name,
            status: 'success',
            savedNotes: saveResult.savedNoteNumbers,
            message:
              saveResult.savedNoteNumbers.length === 1
                ? `Nota ${saveResult.savedNoteNumbers[0]} importada.`
                : `Notas ${saveResult.savedNoteNumbers.join(', ')} importadas.`,
          });
        } else {
          results.push({
            fileName: file.name,
            status: 'error',
            message: saveResult.error ?? 'Erro ao salvar.',
          });
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Erro ao processar o PDF.';
        this.debug.error('Batch PDF error:', file.name, err);
        results.push({ fileName: file.name, status: 'error', message: msg });
      }
    }

    this.batchProgress = null;
    this.batchResults = results;
    this.isProcessing = false;
    this.resetFileInput();
    this.showBatchSummary(results);
  }

  private parseAndSaveFile(
    file: File,
    batch: BatchUploadContext
  ): Promise<FileSaveResult> {
    return new Promise(async (resolve, reject) => {
      try {
        const onTickerRequired = (nome: string, operationData: unknown): Promise<string | null> =>
          new Promise(res => {
            this.currentNome = nome;
            this.currentOperationData = operationData;
            this.pendingTickerResolve = res;
            this.showTickerDialog = true;
          });

        const pdfBroker = mapAccountProviderToPdfBroker(this.accountProvider);
        const parseResult = await this.pdfParserService.parsePdf(file, onTickerRequired, pdfBroker);

        const hasAnyOperations = parseResult.notes.some(n => n.operations.length > 0);
        if (!hasAnyOperations || parseResult.notes.length === 0) {
          reject(
            new Error(
              'Nenhuma operação encontrada. Verifique se o PDF é uma nota válida (XP, BTG ou CLEAR) com camada de texto.'
            )
          );
          return;
        }

        const notesWithClientId: NoteParseResult[] = parseResult.notes.map(n => ({
          ...n,
          operations: n.operations.map(op => ({ ...op, clientId: this.clientId })),
        }));

        let settled = false;
        const settle = (result: FileSaveResult) => {
          if (settled) {
            return;
          }
          settled = true;
          resolve(result);
        };

        this.operationsAdded.emit({
          notes: notesWithClientId,
          fileName: file.name,
          accountNumber: parseResult.accountNumber,
          batch,
          resolveSave: settle,
        });

        // Parent must call resolveSave; fallback if it does not (should not happen).
        setTimeout(() => {
          if (!settled) {
            this.debug.warn('resolveSave not called for', file.name);
            settle({ ok: false, savedNoteNumbers: [], error: 'Salvamento não confirmado pelo portfólio.' });
          }
        }, 120_000);
      } catch (e) {
        reject(e);
      }
    });
  }

  private showBatchSummary(results: BatchFileResult[]): void {
    const ok = results.filter(r => r.status === 'success').length;
    const err = results.filter(r => r.status === 'error').length;
    const skip = results.filter(r => r.status === 'skipped').length;

    if (results.length === 1 && ok === 1) {
      this.successMessage = results[0].message ?? 'Nota importada com sucesso.';
      return;
    }

    const parts: string[] = [];
    if (ok > 0) {
      parts.push(`${ok} importado(s)`);
    }
    if (err > 0) {
      parts.push(`${err} com erro`);
    }
    if (skip > 0) {
      parts.push(`${skip} ignorado(s)`);
    }
    this.successMessage = `Processamento concluído: ${parts.join(', ')}.`;
    if (err > 0 || skip > 0) {
      this.errorMessage = results
        .filter(r => r.status !== 'success')
        .map(r => `${r.fileName}: ${r.message}`)
        .join('\n');
    }
  }

  clearMessages(): void {
    this.errorMessage = null;
    this.successMessage = null;
    this.batchResults = null;
  }

  clearBatchResults(): void {
    this.batchResults = null;
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

  private resetFileInput(): void {
    const input = this.fileInputRef?.nativeElement;
    if (input) {
      input.value = '';
    }
  }

  get progressPercent(): number {
    if (!this.batchProgress) {
      return 0;
    }
    return Math.round((this.batchProgress.current / this.batchProgress.total) * 100);
  }
}
