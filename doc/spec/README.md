# Portfolio Management System - Specification

This document provides the main specification and technology stack for the Portfolio Management System. The complete specification is broken down into application-specific documents.

## Project Overview

The Portfolio Management System (d2xmoney) is a comprehensive full-stack application for managing investment portfolios, processing B3 brokerage notes, and tracking investment positions. The system consists of 11 Django backend apps and multiple Angular frontend components:

**Core Features:**
- **User Management**: Create and manage users with CPF, account information, and profile pictures
- **Brokerage Note Processing**: Parse B3 brokerage note PDFs and extract trading operations
- **Brokerage History**: Track and view history of processed brokerage notes
- **Portfolio Summary**: View positions, operations, and portfolio analytics
- **Fixed Income Management**: Track CDB, Tesouro Direto, and other fixed income investments
- **Stock Catalog**: Master catalog of stocks with ticker symbols and pricing
- **Investment Configuration**: Manage investment types and sub-types
- **Allocation Strategies**: Define and manage portfolio allocation strategies
- **Rebalancing**: Generate and manage rebalancing recommendations
- **Clube do Valor**: Stock recommendations and monthly snapshots
- **Ticker Mappings**: Map company names to stock ticker symbols

## Technology Stack

### Frontend
- **Framework**: Angular 20.1.0
- **Language**: TypeScript 5.8.2
- **Architecture**: Standalone components
- **Control Flow**: Modern Angular syntax (@if, @for)
- **Key Dependencies**:
  - pdfjs-dist@5.4.394 (PDF parsing)
  - concurrently@9.2.1 (development server management)
  - @playwright/test@1.56.1 (E2E testing)

### Backend
- **Framework**: Django 5.0+
- **REST API**: Django REST Framework 3.14.0+
- **Language**: Python 3.10+
- **Database**: SQLite 3 (development)
- **Key Dependencies**:
  - Django>=5.0
  - djangorestframework>=3.14.0
  - django-cors-headers>=4.3.0 (CORS support)
  - python-dateutil>=2.8.0 (date utilities)
  - requests>=2.31.0 (HTTP requests)
  - beautifulsoup4>=4.12.0 (HTML parsing)
  - Pillow>=10.0.0 (Image processing)
  - openpyxl>=3.1.0 (Excel file handling)
  - yfinance>=0.2.0 (Stock price data)

## Project Structure

```
project-root/
├── frontend/          # Angular application (port 4400)
│   ├── src/
│   │   ├── app/
│   │   │   ├── users/              # User Management
│   │   │   ├── brokerage-note/    # Brokerage Note Processing
│   │   │   ├── brokerage-history/ # Brokerage History
│   │   │   ├── portfolio/          # Portfolio Summary
│   │   │   ├── clubedovalor/       # Clube do Valor
│   │   │   ├── configuration/      # Investment Configuration
│   │   │   ├── allocation-strategies/ # Allocation Strategies
│   │   │   ├── fixed-income/       # Fixed Income Management
│   │   │   └── shared/             # Shared components and utilities
│   │   └── assets/
│   ├── angular.json
│   ├── package.json
│   └── proxy.conf.json
├── backend/           # Django REST API (port 8000)
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3    # SQLite database
│   ├── portfolio_api/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── users/         # User Management API
│   ├── brokerage_notes/ # Brokerage Note Processing API
│   ├── portfolio_operations/ # Portfolio Summary API
│   ├── ticker_mappings/ # Ticker Mapping API
│   ├── clubedovalor/  # Clube do Valor API
│   ├── configuration/ # Investment Configuration API
│   ├── stocks/        # Stock Catalog API
│   ├── allocation_strategies/ # Allocation Strategies API
│   ├── ambb_strategy/ # AMBB Strategy API
│   ├── rebalancing/   # Rebalancing API
│   ├── fixed_income/   # Fixed Income API
│   ├── data/          # Data backups and exports
│   └── media/         # File uploads
│       ├── users/
│       ├── brokerage_notes/
│       └── portafolio_wallet/
└── doc/
    └── spec/          # This specification
        ├── README.md (this file)
        ├── 01-user-management.md
        ├── 02-brokerage-note-processing.md
        ├── 03-brokerage-history.md
        ├── 04-portfolio-summary.md
        ├── 05-clube-do-valor-redesign.md
        ├── 09-database-data-model.md
        ├── 10-configuration.md
        ├── 11-stocks.md
        ├── 12-allocation-strategies.md
        ├── 13-rebalancing.md
        ├── 14-fixed-income.md
        └── 15-ticker-mappings.md
```

