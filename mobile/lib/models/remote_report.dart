/// A report as the Core API's GET /reports returns it (backend ReportSummary).
class RemoteReport {
  const RemoteReport({
    required this.reportId,
    required this.ref,
    required this.deviceId,
    required this.lat,
    required this.lon,
    required this.address,
    required this.score,
    required this.status,
    required this.clusterId,
    required this.clusterSize,
    required this.photoUrl,
    required this.createdAt,
    required this.updatedAt,
    required this.dueAt,
    required this.targetOffice,
  });

  final String reportId;
  final String ref;
  final String? deviceId;
  final double lat;
  final double lon;
  final String? address;
  final int? score;

  /// new | confirmed | sheet_sent | fixed | rejected
  final String status;
  final String? clusterId;
  final int clusterSize;
  final String? photoUrl;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? dueAt;
  final String? targetOffice;

  bool get isOpen =>
      status == 'new' || status == 'confirmed' || status == 'sheet_sent';

  factory RemoteReport.fromJson(Map<String, dynamic> json) => RemoteReport(
    reportId: json['report_id'] as String,
    ref: json['ref'] as String,
    deviceId: json['device_id'] as String?,
    lat: (json['lat'] as num).toDouble(),
    lon: (json['lon'] as num).toDouble(),
    address: json['address'] as String?,
    score: json['score'] as int?,
    status: json['status'] as String,
    clusterId: json['cluster_id'] as String?,
    clusterSize: json['cluster_size'] as int? ?? 1,
    photoUrl: json['photo_url'] as String?,
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: DateTime.parse(json['updated_at'] as String),
    dueAt: json['due_at'] == null
        ? null
        : DateTime.parse(json['due_at'] as String),
    targetOffice: json['target_office'] as String?,
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
