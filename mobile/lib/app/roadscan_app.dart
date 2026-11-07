import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../screens/camera_capture_screen.dart' show navigatorKey;
import '../screens/root_shell.dart';
import '../screens/splash_screen.dart';
import '../services/sabeel_data.dart';
import 'brand.dart';

class RoadScanApp extends StatelessWidget {
  const RoadScanApp({super.key, required this.data});

  final SabeelData data;

  @override
  Widget build(BuildContext context) {
    final rounded = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(14),
    );
    return MaterialApp(
      navigatorKey: navigatorKey,
      title: 'Sabeel',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        fontFamily: bodyFont,
        colorScheme: ColorScheme.fromSeed(
          seedColor: sabeelNavy,
          primary: sabeelNavy,
          secondary: sabeelAmber,
          tertiary: sabeelTeal,
          surface: Colors.white,
          onSurface: sabeelInk,
        ),
        scaffoldBackgroundColor: sabeelCream,
        appBarTheme: const AppBarTheme(
          backgroundColor: sabeelCream,
          foregroundColor: sabeelInk,
          elevation: 0,
          scrolledUnderElevation: 0,
          systemOverlayStyle: SystemUiOverlayStyle.dark,
          // No titleTextStyle: the M3 default derives its color from each
          // AppBar's foregroundColor (the camera screen is white-on-black).
        ),
        cardTheme: CardThemeData(
          color: Colors.white,
          elevation: 0,
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
            side: const BorderSide(color: sabeelLine),
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: sabeelNavy,
            foregroundColor: Colors.white,
            minimumSize: const Size(0, 52),
            elevation: 0,
            shape: rounded,
            textStyle: const TextStyle(
              fontFamily: bodyFont,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: sabeelNavy,
            minimumSize: const Size(0, 52),
            side: const BorderSide(color: sabeelNavy, width: 1.2),
            shape: rounded,
            textStyle: const TextStyle(
              fontFamily: bodyFont,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        snackBarTheme: SnackBarThemeData(
          backgroundColor: sabeelInk,
          behavior: SnackBarBehavior.floating,
          shape: rounded,
        ),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: Colors.white,
          surfaceTintColor: Colors.transparent,
          indicatorColor: sabeelNavy.withValues(alpha: 0.10),
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            final selected = states.contains(WidgetState.selected);
            return TextStyle(
              fontFamily: bodyFont,
              fontSize: 12,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
              color: selected ? sabeelNavy : sabeelMuted,
            );
          }),
          iconTheme: WidgetStateProperty.resolveWith((states) {
            final selected = states.contains(WidgetState.selected);
            return IconThemeData(
              size: 24,
              color: selected ? sabeelNavy : sabeelMuted,
            );
          }),
        ),
      ),
      home: SplashScreen(next: (_) => RootShell(data: data)),
    );
  }
}
