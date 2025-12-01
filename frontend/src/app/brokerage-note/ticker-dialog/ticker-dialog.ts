import { Component, EventEmitter, Input, Output, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TickerMappingService } from '../../portfolio/ticker-mapping/ticker-mapping.service';

@Component({
  selector: 'app-ticker-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ticker-dialog.html',
  styleUrl: './ticker-dialog.css'
})
export class TickerDialogComponent implements OnInit {
  @Input() nome: string = ''; // Complete field (company name + classification code)
  @Input() operationData: any = null;
  @Output() confirm = new EventEmitter<string>();
  @Output() cancel = new EventEmitter<void>();

  ticker: string = '';

  constructor(private tickerMappingService: TickerMappingService) {}

  ngOnInit(): void {
    setTimeout(() => {
      const input = document.getElementById('ticker');
      if (input) {
        input.focus();
      }
    }, 100);
  }

  onSubmit(event?: Event): void {
    // Prevent form submission from causing page reload
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    
    if (this.ticker && this.ticker.trim().length > 0) {
      const tickerUpper = this.ticker.trim().toUpperCase();
      
      // Validate ticker format (4 letters + 1-2 digits)
      if (!/^[A-Z]{4}\d{1,2}$/.test(tickerUpper)) {
        alert('Formato de ticker inválido. Use o formato: 4 letras + 1-2 dígitos (ex: PETR4, VALE3)');
        return;
      }
      
      // NOTE: We don't save the mapping here anymore - it's saved in pdf-parser.service.ts
      // after receiving the ticker from the dialog. This ensures all variations are saved correctly.
      
      // Clear the ticker field after confirmation
      this.ticker = '';
      
      this.confirm.emit(tickerUpper);
    }
  }

  onCancel(): void {
    // Clear the ticker field when canceling
    this.ticker = '';
    this.cancel.emit();
  }

  onOverlayClick(event: MouseEvent): void {
    // Only cancel if clicking directly on the overlay, not on child elements
    if (event.target === event.currentTarget) {
      this.onCancel();
    }
  }
}

