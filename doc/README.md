# d2xmoney - Documentation

Welcome to the d2xmoney portfolio management system documentation repository.

## 📁 Documentation Structure

```
doc/
└── spec/
    ├── README.md                              # Documentation overview
    ├── SUMMARY.md                             # Quick test summary
    ├── e2e-test-plan.md                       # E2E test plan
    ├── e2e-test-results*.md                     # E2E test results
    ├── test-specification.md                  # Complete test specification (main document)
    ├── 01-user-management.md                 # User management specification
    ├── 02-brokerage-note-processing.md        # Brokerage note processing specification
    ├── 03-brokerage-history.md               # Brokerage history specification
    ├── 04-portfolio-summary.md               # Portfolio summary specification
    ├── 05-clube-do-valor-redesign.md         # Clube do Valor redesign specification
    ├── 06-home-page-design-system.md         # Home page design system
    ├── 07-clube-do-valor-redesign-implementation.md  # Implementation details
    ├── 08-history-redesign-implementation.md # History redesign implementation
    └── TESTING.md                            # Testing guide
```

## 🚀 Quick Start

1. **View Test Summary**: Open [`spec/SUMMARY.md`](spec/SUMMARY.md) for a quick overview
2. **E2E Test Plan**: Read [`spec/e2e-test-plan.md`](spec/e2e-test-plan.md) for complete E2E test scenarios
3. **Testing Guide**: Read [`spec/TESTING.md`](spec/TESTING.md) for testing instructions
4. **Full Specifications**: Browse individual specification files for detailed feature documentation

## ✅ Test Results

**Status**: Tests available via Playwright E2E automation  
**Test Framework**: Playwright  
**Frontend URL**: http://localhost:4400  
**Backend URL**: http://localhost:8000  

## 📋 Test Coverage

The application includes comprehensive E2E test coverage for:

- **User Management** (TC-002, TC-003, TC-004, TC-015)
  - User creation (with/without picture)
  - CPF validation
  - Form validation
  
- **Portfolio Operations** (TC-005, TC-008, TC-009, TC-010)
  - User selection and portfolio display
  - Position calculations
  - Operation filtering
  - Operation deletion
  
- **Brokerage Note Processing** (TC-006, TC-007)
  - PDF upload and processing
  - Ticker mapping dialog
  
- **History Management** (TC-011, TC-012, TC-013, TC-014)
  - Navigation to history
  - History list display
  - Note detail view
  - Note deletion
  
- **UI/UX** (TC-016, TC-017, TC-018, TC-019)
  - Error handling
  - Responsive design
  - Currency formatting
  - Empty states
  
- **Integration Flows** (TC-020)
  - Complete end-to-end workflows

## 🎯 Application Features

### Core Features
✅ User management with CPF validation  
✅ Portfolio tracking and calculations  
✅ Brokerage note PDF processing  
✅ Ticker mapping and management  
✅ Brokerage history tracking  
✅ Clube do Valor stock recommendations  
✅ Responsive design  
✅ Currency formatting (BRL)  

## 🛠️ Testing Tools

- **Framework**: [Playwright](https://playwright.dev/)
- **Unit Testing**: Jasmine/Karma (Angular)
- **E2E Testing**: Playwright
- **Browser**: Chromium
- **Configuration**: `playwright.config.ts`

## 📖 Documentation Files

### Primary Documents
- **[e2e-test-plan.md](spec/e2e-test-plan.md)** - Complete E2E test plan with 20 test cases
- **[TESTING.md](spec/TESTING.md)** - Comprehensive testing guide
- **[README.md](spec/README.md)** - Specification documentation overview

### Feature Specifications
- **[01-user-management.md](spec/01-user-management.md)** - User management specification
- **[02-brokerage-note-processing.md](spec/02-brokerage-note-processing.md)** - Brokerage note processing
- **[03-brokerage-history.md](spec/03-brokerage-history.md)** - Brokerage history
- **[04-portfolio-summary.md](spec/04-portfolio-summary.md)** - Portfolio summary
- **[05-clube-do-valor-redesign.md](spec/05-clube-do-valor-redesign.md)** - Clube do Valor redesign
- **[06-home-page-design-system.md](spec/06-home-page-design-system.md)** - Home page design
- **[07-clube-do-valor-redesign-implementation.md](spec/07-clube-do-valor-redesign-implementation.md)** - Implementation details
- **[08-history-redesign-implementation.md](spec/08-history-redesign-implementation.md)** - History redesign

## 📊 Application Environment

```
Application:  d2xmoney (Angular 20.1.0)
Frontend URL: http://localhost:4400
Backend URL:  http://localhost:8000
Framework:    Playwright for E2E, Jasmine/Karma for unit tests
Platform:     Windows 10
Browser:      Chromium (via Playwright)
```

## 🎉 Getting Started

For detailed information about running tests, see the [testing guide](spec/TESTING.md).

For feature specifications, browse the individual specification files in the `spec/` directory.

---

**Last Updated**: November 2025  
**Test Execution**: Automated via Playwright E2E tests
