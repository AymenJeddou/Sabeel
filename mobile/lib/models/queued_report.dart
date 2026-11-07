import 'report_draft.dart';

/// Where a locally stored report stands on its way to the Core API.
enum UploadState { pending, uploading, uploaded, failed }

/// A report as this phone keeps it (issue #31): the frozen contract fields,
/// the photo on disk, the upload state with its retry schedule, and the last
/// status the server gave for its pothole. Every report stays here after
/// upload, so "Mes Rapports" never loses history.
class QueuedReport {
  const QueuedReport({
    required this.draft,
    required this.photoPath,
    required this.queuedAt,
    this.locationLabel,
    this.uploadState = UploadState.pending,
    this.attempts = 0,
    this.nextAttemptAt,
    this.lastError,
    this.force = false,
    this.notDetected = false,
    this.potholeId,
    this.ref,
    this.status,
    this.severity,
    this.sheetStatus,
    this.targetOffice,
    this.fixedAt,
    this.updatedAt,
  });

  final ReportDraft draft;

  /// Local filesystem path to the photo, copied into permanent app storage
  /// so it survives OS cache eviction while the report waits to upload.
  final String photoPath;
  final DateTime queuedAt;
  final String? locationLabel;

  final UploadState uploadState;
  final int attempts;
  final DateTime? nextAttemptAt;
  final String? lastError;

  /// "Envoyer quand même" after the model saw no pothole.
  final bool force;

  /// The server answered detected=false: waiting for the citizen's choice.
  final bool notDetected;

  // Last known server state of the pothole this report belongs to.
  final String? potholeId;
  final String? ref;
  final String? status;
  final int? severity;
  final String? sheetStatus;
  final String? targetOffice;
  final DateTime? fixedAt;
  final DateTime? updatedAt;

  String get id => draft.deviceReportId;

  /// Short code before the server assigns the pothole reference.
  String get reference {
    if (ref != null) return ref!;
    final compact = draft.deviceReportId.replaceAll(RegExp('[^0-9a-zA-Z]'), '');
    final suffix = compact.length >= 4 ? compact.substring(0, 4) : compact;
    return 'TN-${suffix.toUpperCase()}';
  }

  bool get isUploaded => uploadState == UploadState.uploaded;

  QueuedReport copyWith({
    UploadState? uploadState,
    int? attempts,
    DateTime? nextAttemptAt,
    String? lastError,
    bool? force,
    bool? notDetected,
    String? potholeId,
    String? ref,
    String? status,
    int? severity,
    String? sheetStatus,
    String? targetOffice,
    DateTime? fixedAt,
    DateTime? updatedAt,
    String? locationLabel,
  }) => QueuedReport(
    draft: draft,
    photoPath: photoPath,
    queuedAt: queuedAt,
    locationLabel: locationLabel ?? this.locationLabel,
    uploadState: uploadState ?? this.uploadState,
    attempts: attempts ?? this.attempts,
    nextAttemptAt: nextAttemptAt ?? this.nextAttemptAt,
    lastError: lastError ?? this.lastError,
    force: force ?? this.force,
    notDetected: notDetected ?? this.notDetected,
    potholeId: potholeId ?? this.potholeId,
    ref: ref ?? this.ref,
    status: status ?? this.status,
    severity: severity ?? this.severity,
    sheetStatus: sheetStatus ?? this.sheetStatus,
    targetOffice: targetOffice ?? this.targetOffice,
    fixedAt: fixedAt ?? this.fixedAt,
    updatedAt: updatedAt ?? this.updatedAt,
  );

  Map<String, dynamic> toJson() => {
    'draft': draft.toApiJson(),
    'photo_path': photoPath,
    'queued_at': queuedAt.toUtc().toIso8601String(),
    'location_label': locationLabel,
    'upload_state': uploadState.name,
    'attempts': attempts,
    'next_attempt_at': nextAttemptAt?.toUtc().toIso8601String(),
    'last_error': lastError,
    'force': force,
    'not_detected': notDetected,
    'pothole_id': potholeId,
    'ref': ref,
    'status': status,
    'severity': severity,
    'sheet_status': sheetStatus,
    'target_office': targetOffice,
    'fixed_at': fixedAt?.toUtc().toIso8601String(),
    'updated_at': updatedAt?.toUtc().toIso8601String(),
  };

  /// Also reads the Sprint 1 queue shape (draft, photo_path, queued_at,
  /// location_label only): those reports were never uploaded, so they come
  /// back as `pending`.
  factory QueuedReport.fromJson(Map<String, dynamic> json) {
    DateTime? date(String key) =>
        json[key] == null ? null : DateTime.parse(json[key] as String).toUtc();
    return QueuedReport(
      draft: ReportDraft.fromApiJson(json['draft'] as Map<String, dynamic>),
      photoPath: json['photo_path'] as String,
      queuedAt: DateTime.parse(json['queued_at'] as String).toUtc(),
      locationLabel: json['location_label'] as String?,
      uploadState: UploadState.values.firstWhere(
        (s) => s.name == json['upload_state'],
        orElse: () => UploadState.pending,
      ),
      attempts: json['attempts'] as int? ?? 0,
      nextAttemptAt: date('next_attempt_at'),
      lastError: json['last_error'] as String?,
      force: json['force'] as bool? ?? false,
      notDetected: json['not_detected'] as bool? ?? false,
      potholeId: json['pothole_id'] as String?,
      ref: json['ref'] as String?,
      status: json['status'] as String?,
      severity: json['severity'] as int?,
      sheetStatus: json['sheet_status'] as String?,
      targetOffice: json['target_office'] as String?,
      fixedAt: date('fixed_at'),
      updatedAt: date('updated_at'),
    );
  }
}
