# Fundos Imobiliários (FIIs) - Specification

This document specifies the FIIs (Real Estate Investment Funds) application for managing and displaying Brazilian real estate investment funds data.

## Overview

The FIIs app provides comprehensive management of Brazilian Real Estate Investment Funds (Fundos Imobiliários) data. It provides:

- Master catalog of FII profiles with complete financial data
- Integration with fiis.com.br for automated data import
- Portfolio FII positions tracking
- FII catalog view in configuration interface
- FII-specific financial metrics (dividend yield, P/VP ratio, IFIX participation, etc.)

## Backend Components

### Models

#### FIIProfile

**Table**: `fii_profiles`

**Purpose**: Extended profile for Real Estate Investment Funds (FIIs), containing detailed financial and operational data.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `stock` | OneToOneField | Stock, CASCADE, related_name='fii_profile' | Reference to base Stock record |
| `segment` | CharField | max_length=100 | FII segment (e.g., "Tijolo:Shoppings", "Papel", "Híbrido") |
| `target_audience` | CharField | max_length=100 | Target investor audience (e.g., "Investidor Qualificado") |
| `administrator` | CharField | max_length=255 | Fund administrator company |
| `last_yield` | DecimalField | max_digits=10, decimal_places=2, Null | Last dividend payment amount (R$) |
| `dividend_yield` | DecimalField | max_digits=10, decimal_places=2, Null | Dividend yield percentage |
| `base_date` | DateField | Null | Base date for dividend calculation |
| `payment_date` | DateField | Null | Dividend payment date |
| `average_yield_12m_value` | DecimalField | max_digits=10, decimal_places=2, Null | 12-month average yield (R$) |
| `average_yield_12m_percentage` | DecimalField | max_digits=10, decimal_places=2, Null | 12-month average yield (%) |
| `equity_per_share` | DecimalField | max_digits=12, decimal_places=2, Null | Equity per share (Patrimônio/Cota) |
| `price_to_vp` | DecimalField | max_digits=10, decimal_places=2, Null | Price to equity ratio (Cotação/VP) |
| `trades_per_month` | IntegerField | Null | Average number of trades per month |
| `ifix_participation` | DecimalField | max_digits=10, decimal_places=2, Null | IFIX index participation percentage |
| `shareholders_count` | IntegerField | Null | Number of shareholders (cotistas) |
| `equity` | DecimalField | max_digits=20, decimal_places=2, Null | Total fund equity (Patrimônio) |
| `base_share_price` | DecimalField | max_digits=12, decimal_places=2, Null | Base share price (Cota base) |

**Relationships**:
- One-to-One: `Stock` (via `stock` OneToOneField)

**Meta Options**:
- `db_table`: `fii_profiles`
- `verbose_name`: `FII Profile`
- `verbose_name_plural`: `FII Profiles`

**Related Stock Model**:
FII records are stored in the `Stock` model with:
- `stock_class`: 'FII'
- `investment_type`: References the 'FIIS' investment type
- `investment_subtype`: Can be TIJOLO, PAPEL, HIBRIDO, or OUTROS

### API Endpoints

**Base URL**: `http://localhost:8000/api/fiis/`

#### List FII Profiles
```
GET /api/fiis/profiles/
```

