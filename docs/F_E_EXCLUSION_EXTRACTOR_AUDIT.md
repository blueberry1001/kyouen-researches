# F-E historical exclusion extractor audit

Freeze base: `224f0dae89f95bfafa20290e872d96b9567dc6d7`.

Before generating the holdout manifest, the historical extractor needs complete fail-closed coverage.

Resolved in `d434fe7`:

1. `.tsv` is parsed with a tab delimiter rather than the CSV default.
2. Structured records are the only source of automatic exclusions; source/document text is routed to a provenance-level review queue.
3. Parser choice is provenance-aware (`blob SHA`, parser kind), so rename history such as `.csv` -> `.tsv` cannot silently select one parser for every occurrence.

Additional fail-closed issue found after `d434fe7`:

- Relevant blobs that fail UTF-8 decoding increment `ambiguous_decode`, but `manifest_gate_open` currently depends only on `conflicts` and the text review queue. Therefore the gate can open even though a reachable structured/review provenance was never inspected.
- Structured parse failures are also represented as an empty result (`[]`). Invalid/truncated JSON, malformed JSONL, or CSV/TSV parser errors are therefore indistinguishable from a valid file containing zero labels, and do not close the manifest gate.

Required correction before manifest freeze:

- Keep `.tsv` tab parsing and provenance-aware parser selection.
- Keep source/document candidates in `review_candidate_provenances`; do not promote them automatically.
- Add an `unresolved_provenances` (or equivalent) class covering every relevant provenance whose bytes cannot be decoded under the declared text policy or whose selected structured parser fails.
- Structured parsers must return success/failure separately from the list of extracted labels. A successful parse with zero labels is allowed; a parser exception or malformed record stream is unresolved.
- `manifest_gate_open` must require: zero WIN/LOSS conflicts, zero review candidates, and zero unresolved relevant provenances.
- Do not generate or inspect the 36-state holdout manifest until all three conditions hold.

This remains a pre-outcome amendment: it changes only leakage detection and does not use candidate holdout labels or outcomes.
