import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:roadscan_mobile/models/queued_report.dart';
import 'package:roadscan_mobile/models/report_draft.dart';
import 'package:roadscan_mobile/services/offline_queue_repository.dart';

QueuedReport _sampleReport(String deviceReportId) {
  return QueuedReport(
    draft: ReportDraft(
      deviceReportId: deviceReportId,
      lat: 36.8065,
      lon: 10.1815,
      gpsAccuracyM: 4.2,
      speedKmh: 0,
      directionDeg: 180,
      capturedAt: DateTime.utc(2026, 9, 15, 10, 32, 0),
      source: ReportSource.manual,
    ),
    photoPath: '/tmp/$deviceReportId.jpg',
    queuedAt: DateTime.utc(2026, 9, 15, 10, 32, 5),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('add() persists the report and notifies listeners', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final repository = OfflineQueueRepository(prefs);
    await repository.load();

    var notified = false;
    repository.addListener(() => notified = true);

    await repository.add(_sampleReport('report-1'));

    expect(repository.queue, hasLength(1));
    expect(repository.queue.single.draft.deviceReportId, 'report-1');
    expect(notified, isTrue);
  });

  test(
    'load() restores a queue persisted by a previous repository instance',
    () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final writer = OfflineQueueRepository(prefs);
      await writer.load();
      await writer.add(_sampleReport('report-2'));

      final reader = OfflineQueueRepository(prefs);
      await reader.load();

      expect(reader.queue, hasLength(1));
      expect(reader.queue.single.draft.deviceReportId, 'report-2');
      expect(reader.queue.single.photoPath, '/tmp/report-2.jpg');
    },
  );

  test('remove drops an uploaded report from disk too', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final repository = OfflineQueueRepository(prefs);
    await repository.add(_sampleReport('sent'));
    await repository.add(_sampleReport('still-queued'));

    await repository.remove(repository.queue.first);

    final reloaded = OfflineQueueRepository(prefs);
    await reloaded.load();
    expect(reloaded.queue.map((r) => r.draft.deviceReportId), ['still-queued']);
  });

  test('queue exposes an unmodifiable list', () async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final repository = OfflineQueueRepository(prefs);
    await repository.load();

    expect(
      () => repository.queue.add(_sampleReport('x')),
      throwsUnsupportedError,
    );
  });
}
