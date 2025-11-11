# Portfolio Management System - Specification

This document provides the main specification and technology stack for the Portfolio Management System. The complete specification is broken down into application-specific documents.

## Project Overview

The Portfolio Management System is a full-stack application for managing investment portfolios, processing B3 brokerage notes, and tracking investment positions. The system consists of:

- **User Management**: Create and manage users with CPF, account information, and profile pictures
- **Brokerage Note Processing**: Parse B3 brokerage note PDFs and extract trading operations
- **Brokerage History**: Track and view history of processed brokerage notes
- **Portfolio Summary**: View positions, operations, and portfolio analytics

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
- **Key Dependencies**:
  - django-cors-headers>=4.3.0 (CORS support)
  - python-dateutil>=2.8.0 (date utilities)

## Project Structure

```
project-root/
├── frontend/          # Angular application (port 4400)
│   ├── src/
│   │   ├── app/
│   │   │   ├── users/              # User Management App
│   │   │   ├── brokerage-note/    # Brokerage Note Processing App
│   │   │   ├── brokerage-history/ # Brokerage History App
│   │   │   ├── portfolio/          # Portfolio Summary App
│   │   │   │   ├── ticker-mapping/ # Ticker Mapping Module
│   │   │   │   │   ├── ticker-mappings.ts
│   │   │   │   │   └── ticker-mapping.service.ts
│   │   │   │   ├── portfolio.service.ts
│   │   │   │   └── ...
│   │   │   └── shared/             # Shared components and utilities
│   │   └── assets/
│   ├── angular.json
│   ├── package.json
│   └── proxy.conf.json
├── backend/           # Django REST API (port 8000)
│   ├── manage.py
│   ├── requirements.txt
│   ├── portfolio_api/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── users/         # User Management API
│   ├── brokerage_notes/ # Brokerage Note Processing API
│   ├── portfolio_operations/ # Portfolio Summary API
│   ├── data/          # JSON file storage
│   │   ├── users.json
│   │   ├── brokerage_notes.json
│   │   └── portfolio.json
│   └── media/         # File uploads
│       └── users/
└── doc/
    └── spec/          # This specification
        ├── README.md (this file)
        ├── 01-user-management.md
        ├── 02-brokerage-note-processing.md
        ├── 03-brokerage-history.md
        └── 04-portfolio-summary.md
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

1. **[01-user-management.md](01-user-management.md)** - User Management Infrastructure
   - User CRUD operations
   - CPF validation
   - Picture upload
   - JSON file storage

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
- `POST /api/brokerage-notes/upload/` - Upload and process PDF
- `GET /api/ticker-mappings/` - Get ticker mappings
- `POST /api/ticker-mappings/` - Update ticker mappings

### Brokerage History API
- `GET /api/brokerage-notes/` - List processed notes
- `GET /api/brokerage-notes/{id}/` - Get note details
- `GET /api/brokerage-notes/{id}/operations/` - Get operations from note

### Portfolio Summary API
- `GET /api/portfolio/?user_id={user_id}` - Get user's ticker summaries
- `POST /api/portfolio/refresh/` - Manually refresh portfolio from brokerage notes

**Note**: Portfolio is automatically refreshed after brokerage note upload/delete.

For detailed API documentation, see the respective application specification files.

## Data Persistence

### Frontend
- Ticker mappings: localStorage key `ticker_mappings`
- Custom ticker mappings: localStorage key `ticker_mappings_custom`

### Backend
- Users: JSON file storage at `backend/data/users.json`
- Brokerage notes: JSON file storage at `backend/data/brokerage_notes.json`
- **Portfolio**: JSON file storage at `backend/data/portfolio.json` (aggregated summary)
- User pictures: File storage at `backend/media/users/`
- Note PDFs: File storage at `backend/media/brokerage_notes/`

**Important**: Portfolio data is stored on the backend, not in localStorage. The `portfolio.json` file is automatically generated from `brokerage_notes.json` using FIFO calculation.

## Development Workflow

1. **Setup**: Follow Initial Project Setup (Prompts 1.1-1.6)
2. **Infrastructure**: Configure infrastructure (Prompts INFRA-1 to INFRA-4)
3. **User Management**: Implement user management (see 01-user-management.md)
4. **Brokerage Note Processing**: Implement note processing (see 02-brokerage-note-processing.md)
5. **Brokerage History**: Implement history tracking (see 03-brokerage-history.md)
6. **Portfolio Summary**: Implement portfolio summary (see 04-portfolio-summary.md)

## Notes

- The application uses standalone Angular components throughout
- User and brokerage note data is stored in JSON files on the Django backend
- Portfolio data is automatically calculated from brokerage notes using FIFO method
- Portfolio is automatically refreshed after brokerage note upload/delete
- PDF parsing supports standard B3 brokerage note format
- Ticker mappings are automatically saved when new company names are encountered
- CPF validation follows Brazilian CPF algorithm (11 digits with checksum validation)
- Frontend runs on port 4400 (not 4200)

---

**Document Version**: 3.0  
**Last Updated**: November 2025  
**Changes**: 
- v3.0: Restructured into application-specific specification files
- Removed task management functionality
- Added brokerage history tracking
