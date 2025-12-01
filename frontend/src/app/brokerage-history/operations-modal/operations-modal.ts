import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { BrokerageHistoryService } from '../history.service';
import { BrokerageNote } from '../note.model';
import { Operation } from '../../brokerage-note/operation.model';
import { StocksService } from '../../configuration/stocks/stocks.service';
import { Stock } from '../../configuration/stocks/stocks.models';
import { ConfigurationService, InvestmentType } from '../../configuration/configuration.service';
import { DebugService } from '../../shared/services/debug.service';
import { formatCurrency } from '../../shared/utils/common-utils';

interface GroupedOperations {
  investmentType: InvestmentType | null;
  operations: Operation[];
}

@Component({
  selector: 'app-operations-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './operations-modal.html',
  styleUrl: './operations-modal.css'
})
export class OperationsModalComponent implements OnInit, OnDestroy {
  @Input() noteId: string | null = null;
  @Output() close = new EventEmitter<void>();

  note: BrokerageNote | null = null;
  groupedOperations: GroupedOperations[] = [];
  isLoading = false;
  error: string | null = null;

  private stockCatalog: Map<string, Stock> = new Map();
  private investmentTypes: InvestmentType[] = [];

  constructor(
    private historyService: BrokerageHistoryService,
    private stocksService: StocksService,
    private configService: ConfigurationService,
    private debug: DebugService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    if (this.noteId) {
      this.loadNoteAndGroupOperations();
    }
  }

  ngOnDestroy(): void {
    // Cleanup if needed
  }

  private loadNoteAndGroupOperations(): void {
    this.isLoading = true;
    this.error = null;

    // Load stock catalog and investment types in parallel
    Promise.all([
      this.loadStockCatalog(),
      this.loadInvestmentTypes()
    ]).then(() => {
      if (this.noteId) {
        this.loadNote();
      }
    }).catch((error) => {
      this.debug.error('Error loading data:', error);
      this.error = 'Erro ao carregar dados necessários.';
      this.isLoading = false;
    });
  }

