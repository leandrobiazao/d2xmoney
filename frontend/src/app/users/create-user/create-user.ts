import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UserService } from '../user.service';
import { PicturePreviewComponent } from '../picture-preview/picture-preview';
import { validateCPF, formatCPF } from '../../shared/utils/cpf-validator';
import { DebugService } from '../../shared/services/debug.service';

@Component({
  selector: 'app-create-user',
  standalone: true,
  imports: [CommonModule, FormsModule, PicturePreviewComponent],
  templateUrl: './create-user.html',
  styleUrl: './create-user.css'
})
export class CreateUserComponent {
  @Output() close = new EventEmitter<void>();
  @Output() userCreated = new EventEmitter<void>();

  name: string = '';
  cpf: string = '';
  accountProvider: string = '';
  accountNumber: string = '';
  pictureFile: File | null = null;

  cpfError: string = '';
  nameError: string = '';
  accountProviderError: string = '';
  accountNumberError: string = '';
  pictureError: string = '';
  isSubmitting: boolean = false;
  errorMessage: string = '';

  constructor(
    private userService: UserService,
    private debug: DebugService
  ) {}

  onCPFInput(event: Event) {
    const input = event.target as HTMLInputElement;
    const formatted = formatCPF(input.value);
    this.cpf = formatted;
    this.cpfError = '';
    this.errorMessage = '';
  }

  onCPFBlur() {
    if (this.cpf && !validateCPF(this.cpf)) {
      this.cpfError = 'CPF inválido';
    } else {
      this.cpfError = '';
    }
  }

  onPictureSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.pictureFile = input.files[0];
      this.pictureError = '';
    }
  }

  onPictureRemove() {
    this.pictureFile = null;
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (input) {
      input.value = '';
    }
  }

  validateForm(): boolean {
    let isValid = true;

    // Validate name
    if (!this.name || this.name.trim().length < 3) {
      this.nameError = 'Nome deve ter pelo menos 3 caracteres';
      isValid = false;
    } else {
      this.nameError = '';
    }

    // Validate CPF
    if (!this.cpf) {
      this.cpfError = 'CPF é obrigatório';
      isValid = false;
    } else if (!validateCPF(this.cpf)) {
      this.cpfError = 'CPF inválido';
      isValid = false;
    } else {
      this.cpfError = '';
    }

    // Validate account provider
    if (!this.accountProvider || this.accountProvider.trim().length === 0) {
      this.accountProviderError = 'Corretora é obrigatória';
      isValid = false;
    } else {
      this.accountProviderError = '';
    }

    // Validate account number
    if (!this.accountNumber || this.accountNumber.trim().length === 0) {
      this.accountNumberError = 'Número da conta é obrigatório';
      isValid = false;
    } else if (!/^[A-Za-z0-9\-]+$/.test(this.accountNumber)) {
      this.accountNumberError = 'Número da conta deve ser alfanumérico';
      isValid = false;
    } else {
      this.accountNumberError = '';
    }

    // Picture is optional - no validation needed
    this.pictureError = '';

    return isValid;
  }

  onSubmit() {
    if (!this.validateForm()) {
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    // Create FormData
    const formData = new FormData();
    formData.append('name', this.name.trim());
    formData.append('cpf', this.cpf);
    formData.append('account_provider', this.accountProvider.trim());
    formData.append('account_number', this.accountNumber.trim());
    if (this.pictureFile) {
      formData.append('picture', this.pictureFile);
    }

    this.userService.createUser(formData).subscribe({
      next: () => {
        this.resetForm();
        this.userCreated.emit();
        this.close.emit();
      },
      error: (error) => {
        this.isSubmitting = false;
        this.debug.error('Error creating user:', error);
        this.debug.error('Error details:', error.error);
        
        if (error.error?.details) {
          const details = error.error.details;
          
          // Handle field-specific errors
          if (details.cpf && Array.isArray(details.cpf)) {
            this.cpfError = details.cpf[0];
          }
          if (details.account_number && Array.isArray(details.account_number)) {
            this.accountNumberError = details.account_number[0];
          }
          if (details.name && Array.isArray(details.name)) {
            this.nameError = details.name[0];
          }
          if (details.account_provider && Array.isArray(details.account_provider)) {
            this.accountProviderError = details.account_provider[0];
          }
          if (details.picture && Array.isArray(details.picture)) {
            this.pictureError = details.picture[0];
          }
          
          // Set general error message if no field-specific errors were set
          if (!this.cpfError && !this.accountNumberError && !this.nameError && 
              !this.accountProviderError && !this.pictureError) {
            this.errorMessage = typeof details === 'string' 
              ? details 
              : JSON.stringify(details);
          }
        } else if (error.error?.error) {
          this.errorMessage = error.error.error;
        } else if (error.error) {
          this.errorMessage = JSON.stringify(error.error);
        } else if (error.message) {
          this.errorMessage = error.message;
        } else {
          this.errorMessage = 'Erro ao criar usuário. Tente novamente.';
        }
      }
    });
  }

  onCancel() {
    this.close.emit();
  }

  private resetForm() {
    this.name = '';
    this.cpf = '';
    this.accountProvider = '';
    this.accountNumber = '';
    this.pictureFile = null;
    this.nameError = '';
    this.cpfError = '';
    this.accountProviderError = '';
    this.accountNumberError = '';
    this.pictureError = '';
    this.errorMessage = '';
    this.isSubmitting = false;
  }
}

