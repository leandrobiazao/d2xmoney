/**
 * Dicionário de mapeamento de nomes de empresas para tickers da B3
 * Este arquivo contém os mapeamentos padrão que são usados quando um nome
 * de empresa é encontrado nas notas de corretagem.
 * 
 * IMPORTANTE: O mapeamento usa o campo completo (nome da empresa + código de classificação)
 * como chave, pois diferentes códigos de classificação podem mapear para diferentes tickers.
 * 
 * ATUALIZAÇÃO AUTOMÁTICA: Este arquivo foi atualizado automaticamente.
 * Última atualização: 05/11/2025, 08:11:45
 */
export const DEFAULT_TICKER_MAPPINGS: { [nome: string]: string } = {
  '3TENTOS': 'TTEN3',
  'ANIMA': 'ANIM3',
  'ARMAC': 'ARML3',
  'ASSAI': 'ASAI3',
  'BLAU': 'BLAU3',
  'BLAU   ON': 'BLAU3',
  'CPFL ENERGIA': 'CPFE3',
  'CSNMINERACAO': 'CMIN3',
  'CYRELA REALT': 'CYRE3',
  'GERDAU': 'GGBR4',
  'GRENDENE': 'GRND3',
  'IGUATEMI S.A': 'IGTI11',
  'ISA ENERGIA': 'MYPK3',
  'JHSF PART   ON': 'JHSF3',
  'KEPLER WEBER': 'KEPL3',
  'LAVVI': 'LAVV3',
  'METAL LEVE': 'LEVE3',
  'PETRORECSA': 'RECV3',
  'PLANOEPLANO': 'PLPL3',
  'PLAYWRIGHT_TEST': 'PTST3',
  'POSITIVO TEC': 'POSI3',
  'TEGMA': 'TGMA3',
  'TESTE': 'TEST4',
  'ULTRAPAR': 'UGPA3',
  'VALE': 'VALE3',
  'VALID': 'VLID3',
  'VAMOS': 'VAMO3'
};

