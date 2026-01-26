# Rebalancing - Specification

This document specifies the Rebalancing application for generating and managing portfolio rebalancing recommendations.

## Overview

The Rebalancing app generates monthly recommendations to help users rebalance their portfolios according to their allocation strategies. It combines:

- **Investment Type Rebalancing**: Adjusts allocations across investment types (Ações, Renda Fixa, etc.)
- **AMBB Strategy Recommendations**: Stock-specific buy/sell recommendations from AMBB strategy
- **Action Tracking**: Tracks individual buy/sell/rebalance actions

## Backend Components

### Models

#### RebalancingRecommendation

**Table**: `rebalancing_recommendations`

**Purpose**: Stores monthly rebalancing recommendations for users based on their allocation strategies.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `user` | ForeignKey | User, CASCADE | User |
| `strategy` | ForeignKey | UserAllocationStrategy, CASCADE | Allocation strategy |
| `recommendation_date` | DateField | Required | Recommendation date |
| `status` | CharField | max_length=20, choices, default='pending' | Recommendation status |
| `created_at` | DateTimeField | auto_now_add=True | Record creation timestamp |
| `updated_at` | DateTimeField | auto_now=True | Last update timestamp |

**Status Choices**:
- `pending`: Recommendation pending user action
- `applied`: Recommendation has been applied
- `dismissed`: Recommendation was dismissed

**Relationships**:
- Many-to-One: `User` (via `user` ForeignKey, related_name='rebalancing_recommendations')
- Many-to-One: `UserAllocationStrategy` (via `strategy` ForeignKey, related_name='recommendations')
- One-to-Many: `RebalancingAction` (via `actions` related_name)

**Meta Options**:
- `db_table`: `rebalancing_recommendations`
- `ordering`: `['-recommendation_date', '-created_at']`

#### RebalancingAction

**Table**: `rebalancing_actions`

**Purpose**: Stores individual buy/sell/rebalance actions within a recommendation.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `recommendation` | ForeignKey | RebalancingRecommendation, CASCADE | Parent recommendation |
| `action_type` | CharField | max_length=20, choices, Required | Action type |
| `stock` | ForeignKey | Stock, SET_NULL, Null | Stock from catalog |
| `current_value` | DecimalField | max_digits=15, decimal_places=2, default=0.0 | Current position value |
| `target_value` | DecimalField | max_digits=15, decimal_places=2, default=0.0 | Target position value |
| `difference` | DecimalField | max_digits=15, decimal_places=2, default=0.0 | Value difference |
| `quantity_to_buy` | IntegerField | Null, Blank | Quantity to buy |
| `quantity_to_sell` | IntegerField | Null, Blank | Quantity to sell |
| `display_order` | IntegerField | default=0 | Display order for UI |

**Action Type Choices**:
- `buy`: Buy action
- `sell`: Sell action
- `rebalance`: Rebalance action

**Relationships**:
- Many-to-One: `RebalancingRecommendation` (via `recommendation` ForeignKey)
- Many-to-One: `Stock` (via `stock` ForeignKey, related_name='rebalancing_actions')

**Meta Options**:
- `db_table`: `rebalancing_actions`
- `ordering`: `['recommendation', 'display_order']`

### API Endpoints

**Base URL**: `http://localhost:8000/api/rebalancing/`

#### List Recommendations
```
GET /api/rebalancing/recommendations/
```

