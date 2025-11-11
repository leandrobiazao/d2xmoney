import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, tap, map } from 'rxjs/operators';
import { Operation } from '../brokerage-note/operation.model';
import { Position } from './position.model';
import { Portfolio } from './portfolio.model';

@Injectable({
  providedIn: 'root'
})
export class PortfolioService {
  private readonly PORTFOLIO_API_URL = '/api/portfolio';
  private readonly OPERATIONS_API_URL = '/api/portfolio-operations'; // Legacy, for operations if needed
  private readonly STORAGE_KEY_PREFIX = 'portfolio-';
  private useBackend = true; // Flag to switch between backend and localStorage

  constructor(private http: HttpClient) {}

  private getStorageKey(clientId: string): string {
    return `${this.STORAGE_KEY_PREFIX}${clientId}`;
  }

  private savePortfolio(portfolio: Portfolio): void {
    const key = this.getStorageKey(portfolio.clientId);
    localStorage.setItem(key, JSON.stringify(portfolio));
  }

  private loadPortfolio(clientId: string): Portfolio | null {
    const key = this.getStorageKey(clientId);
    const data = localStorage.getItem(key);
    if (!data) {
      return null;
    }
    try {
      return JSON.parse(data);
    } catch (error) {
      console.error('Error parsing portfolio data:', error);
      return null;
    }
  }

  getOperations(clientId: string): Operation[] {
    // For now, return empty array - will be loaded async via getOperationsAsync
    // This maintains backward compatibility
    return [];
  }

  getOperationsAsync(clientId: string): Observable<Operation[]> {
    // Note: Operations are now stored in brokerage_notes.json
    // This method is kept for backward compatibility
    // In the future, operations should be fetched from brokerage notes API
    if (this.useBackend) {
      // Try legacy endpoint first, fallback to localStorage
      return this.http.get<Operation[]>(`${this.OPERATIONS_API_URL}/?client_id=${clientId}`).pipe(
        catchError(error => {
          console.error('Error loading operations from backend:', error);
          // Fallback to localStorage
          return of(this.getOperationsFromLocalStorage(clientId));
        })
      );
    }
    return of(this.getOperationsFromLocalStorage(clientId));
  }

  private getOperationsFromLocalStorage(clientId: string): Operation[] {
    const portfolio = this.loadPortfolio(clientId);
    return portfolio?.operations || [];
  }

  addOperations(clientId: string, operations: Operation[]): void {
    if (!operations || operations.length === 0) {
      return;
    }

    // Note: Operations are now managed through brokerage notes API
    // Portfolio is automatically refreshed after note upload
    // This method is kept for backward compatibility but portfolio refresh
    // happens automatically on the backend when brokerage notes are uploaded
    
    if (this.useBackend) {
      // Portfolio refresh happens automatically on backend after note upload
      // No need to call portfolio API here
      console.log(`✅ Operações serão processadas quando a nota de corretagem for salva`);
    } else {
      // Fallback to localStorage for offline mode
      const operationsWithClientId = operations.map(op => ({
        ...op,
        clientId,
        id: op.id || this.generateOperationId()
      }));
      this.addOperationsToLocalStorage(clientId, operationsWithClientId);
    }
  }

  private addOperationsToLocalStorage(clientId: string, operations: Operation[]): void {
    const portfolio = this.loadPortfolio(clientId) || {
      clientId,
      operations: [],
      positions: [],
      lastUpdated: new Date().toISOString()
    };

    // Extract note metadata to check for duplicates
    const firstOperation = operations[0];
    const noteDate = firstOperation.data; // DD/MM/YYYY format
    const noteNumber = firstOperation.nota || '';

    // Check for duplicate operations in localStorage (same note number and date)
    if (noteNumber && noteDate) {
      const existingOperations = portfolio.operations.filter(op => 
        op.nota === noteNumber && 
        op.data === noteDate &&
        op.clientId === clientId
      );

      if (existingOperations.length > 0) {
        console.warn(`⚠️ Duplicata detectada no localStorage: Nota ${noteNumber} de ${noteDate} já existe. Removendo duplicatas antigas...`);
        // Remove old duplicate operations
        portfolio.operations = portfolio.operations.filter(op => 
          !(op.nota === noteNumber && op.data === noteDate && op.clientId === clientId)
        );
      }
    }

    portfolio.operations.push(...operations);
    portfolio.operations.sort((a, b) => {
      // Ordenar por data (mais recente primeiro)
      const dateA = this.parseDate(a.data);
      const dateB = this.parseDate(b.data);
      if (dateB.getTime() !== dateA.getTime()) {
        return dateB.getTime() - dateA.getTime();
      }
      // Se mesma data, ordenar por ordem
      return b.ordem - a.ordem;
    });

    portfolio.lastUpdated = new Date().toISOString();
    portfolio.positions = this.calculatePositions(clientId);
    this.savePortfolio(portfolio);
  }

