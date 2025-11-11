export interface Position {
  titulo: string; // Código da ação
  quantidadeTotal: number; // Quantidade atual na carteira
  precoMedioPonderado: number; // Preço médio ponderado das compras
  valorTotalInvestido: number; // Total investido neste ativo
  valorAtualEstimado?: number; // Valor atual (opcional, se tiver cotação)
  lucroPrejuizoNaoRealizado?: number; // Lucro/prejuízo não realizado
}

