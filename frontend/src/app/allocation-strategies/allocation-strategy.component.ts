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

  constructor(
    private userService: UserService,
    private allocationStrategyService: AllocationStrategyService,
    private configurationService: ConfigurationService
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
    if (!this.strategy?.type_allocations) {
      this.draftTypeAllocations = [];
      this.totalPortfolioValueInput = this.strategy?.total_portfolio_value || null;
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
}