  deleteOperation(clientId: string, operationId: string): void {
    // Note: Operations are now managed through brokerage notes
    // To delete an operation, delete the brokerage note instead
    // Portfolio will be automatically refreshed
    console.warn('deleteOperation is deprecated. Delete brokerage note instead to update portfolio.');
    
    if (this.useBackend) {
      // Try legacy endpoint, but it may not work
      this.http.delete(`${this.OPERATIONS_API_URL}/${operationId}`).pipe(
        tap(() => {
          console.log(`✅ Operação ${operationId} removida do backend`);
        }),
        catchError(error => {
          console.error('Error deleting operation from backend:', error);
          console.warn('Note: Operations are now managed through brokerage notes. Delete the note instead.');
          // Fallback to localStorage
          this.deleteOperationFromLocalStorage(clientId, operationId);
          return of(null);
        })
      ).subscribe();
    } else {
      this.deleteOperationFromLocalStorage(clientId, operationId);
    }
  }

  private deleteOperationFromLocalStorage(clientId: string, operationId: string): void {
    const portfolio = this.loadPortfolio(clientId);
    if (!portfolio) {
      return;
    }

    portfolio.operations = portfolio.operations.filter(op => op.id !== operationId);
    portfolio.lastUpdated = new Date().toISOString();
    portfolio.positions = this.calculatePositions(clientId);
    this.savePortfolio(portfolio);
  }

  calculatePositions(clientId: string, operations?: Operation[]): Position[] {
    // If operations not provided, try to get from localStorage (for backward compatibility)
    if (!operations) {
      operations = this.getOperationsFromLocalStorage(clientId);
    }
    const positionsMap = new Map<string, Position>();

    // Processar operações em ordem cronológica
    const sortedOperations = [...operations].sort((a, b) => {
      const dateA = this.parseDate(a.data);
      const dateB = this.parseDate(b.data);
      if (dateA.getTime() !== dateB.getTime()) {
        return dateA.getTime() - dateB.getTime();
      }
      return a.ordem - b.ordem;
    });

    for (const operation of sortedOperations) {
      const titulo = operation.titulo;
      
      if (!positionsMap.has(titulo)) {
        positionsMap.set(titulo, {
          titulo,
          quantidadeTotal: 0,
          precoMedioPonderado: 0,
          valorTotalInvestido: 0,
          lucroRealizado: 0  // Initialize lucroRealizado
        });
      }

      const position = positionsMap.get(titulo)!;

      if (operation.tipoOperacao === 'C') {
        // Compra: calcular preço médio ponderado
        const quantidadeAtual = position.quantidadeTotal;
        const valorAtual = quantidadeAtual * position.precoMedioPonderado;
        const quantidadeNova = Math.abs(operation.quantidade);
        const valorNovo = operation.valorOperacao;

        const quantidadeTotal = quantidadeAtual + quantidadeNova;
        const valorTotal = valorAtual + valorNovo;

        if (quantidadeTotal > 0) {
          position.precoMedioPonderado = valorTotal / quantidadeTotal;
        }
        position.quantidadeTotal = quantidadeTotal;
        position.valorTotalInvestido = valorTotal;
      } else if (operation.tipoOperacao === 'V') {
        // Venda: reduzir quantidade (usando preço médio para cálculo)
        // Note: This is a simplified calculation. Real FIFO is done on backend.
        const quantidadeVendida = Math.abs(operation.quantidade);
        const precoVenda = operation.preco;
        const precoMedio = position.precoMedioPonderado;
        
        // Simplified realized profit calculation (backend uses FIFO)
        const lucroOperacao = (precoVenda - precoMedio) * quantidadeVendida;
        position.lucroRealizado += lucroOperacao;
        
        position.quantidadeTotal -= quantidadeVendida;
        
        // Reduzir valor investido proporcionalmente
        const valorUnitario = position.precoMedioPonderado;
        const valorReduzido = quantidadeVendida * valorUnitario;
        position.valorTotalInvestido = Math.max(0, position.valorTotalInvestido - valorReduzido);

        // Se quantidade zerou, resetar preço médio
        if (position.quantidadeTotal <= 0) {
          position.quantidadeTotal = 0;
          position.precoMedioPonderado = 0;
          position.valorTotalInvestido = 0;
        }
      }
    }

    // Keep all positions (even with 0 quantity) to preserve lucroRealizado history
    const positions = Array.from(positionsMap.values())
      .sort((a, b) => a.titulo.localeCompare(b.titulo));

    return positions;
  }

