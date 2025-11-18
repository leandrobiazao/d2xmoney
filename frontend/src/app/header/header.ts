import { Component, EventEmitter, Output } from '@angular/core';

@Component({
    selector: 'app-header',
    standalone: true,
    imports: [],
    templateUrl: './header.html',
    styleUrl: './header.css'
})
export class HeaderComponent {
  @Output() showHome = new EventEmitter<void>();
  @Output() showHistory = new EventEmitter<void>();
  @Output() showClubeDoValor = new EventEmitter<void>();
  @Output() showConfiguration = new EventEmitter<void>();
  @Output() showAllocationStrategy = new EventEmitter<void>();

  onShowHome(): void {
    this.showHome.emit();
  }

  onShowHistory(): void {
    this.showHistory.emit();
  }

  onShowClubeDoValor(): void {
    this.showClubeDoValor.emit();
  }

  onShowConfiguration(): void {
    this.showConfiguration.emit();
  }

  onShowAllocationStrategy(): void {
    this.showAllocationStrategy.emit();
  }
}
