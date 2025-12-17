/**
 * Common utility functions shared across the application
 */

/**
 * Parses a date string in DD/MM/YYYY format or ISO format
 * @param dateStr - Date string to parse
 * @returns Date object
 */
export function parseDate(dateStr: string): Date {
  // Format: DD/MM/YYYY
  const parts = dateStr.split('/');
  if (parts.length === 3) {
    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1; // Months are 0-indexed
    const year = parseInt(parts[2], 10);
    return new Date(year, month, day);
  }
  // Fallback to ISO format
  return new Date(dateStr);
}

/**
 * Formats a number as Brazilian Real currency
 * @param value - Number to format
 * @returns Formatted currency string
 */
export function formatCurrency(value: number): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'R$ 0,00';
  }
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
}

/**
 * Compares two date strings
 * @param dateStr1 - First date string (DD/MM/YYYY)
 * @param dateStr2 - Second date string (DD/MM/YYYY)
 * @returns Negative if date1 < date2, 0 if equal, positive if date1 > date2
 */
export function compareDate(dateStr1: string, dateStr2: string): number {
  const date1 = parseDate(dateStr1);
  const date2 = parseDate(dateStr2);
  return date1.getTime() - date2.getTime();
}

