import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

import '../models/queued_report.dart';
import '../models/remote_report.dart';
import '../models/report_result.dart';
import 'api_client.dart';
import 'notifier.dart';
import 'offline_queue_repository.dart';
import 'rules.dart';

/// The app's single source of truth (issue #31):
/// - **uploads** every stored report with retries and backoff (30 s, 2 min,
///   10 min, 1 h), on app start, when the network comes back, and every 30 s
///   while the app is open; retries are safe because POST /reports is
///   idempotent on device_report_id;
/// - **syncs** each report's pothole status from GET /devices/{id}/reports and
///   raises a local notification on confirmed / sent / fixed / reopened;
/// - caches the last map area and the public stats for offline use.
///
/// # ponytail: no background task (workmanager) yet: uploads and status
/// checks run while the app is open or resumed. Add workmanager if citizens
/// need notifications without opening the app.
class SabeelData extends ChangeNotifier {
  SabeelData(
    this.queue, {
    this.api = const RoadScanApiClient(),
    this.notify = true,
  }) {
    queue.addListener(notifyListeners);
  }

  final OfflineQueueRepository queue;
  final RoadScanApiClient api;
  final bool notify;

  /// Server reports of this phone that are not in the local store (e.g. made
  /// before an app update that reset storage).
  List<MyReport> serverOnly = [];
  Map<String, dynamic>? stats;
  List<MapPothole> potholes = [];
  bool mapOffline = false;
  bool online = false;
  bool loading = false;
  bool _flushing = false;
  StreamSubscription<List<ConnectivityResult>>? _connectivity;

  /// Starts the connectivity listener (not in widget tests).
  void watchConnectivity() {
    _connectivity ??= Connectivity().onConnectivityChanged.listen((results) {
      if (results.any((r) => r != ConnectivityResult.none)) {
        unawaited(refresh());
      }
    });
  }

  @override
  void dispose() {
    _connectivity?.cancel();
    queue.removeListener(notifyListeners);
    super.dispose();
  }

  Future<void> refresh() async {
    if (loading) return;
    loading = true;
    notifyListeners();
    try {
      await flushUploads();
      await syncStatus();
      stats = await api.fetchStats();
      online = true;
    } catch (e) {
      debugPrint('[Sabeel] refresh failed: $e');
      online = false;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  /// Stores a new report and tries to send it right away.
  Future<QueuedReport?> submit(QueuedReport report) async {
    await queue.add(report);
    await flushUploads(onlyId: report.id, ignoreSchedule: true);
    final first = queue.queue.where((r) => r.isUploaded).length == 1;
    if (first && notify) unawaited(Notifier.instance.requestPermission());
    return queue.byId(report.id);
  }

  /// After detected=false: resend with force=true, or drop the report.
  Future<QueuedReport?> resolveNotDetected(
    String id, {
    required bool sendAnyway,
  }) async {
    final r = queue.byId(id);
    if (r == null) return null;
    if (!sendAnyway) {
      await queue.remove(r);
      return null;
    }
    await queue.update(
      id,
      (r) => r.copyWith(
        force: true,
        notDetected: false,
        uploadState: UploadState.pending,
      ),
    );
    await flushUploads(onlyId: id, ignoreSchedule: true);
    return queue.byId(id);
  }

  /// Retries pending uploads whose backoff has elapsed.
  Future<void> flushUploads({
    String? onlyId,
    bool ignoreSchedule = false,
  }) async {
    if (_flushing && onlyId == null) return;
    _flushing = true;
    try {
      final now = DateTime.now().toUtc();
      // An explicit retry ("Réessayer") also re-sends a report refused before.
      final candidates = onlyId == null
          ? queue.pending
          : queue.queue.where(
              (r) => r.id == onlyId && !r.isUploaded && !r.notDetected,
            );
      for (final r in candidates) {
        if (!ignoreSchedule &&
            r.nextAttemptAt != null &&
            r.nextAttemptAt!.isAfter(now)) {
          continue;
        }
        await _upload(r);
      }
    } finally {
      _flushing = false;
    }
  }

  Future<void> _upload(QueuedReport r) async {
    await queue.update(
      r.id,
      (r) => r.copyWith(uploadState: UploadState.uploading),
    );
    try {
      final ReportResult res = await api.submitReport(
        draft: r.draft,
        photoPath: r.photoPath,
        force: r.force,
      );
      online = true;
      await queue.update(
        r.id,
        (r) => r.copyWith(
          uploadState: res.awaitingDecision
              ? UploadState.pending
              : UploadState.uploaded,
          notDetected: res.awaitingDecision,
          potholeId: res.potholeId,
          ref: res.ref,
          status: res.status,
          severity: res.score,
          sheetStatus: res.sheetStatus,
          targetOffice: res.targetOffice,
          attempts: r.attempts + 1,
          updatedAt: DateTime.now().toUtc(),
        ),
      );
    } on ApiClientException catch (e) {
      final attempts = r.attempts + 1;
      await queue.update(
        r.id,
        (r) => r.copyWith(
          uploadState: e.retryable ? UploadState.pending : UploadState.failed,
          attempts: attempts,
          nextAttemptAt: DateTime.now().toUtc().add(
            retryDelay(attempts, e.retryAfter),
          ),
          lastError: e.message,
        ),
      );
      if (e.statusCode == null) online = false;
    }
  }

  /// Pulls the server status of this phone's reports and notifies changes.
  Future<void> syncStatus() async {
    final server = await api.fetchMyReports();
    final before = {for (final r in queue.queue) r.id: r.status};
    final local = {for (final r in queue.queue) r.id};
    for (final s in server) {
      if (!local.contains(s.deviceReportId)) continue;
      await queue.update(
        s.deviceReportId,
        (r) => r.copyWith(
          uploadState: UploadState.uploaded,
          potholeId: s.potholeId,
          ref: s.ref,
          status: s.status,
          severity: s.severity,
          sheetStatus: s.sheetStatus,
          targetOffice: s.targetOffice,
          fixedAt: s.fixedAt,
          updatedAt: s.updatedAt,
          locationLabel: s.addressLabel,
        ),
      );
    }
    serverOnly = server
        .where((s) => !local.contains(s.deviceReportId))
        .toList();
    final changes = statusChanges(before, {
      for (final s in server) s.deviceReportId: s.status,
    });
    if (!notify) return;
    for (final (id, status) in changes) {
      final ref = queue.byId(id)?.reference ?? 'Signalement';
      await Notifier.instance.show(
        id.hashCode & 0x7fffffff,
        ref,
        notifyMessages[status]!,
      );
    }
  }

  /// Map area loader with an offline fallback (the last result stays shown).
  Future<void> loadMap({
    required String bbox,
    String? sev,
    String? state,
  }) async {
    try {
      potholes = await api.fetchMap(bbox: bbox, sev: sev, state: state);
      mapOffline = false;
    } catch (e) {
      mapOffline = true;
    }
    notifyListeners();
  }
}
