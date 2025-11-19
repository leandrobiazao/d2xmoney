export interface Position {
  titulo: string; // Código da ação
  quantidadeTotal: number; // Quantidade atual na carteira
  precoMedioPonderado: number; // Preço médio ponderado das compras
  valorTotalInvestido: number; // Total investido neste ativo
  lucroRealizado: number; // Lucro/prejuízo realizado (Average Cost method)
  valorAtualEstimado?: number; // Valor atual (opcional, se tiver cotação)
  lucroPrejuizoNaoRealizado?: number; // Lucro/prejuízo não realizado
  currentPrice?: number; // Preço atual do ativo
  unrealizedPnL?: number; // Lucro/prejuízo não realizado (calculado)
  valorAtual?: number; // Valor atual da posição (Quantidade × Preço Atual)
  totalLucro?: number; // Lucro total (Lucro Realizado + Lucro Não Realizado)
}

