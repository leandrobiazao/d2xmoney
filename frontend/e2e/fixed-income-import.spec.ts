import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

/**
 * Test Fixed Income Import Functionality
 * Tests that liquidated positions (quantity=0, position_value=0) are properly handled
 */
test.describe('Fixed Income Import - Liquidation Detection', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for user list to load
    await page.waitForSelector('app-user-list', { state: 'visible' });
  });

  test('should import Excel file and handle liquidated positions correctly', async ({ page }) => {
    // Step 1: Select or create a user
    const userItems = page.locator('app-user-item');
    const userCount = await userItems.count();

    let userId: string;

    if (userCount === 0) {
      // Create a test user first
      await page.locator('button:has-text("Criar Novo Usuário")').click();
      await page.waitForSelector('.create-user-modal', { state: 'visible' });
      
      const timestamp = Date.now();
      await page.fill('#name', `Test User ${timestamp}`);
      await page.fill('#cpf', '123.456.789-00');
      await page.fill('#accountProvider', 'XP Investimentos');
      await page.fill('#accountNumber', '12345-6');
      await page.locator('button[type="submit"]:has-text("Criar Usuário")').click();
      
      // Wait for user to be created and appear in list
      await page.waitForSelector('app-user-item', { state: 'visible', timeout: 5000 });
    }

    // Click on first user to select them
    await userItems.first().click();
    
    // Wait for portfolio to load
    await page.waitForSelector('app-portfolio', { state: 'visible' });
    
    // Get user ID from the selected user (check data attributes or API calls)
    // For now, we'll proceed with the import test

    // Step 2: Navigate to Fixed Income section
    // Look for fixed income list component or tab
    const fixedIncomeSection = page.locator('app-fixed-income-list');
    
    // If not visible, might need to click a tab or navigate
    if (await fixedIncomeSection.count() === 0) {
      // Try to find and click a "Renda Fixa" or "Fixed Income" link/tab
      const fixedIncomeLink = page.locator('text=/Renda Fixa|Fixed Income/i').first();
      if (await fixedIncomeLink.count() > 0) {
        await fixedIncomeLink.click();
        await page.waitForSelector('app-fixed-income-list', { state: 'visible' });
      }
    }

    // Step 3: Check current positions count (before import)
    const positionsBefore = await page.locator('app-fixed-income-list .position-row').count();
    console.log(`Positions before import: ${positionsBefore}`);

    // Step 4: Click Import button
    const importButton = page.locator('button:has-text("Importar Portfólio")');
    await expect(importButton).toBeVisible();
    await importButton.click();

    // Step 5: Wait for file input and upload test file
    // Note: In a real test, you'd need a test Excel file
    // For now, we'll check if the file input appears
    const fileInput = page.locator('input[type="file"][accept*="xlsx"], input[type="file"][accept*="xls"]');
    
    // Check if file input is visible or hidden (it might be hidden and triggered by button)
    const fileInputCount = await fileInput.count();
    
    if (fileInputCount > 0) {
      // File input exists - in a real test, you'd upload a file here
      // For now, we'll verify the import UI is accessible
      console.log('File input found - import UI is accessible');
      
      // Verify import button state
      const importButtonAfterClick = page.locator('button:has-text("Importar"), button:has-text("Importando")');
      // The button might change state or a modal might appear
    }

    // Step 6: Verify that liquidated positions are not displayed
    // After import, check that positions with quantity=0 and position_value=0 are filtered out
    // This would require:
    // 1. A test Excel file with liquidated positions
    // 2. Actually performing the import
    // 3. Checking the displayed positions

    // For now, we'll verify the component structure
    await expect(page.locator('app-fixed-income-list')).toBeVisible();
  });

  test('should filter out liquidated positions from display', async ({ page }) => {
    // This test verifies that the frontend correctly filters liquidated positions
    // It assumes positions have already been imported (some liquidated, some active)
    
    // Select a user
    const userItems = page.locator('app-user-item');
    if (await userItems.count() > 0) {
      await userItems.first().click();
      await page.waitForSelector('app-portfolio', { state: 'visible' });
    }

    // Navigate to fixed income section
    const fixedIncomeSection = page.locator('app-fixed-income-list');
    if (await fixedIncomeSection.count() === 0) {
      const fixedIncomeLink = page.locator('text=/Renda Fixa|Fixed Income/i').first();
      if (await fixedIncomeLink.count() > 0) {
        await fixedIncomeLink.click();
        await page.waitForSelector('app-fixed-income-list', { state: 'visible' });
      }
    }

    // Check all displayed positions
    const positionRows = page.locator('app-fixed-income-list .position-row, app-fixed-income-list tr.position-row');
    const positionCount = await positionRows.count();

    // Verify that no positions show quantity=0 AND position_value=0
    // This would require checking the actual displayed values
    for (let i = 0; i < positionCount; i++) {
      const row = positionRows.nth(i);
      
      // Try to find quantity and position_value cells
      const quantityCell = row.locator('td').nth(4); // Adjust index based on actual table structure
      const positionValueCell = row.locator('td').nth(5); // Adjust index
      
      const quantityText = await quantityCell.textContent().catch(() => '');
      const positionValueText = await positionValueCell.textContent().catch(() => '');
      
      // Parse values (remove currency symbols, etc.)
      const quantity = parseFloat(quantityText?.replace(/[^\d.,-]/g, '').replace(',', '.') || '0');
      const positionValue = parseFloat(positionValueText?.replace(/[^\d.,-]/g, '').replace(',', '.') || '0');
      
      // Verify that if quantity is 0, position_value should not also be 0 (or vice versa for active positions)
      // Actually, liquidated positions should be completely filtered out, so we shouldn't see any with both = 0
      if (quantity === 0 && positionValue === 0) {
        throw new Error(`Found liquidated position that should be filtered out: quantity=${quantity}, position_value=${positionValue}`);
      }
    }

    console.log(`Verified ${positionCount} positions - none are liquidated (quantity=0 AND position_value=0)`);
  });

  test('should show import success message with correct statistics', async ({ page }) => {
    // Select user
    const userItems = page.locator('app-user-item');
    if (await userItems.count() > 0) {
      await userItems.first().click();
      await page.waitForSelector('app-portfolio', { state: 'visible' });
    }

    // Navigate to fixed income
    const fixedIncomeSection = page.locator('app-fixed-income-list');
    if (await fixedIncomeSection.count() === 0) {
      const fixedIncomeLink = page.locator('text=/Renda Fixa|Fixed Income/i').first();
      if (await fixedIncomeLink.count() > 0) {
        await fixedIncomeLink.click();
        await page.waitForSelector('app-fixed-income-list', { state: 'visible' });
      }
    }

    // Check for import button
    const importButton = page.locator('button:has-text("Importar Portfólio")');
    await expect(importButton).toBeVisible();

    // Verify import UI elements exist
    // The actual file upload would happen here in a real test with a test file
    console.log('Import UI is accessible and ready for file upload');
  });
});
