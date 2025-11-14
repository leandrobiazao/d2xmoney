import { FullConfig } from '@playwright/test';
import { chromium } from '@playwright/test';

/**
 * Global teardown function that runs after all tests complete.
 * Cleans up all test data created during test execution.
 */
async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting global teardown: Cleaning up test data...');

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Use the API to fetch and delete all test users
    const apiBaseUrl = 'http://localhost:8000';
    const usersUrl = `${apiBaseUrl}/api/users/`;

    // Fetch all users using Playwright's request API
    const response = await page.request.get(usersUrl);
    
    if (!response.ok()) {
      console.warn('⚠️  Could not fetch users for cleanup:', response.statusText());
      return;
    }

    const users: Array<{ id: string; name: string }> = await response.json();

    // Identify test users by naming patterns
    const testUserPatterns = [
      /^Test User/i,
      /^Integration Test User/i,
      /^PDF Test User/i,
      /^First User/i,
      /^Second User/i,
      /^Test$/i,
    ];

    const testUsers = users.filter(user => 
      testUserPatterns.some(pattern => pattern.test(user.name))
    );

    if (testUsers.length === 0) {
      console.log('✅ No test users found to clean up');
      return;
    }

    console.log(`🗑️  Found ${testUsers.length} test user(s) to delete`);

    // Delete each test user
    let deletedCount = 0;
    let failedCount = 0;

    for (const user of testUsers) {
      try {
        const deleteResponse = await page.request.delete(`${apiBaseUrl}/api/users/${user.id}/`);

        // DELETE typically returns 204 No Content on success
        if (deleteResponse.status() === 204 || deleteResponse.status() === 200) {
          deletedCount++;
          console.log(`  ✓ Deleted: ${user.name} (${user.id})`);
        } else {
          const responseText = await deleteResponse.text().catch(() => '');
          failedCount++;
          console.warn(`  ✗ Failed to delete: ${user.name} (${user.id}) - Status: ${deleteResponse.status()}, Response: ${responseText}`);
        }
      } catch (error: any) {
        failedCount++;
        console.warn(`  ✗ Error deleting ${user.name} (${user.id}):`, error?.message || error);
      }
    }

    console.log(`✅ Global teardown complete: ${deletedCount} deleted, ${failedCount} failed`);
  } catch (error) {
    console.error('❌ Error during global teardown:', error);
  } finally {
    await browser.close();
  }
}

export default globalTeardown;

