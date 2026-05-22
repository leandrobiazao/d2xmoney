import {
  parseNoteDateFromPdfFileName,
  sortPdfFilesByNoteDate,
  isPdfFile,
} from './upload-pdf-file-order';

describe('upload-pdf-file-order', () => {
  it('parseNoteDateFromPdfFileName extracts CLEAR-style dates', () => {
    expect(parseNoteDateFromPdfFileName('XPINC_NOTA_NEGOCIACAO_B3_11_9_2023.pdf')).toEqual(
      new Date(2023, 8, 11)
    );
    expect(parseNoteDateFromPdfFileName('XPINC_NOTA_NEGOCIACAO_B3_2_1_2024.pdf')).toEqual(
      new Date(2024, 0, 2)
    );
    expect(parseNoteDateFromPdfFileName('other.pdf')).toBeNull();
  });

  it('sortPdfFilesByNoteDate orders by embedded date ascending', () => {
    const files = [
      new File([''], 'XPINC_NOTA_NEGOCIACAO_B3_16_10_2023.pdf'),
      new File([''], 'XPINC_NOTA_NEGOCIACAO_B3_1_9_2023.pdf'),
      new File([''], 'XPINC_NOTA_NEGOCIACAO_B3_2_10_2023.pdf'),
    ];
    const sorted = sortPdfFilesByNoteDate(files);
    expect(sorted.map(f => f.name)).toEqual([
      'XPINC_NOTA_NEGOCIACAO_B3_1_9_2023.pdf',
      'XPINC_NOTA_NEGOCIACAO_B3_2_10_2023.pdf',
      'XPINC_NOTA_NEGOCIACAO_B3_16_10_2023.pdf',
    ]);
  });

  it('isPdfFile accepts pdf mime or extension', () => {
    expect(isPdfFile(new File([''], 'a.pdf', { type: 'application/pdf' }))).toBeTrue();
    expect(isPdfFile(new File([''], 'a.PDF', { type: '' }))).toBeTrue();
    expect(isPdfFile(new File([''], 'a.txt', { type: 'text/plain' }))).toBeFalse();
  });
});
