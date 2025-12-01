export interface FinancialSummary {
  // Resumo dos Negócios (Business Summary)
  debentures?: number;
  vendas_a_vista?: number;
  compras_a_vista?: number;
  valor_das_operacoes?: number;
  
  // Resumo Financeiro (Financial Summary)
  clearing?: number;
  valor_liquido_operacoes?: number;
  taxa_liquidacao?: number;
  taxa_registro?: number;
  total_cblc?: number;
  bolsa?: number;
  emolumentos?: number;
  taxa_transferencia_ativos?: number;
  total_bovespa?: number;
  
  // Custos Operacionais (Operational Costs)
  taxa_operacional?: number;
  execucao?: number;
  taxa_custodia?: number;
  impostos?: number;
  irrf_operacoes?: number;
  irrf_base?: number;
  outros_custos?: number;
  total_custos_despesas?: number;
  liquido?: number;
  liquido_data?: string; // Date for "Líquido para"
}

