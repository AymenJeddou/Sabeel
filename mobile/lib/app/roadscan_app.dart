import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../screens/root_shell.dart';
import '../services/offline_queue_repository.dart';

const roadScanBlue = Color(0xFF1D6FE8);
const roadScanMuted = Color(0xFF6B7280);

class RoadScanApp extends StatelessWidget {
  const RoadScanApp({super.key, required this.queueRepository});

  final OfflineQueueRepository queueRepository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RoadScan',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: roadScanBlue),
        scaffoldBackgroundColor: const Color(0xFFF5F6FA),
        textTheme: GoogleFonts.poppinsTextTheme(),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: Colors.white,
          indicatorColor: Colors.transparent,
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            final selected = states.contains(WidgetState.selected);
            return GoogleFonts.poppins(
              fontSize: 11,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
              color: selected ? roadScanBlue : roadScanMuted,
            );
          }),
          iconTheme: WidgetStateProperty.resolveWith((states) {
            final selected = states.contains(WidgetState.selected);
            return IconThemeData(
              size: 24,
              color: selected ? roadScanBlue : roadScanMuted,
            );
          }),
        ),
      ),
      home: RootShell(queueRepository: queueRepository),
    );
  }
}
