# Brokerage Note Processing - Specification

This document specifies the Brokerage Note Processing application for parsing B3 brokerage note PDFs, extracting trading operations, and mapping company names to stock tickers.

## Overview

The Brokerage Note Processing app allows users to:
- Upload B3 brokerage note PDF files
- Parse PDFs to extract trading operations
- Map company names to B3 stock tickers
- Handle missing ticker mappings with user input
- Save extracted operations for portfolio tracking

## Brokerage Note Example

The following image shows the first page of a B3 brokerage note example (Aurelio's note from September 2025):

![Brokerage Note Example - First Page](brokerage-note-example-first-page.png)

*Figure 1: Example of a B3 brokerage note showing the standard format with operation lines. Note that the company name and classification code (e.g., "3TENTOS ON NM", "CSNMINERACAO ON N2") appear as a single unified field in the "Especificação do título" section, and should be parsed as one field.*

**Important Parsing Note**: In the brokerage note, the company name and its classification code (such as "ON NM", "ON N2", "UNT N1", "ON ED NM") are combined as a single field. For example:
- "3TENTOS ON NM" should be treated as one field
- "CSNMINERACAO ON N2" should be treated as one field
- "IGUATEMI S.A UNT N1" should be treated as one field

**Ticker Mapping Note**: The classification suffix (ON NM, ON N2, UNT N1, etc.) is important for identifying the correct ticker, as different classification codes may map to different tickers for the same company. Use the complete field (company name + classification code) for ticker mapping.

## Backend Components

### Prompt BNP-1: Create Brokerage Notes Django App
```
Create a new Django app for brokerage note processing:
- Navigate to backend/ directory
- Run: python manage.py startapp brokerage_notes
- Register app in INSTALLED_APPS: 'brokerage_notes'
- App structure:
  - backend/brokerage_notes/
    ├── __init__.py
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── serializers.py (create new file)
    └── admin.py
```

### Prompt BNP-2: Create Ticker Mappings Django App
```
Create Django app for ticker mappings:
- Navigate to backend/ directory
- Run: python manage.py startapp ticker_mappings
- Register app in INSTALLED_APPS: 'ticker_mappings'
- App structure:
  - backend/ticker_mappings/
    ├── __init__.py
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── serializers.py (create new file)
    └── admin.py
```

### Prompt BNP-3: Create Ticker Mapping Model
```
Create Django model in backend/ticker_mappings/models.py:
- Model name: TickerMapping
- Fields:
  - nome (CharField, max_length=200, unique=True, primary_key=True)
  - ticker (CharField, max_length=10)
  - created_at (DateTimeField, auto_now_add=True)
  - updated_at (DateTimeField, auto_now=True)
- Meta class with ordering: ['nome']
- __str__ method returning f"{self.nome} -> {self.ticker}"
- Run migrations: python manage.py makemigrations && python manage.py migrate
```

### Prompt BNP-4: Create Ticker Mapping Serializer
```
Create Django REST Framework serializer in backend/ticker_mappings/serializers.py:
- Serializer name: TickerMappingSerializer
- Based on ModelSerializer
- Model: TickerMapping
- Fields: ['nome', 'ticker', 'created_at', 'updated_at']
- Validation:
  - Ticker format: 4 uppercase letters + 1-2 digits (e.g., ANIM3, VALE3)
  - Nome: uppercase, trimmed
- Create method to validate ticker format
```

### Prompt BNP-5: Create Ticker Mapping API View
```
Create Django REST Framework view in backend/ticker_mappings/views.py:
- View name: TickerMappingUpdateView (APIView)
  - POST: Update ticker-mappings.ts file
    - Accept JSON body with 'content' field (TypeScript file content)
    - Write content to frontend/src/app/portfolio/ticker-mappings.ts
    - Return success response with timestamp
    - Handle file writing errors
    - Validate content is valid string
- Import necessary modules: os, json, pathlib
- Use proper file path resolution (relative to project root)
- Log updates to console
- Return appropriate HTTP status codes (200, 400, 500)
```

### Prompt BNP-6: Create Ticker Mapping URLs
```
Create URL configuration in backend/ticker_mappings/urls.py:
- Import path from django.urls
- Import views from ticker_mappings.views
- URL pattern:
  - path('api/ticker-mappings/', views.TickerMappingUpdateView.as_view(), name='ticker-mappings-update')
- Include in main project URLs (backend/portfolio_api/urls.py):
  - Add: path('', include('ticker_mappings.urls'))
```

### Prompt BNP-7: Create Management Command for Ticker Updates (Optional)
```
Create Django management command in backend/ticker_mappings/management/commands/update_tickers.py:
- Command name: update_tickers
- Read custom mappings from JSON file (if exists)
- Read default mappings from frontend/src/app/portfolio/ticker-mappings.ts
- Merge default and custom mappings
- Sort mappings alphabetically
- Generate updated TypeScript file content
- Write to ticker-mappings.ts
- Include timestamp in file header
- Log summary (total, default, custom counts)
- Usage: python manage.py update_tickers
```

## Frontend Components

### Prompt BNP-8: Create Operation Model
```
Create operation model interface in frontend/src/app/brokerage-note/operation.model.ts:
- Interface name: Operation
- Properties:
  - id: string
  - tipoOperacao: 'C' | 'V' (Compra/Venda)
  - tipoMercado: string
  - ordem: number
  - titulo: string (stock ticker, e.g., ANIM3)
  - qtdTotal: number
  - precoMedio: number
  - quantidade: number (negative for sales)
  - preco: number
  - valorOperacao: number
  - dc: 'D' | 'C' (Débito/Crédito)
  - notaTipo: string
  - corretora: string
  - nota: string (note number)
  - data: string (DD/MM/YYYY format)
  - clientId: string
```

### Prompt BNP-9: Use Ticker Mapping Service
```
The ticker mapping functionality is located in the portfolio app:
- Ticker mappings file: frontend/src/app/portfolio/ticker-mapping/ticker-mappings.ts
- Ticker mapping service: frontend/src/app/portfolio/ticker-mapping/ticker-mapping.service.ts
- Import TickerMappingService from portfolio/ticker-mapping in the PDF parser service
- See Portfolio Summary specification (04-portfolio-summary.md) for ticker mapping details
```

### Prompt BNP-11: Create PDF Parser Service
```
Create PDF parser service in frontend/src/app/brokerage-note/pdf-parser.service.ts:
- Service name: PdfParserService
- Injectable, provided in root
- Use pdfjs-dist library
- Configure PDF.js worker from /assets/pdfjs/pdf.worker.min.mjs
- Methods:
  - parsePdf(file: File, onTickerRequired?: callback): Promise<Operation[]>
- Parse B3 brokerage note PDFs:
  - Extract text from all pages
  - Find operation lines matching pattern: "1-BOVESPA   C/V   TIPO_MERCADO   NOME_ACAO_CLASSIFICACAO   @   QTD   PRECO   VALOR   D/C"
  - IMPORTANT: The company name and classification code (e.g., "3TENTOS ON NM", "CSNMINERACAO ON N2") 
    should be treated as a SINGLE unified field, not separate fields
  - Extract: data do pregão, número da nota from PDF
  - Parse each operation line:
    - tipoOperacao (C/V)
    - tipoMercado
    - nomeAcaoCompleto (company name + classification code as one field, e.g., "3TENTOS ON NM")
    - quantidade, preco, valorOperacao
    - dc (D/C)
  - For each operation:
    - Use nomeAcaoCompleto (complete field with classification code) for ticker mapping
    - Import and use TickerMappingService from portfolio/ticker-mapping
    - Try to get ticker from TickerMappingService using nomeAcaoCompleto
    - If not found, try to extract ticker pattern (4 letters + 1-2 digits) from the full field
    - If still not found, call onTickerRequired callback with nomeAcaoCompleto
    - Create Operation object with all fields
- Handle errors gracefully
- Return array of Operation objects
- Support multiple parsing strategies (fallback methods)
- Note: Classification codes (ON NM, ON N2, ON ED NM, UNT N1, etc.) are preserved in the field
  as they may define different tickers for the same company
```

### Prompt BNP-12: Create Ticker Dialog Component
```
Create ticker dialog component in frontend/src/app/brokerage-note/ticker-dialog/:
- Component name: TickerDialogComponent
- Standalone component
- Input: nome (company name with classification code, e.g., "3TENTOS ON NM")
- Input: operationData (operation details for context)
- Output: confirm event with ticker string
- Output: cancel event
- Display dialog asking user to input ticker for company name
- Display the complete field (company name + classification code) as received
- Example display: "3TENTOS ON NM" (showing that classification code is part of the identifier)
- Show operation context (type, market, quantity, price)
- Input field for ticker (text, uppercase)
- "Confirm" and "Cancel" buttons
- Validate ticker format (4 letters + 1-2 digits)
- Modal overlay style
- Import TickerMappingService from portfolio/ticker-mapping
- Use TickerMappingService.setTicker() when user confirms ticker
- Note: The classification code is important and should be preserved in the mapping
```

### Prompt BNP-13: Create Upload PDF Component
```
Create PDF upload component in frontend/src/app/brokerage-note/upload-pdf/:
- Component name: UploadPdfComponent
- Standalone component
- Input: clientId (required)
- Output: operationsAdded event emitter
- File input for PDF selection
- "Upload" button
- Processing state indicator
- Success/error messages
- Integration with PdfParserService
- Integration with TickerDialogComponent for missing tickers
- Import TickerMappingService from portfolio/ticker-mapping (used by PdfParserService)
- Show ticker dialog when ticker is required during parsing
- Check server status for file update capability
- Display server online/offline status
- Handle errors gracefully
- On successful parse:
  - Emit operationsAdded event with array of operations
  - Show success message with number of operations extracted
  - Reset file input
```

### Prompt BNP-14: Create Processing Status Component
```
Create processing status component in frontend/src/app/brokerage-note/processing-status/:
- Component name: ProcessingStatusComponent
- Standalone component
- Display processing state (idle, processing, success, error)
- Show progress indicator during PDF parsing
- Display number of operations found
- Show error messages if parsing fails
- Display server connection status
```

## API Endpoints

### POST /api/ticker-mappings/
**Description**: Update the ticker-mappings.ts file in the frontend

**Request Body**:
```json
{
  "content": "export const DEFAULT_TICKER_MAPPINGS: { [nome: string]: string } = { ... };"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Arquivo atualizado com sucesso",
  "timestamp": "2025-11-05T12:00:00Z"
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "Conteúdo inválido"
}
```

## Data Flow

1. User uploads PDF file via UploadPdfComponent
2. PdfParserService extracts text from PDF
3. Parser searches for operation lines matching B3 format
4. For each operation line:
   - Extract nomeAcaoCompleto as a single field (e.g., "3TENTOS ON NM")
   - Preserve the complete field including classification code
5. For each operation, TickerMappingService tries to find ticker using nomeAcaoCompleto (complete field)
6. If ticker not found, TickerDialogComponent prompts user for input
   - Dialog shows the complete field (e.g., "3TENTOS ON NM")
   - User provides ticker for the complete field
7. Ticker mapping is saved using the complete field (company name + classification code)
8. Operations are created with all required fields
9. Operations are emitted via operationsAdded event
10. Parent component receives operations and saves them

## Integration

### Integrate into Main App
```
Update main app component or brokerage note route:
- Include UploadPdfComponent
- Listen to operationsAdded event
- Save operations to portfolio service or send to backend
- Display processing status
- Handle errors and success messages
```

## Error Handling

- PDF parsing errors: Display user-friendly error messages
- Invalid PDF format: Show specific error about B3 format requirement
- Missing ticker: Prompt user via dialog
- Network errors: Handle server connection issues
- File size limits: Validate before upload

---

**Related Documents**:  
- [Main Specification](README.md)  
- [User Management](01-user-management.md)  
- [Brokerage History](03-brokerage-history.md)  
- [Portfolio Summary](04-portfolio-summary.md)

