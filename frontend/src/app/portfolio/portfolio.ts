import { Component, Input, OnInit, OnChanges, OnDestroy, SimpleChanges, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService } from './portfolio.service';
import { Operation } from '../brokerage-note/operation.model';
import { FinancialSummary } from '../brokerage-note/financial-summary.model';
import { Position } from './position.model';
import { UploadPdfComponent, OperationsAddedEvent } from '../brokerage-note/upload-pdf/upload-pdf';
import { BrokerageHistoryService } from '../brokerage-history/history.service';
import { BrokerageNote } from '../brokerage-history/note.model';
import { DebugService } from '../shared/services/debug.service';
import { formatCurrency } from '../shared/utils/common-utils';
import { FixedIncomeListComponent } from '../fixed-income/fixed-income-list.component';
import { HistoryListComponent } from '../brokerage-history/history-list/history-list';
import { AllocationStrategyComponent } from '../allocation-strategies/allocation-strategy.component';
import { CryptoComponent } from '../crypto/crypto.component';
import { FIIListComponent } from '../fiis/fiis-list.component';
import { StocksService } from '../configuration/stocks/stocks.service';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Stock } from '../configuration/stocks/stocks.models';

@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [CommonModule, FormsModule, UploadPdfComponent, FixedIncomeListComponent, HistoryListComponent, AllocationStrategyComponent, CryptoComponent, FIIListComponent],
  templateUrl: './portfolio.html',
  styleUrl: './portfolio.css'
})
export class PortfolioComponent implements OnInit, OnChanges, OnDestroy {
  @Input() userId!: string;
  @Input() userName!: string;
  @ViewChild('historyList') historyListComponent!: HistoryListComponent;

  operations: Operation[] = [];
  positions: Position[] = [];
  
  // Cache for FII tickers to avoid repeated API calls
  private fiiTickers: Set<string> = new Set();

  // View settings
  showPositions = true;
  activeTab: 'acoes' | 'renda-fixa' | 'historico' | 'allocation-strategy' | 'crypto' | 'fiis' = 'acoes';

  // Store bound event handler for cleanup
  private noteDeletedHandler = (event: Event) => this.onNoteDeleted(event);

  constructor(
    private portfolioService: PortfolioService,
    private historyService: BrokerageHistoryService,
    private stocksService: StocksService,
    private http: HttpClient,
    private debug: DebugService
  ) { }

  ngOnInit(): void {
    // Load data if userId is already set (when component is created with input)
    if (this.userId) {
      this.loadData();
    }

    // Listen for note deletion events to refresh portfolio
    if (typeof window !== 'undefined') {
      window.addEventListener('brokerage-note-deleted', this.noteDeletedHandler);
    }
  }

  ngOnDestroy(): void {
    // Clean up event listener
    if (typeof window !== 'undefined') {
      window.removeEventListener('brokerage-note-deleted', this.noteDeletedHandler);
    }
  }