## Initial Project Setup

### Frontend Setup

#### Prompt 1.1: Create Angular Application
```
Create a new Angular application in the frontend/ directory using Angular CLI version 20.1.1 with the following specifications:
- Project name: portfolio-frontend
- Directory: frontend/
- Use standalone components
- Include routing
- Use Angular 20.1.0
- Configure TypeScript 5.8.2
- Set up the project with modern Angular features (signals, control flow, standalone components)
```

#### Prompt 1.2: Configure Frontend Development Environment
```
Configure the Angular development environment with:
- Proxy configuration file (frontend/proxy.conf.json) for API requests to localhost:8000
- Update angular.json to use the proxy config in development mode
- Configure concurrently package to run multiple processes simultaneously
- Add npm scripts in frontend/package.json:
  - start:dev - runs Django backend and Angular dev server concurrently
  - start - runs Angular dev server only
  - build - builds Angular for production
```

#### Prompt 1.3: Install Frontend Dependencies
```
Install the following dependencies for the Angular project (in frontend/ directory):
- pdfjs-dist@5.4.394 for PDF parsing
- concurrently@9.2.1 for running multiple processes
- @playwright/test@1.56.1 for E2E testing (dev dependency)
- All standard Angular dependencies (@angular/core, @angular/common, @angular/forms, @angular/router, etc.)
```

### Backend Setup

#### Prompt 1.4: Create Django Project
```
Create a new Django project in the backend/ directory:
- Project name: portfolio_api
- Directory: backend/
- Use Django 5.0 or later
- Create virtual environment: python -m venv venv
- Activate virtual environment
- Install Django: pip install django djangorestframework django-cors-headers
- Create project: django-admin startproject portfolio_api backend/
- Ensure manage.py is in backend/ directory
```

#### Prompt 1.5: Configure Django Settings
```
Configure Django settings (backend/portfolio_api/settings.py):
- Add 'rest_framework' to INSTALLED_APPS
- Add 'corsheaders' to INSTALLED_APPS
- Add 'corsheaders.middleware.CorsMiddleware' to MIDDLEWARE (before CommonMiddleware)
- Configure CORS settings:
  - CORS_ALLOWED_ORIGINS = ['http://localhost:4400']
  - CORS_ALLOW_CREDENTIALS = True
  - CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
  - CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
- Configure REST Framework settings:
  - DEFAULT_PERMISSION_CLASSES: ['rest_framework.permissions.AllowAny']
  - DEFAULT_RENDERER_CLASSES: ['rest_framework.renderers.JSONRenderer']
- Configure media settings:
  - MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
  - MEDIA_URL = '/media/'
```

#### Prompt 1.6: Install Backend Dependencies
```
Create requirements.txt in backend/ directory with:
- Django>=5.0
- djangorestframework>=3.14.0
- django-cors-headers>=4.3.0
- python-dateutil>=2.8.0
- requests>=2.31.0
- beautifulsoup4>=4.12.0
- Pillow>=10.0.0
- openpyxl>=3.1.0
- yfinance>=0.2.0

Install dependencies: pip install -r requirements.txt
```

## Infrastructure Configuration

### Frontend Configuration

