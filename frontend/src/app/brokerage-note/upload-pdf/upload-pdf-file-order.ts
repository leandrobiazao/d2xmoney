/** Max PDFs per batch upload (performance + UX). */
export const MAX_BATCH_PDF_FILES = 50;

/**
 * Extract note date from CLEAR/XP-style filenames: ..._B3_11_9_2023.pdf → 11/09/2023
 */
export function parseNoteDateFromPdfFileName(fileName: string): Date | null {
  const match = fileName.match(/_B3_(\d{1,2})_(\d{1,2})_(\d{4})\.pdf$/i);
  if (!match) {
    return null;
  }
  const day = parseInt(match[1], 10);
  const month = parseInt(match[2], 10);
  const year = parseInt(match[3], 10);
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }
  const d = new Date(year, month - 1, day);
  if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) {
    return null;
  }
  return d;
}

/** Sort by embedded note date (asc), then file name. */
export function sortPdfFilesByNoteDate(files: File[]): File[] {
  return [...files].sort((a, b) => {
    const da = parseNoteDateFromPdfFileName(a.name);
    const db = parseNoteDateFromPdfFileName(b.name);
    if (da && db) {
      const diff = da.getTime() - db.getTime();
      if (diff !== 0) {
        return diff;
      }
    } else if (da && !db) {
      return -1;
    } else if (!da && db) {
      return 1;
    }
    return a.name.localeCompare(b.name, 'pt-BR');
  });
}

export function isPdfFile(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
}
