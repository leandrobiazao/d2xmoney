import { Component, OnInit, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UserService } from '../users/user.service';
import { User } from '../users/user.model';
import {
  AllocationStrategyService,
  UserAllocationStrategy,
  PieChartData,
  InvestmentTypeAllocation,
  SubTypeAllocation,
  FIIAllocation
} from './allocation-strategy.service';
import { UserItemComponent } from '../users/user-item/user-item';
import { ConfigurationService, InvestmentType, InvestmentSubType } from '../configuration/configuration.service';
import { RebalancingService, RebalancingRecommendation, RebalancingAction } from '../rebalancing/rebalancing.service';
import { FIIService } from '../fiis/fiis.service';
import { FIIProfile } from '../fiis/fiis.models';
import { HttpClient } from '@angular/common/http';
import * as XLSX from 'xlsx';

interface DraftSubTypeAllocation extends Omit<SubTypeAllocation, 'id'> {
  id?: number;
  sub_type_id?: number;
}

interface DraftFIIAllocation extends Omit<FIIAllocation, 'id'> {
  id?: number;
  stock_id?: number;
}

interface DraftTypeAllocation extends Omit<InvestmentTypeAllocation, 'id' | 'sub_type_allocations' | 'fii_allocations'> {
  id?: number;
  investment_type_id: number;
  sub_type_allocations?: DraftSubTypeAllocation[];
  fii_allocations?: DraftFIIAllocation[];
}

@Component({
  selector: 'app-allocation-strategy',
  standalone: true,
  imports: [CommonModule, FormsModule, UserItemComponent],
  templateUrl: './allocation-strategy.html',
  styleUrl: './allocation-strategy.css'
})
export class AllocationStrategyComponent implements OnInit, OnChanges {
  @Input() userId?: string;
  
  users: User[] = [];
  selectedUser: User | null = null;
  isLoading = false;
  isLoadingStrategy = false;
  isSaving = false;
  errorMessage: string | null = null;
  strategy: UserAllocationStrategy | null = null;
  pieChartData: PieChartData | null = null;
  draftTypeAllocations: DraftTypeAllocation[] = [];
  totalPortfolioValueInput: number | null = null;
  investmentSubTypes: InvestmentSubType[] = [];
  
  // FII catalog
  allFIIs: FIIProfile[] = [];
  fiiSearchTerm: { [key: number]: string } = {}; // Search term per type allocation index
  
  // ETF Renda Fixa catalog
  etfRendaFixaStocks: any[] = [];
  
  // Tab management
  activeTab: 'configuration' | 'rebalancing' = 'configuration';
  
  // Rebalancing data
  recommendations: RebalancingRecommendation[] = [];
  currentRecommendation: RebalancingRecommendation | null = null;
  isLoadingRecommendations = false;
  isGeneratingRecommendations = false;
  currentAllocation: any = null;

