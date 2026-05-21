# CLEAR Corretora (XPINC) brokerage note fixtures

Sample **Nota de Negociação** PDFs from CLEAR Corretora (Grupo XP), layout **B3 RV LISTADO** (not classic `N-BOVESPA`).

## Fixtures used in unit tests

Copied to `frontend/public/fixtures/clear/`:

- `XPINC_NOTA_NEGOCIACAO_B3_1_3_2021.pdf` — 1 operation
- `XPINC_NOTA_NEGOCIACAO_B3_1_3_2023.pdf` — 14 operations
- `XPINC_NOTA_NEGOCIACAO_B3_2_1_2023.pdf` — 2 pages, note `8512`

## Full set (Leandro)

Additional samples live under `backend/media/brokerage_notes/Leandro/` (gitignored media folder).

## Upload

Select user **Leandro** (account `8770006`, CLEAR / XP Investimentos). Upload validates against **Conta corrente** on the PDF, not **Código cliente** (e.g. `0364175`).
