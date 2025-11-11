# Portfolio Summary - Specification

This document specifies the Portfolio Summary application for viewing portfolio positions, operations, and analytics.

## Overview

The Portfolio Summary app allows users to:
- View current portfolio positions aggregated by ticker
- See realized profit/loss calculated using FIFO method
- View portfolio analytics (total invested, number of assets)
- Track all tickers including those with zero quantity (for realized profit history)

## Architecture Overview

The portfolio system uses a backend-driven architecture:
- **Backend**: Django REST API with `PortfolioService` managing `portfolio.json` file
- **Frontend**: Angular service consuming backend API
- **Data Flow**: Portfolio is automatically refreshed after brokerage note upload/delete
- **Calculation**: FIFO (First In, First Out) method for realized profit

## Data Models

### Portfolio JSON Structure

Portfolio data is stored in `backend/data/portfolio.json` with the following structure:

```json
{
  "user-id-1": [
    {
      "titulo": "PETR4",
      "quantidade": 100,
      "precoMedio": 25.50,
      "valorTotalInvestido": 2550.00,
      "lucroRealizado": 150.00
    },
    {
      "titulo": "VALE3",
      "quantidade": 0,
      "precoMedio": 0.00,
      "valorTotalInvestido": 0.00,
      "lucroRealizado": -50.00
    }
  ],
  "user-id-2": [...]
}
```

**Key Points:**
- Top-level keys are `user_id` values (not user names)
- Each user has an array of ticker summaries
- All tickers are included, even with `quantidade: 0` (preserves realized profit history)
- `lucroRealizado` accumulates realized profit/loss from all sales

### Ticker Summary Fields

| Field | Type | Description |
|-------|------|-------------|
| `titulo` | string | Stock ticker code (e.g., "PETR4", "VALE3") |
| `quantidade` | number | Current quantity held (can be 0) |
| `precoMedio` | number | Weighted average purchase price |
| `valorTotalInvestido` | number | Total invested value (current holdings) |
| `lucroRealizado` | number | Cumulative realized profit/loss (FIFO method) |

### Frontend Position Model

```typescript
export interface Position {
  titulo: string;                    // Stock ticker
  quantidadeTotal: number;            // Current quantity
  precoMedioPonderado: number;       // Weighted average price
  valorTotalInvestido: number;       // Total invested
  lucroRealizado: number;            // Realized profit/loss (FIFO)
  valorAtualEstimado?: number;       // Optional: current market value
  lucroPrejuizoNaoRealizado?: number; // Optional: unrealized P&L
}
```

## Business Logic: FIFO Realized Profit Calculation

### Overview

Realized profit is calculated using the **FIFO (First In, First Out)** method:
- When shares are sold, they are matched against the oldest purchases first
- Profit = (Sale Price - Purchase Price) × Quantity Sold
- Cumulative realized profit is tracked per ticker

### FIFO Algorithm

1. **Purchase Operations (C)**:
   - Add to purchase queue with: `{quantidade, preco, data, ordem}`
   - Update weighted average price for current holdings
   - Increase `quantidade` and `valorTotalInvestido`

2. **Sale Operations (V)**:
   - Match against purchase queue in chronological order (oldest first)
   - Calculate profit: `(sale_price - purchase_price) × quantity_matched`
   - Update `lucroRealizado` (cumulative)
   - Reduce `quantidade` and `valorTotalInvestido`
   - Remove matched purchases from queue

### Example Calculation

**Purchases:**
- Day 1: Buy 100 shares @ R$ 20.00
- Day 5: Buy 50 shares @ R$ 25.00

**Sale:**
- Day 10: Sell 80 shares @ R$ 30.00

**FIFO Matching:**
- Match 80 shares against Day 1 purchase (oldest first)
- Profit = (30.00 - 20.00) × 80 = R$ 800.00
- Remaining: 20 shares @ R$ 20.00, 50 shares @ R$ 25.00

**Result:**
- `quantidade`: 70 (100 + 50 - 80)
- `precoMedio`: Weighted average of remaining shares
- `lucroRealizado`: R$ 800.00

## Backend Components

### PortfolioService

**Location**: `backend/portfolio_operations/services.py`

**Key Methods:**

- `load_portfolio() -> Dict[str, List[Dict]]`
  - Loads `portfolio.json` from `backend/data/portfolio.json`
  - Returns dictionary keyed by `user_id`

- `save_portfolio(portfolio: Dict[str, List[Dict]]) -> None`
  - Saves portfolio to JSON file

- `get_user_portfolio(user_id: str) -> List[Dict]`
  - Returns ticker summaries for a specific user
  - Returns empty list if user not found

- `process_operations_fifo(operations: List[Dict]) -> Dict[str, Dict]`
  - Processes operations chronologically using FIFO
  - Returns ticker summaries dictionary

- `calculate_fifo_profit(sale_quantity, sale_price, purchase_queue) -> Tuple[float, List[Dict]]`
  - Calculates realized profit for a sale operation
  - Returns (profit, updated_purchase_queue)