#### Prompt INFRA-1: Configure Angular Proxy
```
Configure Angular proxy for API requests:
- File: frontend/proxy.conf.json
- Proxy /api/* requests to http://localhost:8000
- Set secure: false, changeOrigin: true
- Enable debug logging
- Update frontend/angular.json serve configuration to use proxy in development mode
```

#### Prompt INFRA-2: Add PDF.js Worker Asset
```
Add PDF.js worker file:
- Download pdf.worker.min.mjs from pdfjs-dist package
- Place in frontend/src/assets/pdfjs/pdf.worker.min.mjs
- Ensure asset is included in frontend/angular.json assets array
```

### Backend Configuration

#### Prompt INFRA-3: Configure Django URLs
```
Configure main Django URLs in backend/portfolio_api/urls.py:
- Import include from django.urls
- Include users URLs: path('', include('users.urls'))
- Include brokerage_notes URLs: path('', include('brokerage_notes.urls'))
- Configure media file serving in development:
  - from django.conf import settings
  - from django.conf.urls.static import static
  - if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

#### Prompt INFRA-4: Update Frontend Package Scripts
```
Update frontend/package.json scripts:
- start:dev: "concurrently \"cd ../backend && python manage.py runserver\" \"ng serve\""
- start: "ng serve"
- build: "ng build"
- Ensure concurrently package is installed
```

## Application Specifications

The complete specification is organized into the following application-specific documents:

### Core Applications

1. **[01-user-management.md](01-user-management.md)** - User Management Infrastructure
   - User CRUD operations
   - CPF validation
   - Picture upload
   - Database storage

2. **[02-brokerage-note-processing.md](02-brokerage-note-processing.md)** - Brokerage Note Processing
   - PDF parsing
   - Ticker mapping
   - Operation extraction
   - Upload component

3. **[03-brokerage-history.md](03-brokerage-history.md)** - Brokerage History
   - History tracking
   - Processed notes display
   - Search and filter
   - Note metadata

4. **[04-portfolio-summary.md](04-portfolio-summary.md)** - Portfolio Summary
   - Position calculations
   - Operations display
   - Filters and analytics
   - Portfolio service

5. **[05-clube-do-valor-redesign.md](05-clube-do-valor-redesign.md)** - Clube do Valor
   - Stock recommendations
   - Monthly snapshots
   - Strategy-based filtering
   - Google Sheets integration

### Configuration & Catalog

6. **[10-configuration.md](10-configuration.md)** - Investment Configuration
   - Investment types management
   - Investment sub-types management
   - Excel import functionality
   - Type classification

7. **[11-stocks.md](11-stocks.md)** - Stock Catalog
   - Stock master catalog
   - Ticker management
   - Price updates
   - Stock classification

8. **[15-ticker-mappings.md](15-ticker-mappings.md)** - Ticker Mappings
   - Company name to ticker mapping
   - Mapping management
   - Integration with brokerage note processing

### Portfolio Management

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
    - Portfolio import

### Database & Testing

12. **[09-database-data-model.md](09-database-data-model.md)** - Database Schema
    - Complete database model documentation
    - Entity relationships
    - Field specifications
    - Constraints and validations

13. **[TESTING.md](TESTING.md)** - Testing Guide
    - Unit testing
    - E2E testing
    - Test structure
    - Debugging guides

## Running the Application

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- pip and virtualenv

### Option 1: Run Both Servers Together
```bash
# From frontend directory
npm run start:dev
```

### Option 2: Run Servers Separately

**Terminal 1 - Backend:**
```bash
cd backend
python manage.py runserver
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

### Access the Application:
- Frontend: http://localhost:4400
- Backend API: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/ (if configured)

## API Endpoints Overview

### User Management API
- `GET /api/users/` - List all users
- `POST /api/users/` - Create new user
- `GET /api/users/{id}/` - Get user by ID
- `PUT /api/users/{id}/` - Update user
- `DELETE /api/users/{id}/` - Delete user

