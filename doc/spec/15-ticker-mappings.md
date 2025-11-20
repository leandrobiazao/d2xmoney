# Ticker Mappings - Specification

This document specifies the Ticker Mappings application for mapping company names (with classification codes) to stock ticker symbols.

## Overview

The Ticker Mappings app provides a mapping system that converts company names extracted from brokerage note PDFs (which include classification codes like "ON", "PN") to standard ticker symbols used throughout the system.

## Backend Components

### Models

#### TickerMapping

**Table**: `ticker_mappings`

**Purpose**: Maps company names (with classification codes) to stock ticker symbols for PDF parsing.

**Fields**:

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | AutoField | Primary Key | Unique identifier |
| `company_name` | CharField | max_length=255, unique=True, db_index=True | Company name with classification (e.g., "3TENTOS ON NM") |
| `ticker` | CharField | max_length=20, Required | Stock ticker symbol (e.g., "TTEN3") |

**Meta Options**:
- `db_table`: `ticker_mappings`
- `ordering`: `['company_name']`

### API Endpoints

**Base URL**: `http://localhost:8000/api/`

#### List Ticker Mappings
```
GET /api/ticker-mappings/
```

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "company_name": "3TENTOS ON NM",
    "ticker": "TTEN3"
  }
]
```

#### Create Ticker Mapping
```
POST /api/ticker-mappings/
```

**Request Body**:
```json
{
  "company_name": "3TENTOS ON NM",
  "ticker": "TTEN3"
}
```

**Response** (201 Created): Ticker mapping object

#### Get Ticker Mapping
```
GET /api/ticker-mappings/{nome}/
```

**Response** (200 OK): Ticker mapping object

#### Update Ticker Mapping
```
PUT /api/ticker-mappings/{nome}/
PATCH /api/ticker-mappings/{nome}/
```

**Request Body**: Partial or full ticker mapping object

**Response** (200 OK): Updated ticker mapping object

#### Delete Ticker Mapping
```
DELETE /api/ticker-mappings/{nome}/
```

**Response** (204 No Content)

## Integration with Brokerage Note Processing

### PDF Parsing Workflow

1. PDF parser extracts company name from brokerage note (e.g., "3TENTOS ON NM")
2. System looks up ticker mapping by `company_name`
3. If found, uses mapped ticker (e.g., "TTEN3")
4. If not found:
   - System prompts user to map company name to ticker
   - User provides ticker symbol
   - System creates new ticker mapping
   - System uses mapped ticker for operation

### Automatic Mapping Creation

When a new company name is encountered during PDF processing:
1. System checks if mapping exists
2. If not, user is prompted to provide ticker
3. System creates mapping automatically
4. Mapping is saved for future use

## Data Flow

### Creating a Mapping

1. User uploads brokerage note PDF
2. System extracts company name "3TENTOS ON NM"
3. System checks for existing mapping
4. If not found, user provides ticker "TTEN3"
5. System creates mapping
6. System uses ticker for operation

### Using a Mapping

1. PDF parser extracts company name
2. System queries ticker mappings by company_name
3. System retrieves ticker symbol
4. System uses ticker for portfolio operations

## Common Use Cases

### Initial Setup

1. Import common ticker mappings
2. System has mappings for major companies
3. Users can add custom mappings

### Adding New Mappings

1. User uploads brokerage note with new company
2. System prompts for ticker
3. User provides ticker
4. Mapping is created and saved

## Validation Rules

- `company_name` must be unique
- `ticker` must be provided
- `company_name` and `ticker` are required

## Related Documentation

- [Database Data Model](09-database-data-model.md) - Complete schema
- [Brokerage Note Processing](02-brokerage-note-processing.md) - PDF parsing integration
- [Stocks](11-stocks.md) - Stock catalog

---

**Document Version**: 1.0  
**Last Updated**: November 2025  
**Status**: Complete

