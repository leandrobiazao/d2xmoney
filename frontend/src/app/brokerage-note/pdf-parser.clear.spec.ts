import { TestBed } from '@angular/core/testing';
import { PdfParserService } from './pdf-parser.service';
import { TickerMappingService } from '../portfolio/ticker-mapping/ticker-mapping.service';
import { DebugService } from '../shared/services/debug.service';

/** Auto-map ticker from B3 code embedded in nome (e.g. NSLU11, AERIS ON NM -> no code uses MOCK). */
class TickerMappingServiceStub {
  private mappings: Record<string, string> = {
    'FII LOURDES NSLU11 CI': 'NSLU11',
    'AERIS ON NM': 'AERI3',
    'BEMOBI TECH ON NM': 'BMOB3',
    'CSNMINERACAO ON N2': 'CMIN3',
    'ENAUTA PART ON NM': 'ENAT3'
  };

  getTicker(nome: string): string | null {
    const key = nome.replace(/\s+/g, ' ').trim().toUpperCase();
    for (const [k, v] of Object.entries(this.mappings)) {
      if (k.toUpperCase() === key) {
        return v;
      }
    }
    const code = nome.match(/\b([A-Z]{4}\d{1,2})\b/i);
    return code ? code[1].toUpperCase() : 'TEST3';
  }

  setTicker(): void {
    /* no-op */
  }

  getAllMappings(): Record<string, string> {
    return this.mappings;
  }
}

class DebugServiceStub {
  log(): void {
    /* no-op */
  }
  warn(): void {
    /* no-op */
  }
  error(): void {
    /* no-op */
  }
}

async function loadFixturePdf(name: string): Promise<File> {
  const res = await fetch(`/fixtures/clear/${name}`);
  const buf = await res.arrayBuffer();
  return new File([buf], name, { type: 'application/pdf' });
}

describe('PdfParserService CLEAR (XPINC)', () => {
  let service: PdfParserService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        PdfParserService,
        { provide: TickerMappingService, useClass: TickerMappingServiceStub },
        { provide: DebugService, useClass: DebugServiceStub }
      ]
    });
    service = TestBed.inject(PdfParserService);
  });

  it('auto-detects CLEAR broker and parses single-operation note (2021)', async () => {
    const file = await loadFixturePdf('XPINC_NOTA_NEGOCIACAO_B3_1_3_2021.pdf');
    const result = await service.parsePdf(file, undefined, 'auto');

    expect(result.notes.length).toBe(1);
    expect(result.notes[0].operations.length).toBe(1);
    expect(result.notes[0].noteNumber).toBe('4011558');
    expect(result.notes[0].noteDate).toBe('01/03/2021');
    expect(result.accountNumber).toBe('8770006');
    expect(result.notes[0].operations[0].corretora).toBe('CLEAR Corretora');
  });

  it('uses CLEAR parser when provider hint is xp but PDF is CLEAR (Leandro / XP Investimentos)', async () => {
    const file = await loadFixturePdf('XPINC_NOTA_NEGOCIACAO_B3_1_3_2021.pdf');
    const result = await service.parsePdf(file, undefined, 'xp');

    expect(result.notes[0].operations.length).toBe(1);
    expect(result.accountNumber).toBe('8770006');
  });

  it('parses multi-operation note (2023-03)', async () => {
    const file = await loadFixturePdf('XPINC_NOTA_NEGOCIACAO_B3_1_3_2023.pdf');
    const result = await service.parsePdf(file, undefined, 'auto');

    expect(result.notes.length).toBe(1);
    expect(result.notes[0].operations.length).toBe(14);
    expect(result.notes[0].noteDate).toBe('01/03/2023');
  });

  it('parses two-page note with short note number (2023-01)', async () => {
    const file = await loadFixturePdf('XPINC_NOTA_NEGOCIACAO_B3_2_1_2023.pdf');
    const result = await service.parsePdf(file, undefined, 'auto');

    expect(result.notes.length).toBe(1);
    expect(result.notes[0].noteNumber).toBe('8512');
    expect(result.notes[0].operations.length).toBeGreaterThan(20);
  });

  it('extracts IRRF tax and base from CLEAR financial summary (not vendas amount)', async () => {
    const file = await loadFixturePdf('XPINC_NOTA_NEGOCIACAO_B3_1_3_2021.pdf');
    const result = await service.parsePdf(file, undefined, 'auto');
    const fs = result.notes[0].financialSummary;

    expect(fs?.vendas_a_vista).toBeCloseTo(273.39, 2);
    expect(fs?.irrf_operacoes).toBeCloseTo(0.01, 2);
    expect(fs?.irrf_base).toBeCloseTo(273.39, 2);
  });
});
