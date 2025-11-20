# Investment Configuration - Specification

This document specifies the Investment Configuration application for managing investment types and sub-types used throughout the portfolio management system.

## Overview

The Investment Configuration app provides a hierarchical classification system for investments:
- **Investment Types**: Base categories (e.g., "Ações", "Renda Fixa", "Tesouro Direto")
- **Investment Sub-Types**: Sub-categories within types (e.g., "CDB", "LCI", "LCA" under "Renda Fixa")

This classification system is used to:
- Classify stocks in the stock catalog
- Classify fixed income positions
- Organize allocation strategies
- Filter and group investments in reports

## Backend Components

### Models

#### InvestmentType

**Table**: `investment_types`

**Purpose**: Base investment categories for classifying investments.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `name` | CharField | max_length=255, unique=True | Investment type name (e.g., "Ações") |
| `code` | CharField | max_length=50, unique=True, db_index=True | Type code (e.g., "ACOES") |
| `display_order` | IntegerField | default=0 | Display order for UI |
| `is_active` | BooleanField | default=True | Active status |

**Relationships**:
- One-to-Many: `InvestmentSubType` (via `sub_types` related_name)
- One-to-Many: `Stock` (via `stocks` related_name)
- One-to-Many: `FixedIncomePosition` (via `fixed_income_positions` related_name)
- One-to-Many: `InvestmentTypeAllocation` (via `allocations` related_name)

**Meta Options**:
- `db_table`: `investment_types`
- `ordering`: `['display_order', 'name']`

#### InvestmentSubType

**Table**: `investment_sub_types`

**Purpose**: Sub-categories within investment types.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `investment_type` | ForeignKey | InvestmentType, CASCADE | Parent investment type |
| `name` | CharField | max_length=255 | Sub-type name (e.g., "CDB") |
| `code` | CharField | max_length=50, db_index=True | Sub-type code (e.g., "CDB") |
| `display_order` | IntegerField | default=0 | Display order for UI |
| `is_predefined` | BooleanField | default=False | Whether sub-type is predefined |
| `is_active` | BooleanField | default=True | Active status |

**Relationships**:
- Many-to-One: `InvestmentType` (via `investment_type` ForeignKey)
- One-to-Many: `FixedIncomePosition` (via `fixed_income_positions` related_name)
- One-to-Many: `SubTypeAllocation` (via `allocations` related_name)

**Meta Options**:
- `db_table`: `investment_sub_types`
- `ordering`: `['investment_type', 'display_order', 'name']`
- `unique_together`: `[['investment_type', 'code']]`

### API Endpoints

**Base URL**: `http://localhost:8000/api/configuration/`

#### Investment Types

##### List Investment Types
```
GET /api/configuration/investment-types/
```

**Query Parameters**:
- `active_only` (boolean, default: true) - Filter only active types

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "name": "Ações",
    "code": "ACOES",
    "display_order": 1,
    "is_active": true,
    "sub_types": [
      {
        "id": 1,
        "name": "ON",
        "code": "ON",
        "display_order": 1,
        "is_predefined": true,
        "is_active": true
      }
    ]
  }
]
```

##### Create Investment Type
```
POST /api/configuration/investment-types/
```

**Request Body**:
```json
{
  "name": "Ações",
  "code": "ACOES",
  "display_order": 1,
  "is_active": true
}
```

**Response** (201 Created): Investment type object

##### Get Investment Type
```
GET /api/configuration/investment-types/{id}/
```

**Response** (200 OK): Investment type object with sub-types

##### Update Investment Type
```
PUT /api/configuration/investment-types/{id}/
PATCH /api/configuration/investment-types/{id}/
```

**Request Body**: Partial or full investment type object

**Response** (200 OK): Updated investment type object

##### Delete Investment Type
```
DELETE /api/configuration/investment-types/{id}/
```

**Response** (204 No Content)

**Note**: Deleting an investment type will cascade delete all associated sub-types.

#### Investment Sub-Types

##### List Investment Sub-Types
```
GET /api/configuration/investment-subtypes/
```

**Query Parameters**:
- `investment_type_id` (integer, optional) - Filter by investment type
- `active_only` (boolean, default: true) - Filter only active sub-types

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "name": "CDB",
    "code": "CDB",
    "display_order": 1,
    "is_predefined": true,
    "is_active": true
  }
]
```

##### Create Investment Sub-Type
```
POST /api/configuration/investment-subtypes/
```

**Request Body**:
```json
{
  "investment_type": 2,
  "name": "CDB",
  "code": "CDB",
  "display_order": 1,
  "is_predefined": false,
  "is_active": true
}
```

**Response** (201 Created): Investment sub-type object

##### Get Investment Sub-Type
```
GET /api/configuration/investment-subtypes/{id}/
```

**Response** (200 OK): Investment sub-type object

##### Update Investment Sub-Type
```
PUT /api/configuration/investment-subtypes/{id}/
PATCH /api/configuration/investment-subtypes/{id}/
```

**Request Body**: Partial or full investment sub-type object

