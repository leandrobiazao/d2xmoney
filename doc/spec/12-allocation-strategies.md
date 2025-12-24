# Allocation Strategies - Specification

This document specifies the Allocation Strategies application for defining and managing portfolio allocation strategies for users.

## Overview

The Allocation Strategies app allows users to define target portfolio allocations across investment types, sub-types, and individual stocks. The system supports:

- **User Allocation Strategy**: One strategy per user
- **Investment Type Allocations**: Target percentages for each investment type (e.g., 60% Ações, 30% Renda Fixa, 10% Tesouro Direto)
- **Sub-Type Allocations**: Target percentages within investment types (e.g., 50% CDB, 30% LCI, 20% LCA within Renda Fixa)
- **Stock Allocations**: Target percentages for specific stocks (e.g., 20% PETR4, 15% VALE3 within Ações)
- **FII Allocations**: Manual selection of up to 5 FIIs (Fundos Imobiliários) with individual percentages, bypassing subtype allocations

## Backend Components

### Models

#### UserAllocationStrategy

**Table**: `user_allocation_strategies`

**Purpose**: Links a user to their allocation strategy and stores total portfolio value.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `user` | OneToOneField | User, CASCADE | User (one strategy per user) |
| `total_portfolio_value` | DecimalField | max_digits=15, decimal_places=2, Null | Total portfolio value |
| `created_at` | DateTimeField | auto_now_add=True | Record creation timestamp |
| `updated_at` | DateTimeField | auto_now=True | Last update timestamp |

**Relationships**:
- One-to-One: `User` (via `user` OneToOneField, related_name='allocation_strategy')
- One-to-Many: `InvestmentTypeAllocation` (via `type_allocations` related_name)
- One-to-Many: `RebalancingRecommendation` (via `recommendations` related_name)

**Meta Options**:
- `db_table`: `user_allocation_strategies`
- `ordering`: `['user__name']`

#### InvestmentTypeAllocation

**Table**: `investment_type_allocations`

**Purpose**: Defines target allocation percentage for each investment type within a user's strategy.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `strategy` | ForeignKey | UserAllocationStrategy, CASCADE | Parent strategy |
| `investment_type` | ForeignKey | InvestmentType, CASCADE | Investment type |
| `target_percentage` | DecimalField | max_digits=5, decimal_places=2, validators | Target allocation percentage (0-100) |
| `display_order` | IntegerField | default=0 | Display order for UI |

**Validators**:
- `MinValueValidator(Decimal('0'))`
- `MaxValueValidator(Decimal('100'))`

**Relationships**:
- Many-to-One: `UserAllocationStrategy` (via `strategy` ForeignKey)
- Many-to-One: `InvestmentType` (via `investment_type` ForeignKey)
- One-to-Many: `SubTypeAllocation` (via `sub_type_allocations` related_name)
- One-to-Many: `FIIAllocation` (via `fii_allocations` related_name)

**Meta Options**:
- `db_table`: `investment_type_allocations`
- `ordering`: `['strategy', 'display_order']`
- `unique_together`: `[['strategy', 'investment_type']]`

#### SubTypeAllocation

**Table**: `sub_type_allocations`

**Purpose**: Defines sub-allocation percentages within an investment type allocation.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `type_allocation` | ForeignKey | InvestmentTypeAllocation, CASCADE | Parent type allocation |
| `sub_type` | ForeignKey | InvestmentSubType, SET_NULL, Null | Investment sub-type (optional) |
| `custom_name` | CharField | max_length=255, Null, Blank | Custom name if no sub-type |
| `target_percentage` | DecimalField | max_digits=5, decimal_places=2, validators | Target allocation percentage (0-100) |
| `display_order` | IntegerField | default=0 | Display order for UI |

**Validators**:
- `MinValueValidator(Decimal('0'))`
- `MaxValueValidator(Decimal('100'))`

**Relationships**:
- Many-to-One: `InvestmentTypeAllocation` (via `type_allocation` ForeignKey)
- Many-to-One: `InvestmentSubType` (via `sub_type` ForeignKey, related_name='allocations')
- One-to-Many: `StockAllocation` (via `stock_allocations` related_name)

**Meta Options**:
- `db_table`: `sub_type_allocations`
- `ordering`: `['type_allocation', 'display_order']`

#### StockAllocation

**Table**: `stock_allocations`

**Purpose**: Defines specific stock allocations within a sub-type allocation (for Ações strategies).

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `sub_type_allocation` | ForeignKey | SubTypeAllocation, CASCADE | Parent sub-type allocation |
| `stock` | ForeignKey | Stock, CASCADE | Stock from catalog |
| `target_percentage` | DecimalField | max_digits=5, decimal_places=2, validators | Target allocation percentage (0-100) |
| `display_order` | IntegerField | default=0 | Display order for UI |

**Validators**:
- `MinValueValidator(Decimal('0'))`
- `MaxValueValidator(Decimal('100'))`

**Relationships**:
- Many-to-One: `SubTypeAllocation` (via `sub_type_allocation` ForeignKey)
- Many-to-One: `Stock` (via `stock` ForeignKey, related_name='allocations')

