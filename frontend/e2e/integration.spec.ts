import { test, expect } from '@playwright/test';

/**
 * TC-020: Integration Flow - Complete Workflow
 */

/**
 * Generates a valid CPF based on a seed number (e.g., timestamp)
 * This ensures unique CPFs for each test run
 */
function generateValidCPF(seed: number): string {
  // Use seed to generate base 9 digits (avoiding all same digits)
  const base = Math.abs(seed) % 999999999;
  const baseStr = base.toString().padStart(9, '0');
  
  // Calculate first check digit
  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(baseStr[i]) * (10 - i);
  }
  let remainder = sum % 11;
  const firstDigit = remainder < 2 ? 0 : 11 - remainder;
  
  // Calculate second check digit
  sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(baseStr[i]) * (11 - i);
  }
  sum += firstDigit * 2;
  remainder = sum % 11;
  const secondDigit = remainder < 2 ? 0 : 11 - remainder;
  
  // Format as XXX.XXX.XXX-XX
  return `${baseStr.slice(0, 3)}.${baseStr.slice(3, 6)}.${baseStr.slice(6, 9)}-${firstDigit}${secondDigit}`;
}

test.describe('Integration Flow', () => {
  test('TC-020: should complete full user workflow', async ({ page }) => {
    let createdUserId: string | null = null;

    try {
      // Step 1: Create a new user (without picture)
      await page.goto('/');
      await page.locator('button:has-text("Criar Novo Usuário")').click();
      await expect(page.locator('.create-user-modal')).toBeVisible();

      const timestamp = Date.now();
      const testUserId = `test-${timestamp}`;
      const testName = `Integration Test User ${testUserId}`;
      const testCPF = generateValidCPF(timestamp + 4000000); // Generate unique valid CPF
      const testAccount = `${timestamp % 100000}-${timestamp % 10}`;

      // Fill in form first
      await page.fill('#name', testName);
      await page.fill('#cpf', testCPF);
      await page.fill('#accountProvider', 'XP Investimentos');
      await page.fill('#accountNumber', testAccount);
      
      // Trigger CPF validation by blurring to ensure validation runs
      await page.locator('#cpf').blur();
      await page.waitForTimeout(300);
      
      // Verify no CPF error before submitting
      const cpfErrorVisible = await page.locator('.form-group:has(#cpf) .error-message').isVisible().catch(() => false);
      if (cpfErrorVisible) {
        const errorText = await page.locator('.form-group:has(#cpf) .error-message').textContent();
        throw new Error(`CPF validation failed: ${errorText}`);
      }

      // Wait for API response AFTER filling form but BEFORE clicking submit
      // This is the Playwright best practice - set up the listener before the action
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/api/users/') && response.request().method() === 'POST'
      );

      // Now submit
      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();

      // Wait for API response
      const response = await responsePromise;
      if (response.status() !== 201) {
        const errorText = await page.locator('.error-message, .form-error').textContent().catch(() => 'Unknown error');
        throw new Error(`User creation failed: ${errorText}`);
      }

      // Extract user ID from response for cleanup
      const userData = await response.json();
      createdUserId = userData.id;

      await expect(page.locator('.create-user-modal')).not.toBeVisible({ timeout: 10000 });

      // Step 2: Select the user
      await expect(page.locator(`text=${testName}`)).toBeVisible({ timeout: 5000 });
      await page.locator(`text=${testName}`).click();

      // Step 3: Verify portfolio component appears
      await expect(page.locator('app-portfolio')).toBeVisible();

      // Step 4: Navigate to history
      await page.locator('header nav a:has-text("Histórico")').click();
      await expect(page.locator('app-history-list')).toBeVisible();

      // Step 5: Return to portfolio
      await page.locator('header nav a:has-text("Home")').click();
      await expect(page.locator('app-user-list')).toBeVisible();

      // Step 6: Select user again
      await page.locator(`text=Integration Test User ${testUserId}`).click();
      await expect(page.locator('app-portfolio')).toBeVisible();

      // Verify no console errors
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      // Wait a bit to catch any errors
      await page.waitForTimeout(1000);

      // Filter out known non-critical errors if any
      const criticalErrors = errors.filter(e => 
        !e.includes('favicon') && 
        !e.includes('source map')
      );

      expect(criticalErrors.length).toBe(0);
    } finally {
      // Cleanup: Delete test user if it was created
      if (createdUserId) {
        try {
          await page.request.delete(`http://localhost:8000/api/users/${createdUserId}/`);
        } catch (error) {
          // Ignore cleanup errors (user might already be deleted)
          console.warn(`Failed to cleanup test user ${createdUserId}:`, error);
        }
      }
    }
  });
});

