import { Component, Input, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';
import { PortfolioService } from '../portfolio/portfolio.service';
import { FIIService } from './fiis.service';
import { FIIPosition, FIIProfile } from './fiis.models';
import { Position } from '../portfolio/position.model';
import { Operation } from '../brokerage-note/operation.model';
import { Stock } from '../configuration/stocks/stocks.models';
import { parseDate, formatCurrency, compareDate } from '../shared/utils/common-utils';

@Component({
    selector: 'app-fiis-list',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './fiis-list.component.html',
    styleUrls: ['./fiis-list.component.css']
})
export class FIIListComponent implements OnInit, OnChanges {
    @Input() userId: string | null = null;

    fiiPositions: Position[] = [];
    operations: Operation[] = [];
    filteredOperations: Operation[] = [];
    isLoading = false;
    
    // Cache for FII tickers
    private fiiTickers: Set<string> = new Set();

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
        private fiiService: FIIService,
        private http: HttpClient
    ) { }

    ngOnInit() {
        if (this.userId) {
            this.loadData();
        }
    }

    ngOnChanges(changes: SimpleChanges) {
        if (changes['userId'] && !changes['userId'].firstChange) {
            if (this.userId) {
                this.operations = [];
                this.filteredOperations = [];
                this.fiiPositions = [];
                this.resetFilters();
                this.loadData();
            } else {
                this.operations = [];
                this.filteredOperations = [];
                this.fiiPositions = [];
            }
        }
    }

    loadData() {
        if (!this.userId) return;

        this.isLoading = true;
        const loadingUserId = this.userId;

        // Load operations first
        this.portfolioService.getOperationsAsync(loadingUserId).subscribe({
            next: (operations) => {
                if (this.userId !== loadingUserId) return;
                
                // Load FII tickers to filter operations
                this.loadFIITickers().then(() => {
                    if (this.userId !== loadingUserId) return;
                    
                    // Filter operations for FIIs only
                    this.operations = operations.filter(op => this.fiiTickers.has(op.titulo));
                    this.applyFilters();
                });
            },
            error: (err: any) => {
                if (this.userId !== loadingUserId) return;
                console.error('Error loading operations', err);
                this.operations = [];
                this.filteredOperations = [];
            }
        });

        // Load positions
        this.portfolioService.getPositionsAsync(loadingUserId).subscribe({
            next: (positions) => {
                if (this.userId !== loadingUserId) return;

                // Load FII tickers to filter positions
                this.loadFIITickers().then(() => {
                    if (this.userId !== loadingUserId) return;
                    
                    // Filter positions for FIIs only
                    const fiiPositions = positions.filter(pos => this.fiiTickers.has(pos.titulo));
                    
                    // Fetch current prices and process positions
                    this.processPositions(fiiPositions, loadingUserId);
                });
            },
            error: (err: any) => {
                if (this.userId !== loadingUserId) return;
                console.error('Error loading positions', err);
                this.fiiPositions = [];
                this.isLoading = false;
            }
        });
    }

    private loadFIITickers(): Promise<void> {
        return new Promise((resolve) => {
            let params = new HttpParams();
            params = params.set('exclude_fiis', 'false');
            params = params.set('active_only', 'false');
            
            this.http.get<Stock[]>(`/api/stocks/stocks/`, { params }).subscribe({
                next: (stocks) => {
                    this.fiiTickers.clear();
                    stocks.forEach(stock => {
                        if (stock.stock_class === 'FII' || stock.investment_type?.code === 'FIIS') {
                            this.fiiTickers.add(stock.ticker);
                        }
                    });
                    resolve();
                },
                error: (error) => {
                    console.error('Error loading stocks for FII filtering:', error);
                    // Also try FII profiles as fallback
                    this.fiiService.getFIIProfiles().subscribe({
                        next: (profiles) => {
                            this.fiiTickers.clear();
                            profiles.forEach(profile => {
                                this.fiiTickers.add(profile.ticker);
                            });
                            resolve();
                        },
                        error: (err) => {
                            console.error('Error loading FII profiles:', err);
                            resolve();
                        }
                    });
                }
            });
        });
    }

    private processPositions(positions: Position[], loadingUserId: string): void {
        const tickers = positions.map(p => p.titulo);
        if (tickers.length > 0) {
            this.portfolioService.fetchCurrentPrices(tickers).subscribe({
                next: (priceMap) => {
                    if (this.userId !== loadingUserId) return;
                    
                    const positionsWithPrices = positions.map(position => {
                        const currentPrice = priceMap.get(position.titulo);
                        let unrealizedPnL: number | undefined;
                        let valorAtual: number | undefined;
                        let totalLucro: number | undefined;

                        if (currentPrice !== undefined && position.quantidadeTotal > 0) {
                            unrealizedPnL = (currentPrice - position.precoMedioPonderado) * position.quantidadeTotal;
                            valorAtual = position.quantidadeTotal * currentPrice;
                            totalLucro = (position.lucroRealizado || 0) + unrealizedPnL;
                        } else if (position.quantidadeTotal > 0) {
                            totalLucro = position.lucroRealizado || 0;
                        } else {
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

                    this.fiiPositions = this.sortPositions(positionsWithPrices);
                    this.isLoading = false;
                },
                error: (error) => {
                    if (this.userId !== loadingUserId) return;
                    console.error('Error fetching prices:', error);
                    const positionsWithoutPrices = positions.map(position => ({
                        ...position,
                        totalLucro: position.lucroRealizado || 0
                    }));
                    this.fiiPositions = this.sortPositions(positionsWithoutPrices);
                    this.isLoading = false;
                }
            });
        } else {
            this.fiiPositions = [];
            this.isLoading = false;
        }
    }

    private sortPositions(positions: Position[]): Position[] {
        return [...positions].sort((a, b) => {
            const valorA = a.valorAtual || 0;
            const valorB = b.valorAtual || 0;

            if (valorB !== valorA) {
                return valorB - valorA;
            }
            if (b.valorTotalInvestido !== a.valorTotalInvestido) {
                return b.valorTotalInvestido - a.valorTotalInvestido;
            }
            return (b.lucroRealizado || 0) - (a.lucroRealizado || 0);
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
                        aValue = a.nota.toLowerCase();
                        bValue = b.nota.toLowerCase();
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
        return this.fiiPositions.reduce((sum, pos) => sum + pos.valorTotalInvestido, 0);
    }

    getTotalValorAtual(): number {
        return this.fiiPositions.reduce((sum, pos) => sum + (pos.valorAtual || 0), 0);
    }

    getActivePositionsCount(): number {
        return this.fiiPositions.filter(pos => pos.quantidadeTotal > 0).length;
    }
}