### Brokerage Note Processing API
- `GET /api/brokerage-notes/` - List processed notes
- `POST /api/brokerage-notes/` - Upload and process PDF
- `GET /api/brokerage-notes/{id}/` - Get note details
- `DELETE /api/brokerage-notes/{id}/` - Delete note
- `GET /api/brokerage-notes/{id}/operations/` - Get operations from note

### Portfolio Summary API
- `GET /api/portfolio/?user_id={user_id}` - Get user's ticker summaries
- `POST /api/portfolio/refresh/` - Manually refresh portfolio from brokerage notes
- `GET /api/portfolio/prices/` - Get portfolio prices

**Note**: Portfolio is automatically refreshed after brokerage note upload/delete.

### Ticker Mappings API
- `GET /api/ticker-mappings/` - List all ticker mappings
- `POST /api/ticker-mappings/` - Create ticker mapping
- `GET /api/ticker-mappings/{nome}/` - Get mapping by company name
- `PUT /api/ticker-mappings/{nome}/` - Update mapping
- `DELETE /api/ticker-mappings/{nome}/` - Delete mapping

### Clube do Valor API
- `GET /api/clubedovalor/?strategy={strategy}` - Get current month's stocks
- `GET /api/clubedovalor/history/?strategy={strategy}` - Get historical snapshots
- `POST /api/clubedovalor/refresh/` - Refresh from Google Sheets
- `DELETE /api/clubedovalor/stocks/{codigo}/?strategy={strategy}` - Delete stock

### Configuration API
- `GET /api/configuration/investment-types/` - List investment types
- `POST /api/configuration/investment-types/` - Create investment type
- `GET /api/configuration/investment-types/{id}/` - Get investment type
- `PUT /api/configuration/investment-types/{id}/` - Update investment type
- `DELETE /api/configuration/investment-types/{id}/` - Delete investment type
- `GET /api/configuration/investment-subtypes/` - List investment sub-types
- `POST /api/configuration/investment-subtypes/` - Create investment sub-type
- `POST /api/configuration/investment-subtypes/import_excel/` - Import from Excel

### Stocks API
- `GET /api/stocks/stocks/` - List stocks (with search, filters)
- `POST /api/stocks/stocks/` - Create stock
- `GET /api/stocks/stocks/{ticker}/` - Get stock by ticker
- `PUT /api/stocks/stocks/{ticker}/` - Update stock
- `DELETE /api/stocks/stocks/{ticker}/` - Delete stock
- `POST /api/stocks/stocks/update_prices/` - Update all stock prices
- `POST /api/stocks/stocks/{ticker}/update_price/` - Update specific stock price

### Allocation Strategies API
- `GET /api/allocation-strategies/allocation-strategies/` - List strategies
- `POST /api/allocation-strategies/allocation-strategies/` - Create strategy
- `GET /api/allocation-strategies/allocation-strategies/{id}/` - Get strategy
- `PUT /api/allocation-strategies/allocation-strategies/{id}/` - Update strategy
- `DELETE /api/allocation-strategies/allocation-strategies/{id}/` - Delete strategy

### Rebalancing API
- `GET /api/rebalancing/recommendations/` - List recommendations
- `POST /api/rebalancing/recommendations/` - Create recommendation
- `GET /api/rebalancing/recommendations/{id}/` - Get recommendation
- `POST /api/rebalancing/recommendations/generate/` - Generate recommendations
- `POST /api/rebalancing/recommendations/{id}/apply/` - Apply recommendation
- `POST /api/rebalancing/recommendations/{id}/dismiss/` - Dismiss recommendation

### AMBB Strategy API
- `GET /api/ambb-strategy/ambb-strategy/recommendations/?user_id={user_id}` - Get AMBB recommendations

