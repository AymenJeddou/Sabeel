"""Pothole status state machine.

    new ──> confirmed ──> sheet_sent ──> fixed ──> reopened
                 │                          ▲         │
                 └── (no sheet needed) ─────┘         ├──> sheet_sent
                                                      └──> fixed
    rejected: from any open state (an officer dismisses a false positive)

- `sheet_sent` means an officer *approved* the work sheet (roadmap decision 4),
  not that the LLM wrote it.
- A pothole below the sheet threshold (severity 1-2) never gets a sheet, so it
  may go straight from `confirmed` to `fixed`.
- `reopened` is reached only from `fixed`, when citizens report the pothole is
  still there (issue #22). It is an open state again.
"""

from enum import Enum


class ReportStatus(str, Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    SHEET_SENT = "sheet_sent"
    FIXED = "fixed"
    REJECTED = "rejected"
    REOPENED = "reopened"


S = ReportStatus
OPEN_STATUSES = (S.NEW, S.CONFIRMED, S.SHEET_SENT, S.REOPENED)

_FORWARD = {
    S.NEW: {S.CONFIRMED},
    S.CONFIRMED: {S.SHEET_SENT},
    S.SHEET_SENT: {S.FIXED},
    S.FIXED: {S.REOPENED},
    S.REOPENED: {S.SHEET_SENT, S.FIXED},
    S.REJECTED: set(),
}


def is_valid_transition(current: ReportStatus, new: ReportStatus, sheet_required: bool = True) -> bool:
    """True if `new` may follow `current`. Anything else is answered with HTTP 409."""
    current, new = S(current), S(new)
    if new == S.REJECTED:
        return current in OPEN_STATUSES
    if current == S.CONFIRMED and new == S.FIXED:
        return not sheet_required
    return new in _FORWARD[current]
