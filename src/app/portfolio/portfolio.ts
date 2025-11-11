import { Component, Input, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from './portfolio.service';
import { Operation } from '../brokerage-note/operation.model';
import { Position } from './position.model';
import { UploadPdfComponent } from '../brokerage-note/upload-pdf/upload-pdf';
import { BrokerageHistoryService } from '../brokerage-history/history.service';
import { BrokerageNote } from '../brokerage-history/note.model';

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
  
  // Filtros
  filterTitulo: string = '';
  filterTipoOperacao: string = '';
  filterTipoMercado: string = '';
  filterDataInicio: string = '';
  filterDataFim: string = '';

  // Visualização
  showPositions = true;
  showOperations = true;
  
  // Sorting
  sortField: string = '';
  sortDirection: 'asc' | 'desc' = 'asc';

  constructor(
    private portfolioService: PortfolioService,
    private historyService: BrokerageHistoryService
  ) {}

  ngOnInit(): void {
    this.loadData();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['userId'] && !changes['userId'].firstChange) {
      this.loadData();
      this.resetFilters();
    }
  }

  loadData(): void {
    if (!this.userId) {
      return;
    }
    
    // Load from localStorage
    this.operations = this.portfolioService.getOperations(this.userId);
    this.positions = this.portfolioService.getPositions(this.userId);
    
    // Remove duplicates based on note number and date
    this.removeDuplicateOperations();
    
    this.applyFilters();
  }
  
  private removeDuplicateOperations(): void {
    if (!this.userId || this.operations.length === 0) {
      return;
    }
    
    // Group operations by note number and date
    const noteGroups = new Map<string, Operation[]>();
    const operationsWithoutNote: Operation[] = [];
    
    for (const op of this.operations) {
      if (!op.nota || !op.data) {
        // Keep operations without note number/date
        operationsWithoutNote.push(op);
        continue;
      }
      
      const key = `${op.nota}_${op.data}`;
      if (!noteGroups.has(key)) {
        noteGroups.set(key, []);
      }
      noteGroups.get(key)!.push(op);
    }
    
    // For each note group, keep only unique operations
    // Use a Set to track unique operations by their key characteristics
    const uniqueOperations: Operation[] = [...operationsWithoutNote];
    let duplicatesRemoved = 0;
    
    for (const [key, ops] of noteGroups.entries()) {
      if (ops.length === 0) {
        continue;
      }
      
      // Create a set to track unique operations
      // Operations are considered duplicates if they have same:
      // - nota, data, titulo, tipoOperacao, quantidade, preco
      const seen = new Set<string>();
      const uniqueOpsForNote: Operation[] = [];
      
      for (const op of ops) {
        const opKey = `${op.titulo}_${op.tipoOperacao}_${op.quantidade}_${op.preco}_${op.ordem}`;
        if (!seen.has(opKey)) {
          seen.add(opKey);
          uniqueOpsForNote.push(op);
        }
      }
      
      if (uniqueOpsForNote.length < ops.length) {
        duplicatesRemoved += ops.length - uniqueOpsForNote.length;
        const noteNumber = ops[0].nota;
        const noteDate = ops[0].data;
        console.log(`⚠️ Removidas ${ops.length - uniqueOpsForNote.length} operações duplicadas da nota ${noteNumber} de ${noteDate}`);
      }
      
      uniqueOperations.push(...uniqueOpsForNote);
    }
    
    if (duplicatesRemoved > 0) {
      console.log(`✅ Total de ${duplicatesRemoved} operações duplicadas removidas do localStorage`);
      // Update localStorage with cleaned data
      this.portfolioService.clearPortfolio(this.userId);
      if (uniqueOperations.length > 0) {
        // Re-add unique operations in batches (grouped by note)
        const noteGroupsToAdd = new Map<string, Operation[]>();
        for (const op of uniqueOperations) {
          if (op.nota && op.data) {
            const key = `${op.nota}_${op.data}`;
            if (!noteGroupsToAdd.has(key)) {
              noteGroupsToAdd.set(key, []);
            }
            noteGroupsToAdd.get(key)!.push(op);
          } else {
            // Operations without note - add immediately
            this.portfolioService.addOperations(this.userId, [op]);
          }
        }
        // Add operations grouped by note
        for (const ops of noteGroupsToAdd.values()) {
          this.portfolioService.addOperations(this.userId, ops);
        }
      }
      // Reload
      this.operations = this.portfolioService.getOperations(this.userId);
      this.positions = this.portfolioService.getPositions(this.userId);
    }
  }

  onOperationsAdded(operations: Operation[]): void {
    if (!this.userId || operations.length === 0) {
      return;
    }
    
    // Extract note metadata to check for duplicates
    const firstOperation = operations[0];
    const noteDate = firstOperation.data; // DD/MM/YYYY format
    const noteNumber = firstOperation.nota || '';
    
    // Check for duplicate note BEFORE adding operations
    if (noteNumber && noteDate) {
      this.checkForDuplicateNote(noteNumber, noteDate, operations);
    } else {
      // If no note number/date, proceed normally
      this.addOperationsToPortfolio(operations);
    }
  }
  
  private checkForDuplicateNote(noteNumber: string, noteDate: string, operations: Operation[]): void {
    // Check if note already exists in history (frontend check as first line of defense)
    this.historyService.getHistory({
      user_id: this.userId,
      note_number: noteNumber
    }).subscribe({
      next: (notes) => {
        // Filter notes by exact date match
        const duplicate = notes.find(n => 
          n.note_number === noteNumber && 
          n.note_date === noteDate &&
          n.user_id === this.userId
        );
        
        if (duplicate) {
          // Duplicate found - show warning and don't add operations
          const message = `Esta nota de corretagem (número ${noteNumber} de ${noteDate}) já foi processada anteriormente. As operações não foram adicionadas ao portfólio.`;
          console.warn('⚠️ Duplicata encontrada no frontend:', message);
          alert(`⚠️ ${message}`);
          return;
        }
        
        // No duplicate found in frontend check - proceed to backend save
        // Backend will do final duplicate check before saving
        this.addOperationsToPortfolio(operations);
      },
      error: (error) => {
        console.error('Erro ao verificar duplicatas no frontend:', error);
        // On error checking frontend, still try backend save (backend has final say)
        // Backend will check for duplicates and prevent if needed
        console.log('Continuando com salvamento no backend (backend fará verificação final)...');
        this.addOperationsToPortfolio(operations);
      }
    });
  }
  
  private addOperationsToPortfolio(operations: Operation[]): void {
    // IMPORTANT: Save to backend FIRST, then add to portfolio only if successful
    // This prevents duplicates from being added to portfolio
    this.saveToBrokerageHistoryFirst(operations);
  }
  
  private saveToBrokerageHistoryFirst(operations: Operation[]): void {
    if (operations.length === 0) {
      return;
    }

    // Extract note metadata from first operation
    const firstOperation = operations[0];
    const noteDate = firstOperation.data; // DD/MM/YYYY format
    const noteNumber = firstOperation.nota || '';

    // Create BrokerageNote object
    const note: BrokerageNote = {
      id: '', // Will be generated by backend
      user_id: this.userId,
      file_name: `nota_${noteDate.replace(/\//g, '_')}_${noteNumber}.pdf`,
      original_file_path: `frontend_upload_${Date.now()}.pdf`, // Placeholder path since PDF is parsed in frontend
      processed_at: new Date().toISOString(),
      note_date: noteDate,
      note_number: noteNumber,
      operations_count: operations.length,
      operations: operations,
      status: 'success'
    };

    // Save to backend FIRST - backend will check for duplicates
    this.historyService.addNote(note).subscribe({
      next: (savedNote) => {
        console.log('✅ Nota de corretagem salva no histórico com sucesso:', savedNote);
        
        // Only add to portfolio AFTER successful backend save
        this.portfolioService.addOperations(this.userId, operations);
        this.loadData();
      },
      error: (error) => {
        console.error('❌ Erro ao salvar nota no histórico:', error);
        console.error('Error status:', error.status);
        console.error('Error details:', error.error);
        console.error('Note data being sent:', note);
        
        // Handle duplicate note error (409 Conflict)
        if (error.status === 409) {
          const errorMessage = error.error?.message || 'Esta nota de corretagem já foi processada anteriormente.';
          console.warn('⚠️ Nota duplicada detectada no backend:', errorMessage);
          alert(`⚠️ ${errorMessage}\n\nAs operações NÃO foram adicionadas ao portfólio.`);
          // Don't add operations to portfolio - duplicate detected
        } else if (error.status === 400) {
          // Validation error - show details
          const validationErrors = error.error?.details || error.error || {};
          const errorDetails = typeof validationErrors === 'string' 
            ? validationErrors 
            : JSON.stringify(validationErrors, null, 2);
          console.error('Validation errors:', errorDetails);
          alert(`❌ Erro de validação ao salvar nota:\n\n${errorDetails}\n\nAs operações NÃO foram adicionadas ao portfólio.`);
        } else {
          // Other errors - show error but don't add operations
          const errorMsg = error.error?.error || error.error?.message || error.message || 'Erro desconhecido';
          console.error('Erro ao salvar no backend:', errorMsg);
          alert(`❌ Erro ao salvar nota no histórico: ${errorMsg}\n\nAs operações NÃO foram adicionadas ao portfólio.\n\nVerifique se o servidor Django está rodando na porta 8000.`);
        }
      }
    });
  }


  deleteOperation(operationId: string): void {
    if (confirm('Tem certeza que deseja excluir esta operação?')) {
      this.portfolioService.deleteOperation(this.userId, operationId);
      this.loadData();
    }
  }

  selectSortField(field: string): void {
    if (this.sortField === field) {
      // Toggle direction if clicking the same field
      this.sortField = field;
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      // New field - default to ascending
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.applyFilters();
  }
  
  getSortIcon(field: string): string {
    if (this.sortField !== field) {
      return '⇅'; // Neutral icon when not sorted (double arrow)
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
        this.compareDate(op.data, this.filterDataInicio) >= 0;
      
      const matchesDataFim = !this.filterDataFim || 
        this.compareDate(op.data, this.filterDataFim) <= 0;

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
            aValue = this.parseDate(a.data).getTime();
            bValue = this.parseDate(b.data).getTime();
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
  
  private parseDate(dateStr: string): Date {
    // Formato esperado: DD/MM/YYYY
    const parts = dateStr.split('/');
    if (parts.length === 3) {
      const day = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1; // Meses são 0-indexed
      const year = parseInt(parts[2], 10);
      return new Date(year, month, day);
    }
    // Fallback para formato ISO
    return new Date(dateStr);
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

  private compareDate(dateStr: string, filterDateStr: string): number {
    const date = this.parseDate(dateStr);
    const filterDate = this.parseDate(filterDateStr);
    return date.getTime() - filterDate.getTime();
  }

  formatCurrency(value: number): string {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  }

  getTotalInvestido(): number {
    return this.positions.reduce((sum, pos) => sum + pos.valorTotalInvestido, 0);
  }

  getTotalQuantidade(): number {
    return this.positions.reduce((sum, pos) => sum + pos.quantidadeTotal, 0);
  }
}

