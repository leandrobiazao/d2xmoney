# Portfolio Summary - Specification

This document specifies the Portfolio Summary application for viewing portfolio positions, operations, and analytics.

## Overview

The Portfolio Summary app allows users to:
- View current portfolio positions
- See all trading operations
- Filter operations by multiple criteria
- View portfolio analytics (total invested, number of assets)
- Calculate position values and averages
- Delete operations

## Backend Components

### Prompt PS-1: Create Portfolio Service (Optional - for future API)
```
Create portfolio service in backend/portfolio/ (if implementing backend API):
- Service name: PortfolioService
- Methods for portfolio calculations
- Endpoints for portfolio data
- Note: Currently portfolio data is stored in frontend localStorage
- This can be extended to backend storage in future
```

## Frontend Components

### Prompt PS-2: Create Position Model
```
Create position model interface in frontend/src/app/portfolio/position.model.ts:
- Interface name: Position
- Properties:
  - titulo: string (stock ticker)
  - quantidadeTotal: number
  - precoMedioPonderado: number
  - valorTotalInvestido: number
  - valorAtualEstimado?: number (optional)
  - lucroPrejuizoNaoRealizado?: number (optional)
```

### Prompt PS-3: Create Portfolio Model
```
Create portfolio model interface in frontend/src/app/portfolio/portfolio.model.ts:
- Interface name: Portfolio
- Properties:
  - clientId: string
  - operations: Operation[]
  - positions: Position[]
  - lastUpdated: string (ISO date)
```

### Prompt PS-4: Create Portfolio Service
```
Create portfolio service in frontend/src/app/portfolio/portfolio.service.ts:
- Service name: PortfolioService
- Injectable, provided in root
- Methods:
  - getOperations(clientId: string): Operation[]
  - addOperations(clientId: string, operations: Operation[]): void
  - deleteOperation(clientId: string, operationId: string): void
  - getPositions(clientId: string): Position[]
  - calculatePositions(clientId: string): Position[]
- Persist portfolio data to localStorage with key format: "portfolio-{clientId}"
- Calculate positions from operations:
  - Buy operations: increase quantity, calculate weighted average price
  - Sell operations: decrease quantity proportionally
  - Remove positions with zero quantity
- Sort operations by date (newest first), then by ordem
- Sort positions alphabetically by titulo
```

## Ticker Mapping Components

### Prompt PS-5: Create Ticker Mappings File
```
Create ticker mappings file with:
- File: frontend/src/app/portfolio/ticker-mapping/ticker-mappings.ts
- Export DEFAULT_TICKER_MAPPINGS object
- Map company names to B3 stock tickers
- IMPORTANT: Map the complete field including classification code (company name + classification)
- The classification suffix (ON NM, ON N2, UNT N1, etc.) is important as it may define different tickers
- Include common mappings like:
  - '3TENTOS ON NM': 'TTEN3'
  - 'CSNMINERACAO ON N2': 'CMIN3'
  - 'CYRELA REALT ON NM': 'CYRE3'
  - 'GRENDENE ON ED NM': 'GRND3'
  - 'IGUATEMI S.A UNT N1': 'IGTI11'
  - 'ANIMA ON NM': 'ANIM3'
  - 'VALE ON NM': 'VALE3'
  - etc.
- Format: { [nome: string]: string }
- Include header comment explaining purpose
- Include auto-update timestamp comment
- Note: The mapping uses the complete field (company name + classification code) as the key
  because different classification codes may map to different tickers
```

### Prompt PS-6: Create Ticker Mapping Service
```
Create ticker mapping service in frontend/src/app/portfolio/ticker-mapping/ticker-mapping.service.ts:
- Service name: TickerMappingService
- Injectable, provided in root
- Methods:
  - getTicker(nome: string): string | null
    - Lookup ticker using the complete field (company name + classification code)
    - Normalize nome (uppercase, trim) before lookup
    - Return ticker if found, null otherwise
  - setTicker(nome: string, ticker: string): void
    - Save mapping using the complete field (nome as-is, including classification code)
    - Normalize nome (uppercase, trim) before saving
    - Save to localStorage
    - Send HTTP POST request to http://localhost:8000/api/ticker-mappings/ to update server file
    - Emit browser event 'ticker-mappings-updated'
  - hasMapping(nome: string): boolean
  - getAllMappings(): TickerMapping
  - getMappingsFileContent(): string
  - getCustomMappingsJSON(): string
- Load default mappings from ticker-mappings.ts
- Store custom mappings in localStorage
- Merge default and custom mappings
- Normalize company names (uppercase, trim)
- Use the complete field (company name + classification code) for all mappings
- Note: Classification codes are preserved as they may define different tickers
```

