import 'dart:async';

import 'package:flutter_compass/flutter_compass.dart';
import 'package:geolocator/geolocator.dart';

/// Thrown when GPS/location data can't be captured (service disabled,
/// permission refused, etc). [message] is plain-language and safe to show
/// directly to the citizen.
class LocationServiceException implements Exception {
  const LocationServiceException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// A single GPS + speed + compass reading, matching the fields the frozen
/// contract needs (docs/Sprint1_Action_Plan.md, Section 4.1).
class LocationSnapshot {
  const LocationSnapshot({
    required this.lat,
    required this.lon,
    required this.gpsAccuracyM,
    required this.speedKmh,
    required this.directionDeg,
    required this.capturedAt,
  });

  final double lat;
  final double lon;
  final double gpsAccuracyM;
  final double speedKmh;

  /// Compass heading, 0-360.
  final double directionDeg;
  final DateTime capturedAt;
}

/// Reads GPS position/speed via [Geolocator] and compass heading via
/// [FlutterCompass]. GPS-derived heading only updates while moving, so the
/// magnetometer compass is used first and the GPS heading is only a
/// fallback for devices without a compass sensor.
class LocationService {
  const LocationService();

  Future<LocationSnapshot> captureSnapshot() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw const LocationServiceException(
        'La localisation est désactivée. Active le GPS pour continuer.',
      );
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied) {
      throw const LocationServiceException(
        'Permission de localisation refusée.',
      );
    }
    if (permission == LocationPermission.deniedForever) {
      throw const LocationServiceException(
        "Permission de localisation refusée définitivement. Active-la dans "
        'les réglages du téléphone.',
      );
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );

    final compassHeading = await _readCompassHeading();
    final directionDeg = compassHeading ?? _normalizeHeading(position.heading);
    final speedKmh = position.speed > 0 ? position.speed * 3.6 : 0.0;

    return LocationSnapshot(
      lat: position.latitude,
      lon: position.longitude,
      gpsAccuracyM: position.accuracy,
      speedKmh: speedKmh,
      directionDeg: directionDeg,
      capturedAt: DateTime.now().toUtc(),
    );
  }

  Future<double?> _readCompassHeading() async {
    final events = FlutterCompass.events;
    if (events == null) {
      return null;
    }
    try {
      final event = await events.first.timeout(const Duration(seconds: 2));
      final heading = event.heading;
      return heading == null ? null : _normalizeHeading(heading);
    } on TimeoutException {
      return null;
    }
  }

  double _normalizeHeading(double heading) {
    final normalized = heading % 360;
    return normalized < 0 ? normalized + 360 : normalized;
  }
}
