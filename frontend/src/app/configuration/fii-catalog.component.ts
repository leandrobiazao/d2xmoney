import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FIIService } from '../fiis/fiis.service';
import { FIIProfile } from '../fiis/fiis.models';

@Component({
    selector: 'app-fii-catalog',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './fii-catalog.component.html',
    styleUrls: ['./fii-catalog.component.css']
})
export class FIICatalogComponent implements OnInit {
    allFIIs: FIIProfile[] = [];
    filteredFIIs: FIIProfile[] = [];
    isLoading = false;

    // Filters
    searchTicker = '';
    filterSegment = '';

    // Pagination
    currentPage = 1;
    pageSize = 50;

    constructor(private fiiService: FIIService) { }

    ngOnInit() {
        this.loadFIIs();
    }

    loadFIIs() {
        this.isLoading = true;
        this.fiiService.getFIIProfiles().subscribe({
            next: (fiis) => {
                this.allFIIs = fiis.sort((a, b) => a.ticker.localeCompare(b.ticker));
                this.applyFilters();
                this.isLoading = false;
            },
            error: (err) => {
                console.error('Error loading FIIs', err);
                this.isLoading = false;
            }
        });
    }

    applyFilters() {
        this.filteredFIIs = this.allFIIs.filter(fii => {
            const matchesTicker = !this.searchTicker ||
                fii.ticker.toUpperCase().includes(this.searchTicker.toUpperCase());

            const matchesSegment = !this.filterSegment ||
                fii.segment.toUpperCase().includes(this.filterSegment.toUpperCase());

            return matchesTicker && matchesSegment;
        });

        this.currentPage = 1;
    }

    resetFilters() {
        this.searchTicker = '';
        this.filterSegment = '';
        this.applyFilters();
    }

    get paginatedFIIs(): FIIProfile[] {
        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        return this.filteredFIIs.slice(start, end);
    }

    get totalPages(): number {
        return Math.ceil(this.filteredFIIs.length / this.pageSize);
    }

    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
        }
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
        }
    }

    getUniqueSegments(): string[] {
        const segments = new Set(this.allFIIs.map(fii => fii.segment).filter(s => s));
        return Array.from(segments).sort();
    }

    formatCurrency(value: number): string {
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
    }

    formatPercentage(value: number | string | null | undefined): string {
        if (value == null || value === undefined) return '-';
        const numValue = typeof value === 'string' ? parseFloat(value) : value;
        if (isNaN(numValue)) return '-';
        return numValue.toFixed(2) + '%';
    }

    formatNumber(value: number | string | null | undefined, decimals: number = 2): string {
        if (value == null || value === undefined) return '-';
        const numValue = typeof value === 'string' ? parseFloat(value) : value;
        if (isNaN(numValue)) return '-';
        return numValue.toFixed(decimals);
    }
}
