import 'package:flutter_test/flutter_test.dart';
import 'package:roadscan_mobile/models/queued_report.dart';
import 'package:roadscan_mobile/models/report_draft.dart';

QueuedReport _queued(String deviceReportId, {String? locationLabel}) {
  return QueuedReport(
    draft: ReportDraft(
      deviceReportId: deviceReportId,
      lat: 36.8008,
      lon: 10.1817,
      gpsAccuracyM: 4.2,
      speedKmh: 0,
      directionDeg: 182,
      capturedAt: DateTime.utc(2026, 9, 15, 10, 32, 0),
      source: ReportSource.manual,
    ),
    photoPath: '/tmp/photo.jpg',
    queuedAt: DateTime.utc(2026, 9, 15, 10, 32, 5),
    locationLabel: locationLabel,
  );
}

void main() {
  test('reference takes the first four alphanumerics of the device id', () {
    expect(
      _queued('9f8e1234-abcd-0000-1111-222233334444').reference,
      'TN-9F8E',
    );
  });

  test('reference is stable for the same device id', () {
    const id = 'a1b2c3d4-0000-1111-2222-333344445555';
    expect(_queued(id).reference, _queued(id).reference);
  });

  test('json round-trip preserves the optional location label', () {
    final original = _queued('real-1', locationLabel: 'Av. Habib Bourguiba');
    final roundTripped = QueuedReport.fromJson(original.toJson());

    expect(roundTripped.locationLabel, 'Av. Habib Bourguiba');
    expect(roundTripped.draft.lat, 36.8008);
    expect(roundTripped.draft.lon, 10.1817);
  });

  test('a report with no location label round-trips as null', () {
    final roundTripped = QueuedReport.fromJson(_queued('real-2').toJson());
    expect(roundTripped.locationLabel, isNull);
  });
}
