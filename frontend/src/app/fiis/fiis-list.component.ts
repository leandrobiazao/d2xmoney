import { Component, Input, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PortfolioService } from '../portfolio/portfolio.service';
import { FIIService } from './fiis.service';
import { FIIPosition, FIIProfile } from './fiis.models';
import { Position } from '../portfolio/position.model';

@Component({
    selector: 'app-fiis-list',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './fiis-list.component.html',
    styleUrls: ['./fiis-list.component.css']
})
export class FIIListComponent implements OnInit, OnChanges {
    @Input() userId: string | null = null;

    fiiPositions: FIIPosition[] = [];
    isLoading = false;
    totalInvested = 0;
    totalCurrentValue = 0;

    constructor(
        private portfolioService: PortfolioService,
        private fiiService: FIIService
    ) { }

    ngOnInit() {
        if (this.userId) {
            this.loadData();
        }
    }

    ngOnChanges(changes: SimpleChanges) {
        if (changes['userId'] && !changes['userId'].firstChange && this.userId) {
            this.loadData();
        }
    }

    loadData() {
        if (!this.userId) return;

        this.isLoading = true;

        // 1. Get Portfolio Positions
        this.portfolioService.getPositionsAsync(this.userId).subscribe({
            next: (portfolio: Position[]) => {
                // Filter for FIIs
                this.fiiService.getFIIProfiles().subscribe({
                    next: (profiles) => {
                        const fiiProfilesMap = new Map(profiles.map(p => [p.ticker, p]));

                        this.fiiPositions = portfolio
                            .filter(pos => fiiProfilesMap.has(pos.titulo))
                            .map(pos => {
                                const profile = fiiProfilesMap.get(pos.titulo);
                                return {
                                    ticker: pos.titulo,
                                    quantity: pos.quantidadeTotal,
                                    averagePrice: pos.precoMedioPonderado,
                                    totalInvested: pos.valorTotalInvestido,
                                    currentPrice: pos.currentPrice,
                                    currentValue: pos.valorAtual,
                                    profit: pos.totalLucro,
                                    profile: profile
                                };
                            });

                        this.calculateTotals();
                        this.isLoading = false;
                    },
                    error: (err: any) => {
                        console.error('Error loading FII profiles', err);
                        this.isLoading = false;
                    }
                });
            },
            error: (err: any) => {
                console.error('Error loading portfolio', err);
                this.isLoading = false;
            }
        });
    }

    calculateTotals() {
        this.totalInvested = this.fiiPositions.reduce((sum, pos) => sum + pos.totalInvested, 0);
        this.totalCurrentValue = this.fiiPositions.reduce((sum, pos) => sum + (pos.currentValue || 0), 0);
    }

    formatCurrency(value: number): string {
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
    }
}
