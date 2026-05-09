# BTG Pactual brokerage note PDFs (fixtures)

Add sample **notas de corretagem** from BTG Pactual here when available (e.g. `Aurelio_Avanzi_20260422_*.pdf`) for manual or e2e testing.

The parser supports BTG layout when the selected user’s **`account_provider`** contains `btg` (case-insensitive), or when **auto-detect** finds “BTG” and “Pactual” on the first pages.

If PDFs cannot be committed (PII), keep them locally and capture **text dumps** from the browser console after a one-off run, or redact before committing.

See also [`README-multi-note.md`](README-multi-note.md) for multi-note PDF expectations.