**Description**: Returns all FII profiles with associated stock data.

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "stock_id": 150,
    "ticker": "HGLG11",
    "segment": "Tijolo:Shoppings",
    "target_audience": "Investidor Geral",
    "administrator": "BTG Pactual Serviços Financeiros S.A DTVM",
    "last_yield": 1.05,
    "dividend_yield": 0.95,
    "base_date": "2025-11-15",
    "payment_date": "2025-11-25",
    "average_yield_12m_value": 1.15,
    "average_yield_12m_percentage": 0.98,
    "equity_per_share": 110.50,
    "price_to_vp": 0.99,
    "trades_per_month": 15000,
    "ifix_participation": 2.35,
    "shareholders_count": 125000,
    "equity": 2500000000.00,
    "base_share_price": 109.50
  }
]
```

#### Get FII Profile by Ticker
```
GET /api/fiis/profiles/<ticker>/
```

**Path Parameters**:
- `ticker` (string, required) - FII ticker symbol (e.g., "HGLG11")

**Response** (200 OK): FII profile object

**Error Response** (404 Not Found):
```json
{
  "error": "FII profile not found"
}
```

### Serializers

#### FIIProfileSerializer

**Location**: `backend/fiis/serializers.py`

**Fields**:
- All FIIProfile model fields
- `ticker` (read-only) - From related Stock model
- `stock_id` (read-only) - Stock model ID

**Usage**:
- Serializes FIIProfile data for API responses
- Includes related Stock ticker for easy reference
- All fields optional except stock relationship

### Management Commands

#### import_fiis

**Command**: `python manage.py import_fiis`

**Purpose**: Imports FII data from fiis.com.br using web scraping.

**Location**: `backend/fiis/management/commands/import_fiis.py`

**Technology**: Uses Playwright for browser automation and web scraping

**Process**:

1. **Web Scraping**:
   - Launches headless Chromium browser
   - Navigates to https://fiis.com.br/lupa-de-fiis/
   - Waits for table content to load
   - Extracts all 17 data columns from table rows:
     * Column 0: Ticker
     * Column 1: Público Alvo (Target Audience)
     * Column 2: Tipo de FII (FII Type/Segment)
     * Column 3: Administrador (Administrator)
     * Column 4: Último Rend. (R$)
     * Column 5: Último Rend. (%)
     * Column 6: Data Pagamento
     * Column 7: Data Base
     * Column 8: Rend. Méd. 12m (R$)
     * Column 9: Rend. Méd. 12m (%)
     * Column 10: Patrimônio/Cota
     * Column 11: Cotação/VP
     * Column 12: Nº negócios/mês
     * Column 13: Partic. IFIX
     * Column 14: Número Cotistas
     * Column 15: Patrimônio
     * Column 16: Cota base

2. **Data Processing**:
   - Validates ticker format (4 letters + 2 digits)
   - Parses Brazilian decimal format (comma as decimal separator)
   - Parses date format (DD/MM/YYYY)
   - Converts currency and percentage values

3. **Database Updates**:
   - Ensures FIIS investment type exists
   - Creates/updates investment subtypes (TIJOLO, PAPEL, HIBRIDO, OUTROS)
   - Maps FII segment to appropriate subtype
   - Creates/updates Stock records:
     * Sets stock_class to 'FII'
     * Sets financial_market to 'B3'
     * Assigns investment type and subtype
   - Creates/updates FIIProfile records with all financial data
   - Creates TickerMapping entries for easy lookup

4. **Subtype Mapping**:
   - "Tijolo" keywords: TIJOLO, IMÓVEIS, SHOPPING, LOGÍSTICA → TIJOLO subtype
   - "Papel" keywords: PAPEL, RECEBÍVEIS, CRI → PAPEL subtype
   - "Híbrido" keywords: HÍBRIDO, HIBRIDO → HIBRIDO subtype
   - Default: OUTROS subtype

**Output**:
- Number of FIIs extracted from website
- Number of FIIs successfully imported
- Any errors encountered

**Dependencies**:
- playwright>=1.40.0 (in requirements.txt)
- Requires Playwright browser installation: `playwright install chromium`

### Admin Interface

**Location**: `backend/fiis/admin.py`

**Registered Model**: `FIIProfile`

**List Display**:
- Stock (ticker)
- Segment
- Dividend Yield
- Price to VP ratio

**Search Fields**:
- Stock ticker
- Segment

**Filters**:
- Segment

## Frontend Components

### FIIService

**Location**: `frontend/src/app/fiis/fiis.service.ts`

**Purpose**: HTTP service for FII data operations

**Methods**:

- `getFIIProfiles(): Observable<FIIProfile[]>`
  - Fetches all FII profiles from API
  - Endpoint: GET `/api/fiis/profiles/`
  - Returns: Array of FIIProfile objects

- `getFIIProfile(ticker: string): Observable<FIIProfile>`
  - Fetches single FII profile by ticker
  - Endpoint: GET `/api/fiis/profiles/{ticker}/`
  - Returns: Single FIIProfile object

**Configuration**:
- API URL: `http://localhost:8000/api/fiis`

### FIIListComponent

**Location**: `frontend/src/app/fiis/fiis-list.component.*`

**Purpose**: Displays user's FII holdings in the portfolio view

**Features**:
- Summary cards showing:
  * Total invested amount
  * Current portfolio value
  * Number of FIIs in portfolio
- Table displaying:
  * Ticker
  * Segment
  * Quantity held
  * Average purchase price
  * Total invested
  * 12-month dividend yield (%)
  * Price to VP ratio
  * Last dividend amount
- Integrates portfolio positions with FII profile data
- Filters portfolio positions to show only FIIs

**Input**:
- `userId` (string | null) - User ID to load portfolio for

