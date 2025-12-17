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
  SubTypeAllocation
} from './allocation-strategy.service';
import { UserItemComponent } from '../users/user-item/user-item';
import { ConfigurationService, InvestmentType, InvestmentSubType } from '../configuration/configuration.service';
import { RebalancingService, RebalancingRecommendation, RebalancingAction } from '../rebalancing/rebalancing.service';
import { HttpClient } from '@angular/common/http';
import * as XLSX from 'xlsx';

interface DraftSubTypeAllocation extends Omit<SubTypeAllocation, 'id'> {
  id?: number;
  sub_type_id?: number;
}

interface DraftTypeAllocation extends Omit<InvestmentTypeAllocation, 'id' | 'sub_type_allocations'> {
  id?: number;
  investment_type_id: number;
  sub_type_allocations?: DraftSubTypeAllocation[];
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
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.loadInvestmentSubTypes();
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
          
          // Get available subtypes for this investment type
          const availableSubtypes = this.getSubTypesForInvestmentType(type.id);
          
          if (availableSubtypes.length > 0) {
            // Always show subtypes if they exist for this investment type
            const initializedSubtypes = availableSubtypes.map((subType, subIndex) => {
              // Check if this subtype was in the existing allocation
              const existingSubAlloc = existingAlloc?.sub_type_allocations?.find((sa: any) => sa.sub_type?.id === subType.id || sa.sub_type_id === subType.id);
              
              return {
                ...existingSubAlloc,
                sub_type_id: subType.id,
                sub_type: {
                  id: subType.id,
                  name: subType.name,
                  code: subType.code
                },
                target_percentage: existingSubAlloc ? existingSubAlloc.target_percentage : 0,
                display_order: existingSubAlloc?.display_order ?? subIndex
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
              sub_type_allocations: existingAlloc?.sub_type_allocations || []
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
      },
      error: (error) => {
        console.error('Error loading investment subtypes:', error);
      }
    });
  }

  getSubTypesForInvestmentType(investmentTypeId: number): InvestmentSubType[] {
    return this.investmentSubTypes.filter(s => s.investment_type === investmentTypeId);
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
        this.draftTypeAllocations = investmentTypes.map((type, index) => ({
          investment_type_id: type.id,
          investment_type: {
            id: type.id,
            name: type.name,
            code: type.code
          },
          target_percentage: 0,
          display_order: index,
          sub_type_allocations: []
        }));

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

    // Validate and fix subtype totals for each type allocation
    for (const typeAlloc of this.draftTypeAllocations) {
      if (typeAlloc.sub_type_allocations && typeAlloc.sub_type_allocations.length > 0) {
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

    const payload = this.draftTypeAllocations.map((typeAlloc, index) => {
      // Calculate exact sum of subtypes for this type allocation
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
        sub_type_allocations: (typeAlloc.sub_type_allocations || []).map((subAlloc, subIndex) => ({
          sub_type_id: subAlloc.sub_type_id,
          custom_name: subAlloc.custom_name,
          target_percentage: Number(subAlloc.target_percentage),
          display_order: subIndex
        }))
      };
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
    // Filter actions for "Ações em Reais" stocks (actions with stock ticker, excluding BERK34)
    return this.currentRecommendation.actions.filter(action => 
      action.stock && 
      action.stock.ticker !== 'BERK34' &&
      (action.action_type === 'buy' || action.action_type === 'sell' || action.action_type === 'rebalance')
    );
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
    // Sort by smallest difference (absolute value) for stocks to sell, then by ranking for others
    return actions.sort((a, b) => {
      // If both need to sell (negative difference), sort by smallest absolute difference first
      if (a.difference < 0 && b.difference < 0) {
        const diffA = Math.abs(a.difference);
        const diffB = Math.abs(b.difference);
        if (diffA !== diffB) {
          return diffA - diffB; // Smallest difference first
        }
      }
      // Otherwise, sort by ranking (display_order) - lower is better
      return (a.display_order || 999) - (b.display_order || 999);
    });
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
      
      const rebalanceActions = this.getAcoesReaisRebalanceActions();
      const buyActions = this.getAcoesReaisBuyActions();
      
      const rebalanceTotal = rebalanceActions.reduce((sum, action) => {
        const targetValue = action.target_value ? Number(action.target_value) : 0;
        if (isNaN(targetValue)) {
          console.warn('Invalid target_value for action:', action);
          return sum;
        }
        return sum + targetValue;
      }, 0);
      
      const buyTotal = buyActions.reduce((sum, action) => {
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
    // Get Crypto actions: actions with investment_subtype = Bitcoin/Crypto (no stock)
    // This includes both aggregated subtype actions and individual crypto actions
    return actions.filter(action => {
      // Must have investment_subtype but no stock (crypto positions)
      if (!action.investment_subtype || action.stock) {
        return false;
      }
      // Check if investment_subtype is Bitcoin or Crypto
      // Use investment_subtype.name as primary source (works for aggregated actions with subtype_name=None)
      const investmentSubtypeName = action.investment_subtype.name || '';
      const subtypeName = action.subtype_name || '';
      const nameLower = investmentSubtypeName.toLowerCase();
      const subtypeNameLower = subtypeName.toLowerCase();
      
      // Also check if subtype_name is a crypto symbol (like "BTC", "ETH")
      const isCryptoSymbol = subtypeName && 
                            subtypeName.length <= 10 && 
                            subtypeName === subtypeName.toUpperCase() &&
                            /^[A-Z0-9]+$/.test(subtypeName);
      
      // Match if investment_subtype name contains crypto keywords OR subtype_name is a crypto symbol
      return nameLower.includes('bitcoin') || 
             nameLower.includes('crypto') || 
             nameLower.includes('cripto') ||
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
    
    // Filter only individual crypto actions (crypto symbol like "BTC")
    // Exclude aggregated subtype actions
    const individualActions: RebalancingAction[] = [];
    
    for (const action of allCryptoActions) {
      const subtypeName = action.subtype_name || '';
      const investmentSubtypeName = action.investment_subtype?.name || '';
      
      // Only include individual crypto actions (crypto symbol like "BTC")
      const isIndividual = subtypeName && 
                           subtypeName.length <= 10 && 
                           /^[A-Z0-9]+$/.test(subtypeName) &&
                           subtypeName !== investmentSubtypeName;
      
      if (isIndividual) {
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
    
    // Return grouped structure (only individual actions, no aggregated)
    const result: { subtypeName: string; subtypeActions: RebalancingAction[] }[] = [];
    
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

}

