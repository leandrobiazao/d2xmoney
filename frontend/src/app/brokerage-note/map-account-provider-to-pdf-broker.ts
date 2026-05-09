/**
 * Maps User.account_provider to PDF brokerage note parser mode.
 * BTG is detected before XP so values like "conta BTG na XP" still route to BTG
 * only if that substring order is intended; typical values are mutually exclusive.
 */
export type PdfBrokerParam = 'xp' | 'btg' | 'auto';

/** Resolved broker used after auto-detect or user hint. */
export type PdfBrokerResolved = 'xp' | 'btg';

export function mapAccountProviderToPdfBroker(
  accountProvider: string | undefined | null
): PdfBrokerParam {
  if (!accountProvider?.trim()) {
    return 'auto';
  }
  const s = accountProvider.trim().toLowerCase();
  if (s.includes('btg')) {
    return 'btg';
  }
  if (s.includes('xp')) {
    return 'xp';
  }
  return 'auto';
}

export function labelCorretoraForBroker(broker: PdfBrokerResolved): string {
  return broker === 'btg' ? 'BTG Pactual' : 'XP Investimentos';
}
