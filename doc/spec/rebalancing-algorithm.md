# Wallet Balancing Algorithm

This document describes the algorithm used by the Rebalancing Service to generate monthly portfolio rebalancing recommendations.

## Overview

The rebalancing algorithm combines high-level investment type allocation (e.g., Stocks vs. Fixed Income) with specific stock-picking from **MDIV (Máquina de Dividendos)** to generate a comprehensive list of Buy, Sell, and Rebalance actions.

**Key Goals:**
- Align portfolio with the user's target allocation percentages.
- Adhere to the monthly tax-exempt sales limit (R$ 20,000 total, configured as R$ 19,000 safety limit).
- Optimize stock selection using the MDIV ranking (Clube do Valor Máquina de Dividendos).
- Buy and equal-weight MDIV ranks 1–10; keep existing names in MDIV top 20; slowly exit leftover AMBB 2.0 and MDIV rank > 20.

## Core Flow

The process is orchestrated by `RebalancingService.generate_monthly_recommendations`:

1.  **Initialize**: Fetch user's `AllocationStrategy` and create a pending `RebalancingRecommendation`.
2.  **Calculate Current State**: Determine current portfolio value and allocation per type/subtype.
3.  **Check Sales Limit**: Calculate how much of the R$ 19,000 monthly limit remains, accounting for sales already executed in the current month.
4.  **Type & Subtype Rebalancing**: Generate actions to align broad investment categories (Fixed Income, International, etc.) with targets.
5.  **Stock Strategy (MDIV)**: Generate specific stock buy/sell actions for "Ações em Reais".
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

### 4. MDIV Strategy (Stock Picking)
This is the core logic for "Ações em Reais". It is handled by `AMBBStrategyService`.

#### Inputs
- **Universe**: Only "Ações em Reais".
- **Ranking**: MDIV (Máquina de Dividendos). Lower is better.
- **Keep threshold**: Rank 20 (held names with Rank <= 20 are kept; Rank > 20 are sold slowly).
- **Buy / equal-weight**: Ranks 1–10 only. Target per name = RV Reais meta / 10.
- **Max Stocks**: 20 names in the final portfolio (slot cap).

#### Sell Logic (Prioritized)
The algorithm prioritizes selling names that are no longer in the MDIV top 20, respecting the remaining sales limit.

1.  **Identify Candidates**:
    *   **Priority 1 (Worst)**: Stocks NOT in MDIV ranking (includes leftover AMBB 2.0 names).
    *   **Priority 2 (Bad)**: Stocks with MDIV Rank > 20 (sorted by worst/highest rank first).
    *   *Note: Stocks with MDIV Rank <= 20 are NEVER sold completely.*

2.  **Execution (With Limit)**:
    *   Iterate through candidates in priority order.
    *   **Complete Sale**: If `Stock Value <= Remaining Limit`, sell 100% and deduct from limit.
    *   **Partial Sale**: If `Stock Value > Remaining Limit`, sell as much as possible (up to remaining limit).

#### Buy Logic
1.  **Identify Candidates**:
    *   Must be in MDIV ranking.
    *   Must have **Rank <= 10**.
    *   Must NOT be in current portfolio.
    *   Sort by Rank (Best/Lowest first).

2.  **Selection**:
    *   Fill available slots (up to Max 20 stocks) with the best available top-10 candidates.

#### Rebalancing (Weighting) Logic
1.  **Target Value Per Stock (ranks 1–10)**: `Total "Ações em Reais" Target / 10`.
    *   *Equal weighting among the MDIV top 10.*

2.  **Action Generation**:
    *   **MDIV Rank 1–10**:
        *   If `Current < Target`: **Buy** toward the 1/10 slot. If cash is short, water-fill so **ending** MDIV 1–10 weights are as even as possible (new/small names get larger tickets; names already near the slot get less).
        *   If `Current > Target`: **Partial sell** toward target if monthly sales limit remains after bad-stock sales.
    *   **MDIV Rank 11–20 (already held)**:
        *   **Hold**. No additional buys. No complete sell.
    *   **MDIV Rank > 20 or not in ranking**:
        *   **Sell** (partially or completely, as determined by Sell Logic). Do not buy more.

### 5. Special Cases

#### BERK34 (Berkshire Hathaway)
- Treated as a proxy for "Renda Variável em Dólares" (specifically BDRs).
- **Target**: Calculated based on the BDR subtype allocation.
- **Action**: Buy or Sell to match the specific BDR target value.

## Summary of Rules

| Condition | MDIV 1–10 | MDIV 11–20 (held) | MDIV Rank > 20 | Not in MDIV |
| :--- | :--- | :--- | :--- | :--- |
| **Buy New** | Allowed (priority) | **FORBIDDEN** | **FORBIDDEN** | **FORBIDDEN** |
| **Buy More** | Allowed (to equal 1/10) | **FORBIDDEN** | **FORBIDDEN** | **FORBIDDEN** |
| **Sell Partial** | Allowed if overweight vs 1/10 | No (hold size) | Allowed | Allowed |
| **Sell Complete** | Only if removed from top 20 | **FORBIDDEN** | Allowed (Priority 2) | Allowed (Priority 1) |
