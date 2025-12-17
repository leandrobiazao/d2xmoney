import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CorporateEventsService } from './corporate-events.service';
import { CorporateEvent, CorporateEventCreateRequest } from './corporate-events.models';

@Component({
  selector: 'app-corporate-events',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './corporate-events.component.html',
  styleUrl: './corporate-events.component.css'
})
export class CorporateEventsComponent implements OnInit {
  events: CorporateEvent[] = [];
  filteredEvents: CorporateEvent[] = [];
  isLoading = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;

  // Form state
  showForm = false;
  editingEvent: CorporateEvent | null = null;
  formData: CorporateEventCreateRequest = {
    ticker: '',
    previous_ticker: '',
    event_type: 'GROUPING',
    asset_type: 'STOCK',
    ex_date: '',
    ratio: '',
    description: ''
  };

  // Filters
  searchTicker = '';
  filterEventType = '';
  filterAssetType = '';

  // Application state
  applyingEventId: number | null = null;
  applyingUserId: string | null = null;

  constructor(private corporateEventsService: CorporateEventsService) {}

  ngOnInit(): void {
    this.loadEvents();
  }

  loadEvents(): void {
    this.isLoading = true;
    this.errorMessage = null;
    this.successMessage = null;

    this.corporateEventsService.getAllEvents().subscribe({
      next: (events) => {
        this.events = events.sort((a, b) => {
          const dateA = new Date(a.ex_date);
          const dateB = new Date(b.ex_date);
          return dateB.getTime() - dateA.getTime(); // Most recent first
        });
        this.applyFilters();
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar eventos corporativos';
        this.isLoading = false;
        console.error('Error loading corporate events:', error);
      }
    });
  }

  applyFilters(): void {
    this.filteredEvents = this.events.filter(event => {
      const matchesTicker = !this.searchTicker ||
        event.ticker.toUpperCase().includes(this.searchTicker.toUpperCase());
      
      const matchesEventType = !this.filterEventType ||
        event.event_type === this.filterEventType;
      
      const matchesAssetType = !this.filterAssetType ||
        event.asset_type === this.filterAssetType;
      
      return matchesTicker && matchesEventType && matchesAssetType;
    });
  }

  resetFilters(): void {
    this.searchTicker = '';
    this.filterEventType = '';
    this.filterAssetType = '';
    this.applyFilters();
  }

  onCreate(): void {
    this.formData = {
      ticker: '',
      previous_ticker: '',
      event_type: 'GROUPING',
      asset_type: 'STOCK',
      ex_date: '',
      ratio: '',
      description: ''
    };
    this.editingEvent = null;
    this.showForm = true;
    this.errorMessage = null;
    this.successMessage = null;
  }

  onEdit(event: CorporateEvent): void {
    this.editingEvent = event;
    this.formData = {
      ticker: event.ticker,
      previous_ticker: event.previous_ticker || '',
      event_type: event.event_type,
      asset_type: event.asset_type,
      ex_date: event.ex_date,
      ratio: event.ratio,
      description: event.description || ''
    };
    this.showForm = true;
    this.errorMessage = null;
    this.successMessage = null;
  }

  onCancel(): void {
    this.showForm = false;
    this.editingEvent = null;
    this.errorMessage = null;
    this.successMessage = null;
  }

  onSave(): void {
    // Validate required fields based on event type
    if (!this.formData.ticker || !this.formData.ex_date) {
      this.errorMessage = 'Ticker e data ex-evento são obrigatórios';
      return;
    }

    // For TICKER_CHANGE, previous_ticker is required
    if (this.formData.event_type === 'TICKER_CHANGE') {
      if (!this.formData.previous_ticker) {
        this.errorMessage = 'Ticker anterior é obrigatório para mudança de ticker';
        return;
      }
      this.formData.ratio = ''; // Clear ratio for ticker change
    } else if (this.formData.event_type === 'FUND_CONVERSION') {
      if (!this.formData.previous_ticker) {
        this.errorMessage = 'Ticker do fundo extinto é obrigatório para conversão de fundo';
        return;
      }
      if (!this.formData.ratio) {
        this.errorMessage = 'Proporção é obrigatória para conversão de fundo (ex: 3:2)';
        return;
      }
      if (!/^\d+:\d+$/.test(this.formData.ratio)) {
        this.errorMessage = 'Proporção deve estar no formato X:Y (ex: 3:2 para 3 novas cotas para cada 2 antigas)';
        return;
      }
    } else {
      // For other event types, ratio is required
      if (!this.formData.ratio) {
        this.errorMessage = 'Proporção é obrigatória para este tipo de evento';
        return;
      }

      // Validate ratio format
      if (!/^\d+:\d+$/.test(this.formData.ratio)) {
        this.errorMessage = 'Proporção deve estar no formato X:Y (ex: 20:1, 1:5)';
        return;
      }
    }

    if (this.editingEvent) {
      this.corporateEventsService.updateEvent(this.editingEvent.id, this.formData).subscribe({
        next: () => {
          this.showForm = false;
          this.loadEvents();
          this.successMessage = 'Evento atualizado com sucesso!';
          setTimeout(() => this.successMessage = null, 3000);
        },
        error: (error) => {
          this.errorMessage = error.error?.error || 'Erro ao atualizar evento corporativo';
          console.error('Error updating corporate event:', error);
        }
      });
    } else {
      this.corporateEventsService.createEvent(this.formData).subscribe({
        next: () => {
          this.showForm = false;
          this.loadEvents();
          this.successMessage = 'Evento criado com sucesso!';
          setTimeout(() => this.successMessage = null, 3000);
        },
        error: (error) => {
          this.errorMessage = error.error?.error || 'Erro ao criar evento corporativo';
          console.error('Error creating corporate event:', error);
        }
      });
    }
  }

  onDelete(event: CorporateEvent): void {
    if (!confirm(`Tem certeza que deseja excluir o evento ${event.ticker} - ${event.event_type_display}?`)) {
      return;
    }

    this.corporateEventsService.deleteEvent(event.id).subscribe({
      next: () => {
        this.loadEvents();
        this.successMessage = 'Evento excluído com sucesso!';
        setTimeout(() => this.successMessage = null, 3000);
      },
      error: (error) => {
        this.errorMessage = error.error?.error || 'Erro ao excluir evento corporativo';
        console.error('Error deleting corporate event:', error);
      }
    });
  }

  onApply(event: CorporateEvent): void {
    if (!confirm(`Aplicar o ajuste do evento ${event.ticker} (${event.ratio}) a todas as posições?`)) {
      return;
    }

    this.applyingEventId = event.id;
    this.errorMessage = null;
    this.successMessage = null;

    this.corporateEventsService.applyEvent(event.id).subscribe({
      next: (response) => {
        this.applyingEventId = null;
        this.successMessage = response.message || 'Ajuste aplicado com sucesso!';
        this.loadEvents();
        setTimeout(() => this.successMessage = null, 5000);
      },
      error: (error) => {
        this.applyingEventId = null;
        this.errorMessage = error.error?.error || error.error?.details || 'Erro ao aplicar ajuste';
        console.error('Error applying corporate event:', error);
      }
    });
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR');
  }

  clearMessages(): void {
    this.errorMessage = null;
    this.successMessage = null;
  }
}