**Integration**:
- Uses `PortfolioService` to fetch positions
- Uses `FIIService` to fetch FII profiles
- Matches portfolio positions with FII profiles by ticker
- Displays only positions that have matching FII profiles

### FIICatalogComponent

**Location**: `frontend/src/app/configuration/fii-catalog.component.*`

**Purpose**: Displays complete FII catalog in the configuration interface

**Features**:
- Filter controls:
  * Search by ticker
  * Filter by segment
  * Reset filters button
- Result count display
- Comprehensive data table with 17 columns:
  * Ticker
  * Segment
  * Target Audience
  * Administrator
  * Last Yield (R$)
  * Dividend Yield (%)
  * Base Date
  * Payment Date
  * 12-month Avg Yield (R$)
  * 12-month Avg Yield (%)
  * Equity per Share
  * Price to VP
  * Trades per Month
  * IFIX Participation (%)
  * Number of Shareholders
  * Total Equity
  * Base Share Price
- Pagination:
  * 50 items per page
  * Previous/Next buttons
  * Page indicator
- Currency formatting (Brazilian Real - BRL)
- Responsive table with horizontal scroll

**Styling**:
- Consistent with stocks catalog component
- Clean, modern design using Apple-inspired UI guidelines
- Monospace font for numbers
- Color-coded ticker symbols
- Hover effects on rows

### Models/Interfaces

**Location**: `frontend/src/app/fiis/fiis.models.ts`

**FIIProfile Interface**:
```typescript
interface FIIProfile {
  id: number;
  stock_id: number;
  ticker: string;
  segment: string;
  target_audience: string;
  administrator: string;
  last_yield?: number;
  dividend_yield?: number;
  base_date?: string;
  payment_date?: string;
  average_yield_12m_value?: number;
  average_yield_12m_percentage?: number;
  equity_per_share?: number;
  price_to_vp?: number;
  trades_per_month?: number;
  ifix_participation?: number;
  shareholders_count?: number;
  equity?: number;
  base_share_price?: number;
}
```

**FIIPosition Interface**:
```typescript
interface FIIPosition {
  ticker: string;
  quantity: number;
  averagePrice: number;
  totalInvested: number;
  currentPrice?: number;
  currentValue?: number;
  profit?: number;
  profile?: FIIProfile;
}
```

## Data Flow

### Importing FII Data

1. Administrator runs `python manage.py import_fiis` command
2. Playwright launches browser and navigates to fiis.com.br
3. System scrapes all FII data from table
4. For each FII:
   - Validates ticker format
   - Determines investment subtype from segment
   - Creates/updates Stock record with FII classification
   - Creates/updates FIIProfile with all financial data
   - Creates TickerMapping for lookup
5. Returns import statistics

### Viewing FII Catalog (Configuration)

1. User navigates to Configuration page
2. User selects "Fundos Imobiliários" tab in Assets section
3. FIICatalogComponent loads all FII profiles via FIIService
4. Component displays filterable, paginated table
5. User can search by ticker or filter by segment
6. All 17 data columns are displayed with proper formatting

### Viewing FII Portfolio Positions

1. User views Portfolio page for a specific user
2. User selects "Fundos Imobiliários" tab
3. FIIListComponent loads:
   - User's portfolio positions via PortfolioService
   - All FII profiles via FIIService
4. Component filters positions to only FIIs (by matching with profiles)
5. Component enriches positions with FII profile data
6. Displays summary cards and detailed table

## Integration with Other Apps

### Stocks App
- FIIs are stored as Stock records with `stock_class='FII'`
- FIIProfile extends Stock with additional FII-specific data
- Stock ticker is the primary link between models

### Configuration App
- FIIs use InvestmentType "FIIS" (code: FIIS)
- FIIs use InvestmentSubType: TIJOLO, PAPEL, HIBRIDO, OUTROS
- FII catalog displayed in Configuration interface alongside stock catalog

### Portfolio Operations App
- Portfolio positions can reference FII tickers
- FII positions are distinguished by their Stock classification
- Portfolio valuation includes FII holdings

### Brokerage Notes App
- FII operations are processed and stored in brokerage notes
- **FIIs operations are displayed in the Operations Modal** in a separate section labeled "Fundos Imobiliários"
- When viewing operations in the Operations Modal, FIIs operations are grouped together with other investment types
- FII operations are tracked in portfolio positions and displayed in the "Fundos Imobiliários" tab
- Operations Modal shows "Renda Variável em Reais", "Renda Variável em Dólares", and "Fundos Imobiliários" investment types

