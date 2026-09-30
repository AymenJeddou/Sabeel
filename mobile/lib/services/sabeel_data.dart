import 'package:flutter/foundation.dart';

import '../models/remote_report.dart';
import 'api_client.dart';
import 'device.dart';
import 'offline_queue_repository.dart';

/// What the tabs show from the Core API: every pothole in the city (map),
/// this phone's own reports ("Mes Rapports") and the city-wide figures.
/// Refreshed on start, on tab change and on pull-to-refresh.
class SabeelData extends ChangeNotifier {
  SabeelData(this.queue, {this.api = const RoadScanApiClient()});

  final OfflineQueueRepository queue;
  final RoadScanApiClient api;

  List<RemoteReport> potholes = [];
  List<RemoteReport> mine = [];
  Map<String, dynamic>? stats;
  bool online = false;
  bool loading = false;

  Future<void> refresh() async {
    if (loading) return;
    loading = true;
    notifyListeners();
    try {
      await _flushQueue();
      final reports = await api.fetchReports();
      mine = reports.where((r) => r.deviceId == deviceId).toList();
      potholes = latestPerPothole(reports);
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

  /// Retries the uploads that failed while offline; what gets through leaves
  /// the queue. Stops at the first failure and never blocks the refresh.
  Future<void> _flushQueue() async {
    try {
      for (final report in List.of(queue.queue)) {
        await api.submitReport(
          draft: report.draft,
          photoPath: report.photoPath,
        );
        await queue.remove(report);
      }
    } catch (e) {
      debugPrint('[Sabeel] queued upload still failing: $e');
    }
  }
}

/// One entry per physical pothole: the newest report of each cluster
/// (mirrors backend/app/insights.py latest_per_pothole).
List<RemoteReport> latestPerPothole(List<RemoteReport> reports) {
  final seen = <String, RemoteReport>{};
  for (final r in [
    ...reports,
  ]..sort((a, b) => b.createdAt.compareTo(a.createdAt))) {
    seen.putIfAbsent(r.clusterId ?? r.reportId, () => r);
  }
  return seen.values.toList();
}
