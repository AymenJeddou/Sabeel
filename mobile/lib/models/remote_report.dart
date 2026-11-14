/// One of this phone's reports as GET /devices/{device_id}/reports returns it,
/// with the status of the pothole it belongs to.
class MyReport {
  const MyReport({
    required this.deviceReportId,
    required this.reportId,
    required this.potholeId,
    required this.ref,
    required this.status,
    required this.score,
    required this.severity,
    required this.detected,
    required this.sheetStatus,
    required this.targetOffice,
    required this.addressLabel,
    required this.photoUrl,
    required this.lat,
    required this.lon,
    required this.createdAt,
    required this.updatedAt,
    required this.fixedAt,
  });

  final String deviceReportId;
  final String reportId;
  final String? potholeId;
  final String? ref;

  /// new | confirmed | sheet_sent | fixed | rejected | reopened
  final String status;
  final int? score;
  final int? severity;
  final bool detected;
  final String? sheetStatus;
  final String? targetOffice;
  final String? addressLabel;
  final String? photoUrl;
  final double lat;
  final double lon;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? fixedAt;

  factory MyReport.fromJson(Map<String, dynamic> json) => MyReport(
    deviceReportId: json['device_report_id'] as String,
    reportId: json['report_id'] as String,
    potholeId: json['pothole_id'] as String?,
    ref: json['ref'] as String?,
    status: json['status'] as String,
    score: json['score'] as int?,
    severity: json['severity'] as int?,
    detected: json['detected'] as bool? ?? true,
    sheetStatus: json['sheet_status'] as String?,
    targetOffice: json['target_office'] as String?,
    addressLabel: json['address_label'] as String?,
    photoUrl: json['photo_url'] as String?,
    lat: (json['lat'] as num).toDouble(),
    lon: (json['lon'] as num).toDouble(),
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: DateTime.parse(json['updated_at'] as String),
    fixedAt: json['fixed_at'] == null
        ? null
        : DateTime.parse(json['fixed_at'] as String),
  );
}

/// A pothole on the public map (GET /map): no photos, no device data.
class MapPothole {
  const MapPothole({
    required this.potholeId,
    required this.ref,
    required this.lat,
    required this.lon,
    required this.severity,
    required this.status,
    required this.reportCount,
    required this.confirmCount,
    required this.addressLabel,
    required this.createdOn,
  });

  final String potholeId;
  final String ref;
  final double lat;
  final double lon;
  final int? severity;
  final String status;
  final int reportCount;
  final int confirmCount;
  final String? addressLabel;
  final DateTime createdOn;

  bool get isOpen => status != 'fixed' && status != 'rejected';

  factory MapPothole.fromJson(Map<String, dynamic> json) => MapPothole(
    potholeId: json['pothole_id'] as String,
    ref: json['ref'] as String,
    lat: (json['lat'] as num).toDouble(),
    lon: (json['lon'] as num).toDouble(),
    severity: json['score'] as int?,
    status: json['status'] as String,
    reportCount: json['report_count'] as int? ?? 1,
    confirmCount: json['confirm_count'] as int? ?? 0,
    addressLabel: json['address_label'] as String?,
    createdOn: DateTime.parse(json['created_on'] as String),
  );
}

/// One line of the citizen <-> authority support chat.
class ChatMessage {
  const ChatMessage({
    required this.fromCitizen,
    required this.body,
    required this.createdAt,
  });

  final bool fromCitizen;
  final String body;
  final DateTime createdAt;

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
    fromCitizen: json['sender'] == 'citizen',
    body: json['body'] as String,
    createdAt: DateTime.parse(json['created_at'] as String),
  );
}