### Prompt PS-7: Create Portfolio Summary Component
```
Create portfolio summary component in frontend/src/app/portfolio/portfolio-summary/:
- Component name: PortfolioSummaryComponent
- Standalone component
- Input: userId (required)
- Input: userName (required)
- Display portfolio for selected user
- Sections:
  1. Summary Cards:
     - Total Investido (sum of valorTotalInvestido from all positions)
     - Ativos na Carteira (count of positions)
     - Total de Operações (count of operations)
  2. Positions Section:
     - Table with: Título, Quantidade, Preço Médio, Valor Total Investido
     - Sortable columns
     - Empty state when no positions
  3. Operations Section:
     - Filters: Título, Tipo Operação, Tipo Mercado, Data Início, Data Fim
     - Table with all operation details:
       - Data
       - Título
       - Tipo (C/V)
       - Quantidade
       - Preço
       - Valor Operação
       - Tipo Mercado
       - Nota
       - Actions (delete button)
     - Delete operation button for each row
- Filter operations by multiple criteria
- Format currency as BRL (R$)
- Calculate totals
- Use PortfolioService for data
- Toggle visibility of sections
- Handle loading and error states
```

### Prompt PS-8: Create Operations Table Component
```
Create operations table component in frontend/src/app/portfolio/operations-table/:
- Component name: OperationsTableComponent
- Standalone component
- Input: operations (Operation[])
- Input: filters (OperationFilters)
- Display operations in table format
- Columns:
  - Data (formatted date)
  - Título (ticker)
  - Tipo (C/V with color coding)
  - Tipo Mercado
  - Quantidade (formatted number)
  - Preço (formatted currency)
  - Valor Operação (formatted currency)
  - Nota (note number)
  - Actions (delete button)
- Apply filters to operations
- Sortable columns
- Pagination (optional, for large lists)
- Empty state when no operations match filters
```

### Prompt PS-9: Create Positions Table Component
```
Create positions table component in frontend/src/app/portfolio/positions-table/:
- Component name: PositionsTableComponent
- Standalone component
- Input: positions (Position[])
- Display positions in table format
- Columns:
  - Título (ticker)
  - Quantidade Total (formatted number)
  - Preço Médio Ponderado (formatted currency)
  - Valor Total Investido (formatted currency)
  - Valor Atual Estimado (formatted currency, if available)
  - Lucro/Prejuízo Não Realizado (formatted currency, if available)
- Sortable columns
- Empty state when no positions
- Highlight positive/negative values
```

### Prompt PS-10: Create Portfolio Filters Component
```
Create filters component in frontend/src/app/portfolio/portfolio-filters/:
- Component name: PortfolioFiltersComponent
- Standalone component
- Output: filtersChange event emitter
- Filter controls:
  - Título (text input, search by ticker)
  - Tipo Operação (dropdown: All, Compra, Venda)
  - Tipo Mercado (text input)
  - Data Início (date picker)
  - Data Fim (date picker)
- "Apply Filters" button
- "Clear Filters" button
- Emit filters when changed
- Display active filter count
```

### Prompt PS-11: Create Portfolio Summary Cards Component
```
Create summary cards component in frontend/src/app/portfolio/summary-cards/:
- Component name: SummaryCardsComponent
- Standalone component
- Input: positions (Position[])
- Input: operations (Operation[])
- Display summary cards:
  - Total Investido: Sum of valorTotalInvestido from positions
  - Ativos na Carteira: Count of positions
  - Total de Operações: Count of operations
- Format currency values as BRL
- Update when positions or operations change
- Card styling with icons
```

