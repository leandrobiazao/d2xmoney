import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ConfigurationService, InvestmentType } from '../configuration.service';

@Component({
  selector: 'app-investment-types',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './investment-types.html',
  styleUrl: './investment-types.css'
})
export class InvestmentTypesComponent implements OnInit {
  investmentTypes: InvestmentType[] = [];
  isLoading = false;
  errorMessage: string | null = null;

  showCreateModal = false;
  editingType: InvestmentType | null = null;
  formData: Partial<InvestmentType> = {
    name: '',
    code: '',
    display_order: 0,
    is_active: true
  };

  constructor(private configService: ConfigurationService) {}

  ngOnInit(): void {
    this.loadInvestmentTypes();
  }

  loadInvestmentTypes(): void {
    this.isLoading = true;
    this.errorMessage = null;

    this.configService.getInvestmentTypes(false).subscribe({
      next: (types) => {
        this.investmentTypes = types;
        this.isLoading = false;
      },
      error: (error) => {
        this.errorMessage = 'Erro ao carregar tipos de investimento';
        this.isLoading = false;
        console.error('Error loading investment types:', error);
      }
    });
  }

  onCreate(): void {
    this.formData = { name: '', code: '', display_order: 0, is_active: true };
    this.editingType = null;
    this.showCreateModal = true;
  }

  onEdit(type: InvestmentType): void {
    this.editingType = type;
    this.formData = { ...type };
    this.showCreateModal = true;
  }

  onSave(): void {
    if (this.editingType) {
      this.configService.updateInvestmentType(this.editingType.id, this.formData).subscribe({
        next: () => {
          this.showCreateModal = false;
          this.loadInvestmentTypes();
        },
        error: (error) => {
          console.error('Error updating investment type:', error);
          alert('Erro ao atualizar tipo de investimento');
        }
      });
    } else {
      this.configService.createInvestmentType(this.formData).subscribe({
        next: () => {
          this.showCreateModal = false;
          this.loadInvestmentTypes();
        },
        error: (error) => {
          console.error('Error creating investment type:', error);
          alert('Erro ao criar tipo de investimento');
        }
      });
    }
  }

  onDelete(type: InvestmentType): void {
    if (confirm(`Tem certeza que deseja excluir "${type.name}"?`)) {
      this.configService.deleteInvestmentType(type.id).subscribe({
        next: () => {
          this.loadInvestmentTypes();
        },
        error: (error) => {
          console.error('Error deleting investment type:', error);
          alert('Erro ao excluir tipo de investimento');
        }
      });
    }
  }

  onCloseModal(): void {
    this.showCreateModal = false;
    this.editingType = null;
  }
}