### Ticker Mappings App
- TickerMapping entries created for each FII
- Maps company name variations to ticker
- Enables fuzzy matching in brokerage note processing

## Common Use Cases

### Initial Setup

1. Administrator runs import command:
   ```bash
   cd backend
   python manage.py import_fiis
   ```
2. System imports all FIIs from fiis.com.br
3. FII catalog becomes available throughout the application

### Viewing All Available FIIs

1. Navigate to Configuration page
2. Click "Fundos Imobiliários" tab in Assets section
3. Browse complete FII catalog
4. Use filters to find specific FIIs by ticker or segment
5. View all financial metrics in table

### Tracking FII Portfolio

1. Upload brokerage notes containing FII operations
2. System recognizes FII tickers via TickerMapping
3. FII operations are processed and stored in brokerage notes
4. Portfolio positions include FII holdings
5. Navigate to Portfolio → "Fundos Imobiliários" tab
6. View FII-specific metrics (DY, P/VP, etc.) alongside holdings
7. **Note**: When viewing operations in the History component's Operations Modal, FIIs operations are displayed in a separate section labeled "Fundos Imobiliários", grouped together with other investment types. FII operations can also be viewed through portfolio positions in the "Fundos Imobiliários" tab.

### Updating FII Data

1. Run import command periodically to update data:
   ```bash
   python manage.py import_fiis
   ```
2. System updates existing FII profiles with latest data
3. New FIIs are automatically added
4. Frontend displays updated data on next page load

## Validation Rules

### FII Ticker Format
- Must match pattern: 4 uppercase letters + 2 digits (e.g., HGLG11)
- Example valid tickers: HGLG11, XPML11, MXRF11

### Stock Classification
- `stock_class` must be 'FII'
- `financial_market` must be 'B3'
- `investment_type` must reference FIIS type

### Numeric Fields
- Decimal fields: max 10-12 digits, 2 decimal places
- Integer fields: standard integer limits
- All financial fields are optional (nullable)

### Date Fields
- Brazilian format: DD/MM/YYYY
- Converted to YYYY-MM-DD for storage
- Optional (nullable)

## Error Handling

### Common Errors

**Import Command Errors**:

**Scraping Failures**:
- Website timeout: Increases timeout or retries
- Table structure change: Updates selector logic
- Network errors: Logged and skipped

**Data Validation Errors**:
- Invalid ticker format: Skipped with warning
- Invalid decimal values: Stored as NULL
- Invalid dates: Stored as NULL

**Database Errors**:
- Duplicate ticker: Updates existing record
- Missing investment type: Creates if needed
- Transaction failures: Rolled back, logged

**API Errors**:

**404 Not Found**:
- FII profile not found by ticker
- Returns: `{"error": "FII profile not found"}`

**500 Internal Server Error**:
- Database connection error
- Data serialization error

## Performance Considerations

### Import Process
- Processes ~500+ FIIs in single run
- Uses database transactions for atomicity
- Headless browser mode for efficiency
- Network throttling may affect import speed

### API Queries
- FII list endpoint uses `select_related('stock')` for efficiency
- Single query loads all related Stock data
- No N+1 query problems

### Frontend
- Pagination limits display to 50 items at a time
- Client-side filtering for responsive experience
- Data cached in component after initial load

## Security Considerations

### API Endpoints
- Currently no authentication required
- `authentication_classes = []` for public access
- Consider adding authentication for production

### Web Scraping
- Uses official public data from fiis.com.br
- Respects website structure and load times
- Runs in controlled management command, not user-triggered

## Related Documentation

- [Database Data Model](09-database-data-model.md) - Complete database schema
- [Configuration](10-configuration.md) - Investment type classification
- [Stocks](11-stocks.md) - Stock catalog structure
- [Portfolio Summary](04-portfolio-summary.md) - Portfolio position tracking
- [Ticker Mappings](15-ticker-mappings.md) - Ticker lookup system

## Future Enhancements

### Potential Features
- Real-time price updates from B3 or financial APIs
- Historical dividend tracking
- FII performance analytics and charts
- Dividend yield comparison tools
- FII recommendations based on user criteria
- Automated daily imports via scheduled task
- Email notifications for dividend payments
- FII segment analysis and allocation tracking

### Technical Improvements
- Add caching layer for frequently accessed data
- Implement WebSocket for real-time updates
- Add full-text search capabilities
- Export FII data to Excel/CSV
- API rate limiting and authentication
- Comprehensive unit and integration tests

---

**Document Version**: 1.0  
**Last Updated**: November 2025  
**Status**: Complete

