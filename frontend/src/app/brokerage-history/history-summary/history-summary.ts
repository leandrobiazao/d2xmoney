import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BrokerageNote } from '../note.model';

@Component({
  selector: 'app-history-summary',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './history-summary.html',
  styleUrl: './history-summary.css'
})
export class HistorySummaryComponent implements OnChanges {
  @Input() notes: BrokerageNote[] = [];

  totalNotes: number = 0;
  totalOperations: number = 0;
  successRate: number = 0;
  dateRange: string = '';
  mostActiveUser: string = '';

  ngOnChanges(changes: SimpleChanges) {
    if (changes['notes']) {
      this.calculateSummary();
    }
  }

  private calculateSummary() {
    this.totalNotes = this.notes.length;
    this.totalOperations = this.notes.reduce((sum, note) => sum + note.operations_count, 0);
    
    const successCount = this.notes.filter(n => n.status === 'success').length;
    this.successRate = this.totalNotes > 0 ? (successCount / this.totalNotes) * 100 : 0;
    
    if (this.notes.length > 0) {
      const dates = this.notes.map(n => n.note_date).sort();
      this.dateRange = `${dates[0]} - ${dates[dates.length - 1]}`;
    }
    
    // Find most active user
    const userCounts: { [key: string]: number } = {};
    this.notes.forEach(note => {
      userCounts[note.user_id] = (userCounts[note.user_id] || 0) + 1;
    });
    
    const mostActive = Object.entries(userCounts).sort((a, b) => b[1] - a[1])[0];
    this.mostActiveUser = mostActive ? mostActive[0] : '';
  }
}

