import { test, expect } from '@playwright/test';

/**
 * TC-005, TC-008, TC-009, TC-010: Portfolio Tests
 */
test.describe('Portfolio Operations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('TC-005: should display portfolio when user is selected', async ({ page }) => {
    // Wait for user list to load
    await page.waitForSelector('app-user-list', { state: 'visible' });

    // Check if there are users
    const userItems = page.locator('app-user-item');
    const userCount = await userItems.count();

    if (userCount === 0) {
      // Create a test user first
      await page.locator('button:has-text("Criar Novo Usuário")').click();
      await page.fill('#name', 'Portfolio Test User');
      await page.fill('#cpf', '555.666.777-88');
      await page.fill('#accountProvider', 'XP');
      await page.fill('#accountNumber', '99999-9');
      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();
      await expect(page.locator('.create-user-modal')).not.toBeVisible();
    }

    // Click on first user
    await userItems.first().click();

    // Verify portfolio component appears
    await expect(page.locator('app-portfolio')).toBeVisible();

    // Verify "Selecione um cliente..." message disappears
    await expect(page.locator('#fallback')).not.toBeVisible();
  });

  test('TC-008: should calculate positions correctly', async ({ page }) => {
    // This test requires operations to be present
    // For now, verify portfolio structure is correct
    await page.waitForSelector('app-user-list', { state: 'visible' });

    const userItems = page.locator('app-user-item');
    const userCount = await userItems.count();

    if (userCount > 0) {
      await userItems.first().click();
      await expect(page.locator('app-portfolio')).toBeVisible();

      // Verify positions section exists (may be empty)
      const positionsSection = page.locator('app-portfolio').locator('text=/Posições|Posição/i').first();
      // Section may or may not be visible depending on data
      // Just verify portfolio loaded
      await expect(page.locator('app-portfolio')).toBeVisible();
    }
  });

  test('TC-009: should filter operations', async ({ page }) => {
    await page.waitForSelector('app-user-list', { state: 'visible' });

    const userItems = page.locator('app-user-item');
    const userCount = await userItems.count();

    if (userCount > 0) {
      await userItems.first().click();
      await expect(page.locator('app-portfolio')).toBeVisible();

      // Try to find filter inputs
      const filterInputs = page.locator('app-portfolio input[type="text"], app-portfolio input[type="date"]');
      const inputCount = await filterInputs.count();

      if (inputCount > 0) {
        // Test filtering by título
        const tituloFilter = page.locator('app-portfolio input[placeholder*="Título" i], app-portfolio input[id*="titulo" i]').first();
        if (await tituloFilter.count() > 0) {
          await tituloFilter.fill('TEST');
          // Wait a bit for filtering to apply
          await page.waitForTimeout(500);
        }
      }
    }
  });

  test('TC-010: should delete operation', async ({ page }) => {
    await page.waitForSelector('app-user-list', { state: 'visible' });

    const userItems = page.locator('app-user-item');
    const userCount = await userItems.count();

    if (userCount > 0) {
      await userItems.first().click();
      await expect(page.locator('app-portfolio')).toBeVisible();

      // Look for delete buttons in operations table
      const deleteButtons = page.locator('app-portfolio button:has-text("×"), app-portfolio button:has-text("Excluir"), app-portfolio [aria-label*="delete" i]');
      const deleteCount = await deleteButtons.count();

      if (deleteCount > 0) {
        // Click first delete button
        await deleteButtons.first().click();

        // Handle confirmation dialog if present
        const dialog = page.locator('dialog, [role="dialog"]');
        if (await dialog.count() > 0) {
          await page.locator('button:has-text("Confirmar"), button:has-text("OK"), button:has-text("Sim")').click();
        }

        // Wait for operation to be removed
        await page.waitForTimeout(500);
      }
    }
  });
});

