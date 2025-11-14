import { test, expect } from '@playwright/test';

/**
 * TC-001: Application Load and Title Verification
 */
test.describe('Application Load', () => {
  test('should load application with correct title and header', async ({ page }) => {
    // Navigate to application
    await page.goto('/');

    // Verify page title
    await expect(page).toHaveTitle('D2X Money Manager');

    // Verify header displays correct branding
    const header = page.locator('header');
    await expect(header).toBeVisible();
    await expect(header.locator('h1')).toContainText('Portfolio Management System');

    // Verify navigation links are visible
    const navLinks = page.locator('header nav a');
    await expect(navLinks).toHaveCount(3);
    await expect(navLinks.nth(0)).toContainText('Home');
    await expect(navLinks.nth(1)).toContainText('Histórico');
    await expect(navLinks.nth(2)).toContainText('Clube do Valor');
  });

  test('should navigate to history page', async ({ page }) => {
    await page.goto('/');

    // Click Histórico link
    await page.locator('header nav a:has-text("Histórico")').click();

    // Verify history component is displayed
    await expect(page.locator('app-history-list')).toBeVisible();
  });

  test('should navigate to home page', async ({ page }) => {
    await page.goto('/');

    // Navigate to history first
    await page.locator('header nav a:has-text("Histórico")').click();
    await expect(page.locator('app-history-list')).toBeVisible();

    // Navigate back to home
    await page.locator('header nav a:has-text("Home")').click();

    // Verify user list is displayed
    await expect(page.locator('app-user-list')).toBeVisible();
  });
});

