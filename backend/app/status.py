"""
Report status state machine (Sprint1_Action_Plan.md, Section 4.2).
Exactly four states, forward-only transitions. WP3 owns enforcing this;
WP4 only ever displays the current value.
"""

from enum import Enum

FORWARD_ORDER = ["new", "confirmed", "sheet_sent", "fixed"]


class ReportStatus(str, Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    SHEET_SENT = "sheet_sent"
    FIXED = "fixed"


def is_valid_transition(current: ReportStatus, new: ReportStatus) -> bool:
    """True only if `new` is strictly the next state after `current` in the forward chain."""
    current_index = FORWARD_ORDER.index(current.value)
    new_index = FORWARD_ORDER.index(new.value)
    return new_index == current_index + 1
