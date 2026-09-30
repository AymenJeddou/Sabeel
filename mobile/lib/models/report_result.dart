/// Mirrors WP3's POST /reports response (Section 4.5, plus the additive
/// sheet_summary/target_office fields documented in backend/app/schemas.py).
class ReportResult {
  final String reportId;
  final String deviceReportId;
  final String status;
  final int? score;
  final String? sheetSummary;
  final String? targetOffice;

  const ReportResult({
    required this.reportId,
    required this.deviceReportId,
    required this.status,
    this.score,
    this.sheetSummary,
    this.targetOffice,
  });

  factory ReportResult.fromJson(
    Map<String, dynamic> json, {
    String? deviceReportId,
  }) {
    return ReportResult(
      reportId: json['report_id'] as String,
      deviceReportId: deviceReportId ?? json['device_report_id'] as String,
      status: json['status'] as String,
      score: json['score'] as int?,
      sheetSummary: json['sheet_summary'] as String?,
      targetOffice: json['target_office'] as String?,
    );
  }
}
