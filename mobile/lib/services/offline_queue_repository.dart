import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/queued_report.dart';

/// The phone's report store (issue #31): every report this device created,
/// pending or uploaded, persisted as JSON in [SharedPreferences] under the
/// same key as the Sprint 1 offline queue (old entries load as `pending`).
///
/// Mock reports (`mock-` ids, debug builds only) are never persisted.
class OfflineQueueRepository extends ChangeNotifier {
  OfflineQueueRepository(this._prefs);

  static const _storageKey = 'offline_report_queue';

  final SharedPreferences _prefs;
  final List<QueuedReport> _reports = [];

  /// Every stored report, newest first.
  List<QueuedReport> get queue => List.unmodifiable(_reports);

  /// Reports the uploader retries automatically (not those refused for good
  /// or waiting for the citizen's "send anyway" decision).
  List<QueuedReport> get pending => _reports
      .where(
        (r) =>
            !r.isUploaded &&
            !r.notDetected &&
            r.uploadState != UploadState.failed,
      )
      .toList();

  QueuedReport? byId(String id) {
    for (final r in _reports) {
      if (r.id == id) return r;
    }
    return null;
  }

  Future<void> load() async {
    final raw = _prefs.getString(_storageKey);
    if (raw == null || raw.isEmpty) return;
    final decoded = jsonDecode(raw) as List<dynamic>;
    _reports
      ..clear()
      ..addAll(
        decoded.map((e) => QueuedReport.fromJson(e as Map<String, dynamic>)),
      );
    _sort();
    notifyListeners();
  }

  Future<void> add(QueuedReport report) async {
    _reports.removeWhere((r) => r.id == report.id);
    _reports.add(report);
    _sort();
    await _persist();
    notifyListeners();
  }

  /// Replaces one report with `change(old)`; no-op if it is gone (cancelled).
  Future<void> update(
    String id,
    QueuedReport Function(QueuedReport) change,
  ) async {
    final i = _reports.indexWhere((r) => r.id == id);
    if (i < 0) return;
    _reports[i] = change(_reports[i]);
    await _persist();
    notifyListeners();
  }

  Future<void> remove(QueuedReport report) async {
    _reports.removeWhere((r) => r.id == report.id);
    await _persist();
    notifyListeners();
  }

  void _sort() => _reports.sort((a, b) => b.queuedAt.compareTo(a.queuedAt));

  Future<void> _persist() async {
    final keep = _reports.where((r) => !r.id.startsWith('mock-'));
    await _prefs.setString(
      _storageKey,
      jsonEncode(keep.map((r) => r.toJson()).toList()),
    );
  }
}
