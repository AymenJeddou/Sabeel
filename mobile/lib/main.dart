import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app/roadscan_app.dart';
import 'services/device.dart';
import 'services/offline_queue_repository.dart';
import 'services/sabeel_data.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final queueRepository = OfflineQueueRepository(prefs);
  await queueRepository.load();

  await initDeviceId(prefs);

  final data = SabeelData(queueRepository);
  // Tabs also refresh on start/switch and pull-to-refresh; this keeps an
  // open screen current (status changes made on the dashboard).
  Timer.periodic(const Duration(seconds: 30), (_) => data.refresh());

  runApp(RoadScanApp(data: data));
}
