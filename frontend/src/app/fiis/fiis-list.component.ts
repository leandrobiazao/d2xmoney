import { Component, Input, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpParams } from '@angular/common/http';
import { PortfolioService } from '../portfolio/portfolio.service';
import { FIIService } from './fiis.service';
import { FIIPosition, FIIProfile } from './fiis.models';
import { Position } from '../portfolio/position.model';
import { Stock } from '../configuration/stocks/stocks.models';
import { formatCurrency } from '../shared/utils/common-utils';

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
    isLoading = false;
    
    // Cache for FII tickers
    private fiiTickers: Set<string> = new Set();

    // View settings
    showPositions = true;

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
                this.fiiPositions = [];
                this.loadData();
            } else {
                this.fiiPositions = [];
            }
        }
    }

    loadData() {
        if (!this.userId) return;

        this.isLoading = true;
        const loadingUserId = this.userId;

        // Load positions
        this.portfolioService.getPositionsAsync(loadingUserId).subscribe({
            next: (positions) => {
                if (this.userId !== loadingUserId) return;

                // Load FII tickers to filter positions
                this.loadFIITickers().then(() => {
                    if (this.userId !== loadingUserId) return;
                    
                    // Filter positions for FIIs only
                    const fiiPositions = positions.filter(pos => 
                        this.fiiTickers.has(pos.titulo)
                    );
                    
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
                        const fetchedPrice = priceMap.get(position.titulo);
                        // Use average price if current price is not available (delisted or not found)
                        const currentPrice = fetchedPrice !== undefined ? fetchedPrice : position.precoMedioPonderado;
                        let unrealizedPnL: number | undefined;
                        let valorAtual: number | undefined;
                        let totalLucro: number | undefined;

                        if (position.quantidadeTotal > 0) {
                            if (fetchedPrice !== undefined) {
                                // Real current price available - calculate P&L
                                unrealizedPnL = (currentPrice - position.precoMedioPonderado) * position.quantidadeTotal;
                                valorAtual = position.quantidadeTotal * currentPrice;
                                totalLucro = (position.lucroRealizado || 0) + unrealizedPnL;
                            } else {
                                // No current price - use average price, P&L is zero
                                valorAtual = position.quantidadeTotal * currentPrice;
                                unrealizedPnL = 0; // No unrealized P&L when using average price
                                totalLucro = position.lucroRealizado || 0;
                            }
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
                    // When price fetch fails, use average price as current price
                    const positionsWithoutPrices = positions.map(position => {
                        const currentPrice = position.precoMedioPonderado;
                        let valorAtual: number | undefined;
                        let totalLucro: number | undefined;

                        if (position.quantidadeTotal > 0) {
                            valorAtual = position.quantidadeTotal * currentPrice;
                            totalLucro = position.lucroRealizado || 0; // No unrealized P&L when using average price
                        } else {
                            totalLucro = position.lucroRealizado || 0;
                        }

                        return {
                            ...position,
                            currentPrice,
                            valorAtual,
                            totalLucro
                        };
                    });
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
