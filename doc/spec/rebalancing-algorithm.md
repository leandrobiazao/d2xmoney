# Wallet Balancing Algorithm

This document describes the algorithm used by the Rebalancing Service to generate monthly portfolio rebalancing recommendations.

## Overview

The rebalancing algorithm combines high-level investment type allocation (e.g., Stocks vs. Fixed Income) with specific stock-picking strategies (AMBB 2.0) to generate a comprehensive list of Buy, Sell, and Rebalance actions.

**Key Goals:**
- Align portfolio with the user's target allocation percentages.
- Adhere to the monthly tax-exempt sales limit (R$ 20,000 total, configured as R$ 19,000 safety limit).
- Optimize stock selection using the AMBB 2.0 ranking system.
- Minimize turnover for "Good" stocks while aggressively culling "Bad" stocks.

## Core Flow

The process is orchestrated by `RebalancingService.generate_monthly_recommendations`:

1.  **Initialize**: Fetch user's `AllocationStrategy` and create a pending `RebalancingRecommendation`.
2.  **Calculate Current State**: Determine current portfolio value and allocation per type/subtype.
3.  **Check Sales Limit**: Calculate how much of the R$ 19,000 monthly limit remains, accounting for sales already executed in the current month.
4.  **Type & Subtype Rebalancing**: Generate actions to align broad investment categories (Fixed Income, International, etc.) with targets.
5.  **Stock Strategy (AMBB)**: Generate specific stock buy/sell actions for "Ações em Reais".
6.  **Special Assets**: Handle specific logic for assets like BERK34 (BDRs).
7.  **Finalize**: Save all actions and return the recommendation.

## Detailed Logic

### 1. Sales Limit Calculation
The system strictly enforces a monthly sales limit to maintain tax exemption eligibility.

- **Limit**: R$ 19,000.00 (Safety buffer below the official R$ 20k limit).
- **Used Limit**: Sum of `valor_operacao` for all SELL operations (`tipo_operacao='V'`) in the current month from brokerage notes.
- **Remaining Limit**: `19,000 - Used Limit`.

### 2. Investment Type Rebalancing
For each Investment Type (e.g., Renda Fixa, Renda Variável em Dólares):

1.  **Target Value**: `Total Portfolio Value * Type Target %`.
2.  **Current Value**: Sum of current positions in that type.
3.  **Difference**: `Target - Current`.
4.  **Action**: If `abs(Difference) > R$ 1.00`, create a `rebalance` action.

### 3. Subtype Rebalancing
For types with subtypes (e.g., Fixed Income -> Tesouro Direto, CDB):

1.  **Target Value**: `Total Portfolio Value * Type Target % * Subtype Target %`.
2.  **Current Value**: Current position in that subtype.
3.  **Difference**: `Target - Current`.
4.  **Action**: If `abs(Difference) > Threshold` (max of 1% of target or R$ 100), create a `rebalance` action.

**Note**: Subtype rebalancing is skipped for "Fundos Imobiliários" investment type, which uses FII allocations instead.

### 3.5. FII Rebalancing (Fundos Imobiliários)
For "Fundos Imobiliários" investment type, rebalancing works per selected FII ticker (not per subtype):

1.  **FII Selection**: User manually selects up to 5 FIIs from the FII catalog in allocation strategy.
2.  **Target Value Per FII**: `Total Portfolio Value * Type Target % * FII Target %`.
3.  **Current Value**: Current position value for that specific FII ticker (from PortfolioPosition).
4.  **Difference**: `Target - Current`.

5.  **Action Types** (based on FII presence in portfolio vs strategy):
    - **SELL Action**: FII in portfolio but NOT in strategy configuration
      - Sell entire position: `quantity_to_sell = PortfolioPosition.quantidade`
      - Reason: "FII não está na estratégia configurada"
    - **BUY Action**: FII in strategy but NOT in portfolio (current_value == 0)
      - Buy to reach target: `quantity_to_buy = target_value / current_price`
      - Calculate based on current FII market price
    - **REBALANCE Action**: FII in both portfolio AND strategy
      - Always use REBALANCE (whether difference is positive or negative)
      - If `difference > 0`: Set `quantity_to_buy = difference / current_price`
      - If `difference < 0`: Set `quantity_to_sell = abs(difference) / current_price`

