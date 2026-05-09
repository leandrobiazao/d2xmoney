import {
  labelCorretoraForBroker,
  mapAccountProviderToPdfBroker
} from './map-account-provider-to-pdf-broker';

describe('mapAccountProviderToPdfBroker', () => {
  it('maps BTG Pactual', () => {
    expect(mapAccountProviderToPdfBroker('BTG Pactual')).toBe('btg');
    expect(mapAccountProviderToPdfBroker('btg')).toBe('btg');
  });

  it('maps XP', () => {
    expect(mapAccountProviderToPdfBroker('XP Investimentos')).toBe('xp');
    expect(mapAccountProviderToPdfBroker('xp')).toBe('xp');
  });

  it('returns auto for empty or unknown', () => {
    expect(mapAccountProviderToPdfBroker('')).toBe('auto');
    expect(mapAccountProviderToPdfBroker(undefined)).toBe('auto');
    expect(mapAccountProviderToPdfBroker('Outra corretora')).toBe('auto');
  });
});

describe('labelCorretoraForBroker', () => {
  it('returns display labels', () => {
    expect(labelCorretoraForBroker('btg')).toBe('BTG Pactual');
    expect(labelCorretoraForBroker('xp')).toBe('XP Investimentos');
  });
});
