import { Injectable } from '@angular/core';
import { Operation } from '../brokerage-note/operation.model';
import { Position } from './position.model';
import { Portfolio } from './portfolio.model';

@Injectable({
  providedIn: 'root'
})
export class PortfolioService {
  private readonly STORAGE_KEY_PREFIX = 'portfolio-';

  constructor() {}

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
    const portfolio = this.loadPortfolio(clientId);
    return portfolio?.operations || [];
  }

  addOperations(clientId: string, operations: Operation[]): void {
    if (!operations || operations.length === 0) {
      return;
    }

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

    // Adicionar clientId a cada operação
    const operationsWithClientId = operations.map(op => ({
      ...op,
      clientId,
      id: op.id || this.generateOperationId()
    }));

    portfolio.operations.push(...operationsWithClientId);
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
    const portfolio = this.loadPortfolio(clientId);
    if (!portfolio) {
      return;
    }

    portfolio.operations = portfolio.operations.filter(op => op.id !== operationId);
    portfolio.lastUpdated = new Date().toISOString();
    portfolio.positions = this.calculatePositions(clientId);
    this.savePortfolio(portfolio);
  }

  calculatePositions(clientId: string): Position[] {
    const operations = this.getOperations(clientId);
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
          valorTotalInvestido: 0
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
        const quantidadeVendida = Math.abs(operation.quantidade);
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

    // Remover posições zeradas
    const positions = Array.from(positionsMap.values())
      .filter(p => p.quantidadeTotal > 0)
      .sort((a, b) => a.titulo.localeCompare(b.titulo));

    return positions;
  }

  getPositions(clientId: string): Position[] {
    const portfolio = this.loadPortfolio(clientId);
    if (portfolio && portfolio.positions.length > 0) {
      return portfolio.positions;
    }
    // Recalcular se não houver posições salvas
    return this.calculatePositions(clientId);
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
}

