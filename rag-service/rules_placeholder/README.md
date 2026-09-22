# ⚠️ THESE ARE NOT REAL LAW — MVP STAND-INS

The entries in this folder are informed-engineering-practice placeholders (repair
urgency thresholds, patching method guidance) invented for the MVP demo. They are
**not attributed to any real statute or decree** — no fake law numbers, no fake
article citations. Every entry's `source` field says "MVP engineering placeholder"
explicitly, and `is_placeholder: true` is set at the file level so the RAG
pipeline's `is_placeholder` metadata flag (checked per-chunk, not per-folder) is
always correct regardless of where a file happens to live.

For the actually-sourced jurisdiction/routing rules (who a work order gets sent
to), see [`../rules_real/`](../rules_real/) — those have real citations from
Tunisian legislation.
