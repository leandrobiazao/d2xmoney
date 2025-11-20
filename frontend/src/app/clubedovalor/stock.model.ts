// Base Stock interface with common fields
export interface BaseStock {
  ranking: number;
  codigo: string;
  nome: string;
  setor: string;
  observacao: string;
}

// AMBB1 Stock interface
export interface AMBB1Stock extends BaseStock {
  earningYield: number;
  ev: number;
  ebit: number;
  liquidez: number;
  cotacaoAtual: number;
}

// AMBB2 Stock interface
export interface AMBB2Stock extends BaseStock {
  valueIdx: number;
  earningYield: number;
  cfy: number;
  btm: number;
  mktcap: number;
  ev: number;
  liquidez: number;
  cotacaoAtual: number;
}

// MDIV Stock interface
export interface MDIVStock extends BaseStock {
  dividendYield36m: number;
  liquidezMedia3m: number;
}

// MOM Stock interface
export interface MOMStock extends BaseStock {
  momentum6m: number;
  idRatio: number;
  volumeMm: number;
  capitalizacaoMm: number;
  subsetor: string;
  segmento: string;
}

// Union type for all stock types
export type Stock = AMBB1Stock | AMBB2Stock | MDIVStock | MOMStock;

export interface ClubeDoValorResponse {
  timestamp: string;
  stocks: Stock[];
  count: number;
  strategy_type?: string;
}

export interface ClubeDoValorHistoryResponse {
  snapshots: Array<{
    timestamp: string;
    data: Stock[];
  }>;
  count: number;
  strategy_type?: string;
}

