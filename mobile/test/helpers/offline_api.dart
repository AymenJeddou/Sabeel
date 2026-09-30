import 'package:roadscan_mobile/models/remote_report.dart';
import 'package:roadscan_mobile/services/api_client.dart';

/// Widget tests never touch the network: an empty, always-reachable API.
class OfflineApi extends RoadScanApiClient {
  const OfflineApi();

  @override
  Future<List<RemoteReport>> fetchReports() async => [];

  @override
  Future<Map<String, dynamic>> fetchStats() async => {
    'potholes_total': 0,
    'fixed': 0,
  };
}
