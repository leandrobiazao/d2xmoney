# Fixed Income - Specification

This document specifies the Fixed Income application for managing CDB, Tesouro Direto, and other fixed income investment positions.

## Overview

The Fixed Income app tracks fixed income investment positions with detailed financial metrics, including CDB, LCI, LCA, Debêntures, and Tesouro Direto (Brazilian government bonds).

## Backend Components

### Models

#### FixedIncomePosition

**Table**: `fixed_income_positions`

**Purpose**: Tracks CDB and other fixed income investment positions with detailed financial metrics.

**Key Fields**:
- `user_id`, `asset_name`, `asset_code`
- Dates: `application_date`, `grace_period_end`, `maturity_date`, `price_date`
- Financial: `rate`, `price`, `quantity`, `applied_value`, `position_value`, `net_value`
- Yields: `gross_yield`, `net_yield`
- Taxes: `income_tax`, `iof`
- Attributes: `rating`, `liquidity`, `interest`
- Classification: `investment_type`, `investment_sub_type`
- Metadata: `source`, `import_date`

See [09-database-data-model.md](09-database-data-model.md) for complete field specifications.

#### TesouroDiretoPosition

**Table**: `tesouro_direto_positions`

**Purpose**: Stores Brazilian government bond (Tesouro Direto) specific information.

**Key Fields**:
- `fixed_income_position` (OneToOne link)
- `titulo_name` (e.g., "Tesouro IPCA+ 2029")
- `vencimento` (maturity date)

### API Endpoints

**Base URL**: `http://localhost:8000/api/fixed-income/`

#### List Positions
```
GET /api/fixed-income/positions/?user_id={user_id}&investment_type={type}
```

#### Create Position
```
POST /api/fixed-income/positions/
```

#### Get Position
```
GET /api/fixed-income/positions/{id}/
```

#### Update Position
```
PUT /api/fixed-income/positions/{id}/
PATCH /api/fixed-income/positions/{id}/
```

#### Delete Position
```
DELETE /api/fixed-income/positions/{id}/
```

#### Import from Excel
```
POST /api/fixed-income/positions/import-excel/
```

**Request**: multipart/form-data
- `file` (file, required)
- `user_id` (string, required)

**Response**:
```json
{
  "success": true,
  "imported": 10,
  "errors": []
}
```

#### Tesouro Direto Positions
```
GET /api/fixed-income/tesouro-direto/?user_id={user_id}
POST /api/fixed-income/tesouro-direto/
GET /api/fixed-income/tesouro-direto/{id}/
PUT /api/fixed-income/tesouro-direto/{id}/
DELETE /api/fixed-income/tesouro-direto/{id}/
```

## Frontend Components

### FixedIncomeListComponent

**Location**: `frontend/src/app/fixed-income/fixed-income-list.component.ts`

**Features**:
- List all fixed income positions
- Filter by user and investment type
- Display position details
- Import from Excel

### FixedIncomeService

**Location**: `frontend/src/app/fixed-income/fixed-income.service.ts`

**Methods**:
- `getPositions(userId?, investmentType?)`
- `getPositionById(id)`
- `createPosition(position)`
- `updatePosition(id, position)`
- `deletePosition(id)`
- `importExcel(file, userId)`
- `getTesouroDiretoPositions(userId?)`

## Integration

- **Configuration App**: Uses InvestmentType and InvestmentSubType for classification
- **Portfolio Operations**: Fixed income positions contribute to portfolio value
- **Allocation Strategies**: Fixed income positions are included in allocation calculations

## Related Documentation

- [Database Data Model](09-database-data-model.md) - Complete schema
- [Configuration](10-configuration.md) - Investment types

---

**Document Version**: 1.0  
**Last Updated**: November 2025  
**Status**: Complete