**Query Parameters**:
- `user_id` (string, optional) - Filter by user ID
- `status` (string, optional) - Filter by status (pending, applied, dismissed)

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "user": "user-uuid",
    "user_name": "John Doe",
    "strategy": 1,
    "recommendation_date": "2025-11-15",
    "status": "pending",
    "created_at": "2025-11-15T10:00:00Z",
    "updated_at": "2025-11-15T10:00:00Z",
    "actions": [
      {
        "id": 1,
        "action_type": "buy",
        "stock": {
          "ticker": "PETR4",
          "name": "Petróleo Brasileiro S.A. - Petrobras"
        },
        "current_value": "0.00",
        "target_value": "10000.00",
        "difference": "10000.00",
        "quantity_to_buy": 400,
        "quantity_to_sell": null,
        "display_order": 1
      }
    ]
  }
]
```

#### Get Recommendation
```
GET /api/rebalancing/recommendations/{id}/
```

**Response** (200 OK): Recommendation object with actions

#### Generate Recommendations
```
POST /api/rebalancing/recommendations/generate/
```

**Request Body**:
```json
{
  "user_id": "user-uuid"
}
```

**Response** (201 Created): Generated recommendation object

**Error Response** (400 Bad Request):
```json
{
  "error": "User does not have an allocation strategy"
}
```

#### Apply Recommendation
```
POST /api/rebalancing/recommendations/{id}/apply/
```

**Description**: Marks recommendation as applied.

**Response** (200 OK): Updated recommendation object

#### Dismiss Recommendation
```
POST /api/rebalancing/recommendations/{id}/dismiss/
```

**Description**: Marks recommendation as dismissed.

**Response** (200 OK): Updated recommendation object

### Services

#### RebalancingService

**Location**: `backend/rebalancing/services.py`

**Key Methods**:

- `generate_monthly_recommendations(user: User) -> RebalancingRecommendation`
  - Generates monthly rebalancing recommendations
  - Combines investment type rebalancing with AMBB strategy recommendations
  - Creates recommendation with actions
  - Returns recommendation object

**Recommendation Generation Process**:

1. **Get User Strategy**: Retrieves user's allocation strategy
2. **Calculate Current Allocation**: Gets current portfolio allocation
3. **Compare with Target**: Compares current vs target for each investment type
4. **Generate Type Rebalancing Actions**: Creates rebalance actions for significant differences
5. **Get AMBB Recommendations**: Fetches AMBB strategy recommendations
6. **Generate Stock Actions**: Creates buy/sell/rebalance actions for stocks
7. **Save Recommendation**: Saves recommendation with all actions

## Frontend Components

### Rebalancing Display

Rebalancing recommendations can be displayed in:
- Allocation Strategy component (shows current vs target)
- Dedicated rebalancing view (shows recommendations and actions)
- Portfolio dashboard (shows pending recommendations)

### Integration Points

- **Allocation Strategies**: Recommendations are based on user's allocation strategy
- **AMBB Strategy**: Stock recommendations come from AMBB strategy service
- **Portfolio Operations**: Current allocation is calculated from portfolio positions

## Data Flow

### Generating Recommendations

1. User requests recommendation generation
2. System checks if user has allocation strategy
3. System calculates current portfolio allocation
4. System compares current vs target allocation
5. System generates investment type rebalancing actions
6. System fetches AMBB strategy recommendations
7. System generates stock buy/sell/rebalance actions
8. System creates recommendation with all actions
9. System returns recommendation to user

### Applying Recommendations

1. User reviews recommendation
2. User executes actions (buys/sells stocks)
3. User marks recommendation as applied
4. System updates recommendation status
5. System updates recommendation timestamp

### Dismissing Recommendations

1. User decides not to follow recommendation
2. User dismisses recommendation
3. System updates recommendation status to "dismissed"
4. Recommendation remains in history

## Integration with Other Apps

### Allocation Strategies App
- Recommendations are based on user's allocation strategy
- Compares current allocation with target allocation

### AMBB Strategy App
- Fetches stock-specific recommendations from AMBB strategy
- Combines with allocation strategy recommendations

### Portfolio Operations App
- Calculates current allocation from portfolio positions
- Uses PortfolioPosition model for current values

### Stocks App
- Actions reference stocks from the catalog
- Uses stock prices for value calculations

## Common Use Cases

### Monthly Rebalancing

1. User generates monthly recommendation
2. System shows:
   - Investment type adjustments needed
   - Stocks to buy
   - Stocks to sell
   - Stocks to rebalance
3. User reviews recommendations
4. User executes trades
5. User marks recommendation as applied

### Reviewing Recommendations

1. User views pending recommendations
2. System displays:
   - Recommendation date
   - List of actions
   - Current vs target values
   - Quantities to buy/sell
3. User can apply or dismiss

## ETF Renda Fixa Rebalancing

### Overview

The ETF Renda Fixa feature allows users to allocate a portion of their Renda Fixa investment type to fixed income ETFs (like AUPO11). This provides:

- Single ETF selection per "ETF Renda Fixa" sub-type
- Stock-level rebalancing recommendations with buy/sell quantities
- Integration with existing Renda Fixa allocation

### How It Works

1. **Configuration**: User selects an ETF (e.g., AUPO11) in the allocation strategy under Renda Fixa > ETF Renda Fixa
2. **Price Retrieval**: System fetches current ETF price from stock catalog (can be updated via Yahoo Finance)
3. **Recommendation Generation**: When generating rebalancing recommendations:
   - Calculate target value based on sub-type percentage × total portfolio value
   - Get current position value from portfolio
   - Calculate quantity to buy/sell: (target - current) ÷ current_price
4. **Display**: Shows in Renda Fixa section with columns: Ticker, Nome, Valor Atual, Valor Alvo, Diferença, Ação

### RebalancingAction Fields for ETF Renda Fixa

| Field | Description |
|-------|-------------|
| `stock` | ETF stock (e.g., AUPO11) |
| `investment_subtype` | ETF_RENDA_FIXA sub-type |
| `current_value` | Current position value |
| `target_value` | Target value from allocation |
| `difference` | Target - Current |
| `quantity_to_buy` | Number of ETF shares to buy |
| `quantity_to_sell` | Number of ETF shares to sell |

### Example

```
ETF Renda Fixa sub-type: 7.6% allocation
Total portfolio: R$ 231,655.26
Target value: R$ 17,605.76

ETF selected: AUPO11
Current price: R$ 101.41
Current position: R$ 0.00

Recommendation: Comprar 173 (R$ 17,605.76 ÷ R$ 101.41 = 173 shares)
```

## Validation Rules

### Recommendation Generation
- User must have an allocation strategy
- Current portfolio must have positions
- Target allocation must be defined
- ETF Renda Fixa: ETF must have valid current_price for quantity calculation

### Action Creation
- Actions must have valid stock (if stock-specific)
- Values must be positive
- Quantities must be positive integers

## Error Handling

### Common Errors

**400 Bad Request**:
- User does not have allocation strategy
- Missing user_id
- Invalid user_id

**404 Not Found**:
- User not found
- Recommendation not found

**500 Internal Server Error**:
- Error calculating current allocation
- Error generating AMBB recommendations
- Database error

## Related Documentation

- [Database Data Model](09-database-data-model.md) - Complete database schema
- [Allocation Strategies](12-allocation-strategies.md) - Allocation strategy definitions
- [AMBB Strategy](README.md#ambb-strategy-api) - AMBB strategy recommendations
- [Portfolio Summary](04-portfolio-summary.md) - Portfolio positions

---

**Document Version**: 1.1  
**Last Updated**: January 2026  
**Status**: Complete

## Change Log

### Version 1.1 (January 2026)
- Added ETF Renda Fixa rebalancing feature documentation
- Stock-level recommendations for ETF Renda Fixa sub-type
- Quantity calculation based on ETF current price

