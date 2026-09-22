import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app/roadscan_app.dart';
import 'services/mock_reports.dart';
import 'services/offline_queue_repository.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final queueRepository = OfflineQueueRepository(prefs);
  await queueRepository.load();

  if (kDebugMode && queueRepository.queue.isEmpty) {
    queueRepository.seedMockReports(buildMockReports());
  }

  runApp(RoadScanApp(queueRepository: queueRepository));
}
