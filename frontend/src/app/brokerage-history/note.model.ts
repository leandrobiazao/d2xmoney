import { Operation } from '../brokerage-note/operation.model';

export interface BrokerageNote {
  id: string;
  user_id: string;
  file_name: string;
  original_file_path: string;
  processed_at: string; // ISO datetime
  note_date: string; // DD/MM/YYYY
  note_number: string;
  operations_count: number;
  operations: Operation[];
  status: 'success' | 'partial' | 'failed';
  error_message?: string;
}

export interface HistoryFilters {
  user_id?: string;
  date_from?: string;
  date_to?: string;
  note_number?: string;
}

