import '../utils/iso8601.dart';

/// Which flow created the report. Serializes exactly to the frozen
/// contract's `source` enum (docs/Sprint1_Action_Plan.md, Section 4.1).
///
/// Only [manual] is ever produced this sprint — hands-free driving mode
/// is explicitly deferred.
enum ReportSource {
  manual('manual'),
  drivingMode('driving_mode');

  const ReportSource(this.wireValue);

  final String wireValue;

  static ReportSource fromWireValue(String value) {
    return ReportSource.values.firstWhere(
      (source) => source.wireValue == value,
      orElse: () => ReportSource.manual,
    );
  }
}

/// The report fields that will eventually cross into WP3's API, exactly as
/// frozen in docs/Sprint1_Action_Plan.md Section 4.1.
///
/// Field names and order (lat before lon, never `lng`) are frozen for
/// Sprint 1 — do not rename or reshape without updating that document.
class ReportDraft {
  const ReportDraft({
    required this.deviceReportId,
    required this.lat,
    required this.lon,
    required this.gpsAccuracyM,
    required this.speedKmh,
    required this.directionDeg,
    required this.capturedAt,
    required this.source,
  });

  final String deviceReportId;
  final double lat;
  final double lon;
  final double gpsAccuracyM;
  final double speedKmh;
  final double directionDeg;

  /// Always stored as UTC internally; serialized via [toContractIso8601Utc].
  final DateTime capturedAt;
  final ReportSource source;

  /// Exactly the shape WP3's `POST /reports` expects (Section 4.5).
  Map<String, dynamic> toApiJson() {
    return {
      'device_report_id': deviceReportId,
      'lat': lat,
      'lon': lon,
      'gps_accuracy_m': gpsAccuracyM,
      'speed_kmh': speedKmh,
      'direction_deg': directionDeg,
      'captured_at': toContractIso8601Utc(capturedAt),
      'source': source.wireValue,
    };
  }

  factory ReportDraft.fromApiJson(Map<String, dynamic> json) {
    return ReportDraft(
      deviceReportId: json['device_report_id'] as String,
      lat: (json['lat'] as num).toDouble(),
      lon: (json['lon'] as num).toDouble(),
      gpsAccuracyM: (json['gps_accuracy_m'] as num).toDouble(),
      speedKmh: (json['speed_kmh'] as num).toDouble(),
      directionDeg: (json['direction_deg'] as num).toDouble(),
      capturedAt: DateTime.parse(json['captured_at'] as String).toUtc(),
      source: ReportSource.fromWireValue(json['source'] as String),
    );
  }
}