**Meta Options**:
- `db_table`: `stock_allocations`
- `ordering`: `['sub_type_allocation', 'display_order']`
- `unique_together`: `[['sub_type_allocation', 'stock']]`

#### FIIAllocation

**Table**: `fii_allocations`

**Purpose**: Defines FII allocations linking directly to InvestmentTypeAllocation (bypassing subtypes). Allows manual selection of up to 5 FIIs from the catalog with individual allocation percentages.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `type_allocation` | ForeignKey | InvestmentTypeAllocation, CASCADE | Parent type allocation |
| `stock` | ForeignKey | Stock, CASCADE | FII stock (stock_class='FII') from catalog |
| `target_percentage` | DecimalField | max_digits=5, decimal_places=2, validators | Target allocation percentage (0-100) |
| `display_order` | IntegerField | default=0 | Display order for UI |

**Validators**:
- `MinValueValidator(Decimal('0'))`
- `MaxValueValidator(Decimal('100'))`

**Relationships**:
- Many-to-One: `InvestmentTypeAllocation` (via `type_allocation` ForeignKey)
- Many-to-One: `Stock` (via `stock` ForeignKey, related_name='fii_allocations')

**Meta Options**:
- `db_table`: `fii_allocations`
- `ordering`: `['type_allocation', 'display_order']`
- `unique_together`: `[['type_allocation', 'stock']]`

**Business Rules**:
- Maximum 5 FIIs per InvestmentTypeAllocation
- FII allocations must sum to 100% of the parent type allocation percentage
- Only FII stocks (stock_class='FII') can be allocated
- Used only for "Fundos Imobiliários" investment type (bypasses subtype allocations)

### API Endpoints

**Base URL**: `http://localhost:8000/api/allocation-strategies/`

#### List Allocation Strategies
```
GET /api/allocation-strategies/allocation-strategies/
```

