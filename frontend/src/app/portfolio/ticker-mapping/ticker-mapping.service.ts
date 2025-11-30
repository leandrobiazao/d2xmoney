import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, firstValueFrom } from 'rxjs';
import { catchError, tap, map } from 'rxjs/operators';
import { DebugService } from '../../shared/services/debug.service';

export interface TickerMapping {
  [nome: string]: string;
}

export interface DiscoveryResponse {
  ticker: string | null;
  found: boolean;
  source?: string;
}

@Injectable({
  providedIn: 'root'
})
export class TickerMappingService {
  private readonly API_URL = '/api/ticker-mappings';
  private mappings: TickerMapping = {};
  private mappingsLoaded = false;

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
        
        // Normalize backend mappings keys to match frontend normalization
        const normalizedBackendMappings: TickerMapping = {};
        for (const [nome, ticker] of Object.entries(mappings)) {
          const normalizedNome = this.normalizeNome(nome);
          normalizedBackendMappings[normalizedNome] = ticker;
        }
        
        // Use only database mappings (no defaults fallback)
        this.mappings = normalizedBackendMappings;
        
        this.mappingsLoaded = true;
        this.debug.log('✅ Ticker mappings loaded from database:', Object.keys(this.mappings).length, 'mappings');
        
        if (Object.keys(this.mappings).length === 0) {
          this.debug.warn('⚠️ Database is empty. Run: python manage.py seed_mappings');
        }
      }),
      catchError(error => {
        this.debug.error('❌ Error loading mappings from backend:', error);
        this.mappings = {};
        this.mappingsLoaded = true;
        return of({});
      })
    ).subscribe();
  }

  getTicker(nome: string): string | null {
    const nomeNormalizado = this.normalizeNome(nome);
    return this.mappings[nomeNormalizado] || null;
  }

  async discoverTicker(companyName: string): Promise<string | null> {
    const url = `${this.API_URL}/discover/`;
    this.debug.log(`🔍 Discovering ticker for: "${companyName}"`);
    
    try {
      const response = await firstValueFrom(
        this.http.post<DiscoveryResponse>(url, { company_name: companyName })
      );
      
      if (response.found && response.ticker) {
        this.debug.log(`✅ Ticker discovered: ${response.ticker} (source: ${response.source})`);
        // Update local cache
        this.mappings[this.normalizeNome(companyName)] = response.ticker;
        return response.ticker;
      } else {
        this.debug.warn(`⚠️ Ticker discovery failed for: "${companyName}"`);
        return null;
      }
    } catch (error) {
      this.debug.error(`❌ Error discovering ticker for "${companyName}":`, error);
      return null;
    }
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
      }),
      catchError(error => {
        this.debug.error('❌ Error saving ticker mapping to backend:', error);
        return of(null);
      })
    ).subscribe();
  }

  syncMappingsFromJson(): Observable<any> {
    const url = this.API_URL.endsWith('/') ? this.API_URL : `${this.API_URL}/`;
    this.debug.log('🔄 Syncing ticker mappings from JSON to database...');
    
    return this.http.put(url, {}).pipe(
      tap(response => {
        this.debug.log('✅ Ticker mappings synced:', response);
        // Reload mappings after sync
        this.loadMappings();
      }),
      catchError(error => {
        this.debug.error('❌ Error syncing mappings:', error);
        return of(null);
      })
    );
  }
  
  getAllMappingsFromBackend(): Observable<TickerMapping> {
    return this.http.get<TickerMapping>(this.API_URL).pipe(
      catchError(error => {
        this.debug.warn('Error loading mappings from backend:', error);
        return of({});
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
