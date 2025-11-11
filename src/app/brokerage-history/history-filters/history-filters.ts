import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HistoryFilters } from '../note.model';

@Component({
  selector: 'app-history-filters',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './history-filters.html',
  styleUrl: './history-filters.css'
})
export class HistoryFiltersComponent {
  @Output() filtersChange = new EventEmitter<HistoryFilters>();

  filters: HistoryFilters = {};
  activeFilterCount: number = 0;

  onFilterChange() {
    // Count active filters
    this.activeFilterCount = Object.values(this.filters).filter(v => v && v.toString().trim() !== '').length;
    this.filtersChange.emit(this.filters);
  }

  clearFilters() {
    this.filters = {};
    this.activeFilterCount = 0;
    this.filtersChange.emit(this.filters);
  }
}

