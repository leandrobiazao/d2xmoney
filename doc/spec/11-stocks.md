# Stock Catalog - Specification

This document specifies the Stock Catalog application for managing the master catalog of stocks with ticker symbols, company information, and current prices.

## Overview

The Stock Catalog app maintains a master database of stocks that can be used throughout the portfolio management system. It provides:

- Master stock catalog with ticker symbols
- Company information (name, CNPJ)
- Stock classification (market, class, investment type)
- Current price tracking
- Price updates from external sources (yfinance)

## Backend Components

### Models

#### Stock

**Table**: `stock_catalog`

**Purpose**: Master catalog of stocks with ticker symbols, company information, and current prices.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `ticker` | CharField | max_length=20, unique=True, Primary Key | Stock ticker symbol (e.g., "PETR4") |
| `name` | CharField | max_length=255, Required | Company name |
| `cnpj` | CharField | max_length=18, Null, Blank | Brazilian company tax ID |
| `investment_type` | ForeignKey | InvestmentType, SET_NULL, Null | Investment type classification |
| `financial_market` | CharField | max_length=20, choices, default='B3' | Financial market |
| `stock_class` | CharField | max_length=10, choices, default='ON' | Stock class |
| `current_price` | DecimalField | max_digits=12, decimal_places=2, default=0.0 | Current stock price |
| `last_updated` | DateTimeField | auto_now=True | Last price update timestamp |
| `is_active` | BooleanField | default=True | Active status |

**Financial Market Choices**:
- `B3`: Brazilian stock exchange
- `Nasdaq`: NASDAQ
- `NYExchange`: New York Stock Exchange

**Stock Class Choices**:
- `ON`: Ordinary shares
- `PN`: Preferred shares
- `ETF`: Exchange-traded fund
- `BDR`: Brazilian Depositary Receipt

**Relationships**:
- Many-to-One: `InvestmentType` (via `investment_type` ForeignKey, related_name='stocks')
- One-to-Many: `StockAllocation` (via `allocations` related_name)
- One-to-Many: `RebalancingAction` (via `rebalancing_actions` related_name)

**Meta Options**:
- `db_table`: `stock_catalog`
- `ordering`: `['ticker']`

### API Endpoints

**Base URL**: `http://localhost:8000/api/stocks/`

#### List Stocks
```
GET /api/stocks/stocks/
```

