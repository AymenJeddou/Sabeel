"""All-or-nothing citation validation.

The LLM may only cite rule_ids that were actually shown to it for this call
(the "allowlist" — a per-call subset of the DB, never the whole collection).
If the LLM's response references anything outside that allowlist, or doesn't
include a parseable reference list at all, the whole response is discarded
rather than patched -- an orphan citation could still be sitting in the body
text even after stripping a bad trailer line.
"""
from __future__ import annotations

import re

_REF_LINE_RE = re.compile(r"R[ée]f[ée]rences?\s*:\s*(.+)", re.IGNORECASE)


def extract_claimed_ids(llm_text: str) -> list[str] | None:
    """Returns the list of rule_ids the LLM claims to have used, or None if
    no parseable reference trailer was found at all."""
    match = _REF_LINE_RE.search(llm_text)
    if not match:
        return None
    raw = match.group(1)
    ids = [part.strip().strip(".") for part in raw.split(",")]
    return [i for i in ids if i]


def validate_citations(
    llm_text: str, allowlist: list[dict]
) -> tuple[str | None, list[dict]]:
    """Returns (validated_sheet_text_or_None, matched_chunks).

    validated_sheet_text is None if validation failed for any reason (no
    reference trailer, or any claimed id not in the allowlist) -- the caller
    must then fall back to the template renderer.
    """
    allowlist_by_id = {chunk["metadata"]["rule_id"]: chunk for chunk in allowlist}

    claimed_ids = extract_claimed_ids(llm_text)
    if claimed_ids is None or not claimed_ids:
        return None, []

    matched: list[dict] = []
    for rule_id in claimed_ids:
        chunk = allowlist_by_id.get(rule_id)
        if chunk is None:
            return None, []  # any invalid id discards the whole response
        matched.append(chunk)

    return llm_text, matched