  getPositions(clientId: string): Position[] {
    // Positions are always calculated from operations, not stored
    // This will be called with operations loaded async
    const operations = this.getOperationsFromLocalStorage(clientId);
    return this.calculatePositions(clientId, operations);
  }

  getPositionsAsync(clientId: string): Observable<Position[]> {
    if (this.useBackend) {
      // Use new portfolio API endpoint
      return this.http.get<any[]>(`${this.PORTFOLIO_API_URL}/?user_id=${clientId}`).pipe(
        tap(positions => {
          console.log(`📊 ${positions.length} posições carregadas do backend`);
        }),
        // Map backend format to Position interface
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
          console.error('Error loading positions from backend, falling back to calculation:', error);
          // Fallback to calculating from operations
          return this.getOperationsAsync(clientId).pipe(
            map(operations => {
              const positions = this.calculatePositions(clientId, operations);
              console.log(`✅ ${positions.length} posições calculadas`);
              return positions;
            })
          );
        })
      );
    }
    
    // Fallback: calculate from operations
    return this.getOperationsAsync(clientId).pipe(
      tap(operations => {
        console.log(`📊 Calculando posições para ${operations.length} operações`);
      }),
      map(operations => {
        const positions = this.calculatePositions(clientId, operations);
        console.log(`✅ ${positions.length} posições calculadas`);
        return positions;
      }),
      catchError(error => {
        console.error('Error calculating positions:', error);
        return of([]);
      })
    );
  }

  private generateOperationId(): string {
    return `op-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
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

  clearPortfolio(clientId: string): void {
    const key = this.getStorageKey(clientId);
    localStorage.removeItem(key);
  }

  /**
   * Debug method to trace position calculation for a specific ticker
   */
  debugPositionCalculation(clientId: string, ticker: string): void {
    const operations = this.getOperations(clientId);
    const tickerOperations = operations.filter(op => op.titulo === ticker);
    
    console.log(`\n🔍 DEBUG: ASAI3 Position Calculation`);
    console.log(`Total operations found: ${tickerOperations.length}`);
    console.log(`All ASAI3 operations:`, tickerOperations);
    
    // Sort operations chronologically (as calculatePositions does)
    const sortedOperations = [...tickerOperations].sort((a, b) => {
      const dateA = this.parseDate(a.data);
      const dateB = this.parseDate(b.data);
      if (dateA.getTime() !== dateB.getTime()) {
        return dateA.getTime() - dateB.getTime();
      }
      return a.ordem - b.ordem;
    });
    
    console.log(`\n📅 Operations sorted chronologically:`);
    let runningQuantity = 0;
    let runningValue = 0;
    let runningAvgPrice = 0;
    
    sortedOperations.forEach((op, index) => {
      console.log(`\nOperation ${index + 1}:`);
      console.log(`  Date: ${op.data}`);
      console.log(`  Note: ${op.nota}`);
      console.log(`  Type: ${op.tipoOperacao === 'C' ? 'COMPRA' : 'VENDA'}`);
      console.log(`  Quantity: ${op.quantidade}`);
      console.log(`  Price: ${op.preco}`);
      console.log(`  Value: ${op.valorOperacao}`);
      
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
      
      console.log(`  → Running Total: ${runningQuantity} shares`);
      console.log(`  → Running Avg Price: R$ ${runningAvgPrice.toFixed(2)}`);
      console.log(`  → Running Total Value: R$ ${runningValue.toFixed(2)}`);
    });
    
    console.log(`\n✅ Final Position:`);
    console.log(`  Quantity: ${runningQuantity}`);
    console.log(`  Avg Price: R$ ${runningAvgPrice.toFixed(2)}`);
    console.log(`  Total Value: R$ ${runningValue.toFixed(2)}`);
    
    // Also check what calculatePositions returns
    const positions = this.calculatePositions(clientId);
    const asaiPosition = positions.find(p => p.titulo === ticker);
    console.log(`\n📊 Position from calculatePositions():`, asaiPosition);
  }
}

