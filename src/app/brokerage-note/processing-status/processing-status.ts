import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-processing-status',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './processing-status.html',
  styleUrl: './processing-status.css'
})
export class ProcessingStatusComponent {
  @Input() status: 'idle' | 'processing' | 'success' | 'error' = 'idle';
  @Input() operationsCount: number = 0;
  @Input() errorMessage: string | null = null;
  @Input() serverStatus: 'checking' | 'online' | 'offline' = 'checking';
}

