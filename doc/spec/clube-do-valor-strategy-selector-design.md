# Clube do Valor - Strategy Selector Design

## Component Structure Diagram

```mermaid
graph TB
    subgraph "Clube do Valor Component"
        A[ClubeDoValorComponent]
        
        subgraph "UI Structure"
            B[Strategy Selector Menu]
            C[Month Sidebar]
            D[Content Area]
        end
        
        subgraph "Strategy Selector Menu"
            B1[AMBB1 Button<br/>AMBB 1.0]
            B2[AMBB2 Button<br/>AMBB 2.0]
            B3[MDIV Button<br/>Máquina de Dividendos]
            B4[MOM Button<br/>Momentum]
        end
        
        subgraph "Content Area"
            E[Content Header]
            F[Strategy Table Container]
        end
        
        subgraph "Table Views"
            G[AMBB1 Table<br/>Current Implementation]
            H[AMBB2 Table<br/>Future]
            I[MDIV Table<br/>Future]
            J[MOM Table<br/>Future]
        end
        
        A --> B
        A --> C
        A --> D
        
        B --> B1
        B --> B2
        B --> B3
        B --> B4
        
        D --> E
        D --> F
        
        B1 -.->|selected| G
        B2 -.->|selected| H
        B3 -.->|selected| I
        B4 -.->|selected| J
        
        F --> G
        F --> H
        F --> I
        F --> J
    end
    
    subgraph "Data Flow"
        K[ClubeDoValorService]
        L[Backend API]
        M[Database]
        
        A --> K
        K --> L
        L --> M
    end
    
    style B fill:#e8f4fd
    style G fill:#d4edda
    style H fill:#fff3cd
    style I fill:#fff3cd
    style J fill:#fff3cd
```

## Layout Structure

```mermaid
graph LR
    subgraph "Page Layout"
        A[Left Sidebar<br/>380px fixed]
        B[Right Content Area<br/>1fr - fills remaining]
    end
    
    subgraph "Left Sidebar Content"
        C[Clube do Valor Header]
        D[Month List Navigation]
    end
    
    subgraph "Right Content Area"
        E[Strategy Selector Menu<br/>Top of content area]
        F[Content Header<br/>Title + Actions]
        G[Table Container<br/>Strategy-specific table]
    end
    
    A --> C
    A --> D
    B --> E
    B --> F
    B --> G
    
    style E fill:#e8f4fd
    style G fill:#f8f9fa
```

## Component State Management

```mermaid
stateDiagram-v2
    [*] --> Initializing
    
    Initializing --> LoadingMonths: ngOnInit()
    LoadingMonths --> LoadingStocks: Months loaded
    LoadingStocks --> DisplayingAMBB1: Stocks loaded (default)
    
    DisplayingAMBB1 --> LoadingAMBB2: User selects AMBB2
    DisplayingAMBB1 --> LoadingMDIV: User selects MDIV
    DisplayingAMBB1 --> LoadingMOM: User selects MOM
    
    LoadingAMBB2 --> DisplayingAMBB2: AMBB2 data loaded
    LoadingMDIV --> DisplayingMDIV: MDIV data loaded
    LoadingMOM --> DisplayingMOM: MOM data loaded
    
    DisplayingAMBB2 --> LoadingAMBB1: User selects AMBB1
    DisplayingAMBB2 --> LoadingMDIV: User selects MDIV
    DisplayingAMBB2 --> LoadingMOM: User selects MOM
    
    DisplayingMDIV --> LoadingAMBB1: User selects AMBB1
    DisplayingMDIV --> LoadingAMBB2: User selects AMBB2
    DisplayingMDIV --> LoadingMOM: User selects MOM
    
    DisplayingMOM --> LoadingAMBB1: User selects AMBB1
    DisplayingMOM --> LoadingAMBB2: User selects AMBB2
    DisplayingMOM --> LoadingMDIV: User selects MDIV
    
    LoadingAMBB1 --> DisplayingAMBB1: AMBB1 data loaded
```

## Data Model Changes

```mermaid
erDiagram
    StockSnapshot ||--o{ Stock : contains
    StockSnapshot {
        uuid id PK
        string timestamp
        string strategy_type "NEW: AMBB1, AMBB2, MDIV, MOM"
        bool is_current
        datetime created_at
    }
    
    Stock {
        int id PK
        uuid snapshot_id FK
        int ranking
        string codigo
        decimal earning_yield
        string nome
        string setor
        decimal ev
        decimal ebit
        decimal liquidez
        decimal cotacao_atual
        text observacao
    }
    
    StrategyConfig {
        string code PK "AMBB1, AMBB2, MDIV, MOM"
        string name
        string description
        string display_name
    }
```

## API Endpoint Changes

```mermaid
sequenceDiagram
    participant UI as Frontend Component
    participant Service as ClubeDoValorService
    participant API as Backend API
    participant DB as Database
    
    UI->>Service: getCurrentStocks(strategy: 'AMBB1')
    Service->>API: GET /api/clubedovalor/?strategy=AMBB1
    API->>DB: Query StockSnapshot WHERE strategy='AMBB1' AND is_current=true
    DB-->>API: StockSnapshot + Stocks
    API-->>Service: {timestamp, stocks, count}
    Service-->>UI: ClubeDoValorResponse
    
    UI->>Service: getHistory(strategy: 'AMBB1')
    Service->>API: GET /api/clubedovalor/history/?strategy=AMBB1
    API->>DB: Query StockSnapshot WHERE strategy='AMBB1' AND is_current=false
    DB-->>API: Array of Snapshots
    API-->>Service: {snapshots, count}
    Service-->>UI: ClubeDoValorHistoryResponse
```

## UI Component Hierarchy

```mermaid
graph TD
    A[ClubeDoValorComponent] --> B[StrategySelectorComponent]
    A --> C[MonthSidebarComponent]
    A --> D[ContentAreaComponent]
    
    B --> B1[StrategyButton: AMBB1]
    B --> B2[StrategyButton: AMBB2]
    B --> B3[StrategyButton: MDIV]
    B --> B4[StrategyButton: MOM]
    
    D --> E[ContentHeaderComponent]
    D --> F[StrategyTableComponent]
    
    F --> F1[AMBB1TableComponent]
    F --> F2[AMBB2TableComponent]
    F --> F3[MDIVTableComponent]
    F --> F4[MOMTableComponent]
    
    style B fill:#e8f4fd
    style F fill:#f8f9fa
```

## Implementation Phases

```mermaid
gantt
    title Clube do Valor Strategy Selector Implementation
    dateFormat YYYY-MM-DD
    section Frontend
    Add Strategy Selector Menu    :a1, 2025-01-01, 2d
    Update Component State       :a2, after a1, 2d
    Update Service Methods       :a3, after a1, 1d
    Update Table Display Logic   :a4, after a2, 2d
    section Backend
    Add Strategy Field to Model  :b1, 2025-01-01, 1d
    Update API Endpoints         :b2, after b1, 2d
    Update Service Methods       :b3, after b1, 2d
    Migration                    :b4, after b1, 1d
    section Testing
    Frontend Tests               :c1, after a4, 2d
    Backend Tests                :c2, after b3, 2d
    Integration Tests            :c3, after c1, 2d
```

