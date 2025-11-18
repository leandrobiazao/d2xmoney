import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ConfigurationService, InvestmentSubType, InvestmentType } from '../configuration.service';

@Component({
  selector: 'app-investment-subtypes',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './investment-subtypes.html',
  styleUrl: './investment-subtypes.css'
})
export class InvestmentSubtypesComponent implements OnInit {
  investmentTypes: InvestmentType[] = [];
  subTypes: InvestmentSubType[] = [];
  selectedTypeId: number | null = null;
  isLoading = false;
  showCreateModal = false;
  editingSubType: InvestmentSubType | null = null;
  formData: Partial<InvestmentSubType> = {
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
    this.configService.getInvestmentTypes(false).subscribe({
      next: (types) => {
        this.investmentTypes = types;
        if (types.length > 0 && !this.selectedTypeId) {
          this.selectedTypeId = types[0].id;
          this.loadSubTypes();
        }
      }
    });
  }

  loadSubTypes(): void {
    if (!this.selectedTypeId) return;
    this.isLoading = true;
    this.configService.getInvestmentSubTypes(this.selectedTypeId, false).subscribe({
      next: (subTypes) => {
        this.subTypes = subTypes;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      }
    });
  }

  onTypeChange(): void {
    this.loadSubTypes();
  }

  onCreate(): void {
    this.formData = {
      investment_type: this.selectedTypeId!,
      name: '',
      code: '',
      display_order: 0,
      is_active: true,
      is_predefined: false
    };
    this.editingSubType = null;
    this.showCreateModal = true;
  }


  onSave(): void {
    if (!this.formData.investment_type) {
      this.formData.investment_type = this.selectedTypeId!;
    }

    if (this.editingSubType) {
      this.configService.updateInvestmentSubType(this.editingSubType.id, this.formData).subscribe({
        next: () => {
          this.showCreateModal = false;
          this.loadSubTypes();
        },
        error: (error) => {
          console.error('Error updating investment sub-type:', error);
          alert('Erro ao atualizar sub-tipo de investimento');
        }
      });
    } else {
      this.configService.createInvestmentSubType(this.formData).subscribe({
        next: () => {
          this.showCreateModal = false;
          this.loadSubTypes();
        },
        error: (error) => {
          console.error('Error creating investment sub-type:', error);
          alert('Erro ao criar sub-tipo de investimento');
        }
      });
    }
  }

  onEdit(subType: InvestmentSubType): void {
    this.editingSubType = subType;
    this.formData = { ...subType };
    this.showCreateModal = true;
  }

  onDelete(subType: InvestmentSubType): void {
    if (confirm(`Tem certeza que deseja excluir "${subType.name}"?`)) {
      this.configService.deleteInvestmentSubType(subType.id).subscribe({
        next: () => {
          this.loadSubTypes();
        },
        error: (error) => {
          console.error('Error deleting investment sub-type:', error);
          alert('Erro ao excluir sub-tipo de investimento');
        }
      });
    }
  }

  onCloseModal(): void {
    this.showCreateModal = false;
    this.editingSubType = null;
  }
}

