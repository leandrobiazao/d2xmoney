import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { DEFAULT_TICKER_MAPPINGS } from './ticker-mappings';
import { DebugService } from '../../shared/services/debug.service';

export interface TickerMapping {
  [nome: string]: string;
}

@Injectable({
  providedIn: 'root'
})
export class TickerMappingService {
  private readonly API_URL = '/api/ticker-mappings';
  private mappings: TickerMapping = {};
  private mappingsLoaded = false;
  
  private defaultMappings: TickerMapping = DEFAULT_TICKER_MAPPINGS;

  constructor(
    private http: HttpClient,
    private debug: DebugService
  ) {
    this.loadMappings();
  }

  private loadMappings(): void {
    const url = this.API_URL.endsWith('/') ? this.API_URL : `${this.API_URL}/`;
    this.debug.log('📥 Loading ticker mappings from backend:', url);
    
    this.http.get<TickerMapping>(url).pipe(
      tap(mappings => {
        this.debug.log('📥 Backend returned:', Object.keys(mappings).length, 'mappings');
        this.debug.log('📥 Backend mappings:', mappings);
        
        // Normalize backend mappings keys to match frontend normalization
        const normalizedBackendMappings: TickerMapping = {};
        for (const [nome, ticker] of Object.entries(mappings)) {
          const normalizedNome = this.normalizeNome(nome);
          normalizedBackendMappings[normalizedNome] = ticker;
        }
        
        this.mappings = normalizedBackendMappings;
        this.mappingsLoaded = true;
        this.debug.log('✅ Ticker mappings loaded from backend:', Object.keys(this.mappings).length, 'mappings');
        this.debug.log('✅ Normalized mappings:', this.mappings);
      }),
      catchError(error => {
        this.debug.warn('⚠️ Error loading mappings from backend, using defaults:', error);
        this.debug.warn('⚠️ Error details:', error.status, error.message);
        this.mappings = { ...this.defaultMappings };
        this.mappingsLoaded = true;
        return of(this.defaultMappings);
      })
    ).subscribe();
  }

  getTicker(nome: string): string | null {
    const nomeNormalizado = this.normalizeNome(nome);
    return this.mappings[nomeNormalizado] || null;
  }

  setTicker(nome: string, ticker: string): void {
    const nomeNormalizado = this.normalizeNome(nome);
    const tickerUpper = ticker.toUpperCase();
    
    this.mappings[nomeNormalizado] = tickerUpper;
    
    const url = this.API_URL.endsWith('/') ? this.API_URL : `${this.API_URL}/`;
    this.debug.log('📤 Sending ticker mapping to backend:', { nome: nomeNormalizado, ticker: tickerUpper, url });
    
    this.http.post(url, {
      nome: nomeNormalizado,
      ticker: tickerUpper
    }).pipe(
      tap(response => {
        this.debug.log('✅ Ticker mapping saved to backend:', response);
        if (response && (response as any).file_path) {
          this.debug.log('📁 File saved at:', (response as any).file_path);
        }
      }),
      catchError(error => {
        this.debug.error('❌ Error saving ticker mapping to backend:', error);
        this.debug.error('Error status:', error.status);
        this.debug.error('Error message:', error.message);
        this.debug.error('Error details:', error.error);
        return of(null);
      })
    ).subscribe();
  }

  getCustomMappingsJSON(): string {
    const customMappings: { [nome: string]: string } = {};
    for (const [nome, ticker] of Object.entries(this.mappings)) {
      if (!this.defaultMappings[nome]) {
        customMappings[nome] = ticker;
      }
    }
    return JSON.stringify(customMappings, null, 2);
  }
  
  getAllMappingsFromBackend(): Observable<TickerMapping> {
    return this.http.get<TickerMapping>(this.API_URL).pipe(
      catchError(error => {
        this.debug.warn('Error loading mappings from backend:', error);
        return of(this.defaultMappings);
      })
    );
  }

  hasMapping(nome: string): boolean {
    const nomeNormalizado = this.normalizeNome(nome);
    return !!this.mappings[nomeNormalizado];
  }

  private normalizeNome(nome: string): string {
    return nome.replace(/\s+/g, ' ').trim().toUpperCase();
  }

  getAllMappings(): TickerMapping {
    return { ...this.mappings };
  }
}
