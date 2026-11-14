import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:roadscan_mobile/models/queued_report.dart';
import 'package:roadscan_mobile/models/remote_report.dart';
import 'package:roadscan_mobile/models/report_draft.dart';
import 'package:roadscan_mobile/models/report_result.dart';
import 'package:roadscan_mobile/services/api_client.dart';
import 'package:roadscan_mobile/services/offline_queue_repository.dart';
import 'package:roadscan_mobile/services/sabeel_data.dart';

import '../helpers/offline_api.dart';

QueuedReport _report(String id) => QueuedReport(
  draft: ReportDraft(
    deviceReportId: id,
    lat: 36.8065,
    lon: 10.1815,
    gpsAccuracyM: 4,
    speedKmh: 0,
    directionDeg: 90,
    capturedAt: DateTime.utc(2026, 11, 7, 10),
    source: ReportSource.manual,
  ),
  photoPath: '/tmp/$id.jpg',
  queuedAt: DateTime.utc(2026, 11, 7, 10),
);

ReportResult _ok(String id, {bool detected = true}) => ReportResult(
  reportId: 'r-$id',
  deviceReportId: id,
  potholeId: detected ? 'p-$id' : null,
  ref: detected ? 'TN-ABC123' : null,
  status: 'new',
  detected: detected,
  score: detected ? 3 : null,
);

MyReport _server(String id, String status) => MyReport.fromJson({
  'device_report_id': id,
  'report_id': 'r-$id',
  'pothole_id': 'p-$id',
  'ref': 'TN-ABC123',
  'status': status,
  'score': 3,
  'severity': 3,
  'detected': true,
  'sheet_status': null,
  'target_office': 'Municipalité de Tunis',
  'address_label': 'Rue de Marseille, Tunis',
  'photo_url': null,
  'lat': 36.8,
  'lon': 10.18,
  'created_at': '2026-11-07T10:00:00Z',
  'updated_at': '2026-11-07T11:00:00Z',
  'fixed_at': null,
});

Future<OfflineQueueRepository> _store([
  Map<String, Object> initial = const {},
]) async {
  SharedPreferences.setMockInitialValues(initial);
  final repo = OfflineQueueRepository(await SharedPreferences.getInstance());
  await repo.load();
  return repo;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'a successful upload keeps the report in history with its pothole ref',
    () async {
      final store = await _store();
      final data = SabeelData(store, api: FakeApi([_ok('a')]), notify: false);
      final stored = await data.submit(_report('a'));
      expect(stored!.isUploaded, isTrue);
      expect(stored.ref, 'TN-ABC123');
      expect(store.queue, hasLength(1)); // still listed in "Mes Rapports"
    },
  );

  test(
    'offline: retried later with backoff, same device_report_id (no duplicate)',
    () async {
      final store = await _store();
      final api = FakeApi([
        const ApiClientException('Serveur injoignable.'),
        _ok('a'),
      ]);
      final data = SabeelData(store, api: api, notify: false);
      final first = await data.submit(_report('a'));
      expect(first!.uploadState, UploadState.pending);
      expect(first.attempts, 1);
      expect(first.nextAttemptAt!.isAfter(DateTime.now().toUtc()), isTrue);

      await data.flushUploads(); // backoff not elapsed: nothing sent
      expect(api.calls, hasLength(1));

      await data.flushUploads(ignoreSchedule: true); // connection back
      expect(store.byId('a')!.isUploaded, isTrue);
      expect(api.calls.map((c) => c.$1).toSet(), {'a'});
    },
  );

  test('a 4xx is not retried forever', () async {
    final store = await _store();
    final data = SabeelData(
      store,
      api: FakeApi([
        const ApiClientException('Photo must be a JPEG', statusCode: 415),
      ]),
      notify: false,
    );
    final r = await data.submit(_report('a'));
    expect(r!.uploadState, UploadState.failed);
    expect(store.pending, isEmpty);
  });

  test(
    'detected=false waits for the citizen; "send anyway" resends with force',
    () async {
      final store = await _store();
      final api = FakeApi([_ok('a', detected: false), _ok('a')]);
      final data = SabeelData(store, api: api, notify: false);
      final r = await data.submit(_report('a'));
      expect(r!.notDetected, isTrue);
      expect(store.pending, isEmpty); // not retried automatically

      final sent = await data.resolveNotDetected('a', sendAnyway: true);
      expect(sent!.isUploaded, isTrue);
      expect(api.calls.last, ('a', true));
    },
  );

  test('"Reprendre" drops the report', () async {
    final store = await _store();
    final data = SabeelData(
      store,
      api: FakeApi([_ok('a', detected: false)]),
      notify: false,
    );
    await data.submit(_report('a'));
    await data.resolveNotDetected('a', sendAnyway: false);
    expect(store.queue, isEmpty);
  });

  test('status sync updates the stored report from the server', () async {
    final store = await _store();
    final data = SabeelData(
      store,
      api: FakeApi([_ok('a')], server: [_server('a', 'fixed')]),
      notify: false,
    );
    await data.submit(_report('a'));
    await data.syncStatus();
    expect(store.byId('a')!.status, 'fixed');
    expect(store.byId('a')!.locationLabel, 'Rue de Marseille, Tunis');
  });

  test('Sprint 1 queue entries migrate as pending uploads', () async {
    final old = {
      'draft': _report('old').draft.toApiJson(),
      'photo_path': '/tmp/old.jpg',
      'queued_at': '2026-09-15T10:32:05.000Z',
      'location_label': null,
    };
    final store = await _store({
      'offline_report_queue': jsonEncode([old]),
    });
    expect(store.pending.single.id, 'old');
    expect(store.pending.single.uploadState, UploadState.pending);
  });

  test('mock reports are never persisted', () async {
    final store = await _store();
    await store.add(_report('mock-1'));
    final reloaded = OfflineQueueRepository(
      await SharedPreferences.getInstance(),
    );
    await reloaded.load();
    expect(reloaded.queue, isEmpty);
  });
}
