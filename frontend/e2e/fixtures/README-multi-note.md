# Multi-note PDF fixture

## Purpose

Tests for **multi-note PDF support** require a PDF that contains **more than one brokerage note** in a single file (e.g. note A on pages 1–3, note B on page 4).

## Fixture file

- **Path:** `e2e/fixtures/multi-note.pdf`
- **Format:** A valid B3-style brokerage note PDF where:
  - At least one page contains `Nr. nota XXXXXXXX` and `Data pregão DD/MM/YYYY` for the **first** note.
  - At least one **later** page contains a **different** `Nr. nota YYYYYYYY` (and optionally `Data pregão`) for the **second** note.
- **Effect:** The parser treats each “Nr. nota” header as the start of a new note and splits the file into multiple note results. The upload/portfolio flow then saves one backend `BrokerageNote` per parsed note.

## When the fixture is missing

The e2e test **“multi-note PDF: when fixture exists, two notes are created”** is **skipped** if `e2e/fixtures/multi-note.pdf` does not exist. No fixture is committed by default; add one manually when you want to run this test.

## What the test asserts (when the fixture exists)

1. Uploading `multi-note.pdf` is accepted.
2. After processing, **two** brokerage notes are created (e.g. via history API or UI).
3. Each note has the correct `note_number` and `note_date` (matching the “Nr. nota” and “Data pregão” of its section in the PDF).

## References

- Implementation plan: `doc/spec` and plan file for “Multi-Note PDF Support”.
- Parser: `frontend/src/app/brokerage-note/pdf-parser.service.ts` (boundary detection and per-note parsing).
- Upload/portfolio: one `operationsAdded` event with `notes: NoteParseResult[]`; one backend note saved per item.
