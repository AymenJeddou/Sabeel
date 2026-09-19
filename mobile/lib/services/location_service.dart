import 'dart:async';

import 'package:geolocator/geolocator.dart';

class LocationFix {
  final double lat;
  final double lon;
  final double accuracyM;
  final double speedKmh;
  final double directionDeg;

  LocationFix({
    required this.lat,
    required this.lon,
    required this.accuracyM,
    required this.speedKmh,
    required this.directionDeg,
  });
}

class LocationService {
  Future<LocationFix> getCurrentFix() async {
    final permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      final requested = await Geolocator.requestPermission();
      if (requested == LocationPermission.denied || requested == LocationPermission.deniedForever) {
        throw Exception('Location permission is required to submit a report.');
      }
    }

    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled.');
    }

    // Without a time limit, getCurrentPosition waits forever when no GPS fix
    // arrives (indoors, no signal), leaving the submit button stuck. Bound it,
    // fall back to the last known position, and otherwise fail with a clear
    // message the UI can show.
    Position position;
    try {
      position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 10),
        ),
      );
    } on TimeoutException {
      final lastKnown = await Geolocator.getLastKnownPosition();
      if (lastKnown == null) {
        throw Exception(
          'Could not get a GPS fix. Move to open sky (or enable location) and try again.',
        );
      }
      position = lastKnown;
    }

    return LocationFix(
      lat: position.latitude,
      lon: position.longitude,
      accuracyM: position.accuracy,
      speedKmh: (position.speed) * 3.6, // m/s -> km/h
      directionDeg: position.heading,
    );
  }
}
