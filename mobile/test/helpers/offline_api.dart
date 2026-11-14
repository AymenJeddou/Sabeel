import 'package:roadscan_mobile/models/remote_report.dart';
import 'package:roadscan_mobile/models/report_draft.dart';
import 'package:roadscan_mobile/models/report_result.dart';
import 'package:roadscan_mobile/services/api_client.dart';

/// Widget tests never touch the network: an empty, always-reachable API.
class OfflineApi extends RoadScanApiClient {
  const OfflineApi();

  @override
  Future<List<MyReport>> fetchMyReports() async => [];

  @override
  Future<List<MapPothole>> fetchMap({
    String? bbox,
    String? sev,
    String? state,
  }) async => [];

  @override
  Future<Map<String, dynamic>> fetchStats() async => {
    'reported': 0,
    'fixed': 0,
  };
}

/// A scriptable fake: [answers] are returned (or thrown) in order by submitReport.
class FakeApi extends OfflineApi {
  FakeApi(this.answers, {this.server = const []});

  final List<Object> answers;
  final List<MyReport> server;
  final calls = <(String, bool)>[];

  @override
  Future<ReportResult> submitReport({
    required ReportDraft draft,
    required String photoPath,
    bool force = false,
  }) async {
    calls.add((draft.deviceReportId, force));
    final next = answers.removeAt(0);
    if (next is Exception) throw next;
    return next as ReportResult;
  }

  @override
  Future<List<MyReport>> fetchMyReports() async => server;
}
