import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, tap, map } from 'rxjs/operators';
import { Operation } from '../brokerage-note/operation.model';
import { Position } from './position.model';
import { DebugService } from '../shared/services/debug.service';
import { BrokerageNote } from '../brokerage-history/note.model';

@Injectable({
  providedIn: 'root'
})
export class PortfolioService {
  private readonly PORTFOLIO_API_URL = '/api/portfolio';
  private readonly BROKERAGE_NOTES_API_URL = '/api/brokerage-notes';

  constructor(
    private http: HttpClient,
    private debug: DebugService
  ) {}

  /**
   * Get operations for a specific client from brokerage notes
   */
  getOperationsAsync(clientId: string): Observable<Operation[]> {
    let params = new HttpParams();
    params = params.set('user_id', clientId);
    
    this.debug.log(`🔍 Fetching operations for user_id: ${clientId}`);
    
    return this.http.get<BrokerageNote[]>(this.BROKERAGE_NOTES_API_URL, { params }).pipe(
      tap(notes => {
        this.debug.log(`📋 Received ${notes.length} brokerage notes for user ${clientId}`);
      }),
      map(notes => {
        // Extract and flatten operations from all notes
        const allOperations: Operation[] = [];
        for (const note of notes) {
          this.debug.log(`📄 Processing note ${note.note_number || note.id}, operations count: ${note.operations?.length || 0}`);
          if (note.operations && Array.isArray(note.operations)) {
            // Ensure each operation has the note metadata
            const operationsWithMetadata = note.operations.map(op => ({
              ...op,
              nota: op.nota || note.note_number || '',
              data: op.data || note.note_date || '',
              clientId: op.clientId || note.user_id || clientId
            }));
            allOperations.push(...operationsWithMetadata);
          }
        }
        this.debug.log(`✅ Extracted ${allOperations.length} total operations from ${notes.length} notes`);
        return allOperations;
      }),
      tap(operations => {
        this.debug.log(`📊 ${operations.length} operations loaded from brokerage notes for client ${clientId}`);
      }),
      catchError(error => {
        this.debug.error('Error loading operations from brokerage notes:', error);
        this.debug.error('Error details:', error.status, error.message, error.error);
        return of([]);
      })
    );
  }

  /**
   * Get positions for a specific client from backend
   */
  getPositionsAsync(clientId: string): Observable<Position[]> {
    return this.http.get<any[]>(`${this.PORTFOLIO_API_URL}/?user_id=${clientId}`).pipe(
      tap(positions => {
        this.debug.log(`📊 ${positions.length} positions loaded from backend`);
      }),
      map(tickerSummaries => {
        return tickerSummaries.map((summary: any) => ({
          titulo: summary.titulo,
          quantidadeTotal: summary.quantidade || 0,
          precoMedioPonderado: summary.precoMedio || 0,
          valorTotalInvestido: summary.valorTotalInvestido || 0,
          lucroRealizado: summary.lucroRealizado || 0
        } as Position));
      }),
      catchError(error => {
        this.debug.error('Error loading positions from backend:', error);
        return of([]);
      })
    );
  }

  /**
   * Fetch current prices for multiple tickers
   */
  fetchCurrentPrices(tickers: string[], market: string = 'B3'): Observable<Map<string, number>> {
    if (!tickers || tickers.length === 0) {
      return of(new Map<string, number>());
    }

    this.debug.log(`💰 Fetching prices for ${tickers.length} tickers:`, tickers);

    return this.http.post<{ prices: { [ticker: string]: number } }>(
      `${this.PORTFOLIO_API_URL}/prices/`,
      { tickers, market }
    ).pipe(
      tap(response => {
        this.debug.log(`✅ Received prices for ${Object.keys(response.prices).length} tickers`);
      }),
      map(response => {
        const priceMap = new Map<string, number>();
        for (const [ticker, price] of Object.entries(response.prices)) {
          priceMap.set(ticker, price);
        }
        return priceMap;
      }),
      catchError(error => {
        this.debug.error('Error fetching prices:', error);
        return of(new Map<string, number>());
      })
    );
  }

  /**
   * Debug method to trace position calculation for a specific ticker
   * This helps diagnose position calculation issues
   */
  debugPositionCalculation(clientId: string, ticker: string): void {
    this.debug.group(`🔍 DEBUG: ${ticker} Position Calculation`);
    
    this.getOperationsAsync(clientId).subscribe(operations => {
      const tickerOperations = operations.filter(op => op.titulo === ticker);
      
      this.debug.log(`Total operations found: ${tickerOperations.length}`);
      this.debug.log(`All ${ticker} operations:`, tickerOperations);
      
      // Sort operations chronologically
      const sortedOperations = [...tickerOperations].sort((a, b) => {
        const [dayA, monthA, yearA] = a.data.split('/').map(Number);
        const [dayB, monthB, yearB] = b.data.split('/').map(Number);
        const dateA = new Date(yearA, monthA - 1, dayA);
        const dateB = new Date(yearB, monthB - 1, dayB);
        
        if (dateA.getTime() !== dateB.getTime()) {
          return dateA.getTime() - dateB.getTime();
        }
        return a.ordem - b.ordem;
      });
      
      this.debug.log('\n📅 Operations sorted chronologically:');
      let runningQuantity = 0;
      let runningValue = 0;
      let runningAvgPrice = 0;
      
      sortedOperations.forEach((op, index) => {
        this.debug.log(`\nOperation ${index + 1}:`);
        this.debug.log(`  Date: ${op.data}`);
        this.debug.log(`  Note: ${op.nota}`);
        this.debug.log(`  Type: ${op.tipoOperacao === 'C' ? 'COMPRA' : 'VENDA'}`);
        this.debug.log(`  Quantity: ${op.quantidade}`);
        this.debug.log(`  Price: ${op.preco}`);
        this.debug.log(`  Value: ${op.valorOperacao}`);
        
        if (op.tipoOperacao === 'C') {
          const quantidadeNova = Math.abs(op.quantidade);
          const valorNovo = op.valorOperacao;
          const quantidadeTotal = runningQuantity + quantidadeNova;
          const valorTotal = runningValue + valorNovo;
          runningAvgPrice = quantidadeTotal > 0 ? valorTotal / quantidadeTotal : 0;
          runningQuantity = quantidadeTotal;
          runningValue = valorTotal;
        } else {
          const quantidadeVendida = Math.abs(op.quantidade);
          runningQuantity -= quantidadeVendida;
          const valorReduzido = quantidadeVendida * runningAvgPrice;
          runningValue = Math.max(0, runningValue - valorReduzido);
          if (runningQuantity <= 0) {
            runningQuantity = 0;
            runningAvgPrice = 0;
            runningValue = 0;
          }
        }
        
        this.debug.log(`  → Running Total: ${runningQuantity} shares`);
        this.debug.log(`  → Running Avg Price: R$ ${runningAvgPrice.toFixed(2)}`);
        this.debug.log(`  → Running Total Value: R$ ${runningValue.toFixed(2)}`);
      });
      
      this.debug.log('\n✅ Final Position:');
      this.debug.log(`  Quantity: ${runningQuantity}`);
      this.debug.log(`  Avg Price: R$ ${runningAvgPrice.toFixed(2)}`);
      this.debug.log(`  Total Value: R$ ${runningValue.toFixed(2)}`);
      
      // Also check what backend returns
      this.getPositionsAsync(clientId).subscribe(positions => {
        const position = positions.find(p => p.titulo === ticker);
        this.debug.log('\n📊 Position from backend:', position);
        this.debug.groupEnd();
      });
    });
  }
}
