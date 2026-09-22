import 'package:flutter_test/flutter_test.dart';
import 'package:roadscan_mobile/models/report_draft.dart';

ReportDraft _sample({ReportSource source = ReportSource.manual}) {
  return ReportDraft(
    deviceReportId: 'local-9f8e-test',
    lat: 36.8065,
    lon: 10.1815,
    gpsAccuracyM: 4.2,
    speedKmh: 38.5,
    directionDeg: 270.0,
    capturedAt: DateTime.utc(2026, 9, 15, 10, 32, 0),
    source: source,
  );
}

void main() {
  test(
    'toApiJson uses the exact frozen contract field names, in order, lat before lon',
    () {
      final json = _sample().toApiJson();

      expect(json.keys.toList(), [
        'device_report_id',
        'lat',
        'lon',
        'gps_accuracy_m',
        'speed_kmh',
        'direction_deg',
        'captured_at',
        'source',
      ]);
      expect(json['lat'], 36.8065);
      expect(json['lon'], 10.1815);
      expect(json['captured_at'], '2026-09-15T10:32:00Z');
      expect(json['source'], 'manual');
    },
  );

  test('driving mode source serializes to driving_mode', () {
    final json = _sample(source: ReportSource.drivingMode).toApiJson();
    expect(json['source'], 'driving_mode');
  });

  test('fromApiJson round-trips toApiJson', () {
    final original = _sample();
    final roundTripped = ReportDraft.fromApiJson(original.toApiJson());
    expect(roundTripped.toApiJson(), original.toApiJson());
  });
}