- `refresh_portfolio_from_brokerage_notes() -> None`
  - Rebuilds entire `portfolio.json` from all brokerage notes
  - Processes all operations chronologically
  - Groups by user_id and calculates ticker summaries

### API Endpoints

**Base URL**: `http://localhost:8000`

#### Get User Portfolio
```
GET /api/portfolio/?user_id={user_id}
```

**Response:**
```json
[
  {
    "titulo": "PETR4",
    "quantidade": 100,
    "precoMedio": 25.50,
    "valorTotalInvestido": 2550.00,
    "lucroRealizado": 150.00
  }
]
```

#### Manual Portfolio Refresh
```
POST /api/portfolio/refresh/
```

**Response:**
```json
{
  "success": true,
  "message": "Portfolio refreshed successfully",
  "users_count": 2,
  "total_positions": 15
}
```

**Note**: Portfolio is automatically refreshed after:
- Brokerage note upload (`POST /api/brokerage-notes/`)
- Brokerage note deletion (`DELETE /api/brokerage-notes/{id}/`)

### Django Management Command

Manually refresh portfolio from command line:

```bash
cd backend
python manage.py refresh_portfolio
```

**Location**: `backend/portfolio_operations/management/commands/refresh_portfolio.py`

**Output**: Displays summary of refreshed portfolio including:
- Number of users
- Total ticker positions
- Active positions vs zero-quantity positions
- Total realized profit per user

## Frontend Components

### PortfolioService

**Location**: `frontend/src/app/portfolio/portfolio.service.ts`

**Key Methods:**

- `getPositionsAsync(clientId: string): Observable<Position[]>`
  - Fetches portfolio from backend API: `GET /api/portfolio/?user_id={clientId}`
  - Maps backend format to `Position` interface
  - Falls back to calculation from operations if API fails

- `calculatePositions(clientId: string, operations?: Operation[]): Position[]`
  - Fallback calculation method (simplified, not full FIFO)
  - Used when backend API is unavailable
  - Note: Full FIFO calculation is done on backend

### Portfolio Component

**Location**: `frontend/src/app/portfolio/portfolio.html`

**Features:**
- Displays positions table with columns:
  - Título
  - Quantidade
  - Preço Médio
  - Valor Total Investido
  - **Lucro Realizado** (with color coding: green for profit, red for loss)
- Shows all tickers including zero-quantity positions
- Currency formatting (BRL, R$)
- Loading and error states

## Integration Flow

### Automatic Portfolio Refresh

1. User uploads brokerage note PDF
2. PDF parsed, operations extracted
3. Note saved to `brokerage_notes.json`
4. **`PortfolioService.refresh_portfolio_from_brokerage_notes()` called automatically**
5. All operations from all notes processed chronologically
6. Portfolio recalculated for all users using FIFO
7. `portfolio.json` updated
8. Frontend displays updated portfolio

### Manual Refresh

- User can trigger refresh via `POST /api/portfolio/refresh/`
- Useful for:
  - Initial setup
  - Data recovery
  - Testing

## Data Persistence

### Backend Storage

- **Portfolio**: `backend/data/portfolio.json`
- **Brokerage Notes**: `backend/data/brokerage_notes.json` (source of truth)
- **Users**: `backend/data/users.json`

### Data Flow

```
brokerage_notes.json (source)
    ↓
PortfolioService.refresh_portfolio_from_brokerage_notes()
    ↓
portfolio.json (aggregated summary)
    ↓
Frontend API call
    ↓
Display to user
```

**Important**: Portfolio is derived data, not manually edited. Always refresh from brokerage notes.

## UI/UX Requirements

### Portfolio Display

- **Positions Table**:
  - Sortable columns
  - Color coding for `lucroRealizado`:
    - Green: Positive values (profit)
    - Red: Negative values (loss)
  - Show all tickers (including zero quantity)
  - Currency formatting: R$ X.XXX,XX

- **Summary Cards** (if implemented):
  - Total Investido
  - Ativos na Carteira
  - Lucro Realizado Total

### Loading States

- Show loading indicator while fetching portfolio
- Handle API errors gracefully
- Fallback to operation-based calculation if needed

## Legacy Endpoints (Deprecated)

The following endpoints are deprecated but kept for backward compatibility:

- `GET /api/portfolio-operations/` - Returns HTTP 200 but redirects to new endpoint
- `GET /api/portfolio-operations/{id}/` - Returns HTTP 410 GONE
- `DELETE /api/portfolio-operations/{id}/` - Returns HTTP 410 GONE

**Migration**: Use `/api/portfolio/` endpoints instead.

---

**Related Documents**:  
- [Main Specification](README.md)  
- [User Management](01-user-management.md)  
- [Brokerage Note Processing](02-brokerage-note-processing.md)  
- [Brokerage History](03-brokerage-history.md)
