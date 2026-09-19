import 'package:flutter/material.dart';

import 'screens/capture_screen.dart';

void main() {
  runApp(const RoadScanApp());
}

class RoadScanApp extends StatelessWidget {
  const RoadScanApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RoadScan',
      theme: ThemeData(colorSchemeSeed: Colors.deepOrange, useMaterial3: true),
      home: const CaptureScreen(),
    );
  }
}