### Prompt PS-12: Integrate Portfolio Summary into Main App
```
Update main app component in frontend/src/app/:
- Include PortfolioSummaryComponent when user is selected
- Pass userId and userName to PortfolioSummaryComponent
- Update fallback message: "Selecione um cliente para ver sua carteira de investimentos."
- Integrate with brokerage note processing:
  - Receive operationsAdded event from UploadPdfComponent
  - Add operations to portfolio via PortfolioService
  - Refresh portfolio summary display
```

## Position Calculation Logic

### Prompt PS-13: Implement Position Calculation
```
PortfolioService.calculatePositions() logic:
1. Get all operations for clientId
2. Sort operations by date (oldest first), then by ordem
3. For each operation:
   - If tipoOperacao === 'C' (Compra):
     - Find or create position for titulo
     - Calculate new weighted average price:
       - quantidadeAtual = position.quantidadeTotal
       - valorAtual = quantidadeAtual * position.precoMedioPonderado
       - quantidadeNova = operation.quantidade
       - valorNovo = operation.valorOperacao
       - quantidadeTotal = quantidadeAtual + quantidadeNova
       - valorTotal = valorAtual + valorNovo
       - precoMedioPonderado = valorTotal / quantidadeTotal
     - Update position.quantidadeTotal and position.valorTotalInvestido
   - If tipoOperacao === 'V' (Venda):
     - Find position for titulo
     - Reduce quantidadeTotal by Math.abs(operation.quantidade)
     - Reduce valorTotalInvestido proportionally:
       - valorUnitario = position.precoMedioPonderado
       - valorReduzido = quantidadeVendida * valorUnitario
       - valorTotalInvestido = Math.max(0, valorTotalInvestido - valorReduzido)
     - If quantidadeTotal <= 0, reset position values
4. Filter out positions with quantidadeTotal <= 0
5. Sort positions alphabetically by titulo
6. Return positions array
```

## Operation Filtering Logic

### Prompt PS-14: Implement Operation Filters
```
PortfolioComponent.applyFilters() logic:
Filter operations by:
- Título: Case-insensitive partial match
- Tipo Operação: Exact match (C or V)
- Tipo Mercado: Case-insensitive partial match
- Data Início: Operation date >= filter date
- Data Fim: Operation date <= filter date
- All filters are AND conditions
- Return filtered operations array
```

## Data Persistence

- **Portfolio Data**: localStorage keys `portfolio-{clientId}`
- **Data Structure**:
  ```json
  {
    "clientId": "user-uuid",
    "operations": [...],
    "positions": [...],
    "lastUpdated": "2025-11-05T12:00:00Z"
  }
  ```

## Integration

### Integration Flow
1. User uploads brokerage note → Operations extracted
2. Operations added to PortfolioService
3. PortfolioService calculates positions
4. Portfolio summary displays updated positions and operations
5. User can filter operations
6. User can delete operations (recalculates positions)

## UI/UX Requirements

### Prompt PS-15: Style Portfolio Summary
```
Style the portfolio summary interface:
- Professional financial dashboard look
- Summary cards with highlighted values
- Tables with proper styling and spacing
- Filter controls with clear labels
- Currency formatting (BRL, R$)
- Responsive tables (horizontal scroll on mobile)
- Color coding:
  - Buy operations: Green
  - Sell operations: Red
  - Positive values: Green
  - Negative values: Red
- Loading states during calculations
- Empty states when no data
- Delete confirmation dialogs
```

## API Endpoints (Future)

When backend API is implemented:
- `GET /api/portfolio/{user_id}/` - Get portfolio summary
- `GET /api/portfolio/{user_id}/positions/` - Get positions
- `GET /api/portfolio/{user_id}/operations/` - Get operations
- `POST /api/portfolio/{user_id}/operations/` - Add operations
- `DELETE /api/portfolio/{user_id}/operations/{operation_id}/` - Delete operation

---

**Related Documents**:  
- [Main Specification](README.md)  
- [User Management](01-user-management.md)  
- [Brokerage Note Processing](02-brokerage-note-processing.md)  
- [Brokerage History](03-brokerage-history.md)

