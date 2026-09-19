/// Mirrors the glue backend's POST /reports and GET /reports/{id} responses
/// (Section 4.5 shapes, see backend/app/schemas.py).
class ReportResult {
  final String reportId;
  final String deviceReportId;
  final String status;
  final int? score;
  final String? sheetSummary;
  final String? targetOffice;

  ReportResult({
    required this.reportId,
    required this.deviceReportId,
    required this.status,
    this.score,
    this.sheetSummary,
    this.targetOffice,
  });

  factory ReportResult.fromCreateResponse(Map<String, dynamic> json, String deviceReportId) {
    return ReportResult(
      reportId: json['report_id'] as String,
      deviceReportId: deviceReportId,
      status: json['status'] as String,
      score: json['score'] as int?,
      sheetSummary: json['sheet_summary'] as String?,
      targetOffice: json['target_office'] as String?,
    );
  }

  factory ReportResult.fromStatusResponse(Map<String, dynamic> json, String deviceReportId) {
    return ReportResult(
      reportId: json['report_id'] as String,
      deviceReportId: deviceReportId,
      status: json['status'] as String,
      score: json['score'] as int?,
      sheetSummary: json['sheet_summary'] as String?,
    );
  }
}
