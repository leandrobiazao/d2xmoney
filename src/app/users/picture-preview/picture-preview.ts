import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-picture-preview',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './picture-preview.html',
  styleUrl: './picture-preview.css'
})
export class PicturePreviewComponent implements OnChanges {
  @Input() file: File | null = null;
  @Output() remove = new EventEmitter<void>();
  @Output() change = new EventEmitter<void>();

  previewUrl: string | null = null;
  errorMessage: string | null = null;

  ngOnChanges(changes: SimpleChanges) {
    if (changes['file'] && this.file) {
      this.validateAndPreview(this.file);
    } else if (changes['file'] && !this.file) {
      this.previewUrl = null;
      this.errorMessage = null;
    }
  }

  private validateAndPreview(file: File) {
    this.errorMessage = null;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      this.errorMessage = 'Tipo de arquivo inválido. Use JPEG ou PNG.';
      this.previewUrl = null;
      return;
    }

    // Validate file size (5MB max)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      this.errorMessage = 'Arquivo muito grande. Tamanho máximo: 5MB.';
      this.previewUrl = null;
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      this.previewUrl = e.target?.result as string;
    };
    reader.onerror = () => {
      this.errorMessage = 'Erro ao carregar imagem.';
      this.previewUrl = null;
    };
    reader.readAsDataURL(file);
  }

  onRemove() {
    this.previewUrl = null;
    this.errorMessage = null;
    this.remove.emit();
  }

  onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.change.emit();
    }
  }

  get fileSize() {
    if (!this.file) return '';
    const sizeInMB = this.file.size / (1024 * 1024);
    return `${sizeInMB.toFixed(2)} MB`;
  }
}

