/**
 * @deprecated This file is deprecated. Ticker mappings are now stored in the database.
 * The source of truth is backend/data/ticker.json, which is synced to the database.
 * 
 * To sync mappings from JSON to database, run:
 *   python manage.py sync_ticker_mappings
 * 
 * Or use the API endpoint:
 *   PUT /api/ticker-mappings/
 * 
 * This file is kept for reference only and will be removed in a future version.
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
  'IGUATEMI S.A UNT N1': 'IGTT11',
  'ISA ENERGIA PN N1': 'ISAE4',
  'IOCHP-MAXION ON NM': 'MYPK3',
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

