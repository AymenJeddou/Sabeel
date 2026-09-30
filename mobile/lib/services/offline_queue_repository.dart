import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/queued_report.dart';

/// Holds the not-yet-uploaded reports captured on this device.
///
/// An in-memory list persisted as JSON via [SharedPreferences]. [SabeelData]
/// retries the uploads on every refresh and [remove]s what got through.
class OfflineQueueRepository extends ChangeNotifier {
  OfflineQueueRepository(this._prefs);

  static const _storageKey = 'offline_report_queue';

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

  /// Called once a queued report finally reaches the Core API.
  Future<void> remove(QueuedReport report) async {
    _queue.remove(report);
    await _persist();
    notifyListeners();
  }

  Future<void> _persist() async {
    final encoded = jsonEncode(
      _queue.map((report) => report.toJson()).toList(),
    );
    await _prefs.setString(_storageKey, encoded);
  }
}
