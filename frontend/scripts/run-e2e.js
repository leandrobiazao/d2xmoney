#!/usr/bin/env node

/**
 * Wrapper script to run Playwright tests with suppressed warnings
 */
process.env.NODE_OPTIONS = '--no-warnings';

// Remove NO_COLOR if FORCE_COLOR is set to avoid the warning
if (process.env.FORCE_COLOR) {
  delete process.env.NO_COLOR;
}

// Import and run playwright
const { spawn } = require('child_process');
const args = process.argv.slice(2);

const playwright = spawn('npx', ['playwright', 'test', ...args], {
  stdio: 'inherit',
  shell: true
});

playwright.on('close', (code) => {
  process.exit(code || 0);
});