### Fixed Income API
- `GET /api/fixed-income/positions/` - List fixed income positions
- `POST /api/fixed-income/positions/` - Create position
- `GET /api/fixed-income/positions/{id}/` - Get position
- `PUT /api/fixed-income/positions/{id}/` - Update position
- `DELETE /api/fixed-income/positions/{id}/` - Delete position
- `GET /api/fixed-income/tesouro-direto/` - List Tesouro Direto positions
- `POST /api/fixed-income/tesouro-direto/` - Create Tesouro Direto position

For detailed API documentation, see the respective application specification files.

## Data Persistence

### Database
The system uses **SQLite 3** for data storage (development environment). All data is stored in Django models across 11 apps:

- **Users**: User accounts and profiles
- **Brokerage Notes**: Processed brokerage notes and operations
- **Portfolio Positions**: Calculated portfolio positions (FIFO method)
- **Fixed Income**: CDB, Tesouro Direto, and other fixed income positions
- **Stocks**: Master stock catalog with ticker symbols and prices
- **Investment Types/Sub-types**: Configuration data for investment classification
- **Allocation Strategies**: User-defined portfolio allocation strategies
- **Rebalancing**: Rebalancing recommendations and actions
- **Clube do Valor**: Stock snapshots and recommendations
- **Ticker Mappings**: Company name to ticker symbol mappings

See [09-database-data-model.md](09-database-data-model.md) for complete database schema documentation.

### File Storage
- User pictures: `backend/media/users/`
- Brokerage note PDFs: `backend/media/brokerage_notes/`
- Portfolio exports: `backend/media/portafolio_wallet/`
- Data backups: `backend/data/backup/`

### Frontend
- Ticker mappings: localStorage key `ticker_mappings` (legacy, now uses database)
- Custom ticker mappings: localStorage key `ticker_mappings_custom` (legacy, now uses database)

**Important**: The system has migrated from JSON file storage to SQLite database. All data is now stored in the database with proper relationships and constraints.

## Development Workflow

1. **Setup**: Follow Initial Project Setup (Prompts 1.1-1.6)
2. **Infrastructure**: Configure infrastructure (Prompts INFRA-1 to INFRA-4)
3. **Database**: Run migrations: `python manage.py migrate`
4. **Core Features**: 
   - User Management (see 01-user-management.md)
   - Brokerage Note Processing (see 02-brokerage-note-processing.md)
   - Brokerage History (see 03-brokerage-history.md)
   - Portfolio Summary (see 04-portfolio-summary.md)
5. **Configuration**: 
   - Investment Configuration (see 10-configuration.md)
   - Stock Catalog (see 11-stocks.md)
   - Ticker Mappings (see 15-ticker-mappings.md)
6. **Portfolio Management**:
   - Allocation Strategies (see 12-allocation-strategies.md)
   - Rebalancing (see 13-rebalancing.md)
   - Fixed Income (see 14-fixed-income.md)
7. **Additional Features**:
   - Clube do Valor (see 05-clube-do-valor-redesign.md)
8. **Database Schema**: Reference database models and relationships (see 09-database-data-model.md)

## Notes

- The application uses standalone Angular components throughout
- All data is stored in SQLite database (migrated from JSON files)
- Portfolio data is automatically calculated from brokerage notes using FIFO method
- Portfolio is automatically refreshed after brokerage note upload/delete
- PDF parsing supports standard B3 brokerage note format
- Ticker mappings are stored in database and automatically used during PDF processing
- CPF validation follows Brazilian CPF algorithm (11 digits with checksum validation)
- Frontend runs on port 4400 (not 4200)
- Backend runs on port 8000
- Database migrations must be run: `python manage.py migrate`

---

**Document Version**: 4.0  
**Last Updated**: November 2025  
**Changes**: 
- v4.0: Complete documentation update
  - Added all 11 Django apps documentation
  - Updated technology stack with all dependencies
  - Migrated from JSON file storage to SQLite database
  - Added comprehensive API endpoints documentation
  - Added new application specifications (10-15)
  - Updated project structure
- v3.0: Restructured into application-specific specification files
- Removed task management functionality
- Added brokerage history tracking