  constructor(
    private userService: UserService,
    private allocationStrategyService: AllocationStrategyService,
    private configurationService: ConfigurationService,
    private rebalancingService: RebalancingService,
    private fiiService: FIIService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.loadInvestmentSubTypes();
    this.loadFIIs();
    // Note: loadETFRendaFixaStocks is called after subtypes are loaded (in loadInvestmentSubTypes callback)
    // Only load users if userId is not provided (standalone mode)
    if (!this.userId) {
      this.loadUsers();
    } else {
      // When userId is provided, load that user and their strategy
      this.loadUserAndStrategy(this.userId);
    }
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['userId'] && !changes['userId'].firstChange && this.userId) {
      this.loadUserAndStrategy(this.userId);
    }
  }

  loadUserAndStrategy(userId: string): void {
    this.userService.getUserById(userId).subscribe({
      next: (user) => {
        this.selectedUser = user;
        this.loadStrategy(userId);
      },
      error: (error) => {
        console.error('Error loading user:', error);
        this.errorMessage = 'Erro ao carregar usuário';
      }
    });
  }

  loadUsers(): void {
    this.isLoading = true;
    this.userService.getUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar usuários';
        this.isLoading = false;
        console.error('Error loading users:', error);
      }
    });
  }

  onUserSelected(userId: string): void {
    this.userService.getUserById(userId).subscribe({
      next: (user) => {
        this.selectedUser = user;
        this.loadStrategy(userId);
      },
      error: (error) => {
        console.error('Error loading user:', error);
      }
    });
  }

  loadStrategy(userId: string): void {
    this.isLoadingStrategy = true;
    
    // Ensure subtypes are loaded before loading strategy
    if (this.investmentSubTypes.length === 0) {
      this.configurationService.getInvestmentSubTypes(undefined, true).subscribe({
        next: (subTypes) => {
          this.investmentSubTypes = subTypes.filter(s => s.is_active).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
          this.doLoadStrategy(userId);
        },
        error: (error) => {
          console.error('Error loading investment subtypes:', error);
          // Continue loading strategy even if subtypes fail to load
          this.doLoadStrategy(userId);
        }
      });
    } else {
      this.doLoadStrategy(userId);
    }
  }

  private doLoadStrategy(userId: string): void {
    this.allocationStrategyService.getAllocationStrategies(userId).subscribe({
      next: (strategies) => {
        if (strategies.length > 0) {
          this.strategy = strategies[0];
          this.initializeDraftAllocations();
        } else {
          this.strategy = null;
          this.draftTypeAllocations = [];
          this.totalPortfolioValueInput = null;
        }
        this.loadPieChartData(userId);
        this.loadCurrentAllocation(userId);
        this.loadRecommendations(userId);
        this.isLoadingStrategy = false;
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar estratégia de alocação';
        this.isLoadingStrategy = false;
        console.error('Error loading strategy:', error);
      }
    });
  }

  loadPieChartData(userId: string): void {
    this.allocationStrategyService.getPieChartData(userId).subscribe({
      next: (data) => {
        this.pieChartData = data;
      },
      error: (error) => {
        console.error('Error loading pie chart data:', error);
      }
    });
  }

  initializeDraftAllocations(): void {
    this.totalPortfolioValueInput = this.strategy?.total_portfolio_value || null;
    
    // Always load all active investment types to ensure we show all current types
    this.configurationService.getInvestmentTypes(true).subscribe({
      next: (allInvestmentTypes) => {
        // Create a map of existing allocations by investment_type_id for quick lookup
        const existingAllocationsMap = new Map<number, any>();
        if (this.strategy?.type_allocations) {
          this.strategy.type_allocations.forEach((typeAlloc) => {
            existingAllocationsMap.set(typeAlloc.investment_type.id, typeAlloc);
          });
        }

        // Merge existing allocations with all active investment types
        this.draftTypeAllocations = allInvestmentTypes.map((type, index) => {
          const existingAlloc = existingAllocationsMap.get(type.id);
          
          // Check if this is FII investment type
          const isFIIType = type.code === 'FIIS' || 
                           type.name.includes('Fundos Imobiliários') || 
                           type.name.includes('Fundo Imobiliário');
          
          // Handle FII allocations
          if (isFIIType && existingAlloc?.fii_allocations) {
            // Sort FIIs by display_order and assign to rows 0-4
            const sortedFIIs = [...existingAlloc.fii_allocations].sort((a: any, b: any) => 
              (a.display_order || 0) - (b.display_order || 0)
            );
            const fiiAllocations: DraftFIIAllocation[] = sortedFIIs.map((fii: any, idx: number) => ({
              id: fii.id,
              stock_id: fii.stock?.id || fii.stock_id,
              stock: fii.stock,
              target_percentage: fii.target_percentage,
              display_order: idx // Ensure display_order matches row index (0-4)
            }));
            
            return {
              ...existingAlloc,
              investment_type_id: type.id,
              investment_type: {
                id: type.id,
                name: type.name,
                code: type.code
              },
              target_percentage: existingAlloc.target_percentage ?? 0,
              display_order: existingAlloc.display_order ?? index,
              sub_type_allocations: [], // No subtypes for FIIs
              fii_allocations: fiiAllocations
            };
          }
          
          // Get available subtypes for this investment type
          const availableSubtypes = this.getSubTypesForInvestmentType(type.id);
          
          if (availableSubtypes.length > 0 && !isFIIType) {
            // Always show subtypes if they exist for this investment type
            const initializedSubtypes = availableSubtypes.map((subType, subIndex) => {
              // Check if this subtype was in the existing allocation
              const existingSubAlloc = existingAlloc?.sub_type_allocations?.find((sa: any) => sa.sub_type?.id === subType.id || sa.sub_type_id === subType.id);
              
              // Preserve stock_allocations for ETF Renda Fixa
              const stockAllocations = existingSubAlloc?.stock_allocations || [];
              
              return {
                ...existingSubAlloc,
                sub_type_id: subType.id,
                sub_type: {
                  id: subType.id,
                  name: subType.name,
                  code: subType.code
                },
                target_percentage: existingSubAlloc ? existingSubAlloc.target_percentage : 0,
                display_order: existingSubAlloc?.display_order ?? subIndex,
                stock_allocations: stockAllocations
              };
            });
            
            // Calculate target_percentage from subtypes if they exist
            const subtypeTotal = initializedSubtypes.reduce((sum, sub) => sum + Number(sub.target_percentage || 0), 0);
            const calculatedPercentage = subtypeTotal > 0 ? subtypeTotal : (existingAlloc?.target_percentage ?? 0);
            
            return {
              ...existingAlloc,
              investment_type_id: type.id,
              investment_type: {
                id: type.id,
                name: type.name,
                code: type.code
              },
              target_percentage: calculatedPercentage,
              display_order: existingAlloc?.display_order ?? index,
              sub_type_allocations: initializedSubtypes
            };
          } else {
            // No subtypes available - use existing allocation or create new
            return {
              ...existingAlloc,
              investment_type_id: type.id,
              investment_type: {
                id: type.id,
                name: type.name,
                code: type.code
              },
              target_percentage: existingAlloc?.target_percentage ?? 0,
              display_order: existingAlloc?.display_order ?? index,
              sub_type_allocations: existingAlloc?.sub_type_allocations || [],
              fii_allocations: isFIIType ? (existingAlloc?.fii_allocations || []) : undefined
            };
          }
        });
      },
      error: (error) => {
        console.error('Error loading investment types:', error);
        // Fallback to existing allocations if loading fails
        if (this.strategy?.type_allocations) {
          this.draftTypeAllocations = this.strategy.type_allocations.map((typeAlloc, index) => ({
            ...typeAlloc,
            investment_type_id: typeAlloc.investment_type.id,
            display_order: typeAlloc.display_order ?? index,
            sub_type_allocations: typeAlloc.sub_type_allocations?.map((subAlloc, subIndex) => ({
              ...subAlloc,
              sub_type_id: subAlloc.sub_type?.id,
              display_order: subAlloc.display_order ?? subIndex
            })) || []
          }));
        } else {
          this.draftTypeAllocations = [];
        }
      }
    });
  }

  get typeAllocationTotal(): number {
    return this.draftTypeAllocations.reduce((sum, alloc) => sum + Number(alloc.target_percentage || 0), 0);
  }

  get isTypeTotalValid(): boolean {
    return Math.abs(this.typeAllocationTotal - 100) < 0.01;
  }

  getSubTypeTotal(typeAlloc: DraftTypeAllocation): number {
    const total = (typeAlloc.sub_type_allocations || []).reduce(
      (sum, subAlloc) => sum + Number(subAlloc.target_percentage || 0),
      0
    );
    // Round to 1 decimal place to avoid floating-point precision issues (e.g., 40.099999 -> 40.1)
    return Math.round(total * 10) / 10;
  }

  isSubTypeTotalValid(typeAlloc: DraftTypeAllocation): boolean {
    if (!typeAlloc.sub_type_allocations || typeAlloc.sub_type_allocations.length === 0) {
      return true;
    }
    // Subtypes should sum to the same percentage as the parent type allocation
    const typePercentage = Number(typeAlloc.target_percentage || 0);
    const subTotal = this.getSubTypeTotal(typeAlloc);
    return Math.abs(subTotal - typePercentage) < 0.01;
  }

  onTypePercentageChange(index: number, value: string): void {
    const numericValue = Number(value);
    this.draftTypeAllocations[index].target_percentage = numericValue;
  }

  onFIITypePercentageChange(typeIndex: number, value: string): void {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    const numericValue = Number(value);
    const oldPercentage = Number(typeAlloc.target_percentage || 0);
    
    // Update the parent type percentage
    typeAlloc.target_percentage = numericValue;
    
    // If there are existing FII allocations, redistribute them proportionally
    if (typeAlloc.fii_allocations && typeAlloc.fii_allocations.length > 0) {
      if (oldPercentage > 0) {
        // Redistribute proportionally based on the ratio of new to old percentage
        const ratio = numericValue / oldPercentage;
        typeAlloc.fii_allocations.forEach(fii => {
          fii.target_percentage = Number(fii.target_percentage || 0) * ratio;
        });
      } else {
        // If old percentage was 0, distribute equally
        const equalPercentage = numericValue / typeAlloc.fii_allocations.length;
        typeAlloc.fii_allocations.forEach(fii => {
          fii.target_percentage = equalPercentage;
        });
      }
    }
  }

  onSubTypePercentageChange(typeIndex: number, subIndex: number, value: string, subTypeId: number): void {
    const numericValue = Number(value);
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    
    if (!typeAlloc.sub_type_allocations) {
      typeAlloc.sub_type_allocations = [];
    }
    
    // Find or create the subtype allocation
    let subAlloc = typeAlloc.sub_type_allocations.find(s => s.sub_type_id === subTypeId);
    
    if (!subAlloc) {
      const subType = this.investmentSubTypes.find(s => s.id === subTypeId);
      if (subType) {
        subAlloc = {
          sub_type_id: subTypeId,
          sub_type: {
            id: subType.id,
            name: subType.name,
            code: subType.code
          },
          target_percentage: 0,
          display_order: typeAlloc.sub_type_allocations.length
        };
        typeAlloc.sub_type_allocations.push(subAlloc);
      }
    }
    
    if (subAlloc) {
      subAlloc.target_percentage = numericValue;
      // Update the parent type percentage to match the exact sum of subtypes (without rounding)
      // This ensures consistency when saving
      const exactSubTotal = (typeAlloc.sub_type_allocations || []).reduce(
        (sum, sub) => sum + Number(sub.target_percentage || 0),
        0
      );
      typeAlloc.target_percentage = exactSubTotal;
    }
  }

  loadInvestmentSubTypes(): void {
    this.configurationService.getInvestmentSubTypes(undefined, true).subscribe({
      next: (subTypes) => {
        this.investmentSubTypes = subTypes.filter(s => s.is_active).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
        // Reload ETF Renda Fixa stocks now that we have subtype IDs
        this.loadETFRendaFixaStocks();
      },
      error: (error) => {
        console.error('Error loading investment subtypes:', error);
      }
    });
  }

  loadFIIs(): void {
    this.fiiService.getFIIProfiles().subscribe({
      next: (fiis) => {
        this.allFIIs = fiis.sort((a, b) => a.ticker.localeCompare(b.ticker));
      },
      error: (error) => {
        console.error('Error loading FIIs:', error);
      }
    });
  }

  loadETFRendaFixaStocks(): void {
    // Find ETF_RENDA_FIXA subtype ID
    const etfSubType = this.investmentSubTypes.find(s => s.code === 'ETF_RENDA_FIXA');
    const subtypeId = etfSubType?.id;
    
    if (!subtypeId) {
      console.warn('ETF_RENDA_FIXA subtype not found, loading all ETFs');
    }
    
    // Load stocks with stock_class=ETF and investment_subtype_id for ETF Renda Fixa
    // Note: API endpoint is /api/stocks/stocks/ (stocks router has stocks/ viewset)
    const url = subtypeId 
      ? `/api/stocks/stocks/?stock_class=ETF&investment_subtype_id=${subtypeId}&exclude_fiis=false&active_only=true`
      : '/api/stocks/stocks/?stock_class=ETF&exclude_fiis=false&active_only=true';
    
    console.log('Loading ETF Renda Fixa stocks from:', url);
    
    this.http.get<any[]>(url).subscribe({
      next: (stocks) => {
        console.log('Loaded ETF Renda Fixa stocks:', stocks);
        this.etfRendaFixaStocks = stocks.sort((a, b) => a.ticker.localeCompare(b.ticker));
      },
      error: (error) => {
        console.error('Error loading ETF Renda Fixa stocks:', error);
      }
    });
  }

  isETFRendaFixaSubType(subType: InvestmentSubType): boolean {
    return subType?.code === 'ETF_RENDA_FIXA';
  }

  getSelectedETFForSubType(typeIndex: number, subTypeId: number): any | null {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc?.sub_type_allocations) {
      return null;
    }
    const subAlloc = typeAlloc.sub_type_allocations.find(s => s.sub_type_id === subTypeId);
    // Check if there's a stock_allocation for this subtype
    if (subAlloc && (subAlloc as any).stock_allocations && (subAlloc as any).stock_allocations.length > 0) {
      const stockAlloc = (subAlloc as any).stock_allocations[0];
      // Handle both formats: stock_id (from local changes) or stock.id (from backend)
      return {
        ...stockAlloc,
        stock_id: stockAlloc.stock_id || stockAlloc.stock?.id
      };
    }
    return null;
  }

  getETFCurrentValue(typeIndex: number, subTypeId: number): number {
    // Get selected ETF stock for this subtype
    const selectedETF = this.getSelectedETFForSubType(typeIndex, subTypeId);
    if (!selectedETF?.stock_id) {
      return 0;
    }
    
    // Get the investment type id from the type allocation
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc) {
      return 0;
    }
    
    // Use the subtype's current value (ETF is the only stock in this subtype)
    return this.getCurrentSubTypeValue(typeAlloc.investment_type_id, subTypeId);
  }

  onETFSelectChange(typeIndex: number, subTypeId: number, stockId: string): void {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc?.sub_type_allocations) {
      return;
    }
    
    const numericStockId = stockId ? Number(stockId) : null;
    let subAlloc = typeAlloc.sub_type_allocations.find(s => s.sub_type_id === subTypeId);
    
    if (!subAlloc) {
      // Create subtype allocation if it doesn't exist
      const subType = this.investmentSubTypes.find(s => s.id === subTypeId);
      if (subType) {
        subAlloc = {
          sub_type_id: subTypeId,
          sub_type: {
            id: subType.id,
            name: subType.name,
            code: subType.code
          },
          target_percentage: 0,
          display_order: typeAlloc.sub_type_allocations.length
        };
        typeAlloc.sub_type_allocations.push(subAlloc);
      }
    }
    
    if (subAlloc) {
      // Initialize stock_allocations array if needed
      if (!(subAlloc as any).stock_allocations) {
        (subAlloc as any).stock_allocations = [];
      }
      
      if (numericStockId) {
        // Find the stock from etfRendaFixaStocks
        const stock = this.etfRendaFixaStocks.find(s => s.id === numericStockId);
        if (stock) {
          // Replace any existing stock allocation with the new one (max 1 ETF)
          (subAlloc as any).stock_allocations = [{
            stock_id: numericStockId,
            stock: {
              id: stock.id,
              ticker: stock.ticker,
              name: stock.name
            },
            target_percentage: subAlloc.target_percentage
          }];
        }
      } else {
        // Clear stock allocation
        (subAlloc as any).stock_allocations = [];
      }
    }
  }

  getSubTypesForInvestmentType(investmentTypeId: number): InvestmentSubType[] {
    return this.investmentSubTypes.filter(s => s.investment_type === investmentTypeId);
  }

  isFIIInvestmentType(typeAlloc: DraftTypeAllocation): boolean {
    const code = typeAlloc.investment_type?.code || '';
    const name = typeAlloc.investment_type?.name || '';
    return code === 'FIIS' || 
           name.includes('Fundos Imobiliários') || 
           name.includes('Fundo Imobiliário');
  }

  getAvailableFIIs(typeIndex: number): FIIProfile[] {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc) return [];
    
    const selectedStockIds = new Set(
      (typeAlloc.fii_allocations || []).map(fii => fii.stock_id || fii.stock?.id).filter(Boolean)
    );
    
    const searchTerm = (this.fiiSearchTerm[typeIndex] || '').toLowerCase();
    
    return this.allFIIs.filter(fii => {
      const matchesSearch = !searchTerm || 
        fii.ticker.toLowerCase().includes(searchTerm) ||
        (fii.segment && fii.segment.toLowerCase().includes(searchTerm)) ||
        (fii.administrator && fii.administrator.toLowerCase().includes(searchTerm));
      return !selectedStockIds.has(fii.stock_id) && matchesSearch;
    });
  }

  getSelectedFIIs(typeIndex: number): DraftFIIAllocation[] {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    return (typeAlloc.fii_allocations || []).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
  }

  getFIIAtRow(typeIndex: number, rowIndex: number): DraftFIIAllocation | undefined {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc.fii_allocations) {
      return undefined;
    }
    // Find FII with display_order matching rowIndex
    return typeAlloc.fii_allocations.find(fii => (fii.display_order || 0) === rowIndex);
  }

  getAvailableFIIsForRow(typeIndex: number, rowIndex: number): FIIProfile[] {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc) return [];
    
    // Get all selected FII stock IDs, excluding the one at current row (if any)
    const currentFII = this.getFIIAtRow(typeIndex, rowIndex);
    const selectedStockIds = new Set(
      (typeAlloc.fii_allocations || [])
        .filter(fii => {
          const stockId = fii.stock_id || fii.stock?.id;
          // Exclude current row's FII from the exclusion list
          return stockId && (!currentFII || stockId !== (currentFII.stock_id || currentFII.stock?.id));
        })
        .map(fii => fii.stock_id || fii.stock?.id)
        .filter(Boolean)
    );
    
    return this.allFIIs.filter(fii => !selectedStockIds.has(fii.stock_id));
  }

  canAddMoreFIIs(typeIndex: number): boolean {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    return (typeAlloc.fii_allocations || []).length < 5;
  }

  onAddFII(typeIndex: number, fii: FIIProfile): void {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc.fii_allocations) {
      typeAlloc.fii_allocations = [];
    }
    
    if (typeAlloc.fii_allocations.length >= 5) {
      alert('Máximo de 5 FIIs permitidos');
      return;
    }
    
    // Check if already selected
    if (typeAlloc.fii_allocations.some(f => (f.stock_id || f.stock?.id) === fii.stock_id)) {
      return;
    }
    
    const typePercentage = Number(typeAlloc.target_percentage || 0);
    const currentTotal = typeAlloc.fii_allocations.reduce((sum, f) => sum + Number(f.target_percentage || 0), 0);
    const remainingPercentage = typePercentage - currentTotal;
    const defaultPercentage = remainingPercentage > 0 ? remainingPercentage / (typeAlloc.fii_allocations.length + 1) : typePercentage / (typeAlloc.fii_allocations.length + 1);
    
    typeAlloc.fii_allocations.push({
      stock_id: fii.stock_id,
      stock: {
        id: fii.stock_id,
        ticker: fii.ticker,
        name: fii.ticker // Use ticker as name initially
      },
      target_percentage: defaultPercentage,
      display_order: typeAlloc.fii_allocations.length
    });
    
    // Redistribute percentages equally
    this.redistributeFIIPercentages(typeIndex);
    
    // Clear search
    this.fiiSearchTerm[typeIndex] = '';
  }

  onRemoveFII(typeIndex: number, fiiIndex: number): void {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (typeAlloc.fii_allocations) {
      typeAlloc.fii_allocations.splice(fiiIndex, 1);
      // Redistribute percentages
      this.redistributeFIIPercentages(typeIndex);
    }
  }

  redistributeFIIPercentages(typeIndex: number): void {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc.fii_allocations || typeAlloc.fii_allocations.length === 0) {
      return;
    }
    
    const typePercentage = Number(typeAlloc.target_percentage || 0);
    const equalPercentage = typePercentage / typeAlloc.fii_allocations.length;
    
    typeAlloc.fii_allocations.forEach(fii => {
      fii.target_percentage = equalPercentage;
    });
  }

  onFIIPercentageChange(typeIndex: number, rowIndex: number, value: string): void {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    const fii = this.getFIIAtRow(typeIndex, rowIndex);
    if (fii) {
      const numericValue = Number(value);
      fii.target_percentage = numericValue;
    }
  }

  onFIISelectChange(typeIndex: number, rowIndex: number, stockId: string): void {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc.fii_allocations) {
      typeAlloc.fii_allocations = [];
    }
    
    const numericStockId = stockId ? Number(stockId) : null;
    
    // Find existing FII at this row
    const existingFIIIndex = typeAlloc.fii_allocations.findIndex(
      fii => (fii.display_order || 0) === rowIndex
    );
    
    if (numericStockId) {
      // Find the FII profile
      const fiiProfile = this.allFIIs.find(f => f.stock_id === numericStockId);
      if (!fiiProfile) {
        return;
      }
      
      // Check if this FII is already selected in another row
      const alreadySelected = typeAlloc.fii_allocations.some(
        fii => (fii.stock_id || fii.stock?.id) === numericStockId && (fii.display_order || 0) !== rowIndex
      );
      
      if (alreadySelected) {
        alert('Este FII já está selecionado em outra linha');
        return;
      }
      
      if (existingFIIIndex >= 0) {
        // Update existing FII - keep the percentage, just change the FII
        const fii = typeAlloc.fii_allocations[existingFIIIndex];
        fii.stock_id = numericStockId;
        fii.stock = {
          id: numericStockId,
          ticker: fiiProfile.ticker,
          name: fiiProfile.ticker
        };
        // Don't redistribute - keep the existing percentage
      } else {
        // Add new FII at this row
        const typePercentage = Number(typeAlloc.target_percentage || 0);
        const currentTotal = typeAlloc.fii_allocations.reduce((sum, f) => sum + Number(f.target_percentage || 0), 0);
        const remainingPercentage = typePercentage - currentTotal;
        // Distribute remaining percentage equally among all FIIs (including the new one)
        const defaultPercentage = remainingPercentage > 0 ? remainingPercentage / (typeAlloc.fii_allocations.length + 1) : (typePercentage > 0 ? typePercentage / (typeAlloc.fii_allocations.length + 1) : 0);
        
        typeAlloc.fii_allocations.push({
          stock_id: numericStockId,
          stock: {
            id: numericStockId,
            ticker: fiiProfile.ticker,
            name: fiiProfile.ticker
          },
          target_percentage: defaultPercentage,
          display_order: rowIndex
        });
        
        // Redistribute percentages equally only when adding a new FII
        this.redistributeFIIPercentages(typeIndex);
      }
    } else {
      // Remove FII from this row
      if (existingFIIIndex >= 0) {
        typeAlloc.fii_allocations.splice(existingFIIIndex, 1);
        // Redistribute percentages
        this.redistributeFIIPercentages(typeIndex);
      }
    }
  }

  onRemoveFIIAtRow(typeIndex: number, rowIndex: number): void {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc.fii_allocations) {
      return;
    }
    
    const existingFIIIndex = typeAlloc.fii_allocations.findIndex(
      fii => (fii.display_order || 0) === rowIndex
    );
    
    if (existingFIIIndex >= 0) {
      typeAlloc.fii_allocations.splice(existingFIIIndex, 1);
      // Don't auto-redistribute - let user manually adjust percentages
    }
  }

  getFIITotal(typeAlloc: DraftTypeAllocation): number {
    const total = (typeAlloc.fii_allocations || []).reduce(
      (sum, fii) => sum + Number(fii.target_percentage || 0),
      0
    );
    return Math.round(total * 10) / 10;
  }

  isFIITotalValid(typeAlloc: DraftTypeAllocation): boolean {
    if (!typeAlloc.fii_allocations || typeAlloc.fii_allocations.length === 0) {
      return true;
    }
    const typePercentage = Number(typeAlloc.target_percentage || 0);
    const fiiTotal = this.getFIITotal(typeAlloc);
    return Math.abs(fiiTotal - typePercentage) < 0.01;
  }

  getCurrentFIIValue(typeId: number, ticker: string): number {
    if (!this.currentAllocation?.current?.investment_types) {
      return 0;
    }
    const typeData = this.currentAllocation.current.investment_types.find(
      (type: any) => type.investment_type_id === typeId
    );
    if (!typeData?.sub_types) {
      return 0;
    }
    const fiiData = typeData.sub_types.find(
      (st: any) => st.ticker === ticker
    );
    return fiiData ? Number(fiiData.current_value || 0) : 0;
  }

  getTargetFIIValue(typeAlloc: DraftTypeAllocation, fii: DraftFIIAllocation): number {
    const totalValue = this.getTotalPortfolioValue();
    const percentage = Number(fii.target_percentage || 0);
    return totalValue * (percentage / 100);
  }

  getFIIName(fii: DraftFIIAllocation): string {
    if (fii.stock?.name) {
      return fii.stock.name;
    }
    const stockId = fii.stock_id || fii.stock?.id;
    if (stockId) {
      const fiiProfile = this.allFIIs.find(f => f.stock_id === stockId);
      return fiiProfile?.ticker || fii.stock?.ticker || '-';
    }
    return fii.stock?.ticker || '-';
  }

  getFIIAdministrator(fii: DraftFIIAllocation): string {
    const stockId = fii.stock_id || fii.stock?.id;
    if (stockId) {
      const fiiProfile = this.allFIIs.find(f => f.stock_id === stockId);
      return fiiProfile?.administrator || '-';
    }
    return '-';
  }

  getFIITicker(fii: DraftFIIAllocation): string {
    return fii.stock?.ticker || '';
  }

  getSubTypeAllocation(typeIndex: number, subTypeId: number): DraftSubTypeAllocation | undefined {
    const typeAlloc = this.draftTypeAllocations[typeIndex];
    if (!typeAlloc?.sub_type_allocations) {
      return undefined;
    }
    return typeAlloc.sub_type_allocations.find(s => s.sub_type_id === subTypeId);
  }


  onConfigureStrategy(): void {
    if (!this.selectedUser) {
      return;
    }
    
    // If strategy doesn't exist, create a new one with investment types
    if (!this.strategy) {
      this.createNewStrategy();
    } else {
      // Reload strategy to ensure we have the latest data
      this.loadStrategy(this.selectedUser.id);
    }
  }

  createNewStrategy(): void {
    if (!this.selectedUser) {
      return;
    }

    this.isLoadingStrategy = true;
    this.errorMessage = null;

    // Load investment types to initialize the draft
    this.configurationService.getInvestmentTypes(true).subscribe({
      next: (investmentTypes) => {
        // Initialize draft allocations with all active investment types
        this.draftTypeAllocations = investmentTypes.map((type, index) => {
          const isFIIType = type.code === 'FIIS' || 
                           type.name.includes('Fundos Imobiliários') || 
                           type.name.includes('Fundo Imobiliário');
          return {
            investment_type_id: type.id,
            investment_type: {
              id: type.id,
              name: type.name,
              code: type.code
            },
            target_percentage: 0,
            display_order: index,
            sub_type_allocations: isFIIType ? [] : [],
            fii_allocations: isFIIType ? [] : undefined
          };
        });

        // Initialize total portfolio value if available from pie chart data
        this.totalPortfolioValueInput = null;
        
        this.isLoadingStrategy = false;
      },
      error: (error) => {
        console.error('Error loading investment types:', error);
        this.errorMessage = 'Erro ao carregar tipos de investimento';
        this.isLoadingStrategy = false;
      }
    });
  }

  onSaveStrategy(): void {
    if (!this.selectedUser || !this.isTypeTotalValid) {
      return;
    }

    // Step 1: Adjust parent type percentages to match FII/subtype sums
    for (const typeAlloc of this.draftTypeAllocations) {
      const isFIIType = this.isFIIInvestmentType(typeAlloc);
      
      if (isFIIType) {
        // Validate FII allocations
        if (typeAlloc.fii_allocations && typeAlloc.fii_allocations.length > 0) {
          if (typeAlloc.fii_allocations.length > 5) {
            alert(`Máximo de 5 FIIs permitidos para "${typeAlloc.investment_type.name}"`);
            return;
          }
          
          const exactFIITotal = (typeAlloc.fii_allocations || []).reduce(
            (sum, fii) => sum + Number(fii.target_percentage || 0),
            0
          );
          
          // Validate that FIIs sum matches parent (with tolerance for floating point)
          // Don't auto-calculate parent - it should be manually set
          const parentPercentage = Number(typeAlloc.target_percentage || 0);
          if (Math.abs(exactFIITotal - parentPercentage) >= 0.01) {
            alert(`As alocações de FIIs de "${typeAlloc.investment_type.name}" precisam somar ${parentPercentage.toFixed(2)}% (mesmo valor do tipo). Atual: ${exactFIITotal.toFixed(2)}%`);
            return;
          }
        }
      } else if (typeAlloc.sub_type_allocations && typeAlloc.sub_type_allocations.length > 0) {
        // Calculate exact sum of subtypes (without rounding)
        const exactSubTotal = (typeAlloc.sub_type_allocations || []).reduce(
          (sum, subAlloc) => sum + Number(subAlloc.target_percentage || 0),
          0
        );
        
        // Ensure parent type percentage matches exact sum of subtypes
        // This prevents rounding issues when saving
        typeAlloc.target_percentage = exactSubTotal;
        
        // Validate that subtypes sum matches parent (with tolerance for floating point)
        if (Math.abs(exactSubTotal - Number(typeAlloc.target_percentage || 0)) >= 0.01) {
          alert(`Os subtipos de "${typeAlloc.investment_type.name}" precisam somar ${typeAlloc.target_percentage.toFixed(2)}% (mesmo valor do tipo)`);
          return;
        }
      }
    }

    // Step 2: Normalize type allocations to sum to exactly 100%
    // This ensures that after adjusting parent types to match FII/subtype sums,
    // the total still sums to 100%
    // We only adjust types that don't have FII/subtype constraints to preserve those relationships
    const currentTotal = this.draftTypeAllocations.reduce(
      (sum, alloc) => sum + Number(alloc.target_percentage || 0),
      0
    );
    
    if (Math.abs(currentTotal - 100) >= 0.01 && currentTotal > 0) {
      // Identify types with FII/subtype constraints (these should not be adjusted)
      const constrainedTypes = new Set<number>();
      for (const typeAlloc of this.draftTypeAllocations) {
        const isFIIType = this.isFIIInvestmentType(typeAlloc);
        const hasFIIs = isFIIType && typeAlloc.fii_allocations && typeAlloc.fii_allocations.length > 0;
        const hasSubtypes = !isFIIType && typeAlloc.sub_type_allocations && typeAlloc.sub_type_allocations.length > 0;
        
        if (hasFIIs || hasSubtypes) {
          constrainedTypes.add(typeAlloc.investment_type_id);
        }
      }
      
      // Calculate the sum of constrained types (these won't be adjusted)
      const constrainedTotal = this.draftTypeAllocations
        .filter(alloc => constrainedTypes.has(alloc.investment_type_id))
        .reduce((sum, alloc) => sum + Number(alloc.target_percentage || 0), 0);
      
      // Calculate the sum of unconstrained types
      const unconstrainedTotal = currentTotal - constrainedTotal;
      
      // If we have unconstrained types, adjust them to compensate for the difference
      if (unconstrainedTotal > 0) {
        const targetUnconstrainedTotal = 100 - constrainedTotal;
        const normalizationFactor = targetUnconstrainedTotal / unconstrainedTotal;
        
        for (const typeAlloc of this.draftTypeAllocations) {
          if (!constrainedTypes.has(typeAlloc.investment_type_id)) {
            typeAlloc.target_percentage = Number(typeAlloc.target_percentage || 0) * normalizationFactor;
          }
        }
      } else {
        // All types are constrained - normalize all proportionally
        // This is a fallback case that shouldn't normally happen
        const normalizationFactor = 100 / currentTotal;
        for (const typeAlloc of this.draftTypeAllocations) {
          typeAlloc.target_percentage = Number(typeAlloc.target_percentage || 0) * normalizationFactor;
        }
      }
    }

    const payload = this.draftTypeAllocations.map((typeAlloc, index) => {
      const isFIIType = this.isFIIInvestmentType(typeAlloc);
      
      if (isFIIType) {
        // Handle FII allocations
        // Use the parent type percentage (manually set), not the FII total
        return {
          investment_type_id: typeAlloc.investment_type_id,
          target_percentage: Number(typeAlloc.target_percentage),
          display_order: index,
          sub_type_allocations: [], // No subtypes for FIIs
          fii_allocations: (typeAlloc.fii_allocations || []).map((fii, fiiIndex) => ({
            stock_id: fii.stock_id || fii.stock?.id,
            target_percentage: Number(fii.target_percentage),
            display_order: fiiIndex
          }))
        };
      } else {
        // Handle subtype allocations (normal behavior)
        const exactSubTotal = (typeAlloc.sub_type_allocations || []).reduce(
          (sum, subAlloc) => sum + Number(subAlloc.target_percentage || 0),
          0
        );
        
        // Use exact sum if subtypes exist, otherwise use the type allocation percentage
        const finalTargetPercentage = (typeAlloc.sub_type_allocations && typeAlloc.sub_type_allocations.length > 0)
          ? exactSubTotal
          : Number(typeAlloc.target_percentage);
        
        return {
          investment_type_id: typeAlloc.investment_type_id,
          target_percentage: finalTargetPercentage,
          display_order: index,
          sub_type_allocations: (typeAlloc.sub_type_allocations || []).map((subAlloc, subIndex) => {
            const subType = this.investmentSubTypes.find(s => s.id === subAlloc.sub_type_id);
            const isETFRendaFixa = subType?.code === 'ETF_RENDA_FIXA';
            
            const baseAlloc: any = {
              sub_type_id: subAlloc.sub_type_id,
              custom_name: subAlloc.custom_name,
              target_percentage: Number(subAlloc.target_percentage),
              display_order: subIndex
            };
            
            // Include stock_allocations for ETF Renda Fixa subtype
            if (isETFRendaFixa && (subAlloc as any).stock_allocations) {
              baseAlloc.stock_allocations = ((subAlloc as any).stock_allocations || []).map((stockAlloc: any) => ({
                stock_id: stockAlloc.stock_id || stockAlloc.stock?.id,
                target_percentage: Number(subAlloc.target_percentage) // Use subtype percentage
              }));
            }
            
            return baseAlloc;
          })
        };
      }
    });

    this.isSaving = true;
    this.allocationStrategyService
      .createOrUpdateStrategy(
        this.selectedUser.id,
        payload,
        this.totalPortfolioValueInput !== null ? Number(this.totalPortfolioValueInput) : undefined
      )
      .subscribe({
        next: (updatedStrategy) => {
          this.strategy = updatedStrategy;
          this.initializeDraftAllocations();
          this.isSaving = false;
          this.errorMessage = null;
        },
        error: (error) => {
          console.error('Error saving strategy:', error);
          this.errorMessage = error.error?.error || 'Erro ao salvar estratégia';
          this.isSaving = false;
        }
      });
  }

  // Rebalancing methods
  loadCurrentAllocation(userId: string): void {
    this.allocationStrategyService.getCurrentVsTarget(userId).subscribe({
      next: (data) => {
        this.currentAllocation = data;
      },
      error: (error) => {
        console.error('Error loading current allocation:', error);
      }
    });
  }

  loadRecommendations(userId: string): void {
    if (this.activeTab !== 'rebalancing') {
      return;
    }
    
    this.isLoadingRecommendations = true;
    this.rebalancingService.getRecommendations(userId, 'pending').subscribe({
      next: (recommendations) => {
        this.recommendations = recommendations;
        if (recommendations.length > 0) {
          this.currentRecommendation = recommendations[0];
        } else {
          this.currentRecommendation = null;
        }
        this.isLoadingRecommendations = false;
      },
      error: (error) => {
        console.error('Error loading recommendations:', error);
        this.isLoadingRecommendations = false;
      }
    });
  }

  generateRecommendations(): void {
    if (!this.selectedUser) {
      return;
    }

    this.isGeneratingRecommendations = true;
    this.errorMessage = null;
    
    this.rebalancingService.generateRecommendations(this.selectedUser.id).subscribe({
      next: (recommendation) => {
        this.currentRecommendation = recommendation;
        this.loadRecommendations(this.selectedUser!.id);
        this.loadCurrentAllocation(this.selectedUser!.id);
        this.isGeneratingRecommendations = false;
      },
      error: (error) => {
        console.error('Error generating recommendations:', error);
        this.errorMessage = error.error?.error || 'Erro ao gerar recomendações de rebalanceamento';
        this.isGeneratingRecommendations = false;
      }
    });
  }

  async exportRecommendationExcel(): Promise<void> {
    // Just export Excel without applying the recommendation
    await this.generateOrderRequestExcel();
  }

  async applyRecommendation(recommendationId: number): Promise<void> {
    // Generate Excel file with buy and sell orders before applying
    await this.generateOrderRequestExcel();
    
    this.rebalancingService.applyRecommendation(recommendationId).subscribe({
      next: () => {
        if (this.selectedUser) {
          this.loadRecommendations(this.selectedUser.id);
        }
      },
      error: (error) => {
        console.error('Error applying recommendation:', error);
        this.errorMessage = 'Erro ao aplicar recomendação';
      }
    });
  }

  async generateOrderRequestExcel(): Promise<void> {
    if (!this.currentRecommendation || !this.selectedUser) {
      console.error('Cannot generate Excel: missing recommendation or user');
      return;
    }

    try {
      // Get current date for filename
      const now = new Date();
      const monthNames = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
                         'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
      const month = monthNames[now.getMonth()];
      const year = now.getFullYear();
      
      // Get user identifier and account number
      const userIdentifier = this.selectedUser.name || 'USER';
      const accountNumber = this.selectedUser.account_number || '';
      
      // Prepare single array for all orders (matching Sophia's format)
      const allOrders: any[] = [];

      // Process sell actions (complete sales) - Ações em Reais
      const sellActions = this.getAcoesReaisSellActions();
      sellActions.forEach((action) => {
        if (action.stock && action.quantity_to_sell) {
          allOrders.push({
            'TICKER': action.stock.ticker,
            'C/V': 'V',
            'QTDE': -Math.abs(action.quantity_to_sell), // Negative for sells
            'VOLUME R$': '', // Empty as per example
            'CONTA': accountNumber,
            'PREÇO': 'MERCADO'
          });
        }
      });

      // Process buy actions - Ações em Reais
      const buyActions = this.getAcoesReaisBuyActions();
      buyActions.forEach((action) => {
        if (action.stock && action.quantity_to_buy) {
          allOrders.push({
            'TICKER': action.stock.ticker,
            'C/V': 'C',
            'QTDE': Math.abs(action.quantity_to_buy), // Positive for buys
            'VOLUME R$': '', // Empty as per example
            'CONTA': accountNumber,
            'PREÇO': 'MERCADO'
          });
        }
      });

      // Process rebalance actions (partial sales and buys) - Ações em Reais
      const rebalanceActions = this.getAcoesReaisRebalanceActions();
      rebalanceActions.forEach((action) => {
        if (action.stock) {
          if (action.quantity_to_sell && action.quantity_to_sell > 0) {
            allOrders.push({
              'TICKER': action.stock.ticker,
              'C/V': 'V',
              'QTDE': -Math.abs(action.quantity_to_sell), // Negative for sells
              'VOLUME R$': '', // Empty as per example
              'CONTA': accountNumber,
              'PREÇO': 'MERCADO'
            });
          }
          if (action.quantity_to_buy && action.quantity_to_buy > 0) {
            allOrders.push({
              'TICKER': action.stock.ticker,
              'C/V': 'C',
              'QTDE': Math.abs(action.quantity_to_buy), // Positive for buys
              'VOLUME R$': '', // Empty as per example
              'CONTA': accountNumber,
              'PREÇO': 'MERCADO'
            });
          }
        }
      });

      // Process FII sell actions
      const fiiSellActions = this.getFIISellActions();
      fiiSellActions.forEach((action) => {
        if (action.stock && action.quantity_to_sell) {
          allOrders.push({
            'TICKER': action.stock.ticker,
            'C/V': 'V',
            'QTDE': -Math.abs(action.quantity_to_sell),
            'VOLUME R$': '',
            'CONTA': accountNumber,
            'PREÇO': 'MERCADO'
          });
        }
      });

      // Process FII buy actions
      const fiiBuyActions = this.getFIIBuyActions();
      fiiBuyActions.forEach((action) => {
        if (action.stock && action.quantity_to_buy) {
          allOrders.push({
            'TICKER': action.stock.ticker,
            'C/V': 'C',
            'QTDE': Math.abs(action.quantity_to_buy),
            'VOLUME R$': '',
            'CONTA': accountNumber,
            'PREÇO': 'MERCADO'
          });
        }
      });

      // Process FII rebalance actions
      const fiiRebalanceActions = this.getFIIRebalanceActions();
      fiiRebalanceActions.forEach((action) => {
        if (action.stock) {
          if (action.quantity_to_sell && action.quantity_to_sell > 0) {
            allOrders.push({
              'TICKER': action.stock.ticker,
              'C/V': 'V',
              'QTDE': -Math.abs(action.quantity_to_sell),
              'VOLUME R$': '',
              'CONTA': accountNumber,
              'PREÇO': 'MERCADO'
            });
          }
          if (action.quantity_to_buy && action.quantity_to_buy > 0) {
            allOrders.push({
              'TICKER': action.stock.ticker,
              'C/V': 'C',
              'QTDE': Math.abs(action.quantity_to_buy),
              'VOLUME R$': '',
              'CONTA': accountNumber,
              'PREÇO': 'MERCADO'
            });
          }
        }
      });

      // Process dollar assets actions (including BERK34)
      const dolaresActions = this.getAcoesDolaresActions();
      dolaresActions.forEach((action) => {
        if (action.stock) {
          // Process sell actions
          if (action.action_type === 'sell' && action.quantity_to_sell) {
            allOrders.push({
              'TICKER': action.stock.ticker,
              'C/V': 'V',
              'QTDE': -Math.abs(action.quantity_to_sell), // Negative for sells
              'VOLUME R$': '', // Empty as per example
              'CONTA': accountNumber,
              'PREÇO': 'MERCADO'
            });
          }
          // Process buy actions
          if (action.action_type === 'buy' && action.quantity_to_buy) {
            allOrders.push({
              'TICKER': action.stock.ticker,
              'C/V': 'C',
              'QTDE': Math.abs(action.quantity_to_buy), // Positive for buys
              'VOLUME R$': '', // Empty as per example
              'CONTA': accountNumber,
              'PREÇO': 'MERCADO'
            });
          }
          // Process rebalance actions
          if (action.action_type === 'rebalance') {
            if (action.quantity_to_sell && action.quantity_to_sell > 0) {
              allOrders.push({
                'TICKER': action.stock.ticker,
                'C/V': 'V',
                'QTDE': -Math.abs(action.quantity_to_sell), // Negative for sells
                'VOLUME R$': '', // Empty as per example
                'CONTA': accountNumber,
                'PREÇO': 'MERCADO'
              });
            }
            if (action.quantity_to_buy && action.quantity_to_buy > 0) {
              allOrders.push({
                'TICKER': action.stock.ticker,
                'C/V': 'C',
                'QTDE': Math.abs(action.quantity_to_buy), // Positive for buys
                'VOLUME R$': '', // Empty as per example
                'CONTA': accountNumber,
                'PREÇO': 'MERCADO'
              });
            }
          }
        }
      });

      // Process ETF Renda Fixa actions
      const etfRendaFixaActions = this.getETFRendaFixaActions();
      console.log('ETF Renda Fixa actions for Excel export:', etfRendaFixaActions);
      etfRendaFixaActions.forEach((action) => {
        if (action.stock) {
          // Process any action with quantity_to_sell
          if (action.quantity_to_sell && action.quantity_to_sell > 0) {
            allOrders.push({
              'TICKER': action.stock.ticker,
              'C/V': 'V',
              'QTDE': -Math.abs(action.quantity_to_sell),
              'VOLUME R$': '',
              'CONTA': accountNumber,
              'PREÇO': 'MERCADO'
            });
          }
          // Process any action with quantity_to_buy
          if (action.quantity_to_buy && action.quantity_to_buy > 0) {
            allOrders.push({
              'TICKER': action.stock.ticker,
              'C/V': 'C',
              'QTDE': Math.abs(action.quantity_to_buy),
              'VOLUME R$': '',
              'CONTA': accountNumber,
              'PREÇO': 'MERCADO'
            });
          }
        }
      });

      // Create workbook with single sheet
      const workbook = XLSX.utils.book_new();

      // Add single sheet with all orders
      if (allOrders.length > 0) {
        const ws = XLSX.utils.json_to_sheet(allOrders);
        XLSX.utils.book_append_sheet(workbook, ws, 'COMPRA - VENDA (SIMPLES)');
      }

      // Generate filename: USERNAME ACCOUNTNUMBER - MONTH - YEAR.xlsx
      const filename = accountNumber 
        ? `${userIdentifier} ${accountNumber} - ${month} - ${year}.xlsx`
        : `${userIdentifier} - ${month} - ${year}.xlsx`;

      // Convert workbook to binary string
      const wbout = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
      const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

      // Use download approach (triggers browser's native save dialog)
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      console.log(`Excel file downloaded: ${filename}`);
    } catch (error) {
      console.error('Error generating Excel file:', error);
      this.errorMessage = 'Erro ao gerar arquivo Excel';
    }
  }

  dismissRecommendation(recommendationId: number): void {
    this.rebalancingService.dismissRecommendation(recommendationId).subscribe({
      next: () => {
        if (this.selectedUser) {
          this.loadRecommendations(this.selectedUser.id);
        }
      },
      error: (error) => {
        console.error('Error dismissing recommendation:', error);
        this.errorMessage = 'Erro ao descartar recomendação';
      }
    });
  }

  onTabChange(tab: 'configuration' | 'rebalancing'): void {
    this.activeTab = tab;
    if (this.selectedUser) {
      // Always reload current allocation when switching tabs to ensure data is up-to-date
      this.loadCurrentAllocation(this.selectedUser.id);
      if (tab === 'rebalancing') {
        this.loadRecommendations(this.selectedUser.id);
      }
    }
  }

  getActionsByType(type: 'buy' | 'sell' | 'rebalance'): RebalancingAction[] {
    if (!this.currentRecommendation) {
      return [];
    }
    // Filter by action type and ensure stock exists (for stock-specific actions)
    return this.currentRecommendation.actions.filter(action => 
      action.action_type === type && action.stock !== null && action.stock !== undefined
    );
  }

  getAcoesReaisActions(): RebalancingAction[] {
    if (!this.currentRecommendation) {
      return [];
    }
    
    // Filter actions for "Ações em Reais" stocks (actions with stock ticker, excluding BERK34, FIIs, and crypto ETFs)
    return this.currentRecommendation.actions.filter(action => {
      if (!action.stock) {
        return false;
      }
      
      // Exclude BERK34 (BDR, belongs to "Renda Variável em Dólares")
      if (action.stock.ticker === 'BERK34') {
        return false;
      }
      
      // Exclude stocks from "Renda Variável em Dólares" investment type (includes BDRs, crypto ETFs, etc.)
      if (action.stock.investment_type?.code === 'RENDA_VARIAVEL_DOLARES') {
        return false;
      }
      
      // Exclude FIIs: check if investment_type code is 'FIIS' or if stock_class is 'FII'
      if (action.stock.investment_type?.code === 'FIIS' || (action.stock as any).stock_class === 'FII') {
        return false;
      }
      
      // Exclude ETF Renda Fixa stocks (they have their own section under Renda Fixa)
      const subtypeCode = action.stock.investment_subtype?.code || '';
      const stockClass = (action.stock as any).stock_class || '';
      if (subtypeCode === 'ETF_RENDA_FIXA' || (stockClass === 'ETF' && action.stock.investment_type?.code === 'RENDA_FIXA')) {
        return false;
      }
      
      // Check if stock has crypto-related subtype (crypto ETFs like HASH11, BITH11)
      const subtypeName = action.stock.investment_subtype?.name || '';
      const subtypeNameLower = subtypeName.toLowerCase();
      if (subtypeNameLower.includes('bitcoin') || 
          subtypeNameLower.includes('crypto') || 
          subtypeNameLower.includes('cripto') ||
          subtypeNameLower.includes('cripto moéda')) {
        return false;
      }
      
      // Only include buy, sell, or rebalance actions
      return action.action_type === 'buy' || action.action_type === 'sell' || action.action_type === 'rebalance';
    });
  }

  getAcoesReaisSellActions(): RebalancingAction[] {
    return this.getAcoesReaisActions().filter(a => a.action_type === 'sell');
  }

  getAcoesReaisBuyActions(): RebalancingAction[] {
    const allActions = this.getAcoesReaisActions();
    const buyActions = allActions.filter(a => a.action_type === 'buy');
    
    // Debug: log to see what we have
    if (buyActions.length > 0) {
      console.log('Buy actions found:', buyActions.map(a => ({
        ticker: a.stock?.ticker,
        ranking: a.display_order,
        action_type: a.action_type
      })));
    }
    
    // Sort by ranking (display_order) - lower is better
    return buyActions.sort((a, b) => (a.display_order || 999) - (b.display_order || 999));
  }

  getAcoesReaisRebalanceActions(): RebalancingAction[] {
    const actions = this.getAcoesReaisActions().filter(a => a.action_type === 'rebalance');
    // Sort by ranking (display_order) first - lower is better
    return actions.sort((a, b) => {
      const orderA = a.display_order || 999;
      const orderB = b.display_order || 999;
      if (orderA !== orderB) {
        return orderA - orderB; // Sort by ranking first
      }
      // If same ranking, sort by ticker for consistency
      return (a.stock?.ticker || '').localeCompare(b.stock?.ticker || '');
    });
  }

  getFIIActions(): RebalancingAction[] {
    if (!this.currentRecommendation) {
      return [];
    }
    // Filter actions where stock.stock_class === 'FII' or investment_type.code === 'FIIS'
    return this.currentRecommendation.actions.filter(action => 
      action.stock && 
      (action.stock.stock_class === 'FII' || action.stock.investment_type?.code === 'FIIS')
    );
  }

  getFIISellActions(): RebalancingAction[] {
    return this.getFIIActions().filter(a => a.action_type === 'sell');
  }

  getFIIBuyActions(): RebalancingAction[] {
    const allActions = this.getFIIActions().filter(a => a.action_type === 'buy');
    // Sort by display_order
    return allActions.sort((a, b) => (a.display_order || 999) - (b.display_order || 999));
  }

  getFIIRebalanceActions(): RebalancingAction[] {
    const actions = this.getFIIActions().filter(a => a.action_type === 'rebalance');
    // Sort by display_order
    return actions.sort((a, b) => (a.display_order || 999) - (b.display_order || 999));
  }

  getTotalAcoesReaisValueAfterRebalancing(): number {
    try {
      if (!this.currentRecommendation) {
        return 0;
      }
      
      if (!this.currentRecommendation.actions || this.currentRecommendation.actions.length === 0) {
        return 0;
      }
      
      // Calculate total value after rebalancing:
      // 1. Sum target_value from rebalance actions (stocks that remain after rebalancing)
      // 2. Add target_value from buy actions (new stocks to buy)
      // Note: Sell actions are excluded from the portfolio, so we don't count them
      // IMPORTANT: This should ONLY include "Ações em Reais" stocks, NOT FIIs
      
      const rebalanceActions = this.getAcoesReaisRebalanceActions();
      const buyActions = this.getAcoesReaisBuyActions();
      
      // Additional safety check: explicitly exclude FIIs from the calculation
      const rebalanceTotal = rebalanceActions
        .filter(action => {
          // Double-check: exclude FIIs explicitly
          if (!action.stock) return false;
          if (action.stock.investment_type?.code === 'FIIS') return false;
          if ((action.stock as any).stock_class === 'FII') return false;
          return true;
        })
        .reduce((sum, action) => {
          const targetValue = action.target_value ? Number(action.target_value) : 0;
          if (isNaN(targetValue)) {
            console.warn('Invalid target_value for action:', action);
            return sum;
          }
          return sum + targetValue;
        }, 0);
      
      const buyTotal = buyActions
        .filter(action => {
          // Double-check: exclude FIIs explicitly
          if (!action.stock) return false;
          if (action.stock.investment_type?.code === 'FIIS') return false;
          if ((action.stock as any).stock_class === 'FII') return false;
          return true;
        })
        .reduce((sum, action) => {
          const targetValue = action.target_value ? Number(action.target_value) : 0;
          if (isNaN(targetValue)) {
            console.warn('Invalid target_value for action:', action);
            return sum;
          }
          return sum + targetValue;
        }, 0);
      
      const total = rebalanceTotal + buyTotal;
      
      // Ensure we return a valid number
      return isNaN(total) ? 0 : total;
    } catch (error) {
      console.error('Error calculating total value after rebalancing:', error);
      return 0;
    }
  }

  getAvailableSalesLimitBeforeRecommendation(): number {
    // Calculate the available sales limit BEFORE applying the current recommendation
    // This is: Monthly limit (19,000) - Previous sales this month
    if (!this.currentRecommendation) {
      return 19000;
    }
    
    const monthlyLimit = 19000;
    const previousSales = this.currentRecommendation.previous_sales_this_month || 0;
    const availableLimit = monthlyLimit - previousSales;
    
    // Ensure we return a valid number (not negative)
    return Math.max(0, availableLimit);
  }

  getAcoesDolaresActions(): RebalancingAction[] {
    if (!this.currentRecommendation || !this.strategy) {
      return [];
    }
    
    // Find "Renda Variável em Dólares" investment type from strategy
    const rendaVarDolaresTypeAlloc = this.strategy.type_allocations?.find(
      typeAlloc => typeAlloc.investment_type?.code === 'RENDA_VARIAVEL_DOLARES' || 
                   typeAlloc.investment_type?.name?.toLowerCase().includes('renda variável em dólares')
    );
    
    if (!rendaVarDolaresTypeAlloc) {
      // Fallback: filter by BERK34 ticker (old behavior)
      return this.currentRecommendation.actions.filter(action => 
        action.stock && action.stock.ticker === 'BERK34'
      );
    }
    
    // Filter actions for "Renda Variável em Dólares" type
    // This includes both stock actions (BERK34) and subtype actions (BDRs, Bitcoin, etc.)
    return this.currentRecommendation.actions.filter(action => 
      (action.stock && 
       action.stock.investment_type?.code === 'RENDA_VARIAVEL_DOLARES') ||
      (action.investment_subtype && 
       rendaVarDolaresTypeAlloc.sub_type_allocations?.some(
         subAlloc => subAlloc.sub_type?.id === action.investment_subtype?.id
       )) ||
      (!action.stock && !action.investment_subtype && 
       action.display_order === rendaVarDolaresTypeAlloc.display_order)
    );
  }

  getRendaVarDolaresTypeActions(): RebalancingAction[] {
    // Get type-level actions (no stock, no subtype) - these represent the total type allocation
    const actions = this.getAcoesDolaresActions();
    return actions.filter(action => !action.stock && !action.investment_subtype);
  }

  getAcoesDolaresSubtypeActions(): RebalancingAction[] {
    const actions = this.getAcoesDolaresActions();
    // Get "Ações em Dólares" actions: stocks that are not BDRs and not crypto
    return actions.filter(action => {
      // Must have a stock
      if (!action.stock) {
        return false;
      }
      // Exclude BDRs
      const subtypeName = action.stock.investment_subtype?.name || '';
      if (subtypeName.toLowerCase().includes('bdr')) {
        return false;
      }
      // Exclude crypto-related stocks
      if (subtypeName.toLowerCase().includes('bitcoin') || 
          subtypeName.toLowerCase().includes('crypto') || 
          subtypeName.toLowerCase().includes('cripto')) {
        return false;
      }
      return true;
    }).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
  }

  getBDRsSubtypeActions(): RebalancingAction[] {
    const actions = this.getAcoesDolaresActions();
    // Get BDRs actions: stocks with investment_subtype = BDRs
    return actions.filter(action => {
      // Must have a stock (individual stock recommendations like BERK34)
      if (!action.stock) {
        return false;
      }
      // Check if stock's investment_subtype is BDRs
      const subtypeName = action.stock.investment_subtype?.name || '';
      return subtypeName.toLowerCase().includes('bdr');
    }).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
  }

  getCryptoSubtypeActions(): RebalancingAction[] {
    const actions = this.getAcoesDolaresActions();
    // Get Crypto actions: includes both:
    // 1. Crypto positions (no stock, with crypto investment_subtype)
    // 2. Crypto ETF stocks (with stock and crypto investment_subtype, like HASH11, BITH11)
    
    // Known crypto ETF tickers
    const cryptoETFTickers = ['HASH11', 'BITH11', 'QBTC11', 'QETH11', 'CRPT11', 'ETHE11', 'BCHG11'];
    
    return actions.filter(action => {
      // Check if stock ticker is a known crypto ETF
      const stockTicker = action.stock?.ticker || '';
      const stockName = action.stock?.name || '';
      const stockNameLower = stockName.toLowerCase();
      
      if (stockTicker && cryptoETFTickers.includes(stockTicker.toUpperCase())) {
        return true;
      }
      
      // Also check if stock name contains crypto-related keywords (for crypto ETFs)
      if (action.stock && (stockNameLower.includes('bitcoin') || 
                          stockNameLower.includes('crypto') || 
                          stockNameLower.includes('cripto') ||
                          stockNameLower.includes('hashdex') ||
                          stockNameLower.includes('hash'))) {
        return true;
      }
      
      // Must have investment_subtype for other checks
      if (!action.investment_subtype) {
        return false;
      }
      
      // Check if investment_subtype is Bitcoin or Crypto
      const investmentSubtypeName = action.investment_subtype.name || '';
      const subtypeName = action.subtype_name || '';
      const nameLower = investmentSubtypeName.toLowerCase();
      const subtypeNameLower = subtypeName.toLowerCase();
      
      // Check if stock has crypto-related subtype (for crypto ETFs like HASH11)
      const stockSubtypeName = action.stock?.investment_subtype?.name || '';
      const stockSubtypeLower = stockSubtypeName.toLowerCase();
      
      // Also check if subtype_name is a crypto symbol (like "BTC", "ETH")
      const isCryptoSymbol = subtypeName && 
                            subtypeName.length <= 10 && 
                            subtypeName === subtypeName.toUpperCase() &&
                            /^[A-Z0-9]+$/.test(subtypeName);
      
      // Match if:
      // 1. Investment subtype name contains crypto keywords, OR
      // 2. Stock's investment subtype contains crypto keywords (for crypto ETFs), OR
      // 3. Subtype name contains crypto keywords, OR
      // 4. Subtype name is a crypto symbol
      return nameLower.includes('bitcoin') || 
             nameLower.includes('crypto') || 
             nameLower.includes('cripto') ||
             stockSubtypeLower.includes('bitcoin') ||
             stockSubtypeLower.includes('crypto') ||
             stockSubtypeLower.includes('cripto') ||
             subtypeNameLower.includes('bitcoin') ||
             subtypeNameLower.includes('crypto') ||
             subtypeNameLower.includes('cripto') ||
             isCryptoSymbol;
    }).sort((a, b) => (a.display_order || 0) - (b.display_order || 0));
  }

  getCryptoSubtypeActionsGrouped(): { subtypeName: string; subtypeActions: RebalancingAction[] }[] {
    const allCryptoActions = this.getCryptoSubtypeActions();
    
    if (allCryptoActions.length === 0) {
      return [];
    }
    
    // Separate aggregated subtype actions from individual crypto actions
    const aggregatedActions: RebalancingAction[] = [];
    const individualActions: RebalancingAction[] = [];
    
    for (const action of allCryptoActions) {
      const subtypeName = action.subtype_name || '';
      const investmentSubtypeName = action.investment_subtype?.name || '';
      
      // Check if this is an aggregated subtype action (subtype_name matches investment_subtype name or is null/empty)
      // OR if it's a stock action (crypto ETF like HASH11) - stocks should be shown as individual items
      const isAggregated = (!subtypeName || 
                           subtypeName === investmentSubtypeName ||
                           (subtypeName.length > 10 || !/^[A-Z0-9]+$/.test(subtypeName))) &&
                          !action.stock; // Stocks are not aggregated
      
      if (isAggregated) {
        aggregatedActions.push(action);
      } else {
        // Individual crypto action (crypto symbol like "BTC") or crypto ETF stock (like HASH11)
        individualActions.push(action);
      }
    }
    
    // Group individual actions by subtype
    const grouped: { [key: string]: RebalancingAction[] } = {};
    for (const action of individualActions) {
      const subtypeName = action.investment_subtype?.name || 'Crypto';
      if (!grouped[subtypeName]) {
        grouped[subtypeName] = [];
      }
      grouped[subtypeName].push(action);
    }
    
    // Return grouped structure: aggregated actions first, then individual actions grouped by subtype
    const result: { subtypeName: string; subtypeActions: RebalancingAction[] }[] = [];
    
    // Add aggregated subtype actions (like "Cryptocurrency" overall)
    for (const action of aggregatedActions) {
      const subtypeName = action.investment_subtype?.name || 'Cryptocurrency';
      result.push({
        subtypeName: subtypeName,
        subtypeActions: [action]
      });
    }
    
    // Add individual actions grouped by subtype
    for (const [subtypeName, actions] of Object.entries(grouped)) {
      if (actions.length > 0) {
        result.push({
          subtypeName: subtypeName,
          subtypeActions: actions
        });
      }
    }
    
    return result;
  }

  isCryptoSymbol(subtypeName: string | null | undefined): boolean {
    if (!subtypeName) return false;
    return subtypeName.length <= 10 && 
           subtypeName === subtypeName.toUpperCase() &&
           /^[A-Z0-9]+$/.test(subtypeName);
  }

  getCryptoDisplayName(cryptoCurrencyName: string | null | undefined): string {
    if (!cryptoCurrencyName) return 'Bitcoin';
    // Remove "BTC - " or similar prefix if present
    if (cryptoCurrencyName.includes(' - ')) {
      return cryptoCurrencyName.split(' - ')[1];
    }
    return cryptoCurrencyName;
  }

  getRendaFixaActions(): RebalancingAction[] {
    if (!this.currentRecommendation || !this.strategy) {
      return [];
    }
    
    // Find Renda Fixa investment type from strategy
    const rendaFixaTypeAlloc = this.strategy.type_allocations?.find(
      typeAlloc => typeAlloc.investment_type?.code === 'RENDA_FIXA' || 
                   typeAlloc.investment_type?.name?.toLowerCase().includes('renda fixa')
    );
    
    if (!rendaFixaTypeAlloc) {
      return [];
    }
    
    // Filter actions without stock (type-level and subtype-level rebalancing actions for Renda Fixa)
    // Actions can match either the type display_order OR be subtype actions (which have investment_subtype)
    return this.currentRecommendation.actions.filter(action => 
      !action.stock && (
        action.display_order === rendaFixaTypeAlloc.display_order ||
        (action.investment_subtype && 
         rendaFixaTypeAlloc.sub_type_allocations?.some(
           subAlloc => subAlloc.sub_type?.id === action.investment_subtype?.id
         ))
      )
    );
  }

  getRendaFixaTypeActions(): RebalancingAction[] {
    // Get type-level actions (no stock, no subtype) - these represent the total type allocation
    const actions = this.getRendaFixaActions();
    return actions.filter(action => !action.stock && !action.investment_subtype);
  }

  getETFRendaFixaActions(): RebalancingAction[] {
    if (!this.currentRecommendation) {
      console.log('getETFRendaFixaActions: No currentRecommendation');
      return [];
    }
    
    console.log('getETFRendaFixaActions: Checking recommendation ID:', this.currentRecommendation.id);
    console.log('getETFRendaFixaActions: Total actions:', this.currentRecommendation.actions.length);
    
    // Filter actions for ETF Renda Fixa stocks (stock_class=ETF with ETF_RENDA_FIXA subtype)
    const filtered = this.currentRecommendation.actions.filter(action => {
      if (!action.stock) {
        return false;
      }
      
      // Check action's investment_subtype first (set by backend)
      const actionSubtypeCode = action.investment_subtype?.code || '';
      if (actionSubtypeCode === 'ETF_RENDA_FIXA') {
        console.log('getETFRendaFixaActions: Found ETF Renda Fixa action:', {
          ticker: action.stock?.ticker,
          action_type: action.action_type,
          quantity_to_buy: action.quantity_to_buy,
          quantity_to_sell: action.quantity_to_sell,
          investment_subtype: action.investment_subtype
        });
        return true;
      }
      
      // Check stock's investment_subtype as fallback
      const subtypeCode = action.stock.investment_subtype?.code || '';
      const stockClass = (action.stock as any).stock_class || '';
      
      if (subtypeCode === 'ETF_RENDA_FIXA' || (stockClass === 'ETF' && action.stock.investment_type?.code === 'RENDA_FIXA')) {
        console.log('getETFRendaFixaActions: Found via stock subtype:', {
          ticker: action.stock?.ticker,
          action_type: action.action_type,
          quantity_to_buy: action.quantity_to_buy
        });
        return true;
      }
      
      return false;
    });
    
    console.log('getETFRendaFixaActions: Returning', filtered.length, 'actions');
    return filtered;
  }

  getRendaFixaActionsBySubtype(): Array<{subtypeName: string, subtypeActions: RebalancingAction[]}> {
    const actions = this.getRendaFixaActions();
    const grouped = new Map<string, RebalancingAction[]>();
    
    // First, group actions by subtype
    actions.forEach(action => {
      // Skip type-level actions (no investment_subtype)
      if (!action.investment_subtype) {
        return;
      }
      
      const subtypeName = action.subtype_display_name || 
                         action.investment_subtype?.name || 
                         action.subtype_name || 
                         'Renda Fixa';
      
      if (!grouped.has(subtypeName)) {
        grouped.set(subtypeName, []);
      }
      grouped.get(subtypeName)!.push(action);
    });
    
    // Also include all configured subtypes from strategy, and create synthetic actions from currentAllocation
    // when there are no rebalancing actions (difference below threshold)
    if (this.strategy && this.currentAllocation?.current) {
      const rendaFixaTypeAlloc = this.strategy.type_allocations?.find(
        typeAlloc => typeAlloc.investment_type?.code === 'RENDA_FIXA' || 
                     typeAlloc.investment_type?.name?.toLowerCase().includes('renda fixa')
      );
      
      // Get current allocation data for Renda Fixa
      const rendaFixaCurrentData = this.currentAllocation.current.investment_types?.find(
        (type: any) => type.code === 'RENDA_FIXA' || 
                       type.name?.toLowerCase().includes('renda fixa')
      );
      
      const totalValue = this.currentAllocation.current.total_value || 0;
      
      if (rendaFixaTypeAlloc?.sub_type_allocations) {
        rendaFixaTypeAlloc.sub_type_allocations.forEach(subAlloc => {
          const subtypeName = subAlloc.sub_type?.name || subAlloc.custom_name || 'Renda Fixa';
          const subtypeId = subAlloc.sub_type?.id;
          
          // If this subtype doesn't have any actions, try to create a synthetic one from currentAllocation
          if (!grouped.has(subtypeName) || grouped.get(subtypeName)!.length === 0) {
            // Find current value from currentAllocation
            let currentValue = 0;
            if (rendaFixaCurrentData?.sub_types) {
              const subtypeData = rendaFixaCurrentData.sub_types.find(
                (st: any) => st.sub_type_id === subtypeId || 
                            st.sub_type_name?.toLowerCase() === subtypeName.toLowerCase()
              );
              if (subtypeData) {
                currentValue = Number(subtypeData.current_value || 0);
              }
            }
            
            // Calculate target value from strategy allocation percentage
            const targetValue = totalValue * (subAlloc.target_percentage / 100);
            const difference = targetValue - currentValue;
            
            // Only create synthetic action if we have meaningful data
            if (currentValue > 0 || targetValue > 0) {
              const syntheticAction: any = {
                id: `synthetic_${subtypeId || subtypeName}`,
                action_type: 'rebalance',
                investment_subtype: subAlloc.sub_type ? {
                  id: subAlloc.sub_type.id,
                  name: subAlloc.sub_type.name,
                  code: subAlloc.sub_type.code
                } : null,
                subtype_name: subAlloc.custom_name || null,
                subtype_display_name: subtypeName,
                current_value: currentValue,
                target_value: targetValue,
                difference: difference,
                display_order: subAlloc.display_order || 9999
              };
              
              if (!grouped.has(subtypeName)) {
                grouped.set(subtypeName, []);
              }
              grouped.get(subtypeName)!.push(syntheticAction);
            } else if (!grouped.has(subtypeName)) {
              // Still add empty array to show the subtype header
              grouped.set(subtypeName, []);
            }
          }
        });
      }
    }
    
    // Convert Map to Array for template iteration, sorted by display_order
    return Array.from(grouped.entries()).map(([subtypeName, subtypeActions]) => ({ 
      subtypeName, 
      subtypeActions: subtypeActions.sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
    })).sort((a, b) => {
      // Sort by the first action's display_order, or by subtype name if no actions
      const aOrder = a.subtypeActions.length > 0 ? (a.subtypeActions[0].display_order || 0) : 999999;
      const bOrder = b.subtypeActions.length > 0 ? (b.subtypeActions[0].display_order || 0) : 999999;
      return aOrder - bOrder;
    });
  }

  // Expose Math for template
  Math = Math;

  // Helper methods to get current values for allocation configuration
  getCurrentTypeValue(typeId: number): number {
    if (!this.currentAllocation?.current?.investment_types) {
      return 0;
    }
    const typeData = this.currentAllocation.current.investment_types.find(
      (type: any) => type.investment_type_id === typeId
    );
    return typeData ? Number(typeData.current_value || 0) : 0;
  }

  getCurrentSubTypeValue(typeId: number, subTypeId: number): number {
    if (!this.currentAllocation?.current?.investment_types) {
      return 0;
    }
    const typeData = this.currentAllocation.current.investment_types.find(
      (type: any) => type.investment_type_id === typeId
    );
    if (!typeData?.sub_types) {
      return 0;
    }
    const subTypeData = typeData.sub_types.find(
      (st: any) => st.sub_type_id === subTypeId
    );
    return subTypeData ? Number(subTypeData.current_value || 0) : 0;
  }

  getTotalPortfolioValue(): number {
    return this.currentAllocation?.current?.total_value || 0;
  }

  getTargetTypeValue(typeAlloc: any): number {
    const totalValue = this.getTotalPortfolioValue();
    const percentage = Number(typeAlloc.target_percentage || 0);
    return totalValue * (percentage / 100);
  }

  getTargetTypeValueByCode(typeCode: string): number {
    if (!this.strategy?.type_allocations) {
      return 0;
    }
    const typeAlloc = this.strategy.type_allocations.find(
      (ta: any) => ta.investment_type?.code === typeCode || 
                   (typeCode === 'RENDA_VARIAVEL_REAIS' && ta.investment_type?.name?.includes('Reais'))
    );
    if (!typeAlloc) {
      return 0;
    }
    return this.getTargetTypeValue(typeAlloc);
  }

  getTargetSubTypeValue(typeAlloc: any, subTypeId: number): number {
    const totalValue = this.getTotalPortfolioValue();
    const subAlloc = typeAlloc.sub_type_allocations?.find(
      (sa: any) => sa.sub_type_id === subTypeId
    );
    if (!subAlloc) {
      return 0;
    }
    const percentage = Number(subAlloc.target_percentage || 0);
    return totalValue * (percentage / 100);
  }

  // Helper methods for Summary Card portfolio totals
  getRendaFixaTotal(): { value: number; percentage: number } | null {
    // First try to get from type-level actions (most reliable source)
    const typeActions = this.getRendaFixaTypeActions();
    if (typeActions.length > 0 && typeActions[0].current_value) {
      const totalValue = this.currentAllocation?.current?.total_value || 0;
      const currentValue = Number(typeActions[0].current_value);
      const percentage = totalValue > 0 ? (currentValue / totalValue) * 100 : 0;
      return {
        value: currentValue,
        percentage: percentage
      };
    }
    
    // Fallback to currentAllocation data
    if (!this.currentAllocation?.current?.investment_types) {
      return null;
    }
    const rendaFixa = this.currentAllocation.current.investment_types.find(
      (type: any) => type.code === 'RENDA_FIXA' || 
                     type.name?.toLowerCase().includes('renda fixa')
    );
    if (!rendaFixa) {
      return null;
    }
    return {
      value: Number(rendaFixa.current_value || 0),
      percentage: Number(rendaFixa.current_percentage || 0)
    };
  }

  getRendaVarDolaresTotal(): { value: number; percentage: number } | null {
    // First try to get from type-level actions (most reliable source)
    const typeActions = this.getRendaVarDolaresTypeActions();
    if (typeActions.length > 0 && typeActions[0].current_value) {
      const totalValue = this.currentAllocation?.current?.total_value || 0;
      const currentValue = Number(typeActions[0].current_value);
      const percentage = totalValue > 0 ? (currentValue / totalValue) * 100 : 0;
      return {
        value: currentValue,
        percentage: percentage
      };
    }
    
    // Fallback to currentAllocation data
    if (!this.currentAllocation?.current?.investment_types) {
      return null;
    }
    const rendaVarDolares = this.currentAllocation.current.investment_types.find(
      (type: any) => type.code === 'RENDA_VARIAVEL_DOLARES' || 
                     type.name?.toLowerCase().includes('renda variável em dólar') ||
                     type.name?.toLowerCase().includes('renda variavel em dolar')
    );
    if (!rendaVarDolares) {
      return null;
    }
    return {
      value: Number(rendaVarDolares.current_value || 0),
      percentage: Number(rendaVarDolares.current_percentage || 0)
    };
  }

  getRendaVarReaisTotal(): { value: number; percentage: number } | null {
    // First try to sum from all Ações em Reais actions (most reliable source)
    const acoesReaisActions = this.getAcoesReaisActions();
    if (acoesReaisActions.length > 0) {
      const totalValue = acoesReaisActions.reduce((sum, action) => {
        return sum + Number(action.current_value || 0);
      }, 0);
      const portfolioTotal = this.currentAllocation?.current?.total_value || 0;
      const percentage = portfolioTotal > 0 ? (totalValue / portfolioTotal) * 100 : 0;
      if (totalValue > 0) {
        return {
          value: totalValue,
          percentage: percentage
        };
      }
    }
    
    // Fallback to currentAllocation data
    if (!this.currentAllocation?.current?.investment_types) {
      return null;
    }
    const rendaVarReais = this.currentAllocation.current.investment_types.find(
      (type: any) => type.code === 'RENDA_VARIAVEL_REAIS' || 
                     type.name?.toLowerCase().includes('renda variável em reais') ||
                     type.name?.toLowerCase().includes('renda variavel em reais') ||
                     type.name?.toLowerCase().includes('ações em reais')
    );
    if (!rendaVarReais) {
      return null;
    }
    return {
      value: Number(rendaVarReais.current_value || 0),
      percentage: Number(rendaVarReais.current_percentage || 0)
    };
  }

  getFIITotalSummary(): { value: number; percentage: number } | null {
    // Calculate total FII value from FII actions (sell, buy, rebalance)
    const fiiActions = this.getFIIActions();
    if (fiiActions.length > 0) {
      // Sum current values from all FII actions (what we currently have in portfolio)
      const totalValue = fiiActions.reduce((sum, action) => {
        // Use current_value for all actions (what we currently have)
        // This represents the total FII value in the portfolio
        return sum + Number(action.current_value || 0);
      }, 0);
      
      const portfolioTotal = this.currentAllocation?.current?.total_value || 0;
      const percentage = portfolioTotal > 0 ? (totalValue / portfolioTotal) * 100 : 0;
      
      if (totalValue > 0) {
        return {
          value: totalValue,
          percentage: percentage
        };
      }
    }
    
    // Fallback to currentAllocation data
    if (!this.currentAllocation?.current?.investment_types) {
      return null;
    }
    const fiis = this.currentAllocation.current.investment_types.find(
      (type: any) => type.code === 'FIIS' || 
                     type.name?.toLowerCase().includes('fundos imobiliários') ||
                     type.name?.toLowerCase().includes('fii')
    );
    if (!fiis) {
      return null;
    }
    return {
      value: Number(fiis.current_value || 0),
      percentage: Number(fiis.current_percentage || 0)
    };
  }

}

