# Testing Guide - d2xmoney

This guide provides comprehensive information about testing in the d2xmoney portfolio management system.

## Table of Contents

1. [Overview](#overview)
2. [Unit Tests](#unit-tests)
3. [E2E Tests](#e2e-tests)
4. [Running Tests](#running-tests)
5. [Writing New Tests](#writing-new-tests)
6. [Test Structure](#test-structure)
7. [Debugging Tests](#debugging-tests)

## Overview

The d2xmoney project uses two main testing frameworks:

- **Unit Tests**: Jasmine/Karma (Angular default)
- **E2E Tests**: Playwright

### Test Coverage

- **Unit Tests**: Services, utilities, and components
- **E2E Tests**: Complete user workflows and integration scenarios

## Unit Tests

### Location

Unit tests are located alongside the source files with the `.spec.ts` extension:

```
frontend/src/app/
├── shared/
│   └── utils/
│       ├── cpf-validator.ts
│       └── cpf-validator.spec.ts
├── users/
│   ├── user.service.ts
│   └── user.service.spec.ts
└── ...
```

### Running Unit Tests

```bash
cd frontend
npm test
```

### Running with Coverage

```bash
cd frontend
npm run test:coverage
```

Coverage reports will be generated in `frontend/coverage/`.

### Writing Unit Tests

#### Service Tests

Example: `user.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { UserService } from './user.service';

describe('UserService', () => {
  let service: UserService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [UserService]
    });
    service = TestBed.inject(UserService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('should get users', () => {
    // Test implementation
  });
});
```

#### Utility Tests

Example: `cpf-validator.spec.ts`

```typescript
import { validateCPF, formatCPF } from './cpf-validator';

describe('CPF Validator', () => {
  it('should validate correct CPF', () => {
    expect(validateCPF('123.456.789-00')).toBe(true);
  });
});
```

## E2E Tests

### Location

E2E tests are located in `frontend/e2e/`:

```
frontend/e2e/
├── app.spec.ts              # Application load and navigation
├── users.spec.ts            # User management
├── portfolio.spec.ts        # Portfolio operations
├── brokerage-notes.spec.ts # PDF upload and processing
├── history.spec.ts         # Brokerage history
├── integration.spec.ts     # Complete workflows
└── ui-ux.spec.ts           # UI/UX features
```

### Prerequisites

Before running E2E tests, ensure:

1. **Frontend server** is running on `http://localhost:4400`
2. **Backend server** is running on `http://localhost:8000`

### Running E2E Tests

#### Run all E2E tests

```bash
cd frontend
npm run e2e
```

#### Run with UI (interactive mode)

```bash
cd frontend
npm run e2e:ui
```

This opens Playwright's interactive UI where you can:
- See all tests
- Run individual tests
- Debug tests step by step
- View test results

#### Run in headed mode (see browser)

```bash
cd frontend
npm run e2e:headed
```

#### Run in debug mode

```bash
cd frontend
npm run e2e:debug
```

This opens Playwright Inspector for step-by-step debugging.

### Test Configuration

E2E tests are configured in `frontend/playwright.config.ts`:

- **Base URL**: `http://localhost:4400`
- **Browser**: Chromium
- **Test Directory**: `frontend/e2e/`
- **Screenshots**: Captured on failure
- **Traces**: Collected on retry

### E2E Test Structure

Each test file follows this structure:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should do something', async ({ page }) => {
    // Test steps
    await expect(page.locator('selector')).toBeVisible();
  });
});
```

## Running Tests

### Run All Tests

```bash
cd frontend
npm run test:all
```

This runs both unit tests and E2E tests sequentially.

### Individual Test Commands

| Command | Description |
|---------|-------------|
| `npm test` | Run unit tests |
| `npm run test:coverage` | Run unit tests with coverage |
| `npm run e2e` | Run E2E tests |
| `npm run e2e:ui` | Run E2E tests with UI |
| `npm run e2e:headed` | Run E2E tests in headed mode |
| `npm run e2e:debug` | Run E2E tests in debug mode |
| `npm run test:all` | Run all tests |

## Writing New Tests

### Adding Unit Tests

1. Create a `.spec.ts` file next to your source file
2. Import necessary testing utilities
3. Write test cases using `describe` and `it`
4. Use Angular testing utilities for components/services

Example:

```typescript
import { TestBed } from '@angular/core/testing';
import { MyService } from './my.service';

describe('MyService', () => {
  let service: MyService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(MyService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
```

### Adding E2E Tests

1. Create or edit a test file in `frontend/e2e/`
2. Use Playwright's `test` and `expect` functions
3. Follow the existing test patterns
4. Use descriptive test names

Example:

```typescript
import { test, expect } from '@playwright/test';

test.describe('New Feature', () => {
  test('should work correctly', async ({ page }) => {
    await page.goto('/');
    // Test steps
    await expect(page.locator('selector')).toBeVisible();
  });
});
```

## Test Structure

### Unit Test Structure

```
describe('Component/Service Name', () => {
  beforeEach(() => {
    // Setup
  });

  describe('Feature Group', () => {
    it('should do something specific', () => {
      // Test
    });
  });
});
```

### E2E Test Structure

```
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup
  });

  test('TC-XXX: should do something', async ({ page }) => {
    // Test steps with assertions
  });
});
```

## Debugging Tests

### Unit Tests

1. Use `console.log()` for debugging
2. Use breakpoints in your IDE
3. Run tests in watch mode: `ng test --watch`

### E2E Tests

#### Using Playwright Inspector

```bash
npm run e2e:debug
```

This opens Playwright Inspector where you can:
- Step through tests
- Inspect page state
- View console logs
- Take screenshots

#### Using UI Mode

```bash
npm run e2e:ui
```

Interactive UI for:
- Running individual tests
- Viewing test results
- Debugging specific scenarios

#### Console Logging

Add console logs in your tests:

```typescript
test('should debug', async ({ page }) => {
  await page.goto('/');
  console.log('Current URL:', page.url());
  const text = await page.locator('selector').textContent();
  console.log('Found text:', text);
});
```

#### Screenshots

Screenshots are automatically captured on test failure. They are saved in `frontend/test-results/`.

To take manual screenshots:

```typescript
await page.screenshot({ path: 'screenshot.png' });
```

## Test Data

### E2E Test Data

E2E tests use the actual backend API. Ensure:
- Backend is running
- Test data is available or tests create their own
- Tests clean up after themselves when possible

### Unit Test Data

Unit tests use mocked data:
- HTTP requests are mocked using `HttpTestingController`
- Services are tested in isolation
- No actual API calls are made

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Descriptive Names**: Use clear, descriptive test names
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Avoid Flakiness**: Use proper waits and assertions
5. **Clean Up**: Remove test data when possible
6. **Coverage**: Aim for good coverage of critical paths
7. **Maintainability**: Keep tests simple and readable

## Troubleshooting

### E2E Tests Failing

1. **Check servers**: Ensure frontend and backend are running
2. **Check selectors**: Verify element selectors are correct
3. **Add waits**: Use `waitForSelector` for dynamic content
4. **Check console**: Look for JavaScript errors
5. **Use headed mode**: Run with `--headed` to see what's happening

### Unit Tests Failing

1. **Check imports**: Ensure all dependencies are imported
2. **Check mocks**: Verify mocks are set up correctly
3. **Check async**: Use `async/await` or `done()` for async tests
4. **Check fixtures**: Ensure test data is correct

## Additional Resources

- [Playwright Documentation](https://playwright.dev/)
- [Angular Testing Guide](https://angular.dev/guide/testing)
- [Jasmine Documentation](https://jasmine.github.io/)
- [E2E Test Plan](./e2e-test-plan.md)

---

**Last Updated**: November 2025

