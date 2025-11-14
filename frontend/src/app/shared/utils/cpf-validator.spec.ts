import { validateCPF, formatCPF } from './cpf-validator';

describe('CPF Validator', () => {
  describe('validateCPF', () => {
    it('should validate correct CPF', () => {
      expect(validateCPF('123.456.789-00')).toBe(true);
      expect(validateCPF('12345678900')).toBe(true);
    });

    it('should reject invalid CPF with wrong check digits', () => {
      expect(validateCPF('123.456.789-01')).toBe(false);
      expect(validateCPF('12345678901')).toBe(false);
    });

    it('should reject CPF with incorrect length', () => {
      expect(validateCPF('123.456.789-0')).toBe(false);
      expect(validateCPF('123456789')).toBe(false);
      expect(validateCPF('123456789000')).toBe(false);
    });

    it('should reject CPF with all same digits', () => {
      expect(validateCPF('111.111.111-11')).toBe(false);
      expect(validateCPF('000.000.000-00')).toBe(false);
      expect(validateCPF('22222222222')).toBe(false);
    });

    it('should handle CPF with various formats', () => {
      expect(validateCPF('123 456 789 00')).toBe(true);
      expect(validateCPF('123.456.789-00')).toBe(true);
      expect(validateCPF('12345678900')).toBe(true);
    });
  });

  describe('formatCPF', () => {
    it('should format CPF correctly', () => {
      expect(formatCPF('12345678900')).toBe('123.456.789-00');
      expect(formatCPF('123.456.789-00')).toBe('123.456.789-00');
    });

    it('should handle partial input', () => {
      expect(formatCPF('123')).toBe('123');
      expect(formatCPF('1234')).toBe('123.4');
      expect(formatCPF('123456')).toBe('123.456');
      expect(formatCPF('1234567')).toBe('123.456.7');
      expect(formatCPF('123456789')).toBe('123.456.789');
      expect(formatCPF('1234567890')).toBe('123.456.789-0');
    });

    it('should remove non-digit characters before formatting', () => {
      expect(formatCPF('123.456.789-00')).toBe('123.456.789-00');
      expect(formatCPF('123 456 789 00')).toBe('123.456.789-00');
    });
  });
});