  onNoteDeleted(event: Event): void {
    const customEvent = event as CustomEvent;
    this.debug.log('📢 Note deleted event received, refreshing portfolio:', customEvent.detail);

    // Refresh portfolio data if this component is for the affected user
    // Note: We refresh regardless of user since we don't know which user's note was deleted
    // The backend refresh will update all users' portfolios correctly
    if (this.userId) {
      this.loadData();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Handle userId changes
    if (changes['userId']) {
      // Clear data immediately when userId changes (not first change)
      if (!changes['userId'].firstChange) {
        this.operations = [];
        this.positions = [];
      }
      
      // Load data for the new user
      if (this.userId) {
        this.loadData();
      } else {
        // If userId is removed, clear all data
        this.operations = [];
        this.positions = [];
      }
    }
  }

  loadData(): void {
    if (!this.userId) {
      this.debug.warn('⚠️ loadData() called but userId is not set');
      return;
    }

    // Store the userId at the start of loading to prevent race conditions
    const loadingUserId = this.userId;

    this.debug.log(`🔄 Loading portfolio data for user: ${loadingUserId}`);

    // Clear existing data immediately when loading for a new user
    this.operations = [];
    this.positions = [];

    this.portfolioService.getOperationsAsync(loadingUserId).subscribe({
      next: (operations) => {
        // Ignore response if userId has changed during loading
        if (this.userId !== loadingUserId) {
          this.debug.warn(`⚠️ Ignoring operations response - userId changed from ${loadingUserId} to ${this.userId}`);
          return;
        }
        this.debug.log(`✅ Loaded ${operations.length} operations`);
        this.operations = operations;
      },
      error: (error) => {
        // Ignore error if userId has changed during loading
        if (this.userId !== loadingUserId) {
          this.debug.warn(`⚠️ Ignoring operations error - userId changed from ${loadingUserId} to ${this.userId}`);
          return;
        }
        this.debug.error('❌ Error loading operations:', error);
        // Ensure operations are cleared on error
        this.operations = [];
      }
    });

    this.portfolioService.getPositionsAsync(loadingUserId).subscribe({
      next: (positions) => {
        // Ignore response if userId has changed during loading
        if (this.userId !== loadingUserId) {
          this.debug.warn(`⚠️ Ignoring positions response - userId changed from ${loadingUserId} to ${this.userId}`);
          return;
        }
        this.debug.log(`✅ Loaded ${positions.length} positions`);

        // Filter out FIIs from positions before processing
        // Only filter based on stock catalog - tickers marked as FII in the catalog
        const tickers = positions.map(p => p.titulo);
        if (tickers.length > 0) {
          // Fetch all stocks including FIIs by setting exclude_fiis to false
          let params = new HttpParams();
          params = params.set('exclude_fiis', 'false');
          params = params.set('active_only', 'false');
          
          this.http.get<Stock[]>(`/api/stocks/stocks/`, { params }).subscribe({
            next: (stocks) => {
              // Build set of FII tickers ONLY from stock catalog
              // Only filter stocks explicitly marked as FII (stock_class = 'FII' or investment_type code = 'FIIS')
              this.fiiTickers.clear();
              stocks.forEach(stock => {
                if (stock.stock_class === 'FII' || stock.investment_type?.code === 'FIIS') {
                  this.fiiTickers.add(stock.ticker);
                }
              });
              
              this.debug.log(`[FII Filter] Found ${this.fiiTickers.size} FII tickers from catalog: ${Array.from(this.fiiTickers).join(', ')}`);
              
              // Filter out FII positions - only filter what's confirmed in catalog
              const nonFiiPositions = positions.filter(pos => !this.fiiTickers.has(pos.titulo));
              this.debug.log(`[FII Filter] Filtered ${positions.length} positions to ${nonFiiPositions.length} (removed ${positions.length - nonFiiPositions.length} FIIs)`);
              
              // Continue with filtered positions
              this.processPositions(nonFiiPositions, loadingUserId);
            },
            error: (error) => {
              this.debug.error('❌ Error loading stocks for FII filtering:', error);
              // If we can't load stocks, don't filter anything (show all positions)
              // Better to show too much than to incorrectly filter out non-FIIs
              this.debug.log(`[FII Filter] Error loading stocks - showing all positions without filtering`);
              this.processPositions(positions, loadingUserId);
            }
          });
        } else {
          // No positions - ensure array is empty
          this.positions = [];
        }
      },
      error: (error) => {
        // Ignore error if userId has changed during loading
        if (this.userId !== loadingUserId) {
          this.debug.warn(`⚠️ Ignoring positions error - userId changed from ${loadingUserId} to ${this.userId}`);
          return;
        }
        this.debug.error('❌ Error loading positions:', error);
        // Ensure positions are cleared on error
        this.positions = [];
      }
    });
  }

  private processPositions(positions: Position[], loadingUserId: string): void {
    // Fetch current prices for all positions
    const tickers = positions.map(p => p.titulo);
    if (tickers.length > 0) {
          this.portfolioService.fetchCurrentPrices(tickers).subscribe({
            next: (priceMap) => {
              // Ignore response if userId has changed during loading
              if (this.userId !== loadingUserId) {
                this.debug.warn(`⚠️ Ignoring price fetch response - userId changed from ${loadingUserId} to ${this.userId}`);
                return;
              }
              // Update positions with current prices and calculate unrealized P&L, valor atual, and total lucro
              const positionsWithPrices = positions.map(position => {
                const currentPrice = priceMap.get(position.titulo);
                let unrealizedPnL: number | undefined;
                let valorAtual: number | undefined;
                let totalLucro: number | undefined;

                if (currentPrice !== undefined && position.quantidadeTotal > 0) {
                  // Calculate unrealized P&L: (Current Price - Average Cost) × Quantity
                  unrealizedPnL = (currentPrice - position.precoMedioPonderado) * position.quantidadeTotal;
                  // Calculate Valor Atual: Quantidade × Preço Atual
                  valorAtual = position.quantidadeTotal * currentPrice;
                  // Calculate Total Lucro: Lucro Realizado + Lucro Não Realizado
                  totalLucro = (position.lucroRealizado || 0) + unrealizedPnL;
                } else if (position.quantidadeTotal > 0) {
                  // If no price, total lucro is just realized profit
                  totalLucro = position.lucroRealizado || 0;
                } else {
                  // No quantity, total lucro is just realized profit
                  totalLucro = position.lucroRealizado || 0;
                }

                return {
                  ...position,
                  currentPrice,
                  unrealizedPnL,
                  valorAtual,
                  totalLucro
                };
              });

              this.positions = this.sortPositions(positionsWithPrices);
            },
            error: (error) => {
              // Ignore error if userId has changed during loading
              if (this.userId !== loadingUserId) {
                this.debug.warn(`⚠️ Ignoring price fetch error - userId changed from ${loadingUserId} to ${this.userId}`);
                return;
              }
              this.debug.error('❌ Error fetching prices:', error);
              // Continue with positions without prices, but still calculate totalLucro
              const positionsWithoutPrices = positions.map(position => ({
                ...position,
                totalLucro: position.lucroRealizado || 0
              }));
              this.positions = this.sortPositions(positionsWithoutPrices);
            }
          });
        } else {
          // No positions - ensure array is empty
          this.positions = [];
        }
  }

  onOperationsAdded(event: OperationsAddedEvent): void {
    const { operations, expectedOperationsCount, financialSummary, fileName } = event;
    
    if (!this.userId || operations.length === 0) {
      return;
    }
    
    // Validate operations count if expected count is available
    if (expectedOperationsCount !== null && operations.length !== expectedOperationsCount) {
      const errorMsg = `Validação falhou: O PDF contém ${expectedOperationsCount} operação(ões), mas apenas ${operations.length} foram processadas. Operações não serão salvas.`;
      this.debug.error(`❌ ${errorMsg}`);
      // Show error message to user (you may want to add a toast/notification service here)
      alert(errorMsg);
      return;
    }

    const firstOperation = operations[0];
    const noteDate = firstOperation.data;
    // Use the note number from operation, but if it's 'N/A' or empty, try to extract from file name
    let noteNumber = firstOperation.nota || '';
    // If empty or 'N/A', try to extract from file name
    if (!noteNumber || noteNumber === 'N/A' || noteNumber.trim() === '') {
      noteNumber = '';
      // Try to extract note number from file name if available
      if (fileName) {
        const noteNumberMatch = fileName.match(/(\d{9,})/);
        if (noteNumberMatch) {
          noteNumber = noteNumberMatch[1];
        }
      }
      // If still empty, use 'N/A' for display purposes (backend will accept it)
      if (!noteNumber) {
        noteNumber = 'N/A';
      }
    }

    // Use the original file name if available, otherwise generate one
    let generatedFileName = fileName || `nota_${noteDate.replace(/\//g, '_')}${noteNumber ? '_' + noteNumber : ''}.pdf`;

    const note: BrokerageNote = {
      id: '',
      user_id: this.userId,
      file_name: generatedFileName,
      original_file_path: `frontend_upload_${Date.now()}.pdf`,
      processed_at: new Date().toISOString(),
      note_date: noteDate,
      note_number: noteNumber,
      operations_count: operations.length,
      operations: operations,
      status: 'success',
      // Financial summary fields
      debentures: financialSummary?.debentures,
      vendas_a_vista: financialSummary?.vendas_a_vista,
      compras_a_vista: financialSummary?.compras_a_vista,
      valor_das_operacoes: financialSummary?.valor_das_operacoes,
      clearing: financialSummary?.clearing,
      valor_liquido_operacoes: financialSummary?.valor_liquido_operacoes,
      taxa_liquidacao: financialSummary?.taxa_liquidacao,
      taxa_registro: financialSummary?.taxa_registro,
      total_cblc: financialSummary?.total_cblc,
      bolsa: financialSummary?.bolsa,
      emolumentos: financialSummary?.emolumentos,
      taxa_transferencia_ativos: financialSummary?.taxa_transferencia_ativos,
      total_bovespa: financialSummary?.total_bovespa,
      taxa_operacional: financialSummary?.taxa_operacional,
      execucao: financialSummary?.execucao,
      taxa_custodia: financialSummary?.taxa_custodia,
      impostos: financialSummary?.impostos,
      irrf_operacoes: financialSummary?.irrf_operacoes,
      irrf_base: financialSummary?.irrf_base,
      outros_custos: financialSummary?.outros_custos,
      total_custos_despesas: financialSummary?.total_custos_despesas,
      liquido: financialSummary?.liquido,
      liquido_data: financialSummary?.liquido_data,
    };

    this.historyService.addNote(note).subscribe({
      next: (savedNote) => {
        this.debug.log('✅ Brokerage note saved successfully:', savedNote);
        
        // Validate operations count after saving (double-check)
        if (expectedOperationsCount !== null && savedNote.operations_count !== expectedOperationsCount) {
          const errorMsg = `Validação falhou após salvar: O PDF contém ${expectedOperationsCount} operação(ões), mas apenas ${savedNote.operations_count} foram salvas. A nota será removida.`;
          this.debug.error(`❌ ${errorMsg}`);
          
          // Rollback: Delete the note that was just saved
          if (savedNote.id) {
            this.historyService.deleteNote(savedNote.id).subscribe({
              next: () => {
                this.debug.log('✅ Note deleted due to validation failure');
                alert(errorMsg);
              },
              error: (deleteError) => {
                this.debug.error('❌ Error deleting note during rollback:', deleteError);
                alert(`${errorMsg}\n\nErro ao remover a nota. Por favor, remova manualmente a nota ${savedNote.note_number} de ${savedNote.note_date}.`);
              }
            });
          } else {
            alert(errorMsg);
          }
          
          // Don't reload data or history if validation failed
          return;
        }
        
        this.loadData();
        // Reload history list to show the new note
        // Use setTimeout to ensure ViewChild is available (if tab is active)
        setTimeout(() => {
          if (this.historyListComponent) {
            this.debug.log('🔄 Reloading history list after note addition');
            this.historyListComponent.loadHistory();
          } else {
            this.debug.warn('⚠️ HistoryListComponent not available - list will refresh on next tab switch');
          }
        }, 100);
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


  formatCurrency(value: number): string {
    return formatCurrency(value);
  }

  getTotalInvestido(): number {
    return this.positions.reduce((sum, pos) => sum + pos.valorTotalInvestido, 0);
  }

  getTotalQuantidade(): number {
    return this.positions.reduce((sum, pos) => sum + pos.quantidadeTotal, 0);
  }

  getActivePositionsCount(): number {
    return this.positions.filter(pos => pos.quantidadeTotal > 0).length;
  }

  getTotalValorAtual(): number {
    return this.positions.reduce((sum, pos) => sum + (pos.valorAtual || 0), 0);
  }

  sortPositions(positions: Position[]): Position[] {
    return [...positions].sort((a, b) => {
      // Sort by Valor Atual (descending - highest value first)
      const valorA = a.valorAtual || 0;
      const valorB = b.valorAtual || 0;

      if (valorB !== valorA) {
        return valorB - valorA;
      }
      // If equal, sort by Valor Total Investido (descending)
      if (b.valorTotalInvestido !== a.valorTotalInvestido) {
        return b.valorTotalInvestido - a.valorTotalInvestido;
      }
      // If still equal, sort by Lucro Realizado (descending)
      return (b.lucroRealizado || 0) - (a.lucroRealizado || 0);
    });
  }
}