**Response** (200 OK): Updated investment sub-type object

##### Delete Investment Sub-Type
```
DELETE /api/configuration/investment-subtypes/{id}/
```

**Response** (204 No Content)

##### Import Sub-Types from Excel
```
POST /api/configuration/investment-subtypes/import_excel/
```

**Request**: multipart/form-data
- `file` (file, required) - Excel file
- `investment_type_code` (string, required) - Investment type code
- `sheet_name` (string, optional) - Sheet name (default: first sheet)

**Excel Format**:
- Column A: Sub-type name
- Column B: Sub-type code
- Column C: Display order (optional)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Imported 5 sub-types",
  "count": 5,
  "created": [...],
  "updated": [...]
}
```

## Frontend Components

### ConfigurationComponent

**Location**: `frontend/src/app/configuration/configuration.component.ts`

**Purpose**: Main component for managing investment types and sub-types.

**Features**:
- Tab-based interface (Types / Sub-Types)
- List all investment types
- Create, update, delete investment types
- Manage sub-types for each type
- Excel import functionality

**Child Components**:
- `InvestmentTypesComponent` - Manages investment types
- `InvestmentSubtypesComponent` - Manages investment sub-types

### ConfigurationService

**Location**: `frontend/src/app/configuration/configuration.service.ts`

**Methods**:
- `getInvestmentTypes(activeOnly: boolean): Observable<InvestmentType[]>`
- `getInvestmentType(id: number): Observable<InvestmentType>`
- `createInvestmentType(type: InvestmentType): Observable<InvestmentType>`
- `updateInvestmentType(id: number, type: InvestmentType): Observable<InvestmentType>`
- `deleteInvestmentType(id: number): Observable<void>`
- `getInvestmentSubTypes(investmentTypeId?: number, activeOnly?: boolean): Observable<InvestmentSubType[]>`
- `createInvestmentSubType(subType: InvestmentSubType): Observable<InvestmentSubType>`
- `updateInvestmentSubType(id: number, subType: InvestmentSubType): Observable<InvestmentSubType>`
- `deleteInvestmentSubType(id: number): Observable<void>`
- `importSubTypesFromExcel(file: File, investmentTypeCode: string, sheetName?: string): Observable<any>`

## Data Flow

### Creating Investment Types

1. User creates investment type via frontend
2. Frontend sends POST request to `/api/configuration/investment-types/`
3. Backend validates and creates InvestmentType record
4. Backend returns created type with sub-types (empty array)
5. Frontend refreshes type list

### Creating Investment Sub-Types

1. User selects investment type
2. User creates sub-type for that type
3. Frontend sends POST request to `/api/configuration/investment-subtypes/`
4. Backend validates:
   - Investment type exists
   - Code is unique within the investment type
5. Backend creates InvestmentSubType record
6. Frontend refreshes sub-type list

### Excel Import

1. User uploads Excel file via frontend
2. Frontend sends POST request to `/api/configuration/investment-subtypes/import_excel/`
3. Backend:
   - Saves file temporarily
   - Reads Excel file using openpyxl
   - Validates data format
   - Creates or updates sub-types
   - Returns import results
4. Frontend displays import results

## Integration with Other Apps

### Stocks App
- Stocks are classified by `InvestmentType`
- Stock catalog uses investment types for filtering

### Fixed Income App
- Fixed income positions are classified by `InvestmentType` and `InvestmentSubType`
- Used for organizing and filtering fixed income investments

### Allocation Strategies App
- Allocation strategies reference investment types
- Sub-type allocations reference investment sub-types

## Common Use Cases

### Setting Up Investment Classification

1. Create investment types:
   - "Ações" (code: ACOES)
   - "Renda Fixa" (code: RENDA_FIXA)
   - "Tesouro Direto" (code: TESOURO_DIRETO)

2. Create sub-types for "Renda Fixa":
   - CDB
   - LCI
   - LCA
   - Debêntures

3. Import sub-types from Excel for bulk creation

### Filtering Investments

- Filter stocks by investment type
- Filter fixed income positions by type and sub-type
- Group portfolio positions by investment type

## Validation Rules

### Investment Type
- `name` must be unique
- `code` must be unique
- `name` and `code` are required

### Investment Sub-Type
- `code` must be unique within the investment type
- `investment_type` must exist
- `name` and `code` are required

## Error Handling

### Common Errors

**400 Bad Request**:
- Missing required fields
- Invalid investment type ID
- Duplicate code within investment type
- Invalid Excel file format

**404 Not Found**:
- Investment type not found
- Investment sub-type not found

**500 Internal Server Error**:
- Excel file processing error
- Database error

## Related Documentation

- [Database Data Model](09-database-data-model.md) - Complete database schema
- [Stocks](11-stocks.md) - Stock catalog using investment types
- [Fixed Income](14-fixed-income.md) - Fixed income positions using types and sub-types
- [Allocation Strategies](12-allocation-strategies.md) - Strategies using investment types

---

**Document Version**: 1.0  
**Last Updated**: November 2025  
**Status**: Complete

