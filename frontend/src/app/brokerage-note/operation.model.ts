export interface Operation {
  id: string;
  tipoOperacao: 'C' | 'V'; // Compra ou Venda
  tipoMercado: string; // FRACIONARIO, VISTA, etc.
  ordem: number;
  titulo: string; // Código da ação (ex: ANIM3, ARML3)
  qtdTotal: number;
  precoMedio: number;
  quantidade: number; // Pode ser negativo para vendas
  preco: number;
  valorOperacao: number;
  dc: 'D' | 'C'; // Débito ou Crédito
  notaTipo: string; // Bovespa, etc.
  corretora: string;
  nota: string; // Número da nota
  data: string; // DD/MM/YYYY
  clientId: string; // ID do cliente
}

