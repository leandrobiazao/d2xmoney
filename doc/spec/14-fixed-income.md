# Fixed Income - Specification

This document specifies the Fixed Income application for managing CDB, Tesouro Direto, and other fixed income investment positions.

## Overview

The Fixed Income app tracks fixed income investment positions with detailed financial metrics, including CDB, LCI, LCA, Debêntures, and Tesouro Direto (Brazilian government bonds).

### Import Excel por corretora

O endpoint `POST .../import-excel/` escolhe o processamento **só com base no utilizador** (`user_id` → `User.account_provider`):

| Condição (`account_provider`) | Implementação | Ficheiro Excel |
|-------------------------------|---------------|----------------|
| Substring **`btg`** (case-insensitive), ex. «BTG Pactual» | [`btg_excel_import.import_btg_excel`](../../backend/fixed_income/btg_excel_import.py) | Posição consolidada BTG: abas **Renda Fixa** e **Conta Corrente**; dados de títulos só após **«Posições Detalhadas»**, em blocos **Detalhamento > …** |
| Caso contrário (XP, vazio, outras) | [`PortfolioExcelImportService._import_legacy_excel`](../../backend/fixed_income/services.py) | Uma folha ativa com secções estilo XP (`%|RENDA FIXA`, Tesouro), CDB, Saldo Disponível |

Ordem de decisão no código: se `user_is_btg(account_provider)` → **BTG**; senão **legado** (XP e restantes).

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

**Comportamento por corretora** (definido no backend pelo `User.account_provider`):

- **BTG Pactual** (`account_provider` com substring `btg`): import específico em [`backend/fixed_income/btg_excel_import.py`](../../backend/fixed_income/btg_excel_import.py) — abas **Renda Fixa** e **Conta Corrente**; em Renda Fixa só linhas após o marcador **«Posições Detalhadas»**, em blocos **Detalhamento > …**; colunas mapeadas (Ativo, Vencimento, Valor Compra R$, Saldo Bruto R$, etc.); chave lógica **tipo (Ativo) + Vencimento** com `asset_code` determinístico `BTG_{TIPO}_{YYYYMMDD}`; saldo de caixa: remove posições `asset_code` começado por `CAIXA_` do utilizador e grava `CAIXA_{user_id}` com nome **«BTG Pactual - Conta Corrente (saldo disponível)»** a partir da aba Conta Corrente (**Valor financeiro R$**).
- **XP Investimentos** e outras corretoras: fluxo legado inalterado (`workbook.active`, secções `%|RENDA FIXA` / Tesouro, CDB, Saldo Disponível XP).

**BTG — detalhe técnico**

- **Renda Fixa:** procurar o texto **«Posições Detalhadas»** (sem fixar número de linha); ignorar tudo **acima** desse marcador; dentro de cada **Detalhamento > …**, a linha de cabeçalho com **Ativo** e **Vencimento** define o mapeamento dinâmico de colunas.
- **Chave de atualização:** **Ativo** (tipo, ex. LTN, NTNB) + **Vencimento** → `asset_code` estável `BTG_{TIPO}_{YYYYMMDD}` (caracteres especiais no tipo normalizados para `_`).
- **`application_date`:** preenchido com **Aquisição** do Excel quando existir; atualiza o mesmo registo já identificado por `asset_code`.
- **Conta Corrente:** localizar o bloco com **Valor financeiro R$** e ler o valor na linha seguinte (mesma ou coluna adjacente); antes de gravar, **apaga** todas as posições do utilizador com `asset_code` que começa por `CAIXA_`; depois `update_or_create` em `CAIXA_{user_id}` com `application_date` fixa (1 de janeiro do ano corrente) para manter a chave estável.
- **Classificação:** cada linha importada do BTG em **Detalhamento** é gravada como subtipo **Tesouro Direto** e com registo em `TesouroDiretoPosition` (títulos públicos neste fluxo).
- **CDB / LCI noutras linhas do mesmo export:** não processados pelo parser BTG atual (extensão futura).

**Response** (resumo):
```json
{
  "created": 0,
  "updated": 0,
  "errors": [],
  "cdb_count": 0,
  "tesouro_count": 0,
  "caixa_count": 0,
  "debug_info": []
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
**Template / estilos:** `fixed-income-list.component.html`, `fixed-income-list.component.css`

**Fluxo de importação**

1. Utilizador clica **Importar Portfólio** (`button.btn-import` no cabeçalho da lista).
2. Abre-se um **modal** com título **«Importar posição de Renda Fixa»** e texto: *«Selecione um ficheiro Excel (.xlsx ou .xls) exportado pela sua corretora. O processamento segue o formato do cliente (BTG Pactual ou XP Investimentos).»*
3. Clicar fora (**overlay**), no **×** (Fechar) ou em **Cancelar** (`btn-import-secondary`) fecha o modal sem enviar.
4. **Selecionar ficheiro** dispara o `<input type="file">` oculto (`.xlsx` / `.xls`).
5. Após escolher o ficheiro, o modal fecha e o upload corre via `FixedIncomeService.importExcel` para `import-excel/` (o backend decide BTG vs legado pelo `account_provider`).

**Features**:
- List all fixed income positions
- Filter by user and investment type
- Display position details
- Import Excel conforme acima; posições de **caixa** (CAIXA) reconhecidas por `asset_code` `CAIXA_*`, nome com “caixa”, “conta corrente” ou “xp investimentos” (ver lógica em `isCaixaPosition`)

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
- Código de referência: [`backend/fixed_income/services.py`](../../backend/fixed_income/services.py) (`import_from_excel`, `_import_legacy_excel`), [`backend/fixed_income/btg_excel_import.py`](../../backend/fixed_income/btg_excel_import.py)

---

**Document Version**: 1.2  
**Last Updated**: April 2026  
**Status**: Complete

