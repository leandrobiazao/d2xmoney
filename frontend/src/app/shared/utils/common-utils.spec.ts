import { parseDate, formatCurrency, compareDate } from './common-utils';

describe('Common Utils', () => {
  describe('parseDate', () => {
    it('should parse DD/MM/YYYY format', () => {
      const date = parseDate('15/03/2024');
      expect(date.getDate()).toBe(15);
      expect(date.getMonth()).toBe(2); // 0-indexed
      expect(date.getFullYear()).toBe(2024);
    });

    it('should parse ISO format as fallback', () => {
      const date = parseDate('2024-03-15');
      expect(date.getFullYear()).toBe(2024);
      expect(date.getMonth()).toBe(2);
      expect(date.getDate()).toBe(15);
    });

    it('should handle different date formats', () => {
      const date1 = parseDate('01/01/2024');
      expect(date1.getDate()).toBe(1);
      expect(date1.getMonth()).toBe(0);
      expect(date1.getFullYear()).toBe(2024);
    });
  });

  describe('formatCurrency', () => {
    it('should format number as BRL currency', () => {
      expect(formatCurrency(1234.56)).toContain('R$');
      expect(formatCurrency(1234.56)).toContain('1.234');
      expect(formatCurrency(1234.56)).toContain('56');
    });

    it('should handle zero', () => {
      const formatted = formatCurrency(0);
      expect(formatted).toContain('R$');
      expect(formatted).toContain('0');
    });

    it('should handle large numbers', () => {
      const formatted = formatCurrency(1234567.89);
      expect(formatted).toContain('R$');
      expect(formatted).toContain('1.234.567');
    });

    it('should handle negative numbers', () => {
      const formatted = formatCurrency(-100.50);
      expect(formatted).toContain('R$');
    });
  });

  describe('compareDate', () => {
    it('should return negative when first date is earlier', () => {
      expect(compareDate('01/01/2024', '02/01/2024')).toBeLessThan(0);
    });

    it('should return positive when first date is later', () => {
      expect(compareDate('02/01/2024', '01/01/2024')).toBeGreaterThan(0);
    });

    it('should return zero when dates are equal', () => {
      expect(compareDate('01/01/2024', '01/01/2024')).toBe(0);
    });

    it('should handle different months', () => {
      expect(compareDate('01/01/2024', '01/02/2024')).toBeLessThan(0);
    });

    it('should handle different years', () => {
      expect(compareDate('01/01/2023', '01/01/2024')).toBeLessThan(0);
    });
  });
});

