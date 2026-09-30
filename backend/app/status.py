"""
Report status state machine (Sprint1_Action_Plan.md, Section 4.2).
Four states, forward-only transitions, plus REJECTED: an authority
dismissing a false positive from the dashboard, allowed from any open state.
WP3 owns enforcing this; WP4 only ever displays the current value.
"""

from enum import Enum

FORWARD_ORDER = ["new", "confirmed", "sheet_sent", "fixed"]


class ReportStatus(str, Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    SHEET_SENT = "sheet_sent"
    FIXED = "fixed"
    REJECTED = "rejected"


def is_valid_transition(current: ReportStatus, new: ReportStatus) -> bool:
    """True only if `new` is strictly the next state after `current` in the
    forward chain, or a rejection of a report that isn't closed yet."""
    if new == ReportStatus.REJECTED:
        return current in (ReportStatus.NEW, ReportStatus.CONFIRMED, ReportStatus.SHEET_SENT)
    if current == ReportStatus.REJECTED:
        return False
    current_index = FORWARD_ORDER.index(current.value)
    new_index = FORWARD_ORDER.index(new.value)
    return new_index == current_index + 1
