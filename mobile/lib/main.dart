import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app/roadscan_app.dart';
import 'services/device.dart';
import 'services/notifier.dart';
import 'services/offline_queue_repository.dart';
import 'services/sabeel_data.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final queueRepository = OfflineQueueRepository(prefs);
  await queueRepository.load();

  await initDeviceId(prefs);

  await Notifier.instance.init();

  final data = SabeelData(queueRepository)..watchConnectivity();
  // Uploads and status sync run on start, on tab switch, on pull-to-refresh,
  // when the network comes back, and every 30 s while the app is open.
  Timer.periodic(const Duration(seconds: 30), (_) => data.refresh());

  runApp(RoadScanApp(data: data));
}