**Query Parameters**:
- `user_id` (string, optional) - Filter by user ID

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "user": "user-uuid",
    "user_name": "John Doe",
    "total_portfolio_value": "100000.00",
    "created_at": "2025-11-15T10:00:00Z",
    "updated_at": "2025-11-15T10:00:00Z",
    "type_allocations": [
      {
        "id": 1,
        "investment_type": {
          "id": 1,
          "name": "Ações",
          "code": "ACOES"
        },
        "target_percentage": "60.00",
        "display_order": 1,
        "sub_type_allocations": [...]
      }
    ]
  }
]
```

#### Get Allocation Strategy
```
GET /api/allocation-strategies/allocation-strategies/{id}/
```

**Response** (200 OK): Allocation strategy object

#### Create or Update Strategy
```
POST /api/allocation-strategies/allocation-strategies/create_strategy/
```

**Request Body**:
```json
{
  "user_id": "user-uuid",
  "total_portfolio_value": "100000.00",
  "type_allocations": [
    {
      "investment_type_id": 1,
      "target_percentage": 60.00,
      "display_order": 1,
      "sub_type_allocations": [
        {
          "sub_type_id": 1,
          "target_percentage": 50.00,
          "display_order": 1,
          "stock_allocations": [
            {
              "stock_id": 1,
              "target_percentage": 20.00,
              "display_order": 1
            }
          ]
        }
      ]
    },
    {
      "investment_type_id": 2,
      "target_percentage": 20.00,
      "display_order": 2,
      "sub_type_allocations": [],
      "fii_allocations": [
        {
          "stock_id": 10,
          "target_percentage": 8.00,
          "display_order": 0
        },
        {
          "stock_id": 11,
          "target_percentage": 7.00,
          "display_order": 1
        },
        {
          "stock_id": 12,
          "target_percentage": 5.00,
          "display_order": 2
        }
      ]
    }
  ]
}
```

**Validation**:
- Investment type allocations must sum to 100%
- Sub-type allocations within a type must sum to 100% (or match type percentage)
- Stock allocations within a sub-type must sum to 100%
- FII allocations: Maximum 5 FIIs per type allocation
- FII allocations within a type must sum to 100% of the type allocation percentage

**Response** (201 Created): Created/updated strategy object

#### Get Current vs Target Allocation
```
GET /api/allocation-strategies/allocation-strategies/current_vs_target/?user_id={user_id}
```

**Response** (200 OK):
```json
{
  "current": {
    "investment_types": [
      {
        "investment_type_id": 1,
        "investment_type_name": "Ações",
        "current_value": "55000.00",
        "current_percentage": "55.00"
      }
    ],
    "total_value": "100000.00",
    "unallocated_cash": "0.00"
  },
  "target": {
    "id": 1,
    "type_allocations": [...]
  }
}
```

#### Get Pie Chart Data
```
GET /api/allocation-strategies/allocation-strategies/pie_chart_data/?user_id={user_id}
```

**Response** (200 OK):
```json
{
  "target": {
    "labels": ["Ações", "Renda Fixa", "Tesouro Direto"],
    "data": [60.0, 30.0, 10.0],
    "colors": ["#0071e3", "#86868b", "#1d1d1f"]
  },
  "current": {
    "labels": ["Ações", "Renda Fixa"],
    "data": [55.0, 35.0],
    "colors": ["#0071e3", "#86868b"]
  }
}
```

## Frontend Components

### AllocationStrategyComponent

**Location**: `frontend/src/app/allocation-strategies/allocation-strategy.component.ts`

**Purpose**: Main component for managing user allocation strategies.

**Features**:
- User selection
- Strategy creation and editing
- Investment type allocation management
- Sub-type allocation management
- Stock allocation management
- FII allocation management (manual selection, max 5 FIIs)
- Percentage validation (must sum to 100%)
- Pie chart visualization
- Current vs target comparison

**Key Methods**:
- `loadStrategy(userId: string)` - Load user's strategy
- `createNewStrategy()` - Initialize new strategy
- `onSaveStrategy()` - Save strategy
- `loadPieChartData(userId: string)` - Load pie chart data

### AllocationStrategyService

**Location**: `frontend/src/app/allocation-strategies/allocation-strategy.service.ts`

**Methods**:
- `getAllocationStrategies(userId?: string): Observable<UserAllocationStrategy[]>`
- `getAllocationStrategy(id: number): Observable<UserAllocationStrategy>`
- `createOrUpdateStrategy(userId: string, typeAllocations: any[], totalPortfolioValue?: number): Observable<UserAllocationStrategy>`
- `getCurrentVsTarget(userId: string): Observable<any>`
- `getPieChartData(userId: string): Observable<PieChartData>`

## Data Flow

### Creating a Strategy

1. User selects a user
2. System checks if strategy exists
3. If not, user clicks "Configure Strategy"
4. System loads all investment types
5. User sets target percentages for each type (must sum to 100%)
6. User optionally sets sub-type allocations (must sum to 100% within each type)
7. User optionally sets stock allocations (must sum to 100% within each sub-type)
8. User saves strategy
9. System validates percentages sum to 100% at each level
10. System creates/updates strategy

### Calculating Current Allocation

1. System loads user's portfolio positions
2. System groups positions by investment type (via stock catalog)
3. System calculates current value and percentage for each type
4. System compares with target allocation
5. System generates rebalancing recommendations (see Rebalancing app)

## Validation Rules

### Percentage Validation

- **Investment Type Allocations**: Must sum to exactly 100%
- **Sub-Type Allocations**: Must sum to exactly 100% within each investment type (or match type percentage)
- **Stock Allocations**: Must sum to exactly 100% within each sub-type
- **FII Allocations**: Must sum to exactly 100% of the parent type allocation percentage (max 5 FIIs)
- **Tolerance**: 0.01% rounding difference allowed

### Business Rules

- One strategy per user (enforced by OneToOne relationship)
- Investment types must exist in Configuration app
- Sub-types must exist in Configuration app (if referenced)
- Stocks must exist in Stock catalog (if referenced)
- FIIs must exist in FII catalog and have stock_class='FII'
- Maximum 5 FIIs per Fundos Imobiliários investment type allocation
- Percentages must be between 0 and 100
- FII allocations bypass subtype allocations (used instead of subtypes for FII investment type)

## Integration with Other Apps

### Users App
- Strategies are linked to users via OneToOne relationship

### Configuration App
- Strategies reference InvestmentType and InvestmentSubType
- Types and sub-types are managed in Configuration app

### Stocks App
- Stock allocations reference stocks from the catalog

### Portfolio Operations App
- Current allocation is calculated from portfolio positions
- Uses PortfolioPosition model to determine current values

### Rebalancing App
- Strategies are used to generate rebalancing recommendations
- Recommendations compare current vs target allocations

## Common Use Cases

### Setting Up a Strategy

1. User selects their account
2. User clicks "Configure Strategy"
3. User sets:
   - 60% Ações
   - 30% Renda Fixa
     - 50% CDB
     - 30% LCI
     - 20% LCA
   - 10% Tesouro Direto
4. User saves strategy

### Viewing Current vs Target

1. User selects their account
2. System displays:
   - Current allocation (from portfolio)
   - Target allocation (from strategy)
   - Difference (for rebalancing)

### Pie Chart Visualization

1. System loads pie chart data
2. Displays two pie charts:
   - Target allocation
   - Current allocation
3. User can compare visually

## Error Handling

### Common Errors

**400 Bad Request**:
- Percentages don't sum to 100%
- Invalid investment type ID
- Invalid sub-type ID
- Invalid stock ID
- Missing required fields

**404 Not Found**:
- User not found
- Strategy not found

**500 Internal Server Error**:
- Database error
- Calculation error

## Related Documentation

- [Database Data Model](09-database-data-model.md) - Complete database schema
- [Configuration](10-configuration.md) - Investment types and sub-types
- [Stocks](11-stocks.md) - Stock catalog
- [Rebalancing](13-rebalancing.md) - Rebalancing recommendations
- [Portfolio Summary](04-portfolio-summary.md) - Portfolio positions

---

**Document Version**: 1.0  
**Last Updated**: November 2025  
**Status**: Complete