  private loadStockCatalog(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Load all stocks including FIIs for filtering
      // We need to use HttpClient directly to pass exclude_fiis=false parameter
      const params = new HttpParams()
        .set('active_only', 'false')
        .set('exclude_fiis', 'false');
      
      this.http.get<Stock[]>(`/api/stocks/stocks/`, { params }).subscribe({
        next: (stocks) => {
          this.stockCatalog.clear();
          stocks.forEach(stock => {
            this.stockCatalog.set(stock.ticker.toUpperCase(), stock);
          });
          this.debug.log(`✅ Loaded ${this.stockCatalog.size} stocks into catalog`);
          // Debug: Check if HASH11 and BARI11 are in the catalog
          const hash11 = this.stockCatalog.get('HASH11');
          const bari11 = this.stockCatalog.get('BARI11');
          if (hash11) {
            this.debug.log(`✅ HASH11 found in catalog:`, {
              ticker: hash11.ticker,
              stock_class: hash11.stock_class,
              investment_type: hash11.investment_type ? {
                name: hash11.investment_type.name,
                code: hash11.investment_type.code
              } : null
            });
          } else {
            this.debug.warn(`⚠️ HASH11 NOT found in catalog`);
          }
          if (bari11) {
            this.debug.log(`✅ BARI11 found in catalog:`, {
              ticker: bari11.ticker,
              stock_class: bari11.stock_class,
              investment_type: bari11.investment_type ? {
                name: bari11.investment_type.name,
                code: bari11.investment_type.code
              } : null
            });
          } else {
            this.debug.warn(`⚠️ BARI11 NOT found in catalog`);
          }
          resolve();
        },
        error: (error) => {
          this.debug.error('Error loading stock catalog:', error);
          reject(error);
        }
      });
    });
  }

  private loadInvestmentTypes(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.configService.getInvestmentTypes(true).subscribe({
        next: (types) => {
          this.investmentTypes = types;
          this.debug.log(`✅ Loaded ${this.investmentTypes.length} investment types`);
          resolve();
        },
        error: (error) => {
          this.debug.error('Error loading investment types:', error);
          reject(error);
        }
      });
    });
  }

  private loadNote(): void {
    if (!this.noteId) {
      this.isLoading = false;
      return;
    }

    this.historyService.getNoteById(this.noteId).subscribe({
      next: (note) => {
        this.note = note;
        this.groupOperations(note.operations || []);
        this.isLoading = false;
      },
      error: (error) => {
        this.debug.error('Error loading note:', error);
        this.error = 'Erro ao carregar a nota de corretagem.';
        this.isLoading = false;
      }
    });
  }

  private groupOperations(operations: Operation[]): void {
    // Debug: Check if HASH11 or BARI11 operations are in the list
    const hash11Ops = operations.filter(op => op.titulo.toUpperCase() === 'HASH11');
    const bari11Ops = operations.filter(op => op.titulo.toUpperCase() === 'BARI11');
    if (hash11Ops.length > 0) {
      this.debug.log(`🔍 Found ${hash11Ops.length} HASH11 operation(s) in note`);
    }
    if (bari11Ops.length > 0) {
      this.debug.log(`🔍 Found ${bari11Ops.length} BARI11 operation(s) in note`);
    }
    
    // Create map for investment type lookup by name
    const investmentTypeMap = new Map<string, InvestmentType>();
    this.investmentTypes.forEach(type => {
      investmentTypeMap.set(type.name, type);
      investmentTypeMap.set(type.code, type); // Also map by code for convenience
    });

    // Group operations by investment type
    const groupedMap = new Map<string | null, Operation[]>();

    // Include investment types: "Renda Variável em Reais", "Renda Variável em Dólares", and "Fundos Imobiliários"
    const validInvestmentTypeNames = ['Renda Variável em Reais', 'Renda Variável em Dólares', 'Fundos Imobiliários'];
    const validInvestmentTypeCodes = ['RENDA_VARIAVEL_REAIS', 'RENDA_VARIAVEL_DOLARES', 'FIIS'];
    
    // Debug: Log valid investment types
    this.debug.log(`📋 Valid investment types:`, {
      names: validInvestmentTypeNames,
      codes: validInvestmentTypeCodes
    });

    operations.forEach(operation => {
      const ticker = operation.titulo.toUpperCase();
      const stock = this.stockCatalog.get(ticker);
      
      // Debug logging for troubleshooting - especially for HASH11 and BARI11
      if (ticker === 'HASH11' || ticker === 'BARI11') {
        this.debug.log(`🔍 Processing ${ticker}:`, {
          foundInCatalog: !!stock,
          stockClass: stock?.stock_class,
          investmentType: stock?.investment_type ? {
            name: stock.investment_type.name,
            code: stock.investment_type.code
          } : null
        });
      }
      
      if (!stock) {
        this.debug.log(`⚠️ Stock not found in catalog: ${ticker} - will be classified as "Não Classificado"`);
      } else if (!stock.investment_type) {
        this.debug.log(`⚠️ Stock ${ticker} has no investment_type - will be classified as "Não Classificado"`);
      } else {
        this.debug.log(`ℹ️ Stock ${ticker} has investment_type: ${stock.investment_type.name} (code: ${stock.investment_type.code})`);
      }

      let investmentType: InvestmentType | null = null;

      if (stock && stock.investment_type) {
        const typeName = stock.investment_type.name;
        const typeCode = stock.investment_type.code;

        // Check if it's a FII (by stock_class or investment_type code)
        const isFII = stock.stock_class === 'FII' || typeCode === 'FIIS';
        
        if (isFII) {
          // For FIIs, use "Fundos Imobiliários" as the investment type name
          // Find the FII investment type from the configuration
          const fiiType = this.investmentTypes.find(t => t.code === 'FIIS' || t.name === 'Fundos Imobiliários');
          if (fiiType) {
            investmentType = fiiType;
            this.debug.log(`✅ Matched ${ticker} to FII investment type: ${fiiType.name}`);
          } else {
            // If FII type not found in config, still group as FIIs
            investmentType = { id: 0, name: 'Fundos Imobiliários', code: 'FIIS', display_order: 3, is_active: true } as InvestmentType;
            this.debug.log(`✅ Matched ${ticker} to FII (using default type)`);
          }
        } else if (validInvestmentTypeNames.includes(typeName) || validInvestmentTypeCodes.includes(typeCode)) {
          // Valid investment type (Renda Variável em Reais or Renda Variável em Dólares)
          investmentType = stock.investment_type;
          this.debug.log(`✅ Matched ${ticker} to investment type: ${typeName} (code: ${typeCode})`);
          if (ticker === 'HASH11') {
            this.debug.log(`🔍 HASH11 classification details:`, {
              typeName,
              typeCode,
              inValidNames: validInvestmentTypeNames.includes(typeName),
              inValidCodes: validInvestmentTypeCodes.includes(typeCode),
              validNames: validInvestmentTypeNames,
              validCodes: validInvestmentTypeCodes
            });
          }
        } else {
          // Unmapped or invalid type - go to "Não Classificado"
          this.debug.log(`⚠️ ${ticker} has investment type "${typeName}" (${typeCode}) which is not in valid types - will be classified as "Não Classificado"`);
          if (ticker === 'HASH11') {
            this.debug.log(`🔍 HASH11 NOT matched - details:`, {
              typeName,
              typeCode,
              validNames: validInvestmentTypeNames,
              validCodes: validInvestmentTypeCodes,
              nameMatch: validInvestmentTypeNames.includes(typeName),
              codeMatch: validInvestmentTypeCodes.includes(typeCode)
            });
          }
          investmentType = null;
        }
      } else {
        // No stock found or no investment type - go to "Não Classificado"
        investmentType = null;
        if (ticker === 'HASH11' || ticker === 'BARI11') {
          this.debug.log(`⚠️ ${ticker} will be classified as "Não Classificado" because:`, {
            stockFound: !!stock,
            hasInvestmentType: !!(stock?.investment_type)
          });
        }
      }

      const key = investmentType ? investmentType.name : null;
      if (!groupedMap.has(key)) {
        groupedMap.set(key, []);
      }
      groupedMap.get(key)!.push(operation);
      
      if (ticker === 'HASH11' || ticker === 'BARI11') {
        this.debug.log(`✅ ${ticker} added to group: "${key || 'Não Classificado'}"`);
      }
    });

    // Convert map to array and sort by display_order
    this.groupedOperations = Array.from(groupedMap.entries())
      .map(([key, ops]) => {
        const investmentType = key ? investmentTypeMap.get(key) || null : null;
        return {
          investmentType,
          operations: ops.sort((a, b) => {
            // Sort operations by date, then by order
            const dateA = new Date(a.data.split('/').reverse().join('-'));
            const dateB = new Date(b.data.split('/').reverse().join('-'));
            if (dateA.getTime() !== dateB.getTime()) {
              return dateA.getTime() - dateB.getTime();
            }
            return a.ordem - b.ordem;
          })
        };
      })
      .filter(group => group.operations.length > 0) // Remove empty groups
      .sort((a, b) => {
        // Sort groups by display_order if available
        if (a.investmentType && b.investmentType) {
          return a.investmentType.display_order - b.investmentType.display_order;
        }
        // "Não Classificado" goes last
        if (!a.investmentType) return 1;
        if (!b.investmentType) return -1;
        return 0;
      });

    // Debug: Log all groups and their operations
    this.debug.log(`✅ Grouped ${operations.length} operations into ${this.groupedOperations.length} groups:`);
    this.groupedOperations.forEach(group => {
      const groupName = group.investmentType ? group.investmentType.name : 'Não Classificado';
      const tickers = group.operations.map(op => op.titulo).join(', ');
      this.debug.log(`  - ${groupName}: ${group.operations.length} operação(ões) - ${tickers}`);
    });
  }

  onClose(): void {
    this.close.emit();
  }

  onBackdropClick(event: Event): void {
    if (event.target === event.currentTarget) {
      this.onClose();
    }
  }

  formatCurrency(value: number): string {
    return formatCurrency(value);
  }

  getInvestmentTypeName(group: GroupedOperations): string {
    return group.investmentType ? group.investmentType.name : 'Não Classificado';
  }
}

