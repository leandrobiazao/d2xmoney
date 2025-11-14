# d2xmoney - Portfolio Management System

This project is a full-stack portfolio management system with Angular frontend and Django backend.

> **⚠️ Important**: Before running any backend commands, always activate the Python virtual environment first! See [Project Setup](./.project-setup.md) for details.

## Project Structure

```
project-root/
├── frontend/          # Angular application (port 4400)
├── backend/           # Django REST API (port 8000)
└── doc/               # Documentation
```

## Development server

### Frontend

To start the Angular development server, navigate to the frontend directory and run:

```bash
cd frontend
npm install  # First time setup
ng serve
```

Or use npm scripts:

```bash
cd frontend
npm start
```

Once the server is running, open your browser and navigate to `http://localhost:4400/`. The application will automatically reload whenever you modify any of the source files.

### Backend

To start the Django backend server, navigate to the backend directory:

**First-time setup:**

1. Activate the virtual environment (a `venv` directory already exists in the backend folder):
   
   For PowerShell:
   ```bash
   cd backend
   .\venv\Scripts\Activate.ps1
   ```
   
   For Command Prompt (CMD):
   ```bash
   cd backend
   .\venv\Scripts\activate.bat
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

**Starting the server:**

Make sure the virtual environment is activated (you should see `(venv)` in your terminal prompt), then run:

```bash
python manage.py runserver
```

The backend API will be available at `http://localhost:8000/`.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, navigate to the frontend directory and run:

```bash
cd frontend
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
cd frontend
ng generate --help
```

## Building

To build the frontend project, navigate to the frontend directory and run:

```bash
cd frontend
ng build
```

This will compile your project and store the build artifacts in the `frontend/dist/` directory. By default, the production build optimizes your application for performance and speed.

## Testing

### Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner:

```bash
cd frontend
npm test
```

To run tests with code coverage:

```bash
cd frontend
npm run test:coverage
```

### Running end-to-end tests

The project uses [Playwright](https://playwright.dev/) for E2E testing. Make sure both frontend and backend servers are running before executing E2E tests.

**Prerequisites:**
- Frontend running on `http://localhost:4400`
- Backend running on `http://localhost:8000`

**Run E2E tests:**

```bash
cd frontend
npm run e2e
```

**Run E2E tests with UI (interactive mode):**

```bash
cd frontend
npm run e2e:ui
```

**Run E2E tests in headed mode (see browser):**

```bash
cd frontend
npm run e2e:headed
```

**Run E2E tests in debug mode:**

```bash
cd frontend
npm run e2e:debug
```

**Run all tests (unit + E2E):**

```bash
cd frontend
npm run test:all
```

### Test Coverage

The E2E test suite covers all major application features:
- User management (creation, validation, CPF checks)
- Portfolio operations (display, filtering, deletion)
- Brokerage note processing (PDF upload, ticker mapping)
- History management (list, detail, deletion)
- UI/UX features (error handling, responsive design, currency formatting)

For detailed test documentation, see [Testing Guide](doc/spec/TESTING.md) and [E2E Test Plan](doc/spec/e2e-test-plan.md).

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.

For detailed project specifications, see the [Documentation](doc/spec/README.md).