**Query Parameters**:
- `search` (string, optional) - Search by ticker or name
- `investment_type_id` (integer, optional) - Filter by investment type
- `financial_market` (string, optional) - Filter by market (B3, Nasdaq, NYExchange)
- `active_only` (boolean, default: true) - Filter only active stocks

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "ticker": "PETR4",
    "name": "Petróleo Brasileiro S.A. - Petrobras",
    "cnpj": "33.000.167/0001-01",
    "investment_type": {
      "id": 1,
      "name": "Ações",
      "code": "ACOES"
    },
    "financial_market": "B3",
    "stock_class": "ON",
    "current_price": "25.50",
    "last_updated": "2025-11-15T10:30:00Z",
    "is_active": true
  }
]
```

#### Create Stock
```
POST /api/stocks/stocks/
```

**Request Body**:
```json
{
  "ticker": "PETR4",
  "name": "Petróleo Brasileiro S.A. - Petrobras",
  "cnpj": "33.000.167/0001-01",
  "investment_type_id": 1,
  "financial_market": "B3",
  "stock_class": "ON",
  "current_price": "25.50",
  "is_active": true
}
```

**Response** (201 Created): Stock object

#### Get Stock by Ticker
```
GET /api/stocks/stocks/{ticker}/
```

**Response** (200 OK): Stock object

#### Update Stock
```
PUT /api/stocks/stocks/{ticker}/
PATCH /api/stocks/stocks/{ticker}/
```

**Request Body**: Partial or full stock object

**Response** (200 OK): Updated stock object

#### Delete Stock
```
DELETE /api/stocks/stocks/{ticker}/
```

**Response** (204 No Content)

#### Update All Stock Prices
```
POST /api/stocks/stocks/update_prices/
```

**Description**: Updates prices for all active stocks using yfinance.

**Response** (200 OK):
```json
{
  "updated": 150,
  "total": 200,
  "errors": [
    "TICKER1: Price not found",
    "TICKER2: Network error"
  ]
}
```

#### Update Specific Stock Price
```
POST /api/stocks/stocks/{ticker}/update_price/
```

**Request Body**:
```json
{
  "price": 25.50
}
```

**Response** (200 OK): Updated stock object

**Error Response** (400 Bad Request):
```json
{
  "error": "price is required"
}
```

### Services

#### StockService

**Location**: `backend/stocks/services.py`

**Key Methods**:

- `get_stock_by_ticker(ticker: str) -> Optional[Stock]`
  - Get stock by ticker symbol

- `search_stocks(query: str, limit: int = 50) -> List[Stock]`
  - Search stocks by ticker or name
  - Returns up to limit results

- `update_stock_price(ticker: str, price: float) -> Optional[Stock]`
  - Update stock price manually
  - Updates last_updated timestamp

- `fetch_price_from_google_finance(ticker: str, market: str = 'B3') -> Optional[float]`
  - Fetch current price from yfinance
  - For B3 stocks, appends `.SA` suffix (e.g., PETR4 -> PETR4.SA)
  - Returns price as float or None if fetch fails

- `update_prices_daily() -> Dict`
  - Updates prices for all active stocks
  - Returns dict with updated count, total, and errors

## Frontend Components

### Stock Catalog Management

The stock catalog is primarily managed through the backend API. Frontend components can:

- Display stock lists with filtering
- Search stocks by ticker or name
- View stock details
- Update stock prices (manual or automatic)

### Integration Points

Stocks are referenced in:
- **Portfolio Positions**: Portfolio positions reference stocks by ticker
- **Allocation Strategies**: Stock allocations reference stocks
- **Rebalancing**: Rebalancing actions reference stocks
- **Clube do Valor**: Stock recommendations may reference catalog stocks

## Price Updates

### Automatic Price Updates

The system supports automatic price updates using the yfinance library:

1. **Daily Update**: Call `POST /api/stocks/stocks/update_prices/` to update all active stocks
2. **Individual Update**: Call `POST /api/stocks/stocks/{ticker}/update_price/` with price value

### Price Source

- **B3 Stocks**: Uses yfinance with `.SA` suffix (e.g., `PETR4.SA`)
- **International Stocks**: Uses yfinance with ticker as-is
- **Manual Updates**: Can be updated via API with specific price value

### Price Update Process

1. System fetches price from yfinance
2. Updates `current_price` field
3. Updates `last_updated` timestamp
4. Saves stock record

## Data Flow

### Creating a Stock

1. User creates stock via API or admin interface
2. System validates:
   - Ticker is unique
   - Required fields are present
   - Investment type exists (if provided)
3. Stock record is created
4. Price can be set manually or fetched automatically

### Updating Stock Price

1. System calls `fetch_price_from_google_finance()`
2. For B3 stocks, appends `.SA` to ticker
3. Fetches price from yfinance
4. Updates stock record with new price and timestamp

### Searching Stocks

1. User provides search query
2. System searches by ticker (contains) or name (contains)
3. Returns matching stocks (case-insensitive)
4. Results limited to 50 by default

## Integration with Other Apps

### Configuration App
- Stocks are classified by `InvestmentType`
- Investment types are managed in the Configuration app

### Allocation Strategies App
- Stock allocations reference stocks from the catalog
- Used to define specific stock allocations within strategies

### Rebalancing App
- Rebalancing actions reference stocks from the catalog
- Used to generate buy/sell recommendations

### Portfolio Operations App
- Portfolio positions reference stocks by ticker
- Stock prices are used for portfolio valuation

## Common Use Cases

### Setting Up Stock Catalog

1. Create investment types (e.g., "Ações")
2. Add stocks to catalog:
   - Ticker: PETR4
   - Name: Petróleo Brasileiro S.A. - Petrobras
   - Investment Type: Ações
   - Market: B3
   - Class: ON
3. Update prices automatically or manually

### Daily Price Updates

1. Schedule daily price update job
2. Call `update_prices_daily()` endpoint
3. System updates all active stocks
4. Review errors for failed updates

### Stock Search

1. User searches for "PETR"
2. System returns stocks matching ticker or name
3. Results include: PETR3, PETR4, etc.

## Validation Rules

### Stock Creation
- `ticker` must be unique
- `ticker` and `name` are required
- `investment_type_id` must exist (if provided)
- `financial_market` must be valid choice
- `stock_class` must be valid choice

### Price Updates
- Price must be positive number
- Price precision: 2 decimal places
- Maximum price: 999,999,999,999.99

## Error Handling

### Common Errors

**400 Bad Request**:
- Missing required fields
- Invalid investment type ID
- Invalid financial market or stock class
- Invalid price value
- Duplicate ticker

**404 Not Found**:
- Stock not found by ticker

**500 Internal Server Error**:
- yfinance API error
- Network error during price fetch
- Database error

## Management Commands

### Import Stocks from CSV/Excel

Stocks can be imported via Django management commands or API endpoints. The system supports bulk import for initial catalog setup.

## Related Documentation

- [Database Data Model](09-database-data-model.md) - Complete database schema
- [Configuration](10-configuration.md) - Investment type classification
- [Allocation Strategies](12-allocation-strategies.md) - Stock allocations in strategies
- [Rebalancing](13-rebalancing.md) - Rebalancing actions using stocks

---

**Document Version**: 1.0  
**Last Updated**: November 2025  
**Status**: Complete

