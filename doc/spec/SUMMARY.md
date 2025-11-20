# Documentation Summary - d2xmoney Portfolio Management System

## Overview

This directory contains comprehensive documentation for the d2xmoney Portfolio Management System, a full-stack application for managing investment portfolios, processing B3 brokerage notes, and tracking investment positions.

## Project Structure

The system consists of:
- **11 Django backend apps** providing REST API services
- **Multiple Angular frontend components** for user interaction
- **SQLite database** for data persistence
- **Comprehensive E2E testing** with Playwright

## Documentation Files

### Core Application Specifications

1. **[01-user-management.md](01-user-management.md)** - User Management
   - User CRUD operations
   - CPF validation
   - Profile picture management
   - Database storage

2. **[02-brokerage-note-processing.md](02-brokerage-note-processing.md)** - Brokerage Note Processing
   - PDF parsing from B3 brokerage notes
   - Ticker mapping
   - Operation extraction
   - Upload component

3. **[03-brokerage-history.md](03-brokerage-history.md)** - Brokerage History
   - History tracking
   - Processed notes display
   - Search and filter
   - Note metadata

4. **[04-portfolio-summary.md](04-portfolio-summary.md)** - Portfolio Summary
   - Position calculations (FIFO method)
   - Operations display
   - Filters and analytics
   - Portfolio service

5. **[05-clube-do-valor-redesign.md](05-clube-do-valor-redesign.md)** - Clube do Valor
   - Stock recommendations
   - Monthly snapshots
   - Strategy-based filtering
   - Google Sheets integration

### Configuration & Catalog Specifications

6. **[10-configuration.md](10-configuration.md)** - Investment Configuration
   - Investment types management
   - Investment sub-types management
   - Excel import functionality
   - Type classification

7. **[11-stocks.md](11-stocks.md)** - Stock Catalog
   - Stock master catalog
   - Ticker management
   - Price updates (yfinance integration)
   - Stock classification

8. **[15-ticker-mappings.md](15-ticker-mappings.md)** - Ticker Mappings
   - Company name to ticker mapping
   - Mapping management
   - Integration with brokerage note processing

### Portfolio Management Specifications

9. **[12-allocation-strategies.md](12-allocation-strategies.md)** - Allocation Strategies
   - User allocation strategies
   - Investment type allocations
   - Sub-type allocations
   - Stock-specific allocations

10. **[13-rebalancing.md](13-rebalancing.md)** - Rebalancing
    - Rebalancing recommendations
    - Recommendation generation
    - Action tracking
    - Status management

11. **[14-fixed-income.md](14-fixed-income.md)** - Fixed Income
    - Fixed income positions
    - CDB management
    - Tesouro Direto tracking
    - Portfolio import from Excel

### Database & Testing

12. **[09-database-data-model.md](09-database-data-model.md)** - Database Schema
    - Complete database model documentation
    - Entity relationships
    - Field specifications
    - Constraints and validations
    - 18 models across 11 Django apps

13. **[TESTING.md](TESTING.md)** - Testing Guide
    - Unit testing (Jasmine/Karma)
    - E2E testing (Playwright)
    - Test structure
    - Debugging guides

### Main Documentation

- **[README.md](README.md)** - Main specification document
  - Project overview
  - Technology stack
  - Project structure
  - API endpoints overview
  - Setup instructions

## Key Features

### Portfolio Management
- User account management with CPF validation
- B3 brokerage note PDF processing
- Portfolio position tracking with FIFO calculation
- Fixed income investment tracking
- Stock catalog management

### Investment Strategy
- Allocation strategy definition
- Rebalancing recommendations
- AMBB strategy integration
- Investment type classification

### Data Management
- SQLite database for all data
- Excel import for fixed income positions
- Google Sheets integration for Clube do Valor
- Ticker mapping system

## Technology Stack

### Frontend
- Angular 20.1.0
- TypeScript 5.8.2
- Standalone components
- Modern Angular syntax

### Backend
- Django 5.0+
- Django REST Framework 3.14.0+
- SQLite 3 (development)
- Python 3.10+

### Key Dependencies
- pdfjs-dist (PDF parsing)
- yfinance (stock prices)
- openpyxl (Excel handling)
- beautifulsoup4 (HTML parsing)
- Playwright (E2E testing)

## API Endpoints

The system provides REST APIs for:
- User management
- Brokerage note processing
- Portfolio operations
- Stock catalog
- Investment configuration
- Allocation strategies
- Rebalancing recommendations
- Fixed income positions
- Clube do Valor data
- Ticker mappings

See [README.md](README.md) for complete API endpoints overview.

## Database Schema

The system uses 18 models across 11 Django apps:
- Users (1 model)
- Brokerage Notes (2 models)
- Portfolio Operations (1 model)
- Fixed Income (2 models)
- Stocks (1 model)
- Configuration (2 models)
- Allocation Strategies (4 models)
- Rebalancing (2 models)
- Clube do Valor (2 models)
- Ticker Mappings (1 model)

See [09-database-data-model.md](09-database-data-model.md) for complete schema documentation.

## Testing

The project includes:
- Unit tests for services and utilities
- E2E tests for complete user workflows
- Test coverage for all major features

See [TESTING.md](TESTING.md) for testing documentation.

## Getting Started

1. Review [README.md](README.md) for project overview
2. Follow setup instructions in README.md
3. Review application-specific specifications (01-15)
4. Reference database schema (09-database-data-model.md)
5. Check testing guide (TESTING.md)

## Document Status

All specification documents are current and reflect the system's migration from JSON file storage to SQLite database. The documentation covers all 11 Django apps and their corresponding frontend components.

---

**Last Updated**: November 2025  
**Project**: d2xmoney Portfolio Management System  
**Status**: Documentation Complete
