import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { DEFAULT_TICKER_MAPPINGS } from './ticker-mappings';

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
  
  // Dicionário inicial com alguns mapeamentos comuns (fallback)
  private defaultMappings: TickerMapping = DEFAULT_TICKER_MAPPINGS;

  constructor(private http: HttpClient) {
    this.loadMappings();
  }

  private loadMappings(): void {
    // Load from backend API
    const url = this.API_URL.endsWith('/') ? this.API_URL : `${this.API_URL}/`;
    console.log('📥 Carregando ticker mappings do backend:', url);
    
    this.http.get<TickerMapping>(url).pipe(
      tap(mappings => {
        console.log('📥 Backend retornou:', Object.keys(mappings).length, 'mapeamentos');
        console.log('📥 Mapeamentos do backend:', mappings);
        
        // Normalize backend mappings keys to match frontend normalization
        const normalizedBackendMappings: TickerMapping = {};
        for (const [nome, ticker] of Object.entries(mappings)) {
          const normalizedNome = this.normalizeNome(nome);
          normalizedBackendMappings[normalizedNome] = ticker;
        }
        
        // Use ONLY backend mappings (not merged with defaults)
        // Defaults are only used as fallback if backend fails
        this.mappings = normalizedBackendMappings;
        this.mappingsLoaded = true;
        console.log('✅ Ticker mappings carregados do backend:', Object.keys(this.mappings).length, 'mapeamentos');
        console.log('✅ Mapeamentos normalizados:', this.mappings);
      }),
      catchError(error => {
        console.warn('⚠️ Erro ao carregar mapeamentos do backend, usando defaults:', error);
        console.warn('⚠️ Error details:', error.status, error.message);
        // Fallback to defaults if backend fails
        this.mappings = { ...this.defaultMappings };
        this.mappingsLoaded = true;
        return of(this.defaultMappings);
      })
    ).subscribe();
  }

  getTicker(nome: string): string | null {
    // IMPORTANT: Use complete field (company name + classification code) for lookup
    const nomeNormalizado = this.normalizeNome(nome);
    return this.mappings[nomeNormalizado] || null;
  }

  setTicker(nome: string, ticker: string): void {
    // IMPORTANT: Save using complete field (company name + classification code)
    const nomeNormalizado = this.normalizeNome(nome);
    const tickerUpper = ticker.toUpperCase();
    
    // Update local cache immediately for responsive UI
    this.mappings[nomeNormalizado] = tickerUpper;
    
    // Save to backend
    const url = this.API_URL.endsWith('/') ? this.API_URL : `${this.API_URL}/`;
    console.log('📤 Enviando ticker mapping para backend:', { nome: nomeNormalizado, ticker: tickerUpper, url });
    
    this.http.post(url, {
      nome: nomeNormalizado,
      ticker: tickerUpper
    }).pipe(
      tap(response => {
        console.log('✅ Ticker mapping salvo no backend:', response);
        if (response && (response as any).file_path) {
          console.log('📁 Arquivo salvo em:', (response as any).file_path);
        }
      }),
      catchError(error => {
        console.error('❌ Erro ao salvar ticker mapping no backend:', error);
        console.error('Error status:', error.status);
        console.error('Error message:', error.message);
        console.error('Error details:', error.error);
        // Keep local change even if backend fails
        return of(null);
      })
    ).subscribe();
  }

  /**
   * Retorna os mapeamentos customizados em formato JSON
   */
  getCustomMappingsJSON(): string {
    const customMappings: { [nome: string]: string } = {};
    for (const [nome, ticker] of Object.entries(this.mappings)) {
      if (!this.defaultMappings[nome]) {
        customMappings[nome] = ticker;
      }
    }
    return JSON.stringify(customMappings, null, 2);
  }
  
  /**
   * Get all mappings from backend
   */
  getAllMappingsFromBackend(): Observable<TickerMapping> {
    return this.http.get<TickerMapping>(this.API_URL).pipe(
      catchError(error => {
        console.warn('Erro ao carregar mapeamentos do backend:', error);
        return of(this.defaultMappings);
      })
    );
  }

  hasMapping(nome: string): boolean {
    const nomeNormalizado = this.normalizeNome(nome);
    return !!this.mappings[nomeNormalizado];
  }

  private normalizeNome(nome: string): string {
    // Normalizar o nome removendo espaços extras e convertendo para maiúsculas
    // IMPORTANT: Preserve the complete field including classification code
    // Replace multiple spaces with single space, then trim and uppercase
    return nome.replace(/\s+/g, ' ').trim().toUpperCase();
  }

  getAllMappings(): TickerMapping {
    return { ...this.mappings };
  }
}

