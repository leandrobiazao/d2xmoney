export interface Stock {
  ranking: number;
  codigo: string;
  earningYield: number;
  nome: string;
  setor: string;
  ev: number;
  ebit: number;
  liquidez: number;
  cotacaoAtual: number;
  observacao: string;
}

export interface ClubeDoValorResponse {
  timestamp: string;
  stocks: Stock[];
  count: number;
}

export interface ClubeDoValorHistoryResponse {
  snapshots: Array<{
    timestamp: string;
    data: Stock[];
  }>;
  count: number;
}

