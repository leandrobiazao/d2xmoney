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
import { ConfigurationService, InvestmentType } from '../configuration/configuration.service';
import { RebalancingService, RebalancingRecommendation, RebalancingAction } from '../rebalancing/rebalancing.service';
import { HttpClient } from '@angular/common/http';

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
    // If strategy exists but has no type_allocations, initialize with all investment types at 0%
    if (!this.strategy?.type_allocations || this.strategy.type_allocations.length === 0) {
      this.totalPortfolioValueInput = this.strategy?.total_portfolio_value || null;
      
      // Load all investment types and initialize them at 0%
      this.configurationService.getInvestmentTypes(true).subscribe({
        next: (investmentTypes) => {
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
        },
        error: (error) => {
          console.error('Error loading investment types:', error);
          this.draftTypeAllocations = [];
        }
      });
      return;
    }

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

    this.totalPortfolioValueInput = this.strategy.total_portfolio_value || null;
  }

  get typeAllocationTotal(): number {
    return this.draftTypeAllocations.reduce((sum, alloc) => sum + Number(alloc.target_percentage || 0), 0);
  }

  get isTypeTotalValid(): boolean {
    return Math.abs(this.typeAllocationTotal - 100) < 0.01;
  }

  getSubTypeTotal(typeAlloc: DraftTypeAllocation): number {
    return (typeAlloc.sub_type_allocations || []).reduce(
      (sum, subAlloc) => sum + Number(subAlloc.target_percentage || 0),
      0
    );
  }

  isSubTypeTotalValid(typeAlloc: DraftTypeAllocation): boolean {
    if (!typeAlloc.sub_type_allocations || typeAlloc.sub_type_allocations.length === 0) {
      return true;
    }
    return Math.abs(this.getSubTypeTotal(typeAlloc) - 100) < 0.01;
  }

  onTypePercentageChange(index: number, value: string): void {
    const numericValue = Number(value);
    this.draftTypeAllocations[index].target_percentage = numericValue;
  }

  onSubTypePercentageChange(typeIndex: number, subIndex: number, value: string): void {
    const numericValue = Number(value);
    const subAllocations = this.draftTypeAllocations[typeIndex].sub_type_allocations;
    if (subAllocations) {
      subAllocations[subIndex].target_percentage = numericValue;
    }
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

    const payload = this.draftTypeAllocations.map((typeAlloc, index) => ({
      investment_type_id: typeAlloc.investment_type_id,
      target_percentage: Number(typeAlloc.target_percentage),
      display_order: index,
      sub_type_allocations: (typeAlloc.sub_type_allocations || []).map((subAlloc, subIndex) => ({
        sub_type_id: subAlloc.sub_type_id,
        custom_name: subAlloc.custom_name,
        target_percentage: Number(subAlloc.target_percentage),
        display_order: subIndex
      }))
    }));

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

  applyRecommendation(recommendationId: number): void {
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
    if (tab === 'rebalancing' && this.selectedUser) {
      this.loadRecommendations(this.selectedUser.id);
      this.loadCurrentAllocation(this.selectedUser.id);
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
    // Sort by ranking (display_order) - lower is better
    return actions.sort((a, b) => (a.display_order || 999) - (b.display_order || 999));
  }

  getAcoesDolaresActions(): RebalancingAction[] {
    if (!this.currentRecommendation) {
      return [];
    }
    // Filter actions for BERK34 (Ações em Dólares)
    return this.currentRecommendation.actions.filter(action => 
      action.stock && action.stock.ticker === 'BERK34'
    );
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
    
    // Filter actions without stock AND matching Renda Fixa display_order
    return this.currentRecommendation.actions.filter(action => 
      !action.stock && 
      action.display_order === rendaFixaTypeAlloc.display_order
    );
  }

  // Expose Math for template
  Math = Math;

}

