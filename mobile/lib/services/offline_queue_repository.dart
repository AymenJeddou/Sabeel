import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/queued_report.dart';

/// Holds the not-yet-uploaded reports captured on this device.
///
/// This is the Sprint 1 sketch of the offline queue: an in-memory list
/// persisted as JSON via [SharedPreferences]. There is no upload, retry, or
/// sync logic yet — that's later-sprint work once WP3's API exists.
class OfflineQueueRepository extends ChangeNotifier {
  OfflineQueueRepository(this._prefs);

  static const _storageKey = 'offline_report_queue';

  /// Ids from [buildMockReports]; these are shown in the UI during
  /// development but never persisted alongside real captures.
  static const _mockIdPrefix = 'mock-';

  final SharedPreferences _prefs;
  final List<QueuedReport> _queue = [];

  List<QueuedReport> get queue => List.unmodifiable(_queue);

  /// Loads any previously queued reports from disk. Call once at startup.
  Future<void> load() async {
    final raw = _prefs.getString(_storageKey);
    if (raw == null || raw.isEmpty) {
      return;
    }
    final decoded = jsonDecode(raw) as List<dynamic>;
    _queue
      ..clear()
      ..addAll(
        decoded.map(
          (entry) => QueuedReport.fromJson(entry as Map<String, dynamic>),
        ),
      );
    notifyListeners();
  }

  Future<void> add(QueuedReport report) async {
    _queue.add(report);
    await _persist();
    notifyListeners();
  }

  /// Adds development sample data to the in-memory queue without persisting
  /// it, so it disappears on the next launch and never mixes into the real
  /// queue written to disk.
  void seedMockReports(List<QueuedReport> reports) {
    _queue.addAll(reports);
    notifyListeners();
  }

  Future<void> _persist() async {
    final encoded = jsonEncode(
      _queue
          .where(
            (report) => !report.draft.deviceReportId.startsWith(_mockIdPrefix),
          )
          .map((report) => report.toJson())
          .toList(),
    );
    await _prefs.setString(_storageKey, encoded);
  }
}
