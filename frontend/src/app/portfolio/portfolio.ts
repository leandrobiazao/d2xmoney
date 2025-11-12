import { Component, Input, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from './portfolio.service';
import { Operation } from '../brokerage-note/operation.model';
import { Position } from './position.model';
import { UploadPdfComponent } from '../brokerage-note/upload-pdf/upload-pdf';
import { BrokerageHistoryService } from '../brokerage-history/history.service';
import { BrokerageNote } from '../brokerage-history/note.model';
import { DebugService } from '../shared/services/debug.service';
import { parseDate, formatCurrency, compareDate } from '../shared/utils/common-utils';

@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [CommonModule, FormsModule, UploadPdfComponent],
  templateUrl: './portfolio.html',
  styleUrl: './portfolio.css'
})
export class PortfolioComponent implements OnInit, OnChanges {
  @Input() userId!: string;
  @Input() userName!: string;

  operations: Operation[] = [];
  positions: Position[] = [];
  filteredOperations: Operation[] = [];
  
  // Filters
  filterTitulo: string = '';
  filterTipoOperacao: string = '';
  filterTipoMercado: string = '';
  filterDataInicio: string = '';
  filterDataFim: string = '';

  // View settings
  showPositions = true;
  showOperations = true;
  
  // Sorting
  sortField: string = '';
  sortDirection: 'asc' | 'desc' = 'asc';

  constructor(
    private portfolioService: PortfolioService,
    private historyService: BrokerageHistoryService,
    private debug: DebugService
  ) {}

  ngOnInit(): void {
    // Load data if userId is already set (when component is created with input)
    if (this.userId) {
      this.loadData();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Load data whenever userId changes (including first change)
    if (changes['userId'] && this.userId) {
      this.loadData();
      // Only reset filters if this is not the first change
      if (!changes['userId'].firstChange) {
        this.resetFilters();
      }
    }
  }

  loadData(): void {
    if (!this.userId) {
      this.debug.warn('⚠️ loadData() called but userId is not set');
      return;
    }
    
    this.debug.log(`🔄 Loading portfolio data for user: ${this.userId}`);
    
    this.portfolioService.getOperationsAsync(this.userId).subscribe({
      next: (operations) => {
        this.debug.log(`✅ Loaded ${operations.length} operations`);
        this.operations = operations;
        this.applyFilters();
      },
      error: (error) => {
        this.debug.error('❌ Error loading operations:', error);
      }
    });
    
    this.portfolioService.getPositionsAsync(this.userId).subscribe({
      next: (positions) => {
        this.debug.log(`✅ Loaded ${positions.length} positions`);
        this.positions = positions;
      },
      error: (error) => {
        this.debug.error('❌ Error loading positions:', error);
      }
    });
  }

  onOperationsAdded(operations: Operation[]): void {
    if (!this.userId || operations.length === 0) {
      return;
    }
    
    const firstOperation = operations[0];
    const noteDate = firstOperation.data;
    const noteNumber = firstOperation.nota || '';

    const note: BrokerageNote = {
      id: '',
      user_id: this.userId,
      file_name: `nota_${noteDate.replace(/\//g, '_')}_${noteNumber}.pdf`,
      original_file_path: `frontend_upload_${Date.now()}.pdf`,
      processed_at: new Date().toISOString(),
      note_date: noteDate,
      note_number: noteNumber,
      operations_count: operations.length,
      operations: operations,
      status: 'success'
    };

    this.historyService.addNote(note).subscribe({
      next: (savedNote) => {
        this.debug.log('✅ Brokerage note saved successfully:', savedNote);
        this.loadData();
      },
      error: (error) => {
        this.debug.error('❌ Error saving brokerage note:', error);
        
        if (error.status === 409) {
          const errorMessage = error.error?.message || 'This brokerage note has already been processed.';
          alert(`⚠️ ${errorMessage}\n\nOperations were NOT added to portfolio.`);
        } else if (error.status === 400) {
          const validationErrors = error.error?.details || error.error || {};
          const errorDetails = typeof validationErrors === 'string' 
            ? validationErrors 
            : JSON.stringify(validationErrors, null, 2);
          alert(`❌ Validation error:\n\n${errorDetails}\n\nOperations were NOT added to portfolio.`);
        } else {
          const errorMsg = error.error?.error || error.error?.message || error.message || 'Unknown error';
          alert(`❌ Error saving note: ${errorMsg}\n\nOperations were NOT added to portfolio.\n\nMake sure the Django server is running on port 8000.`);
        }
      }
    });
  }

  selectSortField(field: string): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.applyFilters();
  }
  
  getSortIcon(field: string): string {
    if (this.sortField !== field) {
      return '⇅';
    }
    return this.sortDirection === 'asc' ? '↑' : '↓';
  }
  
  applyFilters(): void {
    let filtered = this.operations.filter(op => {
      const matchesTitulo = !this.filterTitulo || 
        op.titulo.toUpperCase().includes(this.filterTitulo.toUpperCase());
      
      const matchesTipoOperacao = !this.filterTipoOperacao || 
        op.tipoOperacao === this.filterTipoOperacao;
      
      const matchesTipoMercado = !this.filterTipoMercado || 
        op.tipoMercado.toUpperCase().includes(this.filterTipoMercado.toUpperCase());
      
      const matchesDataInicio = !this.filterDataInicio || 
        compareDate(op.data, this.filterDataInicio) >= 0;
      
      const matchesDataFim = !this.filterDataFim || 
        compareDate(op.data, this.filterDataFim) <= 0;

      return matchesTitulo && matchesTipoOperacao && matchesTipoMercado && 
             matchesDataInicio && matchesDataFim;
    });

    // Apply sorting
    if (this.sortField) {
      filtered.sort((a, b) => {
        let aValue: any;
        let bValue: any;

        switch (this.sortField) {
          case 'data':
            aValue = parseDate(a.data).getTime();
            bValue = parseDate(b.data).getTime();
            break;
          case 'tipo':
            aValue = a.tipoOperacao;
            bValue = b.tipoOperacao;
            break;
          case 'titulo':
            aValue = a.titulo.toLowerCase();
            bValue = b.titulo.toLowerCase();
            break;
          case 'mercado':
            aValue = a.tipoMercado.toLowerCase();
            bValue = b.tipoMercado.toLowerCase();
            break;
          case 'quantidade':
            aValue = a.quantidade;
            bValue = b.quantidade;
            break;
          case 'preco':
            aValue = a.preco;
            bValue = b.preco;
            break;
          case 'valorOperacao':
            aValue = a.valorOperacao;
            bValue = b.valorOperacao;
            break;
          case 'corretora':
            aValue = a.corretora.toLowerCase();
            bValue = b.corretora.toLowerCase();
            break;
          case 'nota':
            aValue = a.nota || '';
            bValue = b.nota || '';
            break;
          default:
            return 0;
        }

        if (aValue < bValue) {
          return this.sortDirection === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return this.sortDirection === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }

    this.filteredOperations = filtered;
  }

  resetFilters(): void {
    this.filterTitulo = '';
    this.filterTipoOperacao = '';
    this.filterTipoMercado = '';
    this.filterDataInicio = '';
    this.filterDataFim = '';
    this.sortField = '';
    this.sortDirection = 'asc';
    this.applyFilters();
  }

  formatCurrency(value: number): string {
    return formatCurrency(value);
  }

  getTotalInvestido(): number {
    return this.positions.reduce((sum, pos) => sum + pos.valorTotalInvestido, 0);
  }

  getTotalQuantidade(): number {
    return this.positions.reduce((sum, pos) => sum + pos.quantidadeTotal, 0);
  }
}
