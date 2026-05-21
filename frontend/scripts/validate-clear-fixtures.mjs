/**
 * Batch-check CLEAR fixture PDFs with pdf.js (same library as the app).
 * Usage: node scripts/validate-clear-fixtures.mjs [directory]
 * Default directory: public/fixtures/clear
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const defaultDir = path.join(__dirname, '..', 'public', 'fixtures', 'clear');
const dir = process.argv[2] ? path.resolve(process.argv[2]) : defaultDir;

const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');

async function spatialPageText(page) {
  const textContent = await page.getTextContent();
  const items = textContent.items.map((item) => ({
    str: item.str,
    x: item.transform[4],
    y: item.transform[5]
  }));
  items.sort((a, b) => (Math.abs(a.y - b.y) < 5 ? a.x - b.x : b.y - a.y));
  let text = '';
  let currentY = -1;
  let line = [];
  for (const item of items) {
    if (currentY === -1 || Math.abs(item.y - currentY) < 5) {
      line.push(item);
      if (currentY === -1) currentY = item.y;
    } else {
      line.sort((a, b) => a.x - b.x);
      text += line.map((i) => i.str).join(' ') + '\n';
      line = [item];
      currentY = item.y;
    }
  }
  if (line.length) {
    line.sort((a, b) => a.x - b.x);
    text += line.map((i) => i.str).join(' ') + '\n';
  }
  return text;
}

function countB3RvListado(text) {
  return (text.match(/B3\s+RV\s+LISTADO/gi) || []).length;
}

function extractAccount(text) {
  const m = text.match(/Conta\s+corrente[\s\S]{0,200}?\b\d{1,4}\s+\d{1,6}\s+(\d{5,})\b/i);
  return m?.[1] ?? null;
}

const files = fs.readdirSync(dir).filter((f) => f.toLowerCase().endsWith('.pdf'));
if (!files.length) {
  console.error(`No PDFs in ${dir}`);
  process.exit(1);
}

let failed = 0;
for (const name of files.sort()) {
  const data = new Uint8Array(fs.readFileSync(path.join(dir, name)));
  const doc = await pdfjs.getDocument({ data, verbosity: 0 }).promise;
  let text = '';
  for (let p = 1; p <= doc.numPages; p++) {
    text += await spatialPageText(await doc.getPage(p));
  }
  const ops = countB3RvListado(text);
  const account = extractAccount(text);
  const isClear = /clear\s+corretora/i.test(text);
  const ok = isClear && ops > 0;
  console.log(`${ok ? 'OK' : 'FAIL'}  ${name}  ops=${ops}  account=${account ?? '-'}  clear=${isClear}`);
  if (!ok) failed++;
}

process.exit(failed ? 1 : 0);