6.  **Threshold**: `max(R$ 1.00, 1% of target value)` - only create action if `abs(difference) > threshold`.

7.  **Quantity Calculation**: Based on current FII price from StockService: `abs(difference) / current_price`.

**Key Differences from Stocks**:
- **No Sales Limit**: FIIs don't count toward the R$ 19,000 monthly sales limit (stocks do)
- **Tax**: FIIs always pay 15% income tax on profit (no tax exemption like stocks)
- **No AMBB Ranking**: FIIs don't use AMBB 2.0 ranking system (manual selection only)
- **Manual Selection**: FIIs are manually selected in allocation strategy (up to 5 FIIs)
- **Per-Ticker Actions**: Each selected FII gets its own rebalancing action (not grouped by subtype)
- **Action Logic**: If FII is in strategy, always rebalance (not separate buy/sell like stocks)

### 4. AMBB Strategy (Stock Picking)
This is the core logic for "Ações em Reais". It is handled by `AMBBStrategyService`.

#### Inputs
- **Universe**: Only "Ações em Reais".
- **Ranking**: AMBB 2.0 Ranking (lower is better).
- **Threshold**: Rank 30 (Stocks with Rank <= 30 are "Good", Rank > 30 are "Bad").
- **Max Stocks**: 20 stocks in the final portfolio.

#### Sell Logic (Prioritized)
The algorithm prioritizes selling "Bad" stocks to free up capital, respecting the remaining sales limit.

1.  **Identify Candidates**:
    *   **Priority 1 (Worst)**: Stocks NOT in AMBB 2.0 ranking.
    *   **Priority 2 (Bad)**: Stocks with Rank > 30 (sorted by worst/highest rank first).
    *   *Note: Stocks with Rank <= 30 are NEVER sold completely, even if overweight.*

2.  **Execution (With Limit)**:
    *   Iterate through candidates in priority order.
    *   **Complete Sale**: If `Stock Value <= Remaining Limit`, sell 100% and deduct from limit.
    *   **Partial Sale**: If `Stock Value > Remaining Limit`, sell as much as possible (up to remaining limit) and stop further sales.

#### Buy Logic
1.  **Identify Candidates**:
    *   Must be in AMBB 2.0 Ranking.
    *   Must have **Rank <= 30**.
    *   Must NOT be in current portfolio.
    *   Sort by Rank (Best/Lowest first).

2.  **Selection**:
    *   Fill available slots (up to Max 20 stocks) with the best available candidates.

#### Rebalancing (Weighting) Logic
1.  **Target Value Per Stock**: `Total "Ações em Reais" Target / Number of Stocks (Max 20)`.
    *   *Equal weighting strategy.*

2.  **Action Generation**:
    *   **Good Stocks (Rank <= 30)**:
        *   If `Current < Target`: **Buy** to reach target.
        *   If `Current > Target`: **Hold** (Do NOT sell winners partially). `Quantity to Sell = 0`.
    *   **Bad Stocks (Rank > 30)**:
        *   If `Current > Target`: **Sell** (Partially or Completely, as determined by Sell Logic).
        *   If `Current < Target`: **Hold** (Do NOT buy more losers). `Quantity to Buy = 0`.

### 5. Special Cases

#### BERK34 (Berkshire Hathaway)
- Treated as a proxy for "Renda Variável em Dólares" (specifically BDRs).
- **Target**: Calculated based on the BDR subtype allocation.
- **Action**: Buy or Sell to match the specific BDR target value.

## Summary of Rules

| Condition | Rank <= 30 (Good) | Rank > 30 (Bad) | Not in Ranking |
| :--- | :--- | :--- | :--- |
| **Buy New** | Allowed (Top Priority) | **FORBIDDEN** | **FORBIDDEN** |
| **Buy More** | Allowed (to reach target) | **FORBIDDEN** | **FORBIDDEN** |
| **Sell Partial** | **FORBIDDEN** (Let winners run) | Allowed (to reduce weight) | Allowed |
| **Sell Complete**| Only if removed from strategy | Allowed (Priority 2) | Allowed (Priority 1) |
