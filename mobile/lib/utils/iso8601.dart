/// Formats [dateTime] as the UTC ISO 8601 string required by the frozen
/// data contract (docs/Sprint1_Action_Plan.md, Section 4.1): always UTC,
/// always a trailing `Z`, no fractional seconds
/// (e.g. `2026-09-15T10:32:00Z`).
String toContractIso8601Utc(DateTime dateTime) {
  final utc = dateTime.toUtc();
  final year = utc.year.toString().padLeft(4, '0');
  final month = utc.month.toString().padLeft(2, '0');
  final day = utc.day.toString().padLeft(2, '0');
  final hour = utc.hour.toString().padLeft(2, '0');
  final minute = utc.minute.toString().padLeft(2, '0');
  final second = utc.second.toString().padLeft(2, '0');
  return '$year-$month-${day}T$hour:$minute:${second}Z';
}
