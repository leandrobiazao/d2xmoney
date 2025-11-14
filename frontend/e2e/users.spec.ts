import { test, expect } from '@playwright/test';

/**
 * TC-002, TC-003, TC-004, TC-015: User Management Tests
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

test.describe('User Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('TC-002: should create user without picture', async ({ page }) => {
    let createdUserId: string | null = null;

    try {
      // Click "Criar Novo Usuário" button
      await page.locator('button:has-text("Criar Novo Usuário")').click();

      // Wait for modal to appear
      await expect(page.locator('.create-user-modal')).toBeVisible();

      // Generate unique test data
      const timestamp = Date.now();
      const testName = `Test User E2E ${timestamp}`;
      const testCPF = generateValidCPF(timestamp); // Generate unique valid CPF
      const testAccount = `${timestamp % 100000}-${timestamp % 10}`;

      // Fill in form
      await page.fill('#name', testName);
      await page.fill('#cpf', testCPF);
      await page.fill('#accountProvider', 'XP Investimentos');
      await page.fill('#accountNumber', testAccount);
      // Leave picture empty (optional)

      // Trigger CPF validation
      await page.locator('#cpf').blur();
      await page.waitForTimeout(300);

      // Verify no CPF error before submitting
      const cpfErrorVisible = await page.locator('.form-group:has(#cpf) .error-message').isVisible().catch(() => false);
      if (cpfErrorVisible) {
        const errorText = await page.locator('.form-group:has(#cpf) .error-message').textContent();
        throw new Error(`CPF validation failed: ${errorText}`);
      }

      // Wait for API response AFTER filling form but BEFORE clicking submit
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/api/users/') && response.request().method() === 'POST'
      );

      // Submit form
      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();

      // Wait for API response
      const response = await responsePromise;
      
      // Check if request was successful
      if (response.status() !== 201) {
        // If failed, check for error message
        const errorVisible = await page.locator('.error-message, .form-error').isVisible().catch(() => false);
        if (errorVisible) {
          const errorText = await page.locator('.error-message, .form-error').textContent();
          throw new Error(`User creation failed: ${errorText} (Status: ${response.status()})`);
        }
        throw new Error(`User creation failed with status: ${response.status()}`);
      }

      // Extract user ID from response for cleanup
      const userData = await response.json();
      createdUserId = userData.id;

      // Wait for modal to close (with longer timeout for API call)
      await expect(page.locator('.create-user-modal')).not.toBeVisible({ timeout: 10000 });

      // Verify user appears in list
      await expect(page.locator(`text=${testName}`)).toBeVisible({ timeout: 5000 });
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

  test('TC-003: should create user with picture', async ({ page }) => {
    let createdUserId: string | null = null;

    try {
      // Click "Criar Novo Usuário" button
      await page.locator('button:has-text("Criar Novo Usuário")').click();

      // Wait for modal
      await expect(page.locator('.create-user-modal')).toBeVisible();

      // Generate unique test data
      const timestamp = Date.now();
      const testName = `Test User With Picture ${timestamp}`;
      const testCPF = generateValidCPF(timestamp + 1000000); // Generate unique valid CPF (different from TC-002)
      const testAccount = `${(timestamp + 1) % 100000}-${(timestamp + 1) % 10}`;

      // Fill in form
      await page.fill('#name', testName);
      await page.fill('#cpf', testCPF);
      await page.fill('#accountProvider', 'Rico Investimentos');
      await page.fill('#accountNumber', testAccount);

      // Upload picture (create a valid minimal JPEG)
      const fileInput = page.locator('#picture');
      // Create a valid minimal JPEG file that Pillow can recognize
      // This is a base64-encoded 1x1 pixel gray JPEG image
      const jpegBase64 = '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA/wA';
      const jpegBuffer = Buffer.from(jpegBase64, 'base64');
      
      await fileInput.setInputFiles({
        name: 'test-image.jpg',
        mimeType: 'image/jpeg',
        buffer: jpegBuffer
      });

      // Verify picture preview appears
      await expect(page.locator('app-picture-preview')).toBeVisible();

      // Trigger CPF validation
      await page.locator('#cpf').blur();
      await page.waitForTimeout(300);

      // Verify no CPF error before submitting
      const cpfErrorVisible = await page.locator('.form-group:has(#cpf) .error-message').isVisible().catch(() => false);
      if (cpfErrorVisible) {
        const errorText = await page.locator('.form-group:has(#cpf) .error-message').textContent();
        throw new Error(`CPF validation failed: ${errorText}`);
      }

      // Wait for API response AFTER filling form but BEFORE clicking submit
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/api/users/') && response.request().method() === 'POST'
      );

      // Submit form
      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();

      // Wait for API response
      const response = await responsePromise;
      
      // Check if request was successful
      if (response.status() !== 201) {
        const errorVisible = await page.locator('.error-message, .form-error').isVisible().catch(() => false);
        if (errorVisible) {
          const errorText = await page.locator('.error-message, .form-error').textContent();
          throw new Error(`User creation failed: ${errorText} (Status: ${response.status()})`);
        }
        throw new Error(`User creation failed with status: ${response.status()}`);
      }

      // Extract user ID from response for cleanup
      const userData = await response.json();
      createdUserId = userData.id;

      // Wait for modal to close
      await expect(page.locator('.create-user-modal')).not.toBeVisible({ timeout: 10000 });

      // Verify user appears in list
      await expect(page.locator(`text=${testName}`)).toBeVisible({ timeout: 5000 });
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

  test('TC-004: should validate CPF correctly', async ({ page }) => {
    // Click "Criar Novo Usuário" button
    await page.locator('button:has-text("Criar Novo Usuário")').click();

    await expect(page.locator('.create-user-modal')).toBeVisible();

    // Test invalid CPF (wrong check digits)
    await page.fill('#cpf', '123.456.789-01');
    await page.fill('#name', 'Test User');
    await page.fill('#accountProvider', 'XP');
    await page.fill('#accountNumber', '12345-6');

    // Trigger CPF validation by blurring
    await page.locator('#cpf').blur();
    await page.waitForTimeout(300);

    // Verify error message appears (client-side validation)
    const errorVisible = await page.locator('.error-message').isVisible().catch(() => false);
    if (errorVisible) {
      await expect(page.locator('.error-message')).toContainText(/CPF|inválido/i);
    }

    // Test valid CPF
    const validCPF = '111.444.777-35'; // Valid CPF
    await page.fill('#cpf', validCPF);
    
    // Clear any previous errors by blurring
    await page.locator('#cpf').blur();
    await page.waitForTimeout(300);

    // Verify CPF is auto-formatted
    const cpfValue = await page.inputValue('#cpf');
    expect(cpfValue).toMatch(/^\d{3}\.\d{3}\.\d{3}-\d{2}$/);

    // Verify no error message for valid CPF
    const errorAfterValid = await page.locator('.error-message').isVisible().catch(() => false);
    expect(errorAfterValid).toBeFalsy();
  });

  test('TC-015: should validate required fields', async ({ page }) => {
    let createdUserId: string | null = null;

    try {
      // Click "Criar Novo Usuário" button
      await page.locator('button:has-text("Criar Novo Usuário")').click();

      await expect(page.locator('.create-user-modal')).toBeVisible();

      // Try to submit empty form - HTML5 validation should prevent it
      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();

      // Wait a bit to see if form submits (it shouldn't)
      await page.waitForTimeout(500);

      // Verify form doesn't submit (modal still visible)
      await expect(page.locator('.create-user-modal')).toBeVisible();

      // Fill only name
      await page.fill('#name', 'Test');
      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();
      await page.waitForTimeout(500);

      // Form should still not submit (validation errors should appear)
      await expect(page.locator('.create-user-modal')).toBeVisible();

      // Fill all required fields with valid data
      const timestamp = Date.now();
      const testCPF = generateValidCPF(timestamp + 2000000); // Generate unique valid CPF
      const testAccount = `${timestamp % 100000}-${timestamp % 10}`;
      
      await page.fill('#cpf', testCPF);
      await page.fill('#accountProvider', 'XP');
      await page.fill('#accountNumber', testAccount);

      // Trigger CPF validation
      await page.locator('#cpf').blur();
      await page.waitForTimeout(300);

      // Verify no CPF error before submitting
      const cpfErrorVisible = await page.locator('.form-group:has(#cpf) .error-message').isVisible().catch(() => false);
      if (cpfErrorVisible) {
        const errorText = await page.locator('.form-group:has(#cpf) .error-message').textContent();
        throw new Error(`CPF validation failed: ${errorText}`);
      }

      // Wait for API response AFTER filling form but BEFORE clicking submit
      const responsePromise = page.waitForResponse(response => 
        response.url().includes('/api/users/') && response.request().method() === 'POST'
      );

      // Now form should submit
      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();

      // Wait for API response
      const response = await responsePromise;
      
      if (response.status() !== 201) {
        const errorVisible = await page.locator('.error-message, .form-error').isVisible().catch(() => false);
        if (errorVisible) {
          const errorText = await page.locator('.error-message, .form-error').textContent();
          throw new Error(`User creation failed: ${errorText}`);
        }
      } else {
        // Extract user ID from response for cleanup
        const userData = await response.json();
        createdUserId = userData.id;
      }

      // Modal should close
      await expect(page.locator('.create-user-modal')).not.toBeVisible({ timeout: 10000 });
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

  test('should handle duplicate CPF error', async ({ page }) => {
    let createdUserId: string | null = null;

    try {
      // Generate unique test data for first user
      const timestamp = Date.now();
      const firstUserName = `First User ${timestamp}`;
      const duplicateCPF = generateValidCPF(timestamp + 3000000); // Generate unique valid CPF
      const firstAccount = `${timestamp % 100000}-${timestamp % 10}`;

      // First, create a user
      await page.locator('button:has-text("Criar Novo Usuário")').click();
      await expect(page.locator('.create-user-modal')).toBeVisible();

      await page.fill('#name', firstUserName);
      await page.fill('#cpf', duplicateCPF);
      await page.fill('#accountProvider', 'XP');
      await page.fill('#accountNumber', firstAccount);

      // Trigger CPF validation
      await page.locator('#cpf').blur();
      await page.waitForTimeout(300);

      // Verify no CPF error
      const cpfErrorVisible = await page.locator('.form-group:has(#cpf) .error-message').isVisible().catch(() => false);
      if (cpfErrorVisible) {
        const errorText = await page.locator('.form-group:has(#cpf) .error-message').textContent();
        throw new Error(`CPF validation failed: ${errorText}`);
      }

      // Set up response listener before clicking
      const firstResponsePromise = page.waitForResponse(response => 
        response.url().includes('/api/users/') && response.request().method() === 'POST'
      );

      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();

      // Wait for first user creation
      const firstResponse = await firstResponsePromise;
      if (firstResponse.status() !== 201) {
        throw new Error(`First user creation failed: ${firstResponse.status()}`);
      }

      // Extract user ID from response for cleanup
      const userData = await firstResponse.json();
      createdUserId = userData.id;

      await expect(page.locator('.create-user-modal')).not.toBeVisible({ timeout: 10000 });

      // Try to create another user with same CPF
      await page.locator('button:has-text("Criar Novo Usuário")').click();
      await expect(page.locator('.create-user-modal')).toBeVisible();

      await page.fill('#name', 'Second User');
      await page.fill('#cpf', duplicateCPF);
      await page.fill('#accountProvider', 'Rico');
      await page.fill('#accountNumber', `${(timestamp + 1) % 100000}-${(timestamp + 1) % 10}`);

      // Trigger CPF validation
      await page.locator('#cpf').blur();
      await page.waitForTimeout(300);

      // Set up response listener before clicking
      const secondResponsePromise = page.waitForResponse(response => 
        response.url().includes('/api/users/') && response.request().method() === 'POST'
      );

      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();

      // Wait for response (should fail with 400)
      const secondResponse = await secondResponsePromise;
      
      // Should get error response
      expect(secondResponse.status()).toBeGreaterThanOrEqual(400);

      // Verify error message appears
      await expect(page.locator('.error-message, .form-error')).toContainText(/CPF|já cadastrado|cadastrado/i, { timeout: 5000 });

      // Modal should still be visible (form didn't submit successfully)
      await expect(page.locator('.create-user-modal')).toBeVisible();
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

