/// POST /reports response. `detected == false` with no pothole means the
/// model saw no pothole: the app offers "Reprendre" or "Envoyer quand même"
/// (which resends the same report with force=true).
class ReportResult {
  final String reportId;
  final String deviceReportId;
  final String? potholeId;
  final String? ref;
  final String status;
  final bool detected;
  final bool needsReview;
  final int? score;
  final String? sheetStatus;
  final String? targetOffice;

  const ReportResult({
    required this.reportId,
    required this.deviceReportId,
    required this.status,
    this.potholeId,
    this.ref,
    this.detected = true,
    this.needsReview = false,
    this.score,
    this.sheetStatus,
    this.targetOffice,
  });

  /// The server stored the photo but did not attach it to a pothole.
  bool get awaitingDecision => !detected && potholeId == null;

  factory ReportResult.fromJson(
    Map<String, dynamic> json, {
    String? deviceReportId,
  }) {
    return ReportResult(
      reportId: json['report_id'] as String,
      deviceReportId: deviceReportId ?? json['device_report_id'] as String,
      potholeId: json['pothole_id'] as String?,
      ref: json['ref'] as String?,
      status: json['status'] as String,
      detected: json['detected'] as bool? ?? true,
      needsReview: json['needs_review'] as bool? ?? false,
      score: json['score'] as int?,
      sheetStatus: json['sheet_status'] as String?,
      targetOffice: json['target_office'] as String?,
    );
  }
}
