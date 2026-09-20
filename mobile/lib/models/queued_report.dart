import 'report_draft.dart';

/// The offline queue's data shape (docs/Sprint1_Action_Plan.md, Section 3,
/// WP4): a not-yet-uploaded report waiting on the phone.
///
/// Wraps the frozen [ReportDraft] contract fields with local-only metadata
/// that never gets sent to the API. Full sync/upload/retry logic is out of
/// scope this sprint — this is the sketch of what one queued item holds.
class QueuedReport {
  const QueuedReport({
    required this.draft,
    required this.photoPath,
    required this.queuedAt,
    this.locationLabel,
  });

  final ReportDraft draft;

  /// Local filesystem path to the photo, copied into permanent app storage
  /// so it survives OS cache eviction while the report waits to upload.
  final String photoPath;

  final DateTime queuedAt;

  /// Human-readable place name when one is known. Null for real captures
  /// until reverse geocoding exists, in which case the UI shows coordinates.
  final String? locationLabel;

  /// Short code the citizen can quote to follow this report without an
  /// account. Derived from [ReportDraft.deviceReportId] so it is stable for
  /// the life of the report and needs no extra storage.
  String get reference {
    // Development samples carry a `mock-` prefix (see mock_reports.dart);
    // skipping it keeps their references readable.
    final raw = draft.deviceReportId.startsWith('mock-')
        ? draft.deviceReportId.substring(5)
        : draft.deviceReportId;
    final compact = raw.replaceAll(RegExp('[^0-9a-zA-Z]'), '');
    final suffix = compact.length >= 4 ? compact.substring(0, 4) : compact;
    return 'TN-${suffix.toUpperCase()}';
  }

  Map<String, dynamic> toJson() {
    return {
      'draft': draft.toApiJson(),
      'photo_path': photoPath,
      'queued_at': queuedAt.toUtc().toIso8601String(),
      'location_label': locationLabel,
    };
  }

  factory QueuedReport.fromJson(Map<String, dynamic> json) {
    return QueuedReport(
      draft: ReportDraft.fromApiJson(json['draft'] as Map<String, dynamic>),
      photoPath: json['photo_path'] as String,
      queuedAt: DateTime.parse(json['queued_at'] as String).toUtc(),
      locationLabel: json['location_label'] as String?,
    );
  }
}
