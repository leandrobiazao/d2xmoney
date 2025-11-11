/**
 * CPF validation utility for Brazilian CPF format.
 */

/**
 * Validates Brazilian CPF using checksum algorithm.
 * @param cpf - CPF string (with or without formatting)
 * @returns true if valid, false otherwise
 */
export function validateCPF(cpf: string): boolean {
  // Remove formatting (dots, dashes, spaces)
  const cpfDigits = cpf.replace(/[^\d]/g, '');
  
  // Check length
  if (cpfDigits.length !== 11) {
    return false;
  }
  
  // Check if all digits are the same (invalid CPF)
  if (/^(\d)\1{10}$/.test(cpfDigits)) {
    return false;
  }
  
  // Calculate first check digit
  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(cpfDigits[i]) * (10 - i);
  }
  let remainder = sum % 11;
  const firstDigit = remainder < 2 ? 0 : 11 - remainder;
  
  if (parseInt(cpfDigits[9]) !== firstDigit) {
    return false;
  }
  
  // Calculate second check digit
  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(cpfDigits[i]) * (11 - i);
  }
  remainder = sum % 11;
  const secondDigit = remainder < 2 ? 0 : 11 - remainder;
  
  return parseInt(cpfDigits[10]) === secondDigit;
}

/**
 * Formats CPF as XXX.XXX.XXX-XX
 * @param cpf - CPF string (with or without formatting)
 * @returns Formatted CPF string
 */
export function formatCPF(cpf: string): string {
  // Remove all non-digit characters
  const digits = cpf.replace(/[^\d]/g, '');
  
  // Handle partial input
  if (digits.length <= 3) {
    return digits;
  } else if (digits.length <= 6) {
    return `${digits.slice(0, 3)}.${digits.slice(3)}`;
  } else if (digits.length <= 9) {
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
  } else {
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9, 11)}`;
  }
}

