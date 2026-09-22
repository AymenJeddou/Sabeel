from backend.app.status import ReportStatus, is_valid_transition

FORWARD_PAIRS = [
    (ReportStatus.NEW, ReportStatus.CONFIRMED),
    (ReportStatus.CONFIRMED, ReportStatus.SHEET_SENT),
    (ReportStatus.SHEET_SENT, ReportStatus.FIXED),
]

INVALID_PAIRS = [
    (ReportStatus.NEW, ReportStatus.NEW),  # same state
    (ReportStatus.CONFIRMED, ReportStatus.NEW),  # backward
    (ReportStatus.FIXED, ReportStatus.SHEET_SENT),  # backward
    (ReportStatus.NEW, ReportStatus.SHEET_SENT),  # skips confirmed
    (ReportStatus.NEW, ReportStatus.FIXED),  # skips two states
    (ReportStatus.FIXED, ReportStatus.NEW),  # backward to start
]


def test_valid_forward_transitions():
    for current, new in FORWARD_PAIRS:
        assert is_valid_transition(current, new) is True


def test_invalid_transitions_rejected():
    for current, new in INVALID_PAIRS:
        assert is_valid_transition(current, new) is False


def test_all_four_states_covered():
    assert {s.value for s in ReportStatus} == {"new", "confirmed", "sheet_sent", "fixed"}
